"""Adquisición forense de un recurso web (artículo, PDF, consulta de API).

Para cada URL guarda, en evidencia/<categoria>/<nombre>/<marca de tiempo UTC>/:
  body.<ext>       el cuerpo exacto de la respuesta (bytes sin modificar)
  headers.json     estado HTTP, URL final, cadena de redirecciones y encabezados
                   de cada respuesta (Last-Modified, ETag, Date, Server, ...)
  screenshot.png   (opcional, --screenshot) captura de página completa con Chromium
y registra cada archivo en evidencia/manifest.jsonl con su SHA-256.

Las redirecciones se siguen a mano para conservar los encabezados de cada salto.
Solo hace lecturas (GET), con un User-Agent que se identifica como adquisición forense.

Uso:
    python3 scripts/acquire.py URL --name NOMBRE [--category web|pdf|wayback] [--screenshot]
"""
import argparse
import json
import mimetypes
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

from common import EVID_DIR, USER_AGENT, record, stamp, utc_now


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def fetch(url, max_hops=8):
    opener = urllib.request.build_opener(NoRedirect)
    hops = []
    for _ in range(max_hops):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        t = utc_now()
        try:
            resp = opener.open(req, timeout=60)
            status, headers, body = resp.status, dict(resp.headers.items()), resp.read()
        except urllib.error.HTTPError as e:
            status, headers, body = e.code, dict(e.headers.items()), e.read()
        hops.append({"url": url, "status": status, "requested_utc": t, "headers": headers})
        if status in (301, 302, 303, 307, 308) and "Location" in headers:
            nxt = urllib.parse.urljoin(url, headers["Location"])
            if nxt.startswith("http://"):  # el proxy solo admite HTTPS
                nxt = "https://" + nxt[len("http://"):]
            url = nxt
            continue
        return hops, body
    sys.exit("[x] Demasiadas redirecciones")


def ext_for(headers, url):
    ctype = (headers.get("Content-Type") or "").split(";")[0].strip()
    if url.lower().split("?")[0].endswith(".pdf") or ctype == "application/pdf":
        return ".pdf"
    return mimetypes.guess_extension(ctype) or ".bin"


def screenshot(url, out):
    js = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch();
  const p = await b.newPage({{ viewport: {{ width: 1280, height: 900 }} }});
  await p.goto({json.dumps(url)}, {{ waitUntil: 'load', timeout: 60000 }});
  await p.waitForTimeout(3000);
  await p.screenshot({{ path: {json.dumps(str(out))}, fullPage: true }});
  console.log(await p.title());
  await b.close();
}})();"""
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout or r.stderr).strip()[:200]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--name", required=True)
    ap.add_argument("--category", default="web")
    ap.add_argument("--screenshot", action="store_true")
    a = ap.parse_args()

    outdir = EVID_DIR / a.category / a.name / stamp()
    outdir.mkdir(parents=True, exist_ok=True)
    hops, body = fetch(a.url)
    final = hops[-1]
    meta = {"categoria": a.category, "nombre": a.name, "url_solicitada": a.url,
            "url_final": final["url"], "http_status": final["status"], "adquirido_utc": final["requested_utc"]}
    bfile = outdir / ("body" + ext_for(final["headers"], final["url"]))
    bfile.write_bytes(body)
    hfile = outdir / "headers.json"
    hfile.write_text(json.dumps({"hops": hops}, indent=2, ensure_ascii=False), encoding="utf-8")
    e = record(bfile, meta)
    record(hfile, meta)
    print(f"[+] {a.url} -> {final['status']} {len(body)} bytes sha256={e['sha256'][:16]}…  {bfile}")
    for k in ("Last-Modified", "ETag", "Date", "Server", "Content-Type"):
        for kk, v in final["headers"].items():
            if kk.lower() == k.lower():
                print(f"    {k}: {v}")
    if a.screenshot:
        sfile = outdir / "screenshot.png"
        ok, info = screenshot(final["url"], sfile)
        if ok and sfile.exists():
            record(sfile, dict(meta, tipo="captura_pagina_completa", titulo=info))
            print(f"    captura: {sfile.name} ({info})")
        else:
            print(f"    [!] sin captura: {info}")


if __name__ == "__main__":
    main()
