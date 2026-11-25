"""Fase 2 - Análisis forense de metadatos y estructura de los PDF adquiridos.

Para cada PDF en evidencia/pdf/<nombre>/<marca>/body.pdf extrae:
  * encabezados HTTP de la descarga (Last-Modified, ETag) y si el MD5 coincide con el ETag
    (en S3, el ETag de un objeto subido en una sola parte es el MD5 del contenido);
  * diccionario Info y XMP (exiftool): CreateDate, ModifyDate, MetadataDate, Creator,
    Producer, SourceModified, XMPToolkit, DocumentID / InstanceID;
  * /ID del trailer: si ID[0] != ID[1], el archivo se volvió a guardar después de creado;
  * estructura: versión, linealización, cantidad de startxref / %%EOF, advertencias de qpdf
    (p. ej. tablas de hint inconsistentes = bytes modificados después de linealizar);
  * fuentes y páginas.

Salida: datos/metadatos_pdf.csv, datos/metadatos_pdf.json y datos/pdf_<nombre>/ (volcados).

Uso:
    python3 scripts/analyze_pdf.py
"""
import csv
import hashlib
import json
import re
import subprocess

import pikepdf

from common import BASE_DIR, DATA_DIR, EVID_DIR


def run(cmd):
    # Se ejecuta desde la carpeta del ejercicio con rutas relativas, para que las salidas no
    # contengan rutas absolutas del equipo donde se corrió el análisis.
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
    return (r.stdout or "") + (r.stderr or "")


def latest(d):
    subs = sorted(p for p in d.iterdir() if p.is_dir())
    return subs[-1] if subs else None


def analyze(name, folder):
    pdf = (folder / "body.pdf").relative_to(BASE_DIR)
    hdr = json.loads((folder / "headers.json").read_text(encoding="utf-8"))["hops"][-1]
    h = {k.lower(): v for k, v in hdr["headers"].items()}
    raw = (BASE_DIR / pdf).read_bytes()
    md5 = hashlib.md5(raw).hexdigest()
    etag = h.get("etag", "").strip('"')
    ex = json.loads(run(["exiftool", "-j", "-a", "-G1", "-s", str(pdf)]))[0]

    def g(*keys):
        for k in keys:
            if k in ex and str(ex[k]).strip():
                return str(ex[k])
        return ""

    out = DATA_DIR / f"pdf_{name}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "exiftool.json").write_text(json.dumps(ex, indent=2, ensure_ascii=False), encoding="utf-8")
    qcheck = run(["qpdf", "--check", str(pdf)])
    (out / "qpdf_check.txt").write_text(qcheck, encoding="utf-8")
    (out / "pdffonts.txt").write_text(run(["pdffonts", str(pdf)]), encoding="utf-8")
    (out / "pdfinfo.txt").write_text(run(["pdfinfo", "-isodates", str(pdf)]), encoding="utf-8")
    (out / "texto.txt").write_text(run(["pdftotext", "-layout", str(pdf), "-"]), encoding="utf-8")

    with pikepdf.open(BASE_DIR / pdf) as p:
        ids = [bytes(x).hex() for x in p.trailer.get("/ID", [])]
        npages = len(p.pages)
        xmp_raw = ""
        if "/Metadata" in p.Root:
            xmp_raw = bytes(p.Root.Metadata.read_bytes()).decode("utf-8", "replace")
    (out / "xmp.xml").write_text(xmp_raw, encoding="utf-8")
    hist = re.findall(r"<stEvt:when>([^<]+)</stEvt:when>", xmp_raw)

    warnings = [l for l in qcheck.splitlines() if l.startswith("WARNING")]
    return {
        "nombre": name,
        "url": hdr["url"],
        "http_last_modified": h.get("last-modified", ""),
        "bytes": len(raw),
        "md5_igual_etag": md5 == etag,
        "pdf_version": g("PDF:PDFVersion"),
        "linealizado": g("PDF:Linearized"),
        "creator": g("PDF:Creator", "XMP-xmp:CreatorTool"),
        "producer": g("PDF:Producer", "XMP-pdf:Producer"),
        "create_date": g("PDF:CreateDate", "XMP-xmp:CreateDate"),
        "modify_date": g("PDF:ModifyDate", "XMP-xmp:ModifyDate"),
        "metadata_date": g("XMP-xmp:MetadataDate"),
        "source_modified": g("PDF:SourceModified", "XMP-pdfx:SourceModified"),
        "xmp_toolkit": g("XMP-x:XMPToolkit"),
        "author": g("PDF:Author", "XMP-dc:Creator"),
        "document_id": g("XMP-xmpMM:DocumentID"),
        "instance_id": g("XMP-xmpMM:InstanceID"),
        "historial_xmp": ";".join(hist),
        "trailer_id_iguales": (len(ids) == 2 and ids[0] == ids[1]),
        "startxref": raw.count(b"startxref"),
        "eof": raw.count(b"%%EOF"),
        "paginas": npages,
        "qpdf_advertencias": len(warnings),
        "qpdf_hint_inconsistente": any("hint" in w.lower() or "offset" in w.lower() for w in warnings),
    }


def main():
    rows = []
    for d in sorted((EVID_DIR / "pdf").iterdir()):
        f = latest(d)
        if f and (f / "body.pdf").exists():
            rows.append(analyze(d.name, f))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / "metadatos_pdf.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (DATA_DIR / "metadatos_pdf.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    for r in rows:
        print(f"{r['nombre']:<14} {r['create_date'][:19]:<20} {r['modify_date'][:19]:<20} "
              f"{r['producer'][:30]:<30} {r['creator'][:30]:<30} LM={r['http_last_modified'][5:25]} "
              f"IDs={'=' if r['trailer_id_iguales'] else '≠'} hintErr={r['qpdf_hint_inconsistente']} md5=etag:{r['md5_igual_etag']}")


if __name__ == "__main__":
    main()
