"""Fase 2 - Adquisición del historial completo vía Etherscan API v2.

Para cada red y dirección descarga:
  txlist          transacciones normales (entrantes y salientes)
  txlistinternal  transferencias internas generadas por contratos
  tokentx         transferencias ERC-20
  tokennfttx      transferencias ERC-721
  token1155tx     transferencias ERC-1155
  balance         saldo nativo actual

Reproducibilidad: al inicio se toma el número de bloque actual de cada red
(SNAPSHOT) y todas las consultas usan endblock=SNAPSHOT. Re-ejecutar con
--snapshot <bloque> devuelve exactamente el mismo conjunto de datos.

Cada página cruda queda en evidencia/raw/fetch/... con su SHA-256 en el
manifiesto. El consolidado (sin duplicados) va a datos/consolidado/.

Requiere: variable de entorno ETHERSCAN_API_KEY (cuenta gratuita en
etherscan.io -> API Keys). NUNCA la pegues en archivos del repo.

Uso:
    python3 scripts/fetch.py --chains 1
    python3 scripts/fetch.py --chains 1,137 --address 0x... --address 0x...
"""
import argparse
import json
import os
import sys
import time
import urllib.parse

from common import ADDRESSES, DATA_DIR, http_request, preserve, redact, sleep_rate, stamp, utc_now

ETHERSCAN = "https://api.etherscan.io/v2/api"
ACTIONS = ["txlist", "txlistinternal", "tokentx", "tokennfttx", "token1155tx"]
PAGE_SIZE = 1000
RATE_MSGS = ("rate limit", "max calls", "too many")


def call(params, key, rel_dir, label, meta):
    """Llama a Etherscan con reintentos ante rate limit. Preserva cada respuesta."""
    q = dict(params, apikey=key)
    url = ETHERSCAN + "?" + urllib.parse.urlencode(q)
    for attempt in range(5):
        ts = utc_now()
        status, raw = http_request(url)
        preserve(raw, f"{rel_dir}/{label}_{stamp()}.json",
                 dict(meta, url=redact(url), ts_utc=ts, http_status=status, attempt=attempt))
        sleep_rate()
        try:
            j = json.loads(raw)
        except Exception:
            j = {"status": "0", "message": "respuesta no JSON", "result": raw[:200].decode("latin1")}
        res = j.get("result")
        if isinstance(res, str) and any(m in res.lower() for m in RATE_MSGS):
            time.sleep(2 * (attempt + 1))
            continue
        return j
    return j


def snapshot_block(chainid, key, name):
    j = call({"chainid": chainid, "module": "proxy", "action": "eth_blockNumber"}, key,
             f"fetch/{name}/_snapshot", "eth_blockNumber",
             {"phase": "fetch", "chainid": chainid, "chain": name, "action": "eth_blockNumber"})
    res = j.get("result")
    if isinstance(res, str) and res.startswith("0x"):
        return int(res, 16)
    sys.exit(f"[x] No se pudo obtener el bloque actual de chainid {chainid}: {j}")


def fetch_action(chainid, name, address, action, key, snapshot):
    """Pagina por rango de bloques (evita el tope de 10.000 resultados de Etherscan)."""
    items, seen = [], set()
    start, n = 0, 0
    meta = {"phase": "fetch", "chainid": chainid, "chain": name, "address": address,
            "action": action, "snapshot_block": snapshot}
    while True:
        params = {"chainid": chainid, "module": "account", "action": action, "address": address,
                  "startblock": start, "endblock": snapshot, "page": 1, "offset": PAGE_SIZE,
                  "sort": "asc"}
        j = call(params, key, f"fetch/{name}/{address}/{action}", f"p{n:03d}_from{start}",
                 dict(meta, startblock=start))
        res = j.get("result")
        if not isinstance(res, list):
            print(f"    [!] {action}: {j.get('message')} -> {str(res)[:120]}")
            return items, f"error: {j.get('message')} / {str(res)[:120]}"
        new = 0
        for it in res:
            k = json.dumps(it, sort_keys=True)
            if k not in seen:
                seen.add(k)
                items.append(it)
                new += 1
        n += 1
        if len(res) < PAGE_SIZE:
            return items, "ok"
        last = int(res[-1]["blockNumber"])
        if last == start and new == 0:
            print(f"    [!] {action}: más de {PAGE_SIZE} eventos en el bloque {last}; revisar a mano")
            return items, "truncado"
        start = last  # inclusivo; los duplicados se descartan arriba


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", default="1", help="chainids separados por coma (ver sweep.py)")
    ap.add_argument("--address", action="append", help="dirección (repetible). Default: las del caso")
    ap.add_argument("--snapshot", type=int, help="bloque fijo (solo con una red)")
    args = ap.parse_args()

    key = os.environ.get("ETHERSCAN_API_KEY", "").strip()
    if not key:
        sys.exit("[x] Definí ETHERSCAN_API_KEY en el entorno antes de correr este script.")
    addrs = [a.lower() for a in (args.address or ADDRESSES.values())]
    chains = [int(c) for c in args.chains.split(",")]

    outdir = DATA_DIR / "consolidado"
    outdir.mkdir(parents=True, exist_ok=True)
    resumen = []
    for chainid in chains:
        name = str(chainid)
        snap = args.snapshot or snapshot_block(chainid, key, name)
        print(f"[+] chainid {chainid}: snapshot en bloque {snap}")
        for addr in addrs:
            print(f"  [*] {addr}")
            bal = call({"chainid": chainid, "module": "account", "action": "balance",
                        "address": addr, "tag": "latest"}, key,
                       f"fetch/{name}/{addr}/balance", "balance",
                       {"phase": "fetch", "chainid": chainid, "address": addr, "action": "balance"})
            for action in ACTIONS:
                items, estado = fetch_action(chainid, name, addr, action, key, snap)
                out = outdir / f"{chainid}_{addr}_{action}.json"
                out.write_text(json.dumps({
                    "chainid": chainid, "address": addr, "action": action,
                    "snapshot_block": snap, "estado": estado, "generado_utc": utc_now(),
                    "cantidad": len(items), "items": items,
                }, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"    {action:15s} {len(items):6d} registros ({estado})")
                resumen.append((chainid, addr, action, len(items), estado))
            print(f"    saldo actual (wei): {bal.get('result')}")
    print("\n[+] Listo. Consolidado en", outdir)
    print("[+] Siguiente paso: python3 scripts/hash_evidence.py")


if __name__ == "__main__":
    main()
