"""Fase 1 - Barrido multired de las direcciones del caso.

Una misma dirección EVM existe en todas las redes compatibles. Este script
determina en cuáles hay actividad, sin interactuar con las wallets (solo
consultas de lectura):

  * Por RPC público (no requiere API key): eth_getCode (¿EOA o contrato?),
    eth_getTransactionCount (nonce = cantidad de tx ENVIADAS) y eth_getBalance.
  * Si existe la variable ETHERSCAN_API_KEY: además consulta Etherscan v2 si
    hay al menos una tx normal / interna / de token (detecta wallets que solo
    RECIBIERON fondos, cuyo nonce es 0).

Toda respuesta cruda queda en evidencia/raw/sweep/ y en el manifiesto.
Salida resumida: datos/barrido_redes.csv

Uso:
    python3 scripts/sweep.py
"""
import csv
import json
import os
import urllib.parse

from common import ADDRESSES, DATA_DIR, http_request, preserve, redact, sleep_rate, stamp, utc_now

# chainid, nombre, RPC público
CHAINS = [
    (1, "ethereum", "https://ethereum-rpc.publicnode.com"),
    (11155111, "sepolia", "https://ethereum-sepolia-rpc.publicnode.com"),
    (17000, "holesky", "https://ethereum-holesky-rpc.publicnode.com"),
    (56, "bsc", "https://bsc-rpc.publicnode.com"),
    (137, "polygon", "https://polygon-bor-rpc.publicnode.com"),
    (42161, "arbitrum", "https://arbitrum-one-rpc.publicnode.com"),
    (10, "optimism", "https://optimism-rpc.publicnode.com"),
    (8453, "base", "https://base-rpc.publicnode.com"),
    (43114, "avalanche", "https://avalanche-c-chain-rpc.publicnode.com"),
    (59144, "linea", "https://linea-rpc.publicnode.com"),
    (534352, "scroll", "https://scroll-rpc.publicnode.com"),
]

ETHERSCAN = "https://api.etherscan.io/v2/api"


def rpc(chainid, name, url, method, params, address):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ts = utc_now()
    status, raw = http_request(url, payload)
    preserve(raw, f"sweep/{name}/{address}/{method}_{stamp()}.json", {
        "phase": "sweep", "source": "rpc", "chainid": chainid, "chain": name,
        "address": address, "method": method, "params": params,
        "url": url, "ts_utc": ts, "http_status": status,
    })
    try:
        return json.loads(raw).get("result")
    except Exception:
        return None


def es_has_activity(chainid, name, address, action, key):
    q = {"chainid": chainid, "module": "account", "action": action, "address": address,
         "startblock": 0, "endblock": 99999999, "page": 1, "offset": 1, "sort": "asc", "apikey": key}
    url = ETHERSCAN + "?" + urllib.parse.urlencode(q)
    ts = utc_now()
    status, raw = http_request(url)
    preserve(raw, f"sweep/{name}/{address}/etherscan_{action}_{stamp()}.json", {
        "phase": "sweep", "source": "etherscan_v2", "chainid": chainid, "chain": name,
        "address": address, "action": action, "url": redact(url), "ts_utc": ts,
        "http_status": status,
    })
    sleep_rate()
    try:
        j = json.loads(raw)
    except Exception:
        return "error"
    if isinstance(j.get("result"), list):
        return "SI" if j["result"] else "no"
    return f"error: {j.get('message')} / {str(j.get('result'))[:80]}"


def main():
    key = os.environ.get("ETHERSCAN_API_KEY", "").strip()
    if not key:
        print("[!] ETHERSCAN_API_KEY no definida: solo se hará el barrido por RPC.\n")
    rows = []
    for chainid, name, url in CHAINS:
        for role, addr in ADDRESSES.items():
            code = rpc(chainid, name, url, "eth_getCode", [addr, "latest"], addr)
            nonce = rpc(chainid, name, url, "eth_getTransactionCount", [addr, "latest"], addr)
            bal = rpc(chainid, name, url, "eth_getBalance", [addr, "latest"], addr)
            row = {
                "chainid": chainid, "red": name, "rol": role, "direccion": addr,
                "tipo": ("error" if code is None else "EOA" if code in ("0x", "0x0") else "CONTRATO"),
                "nonce_tx_enviadas": int(nonce, 16) if isinstance(nonce, str) else "error",
                "saldo_nativo": int(bal, 16) / 1e18 if isinstance(bal, str) else "error",
            }
            if key:
                for action in ("txlist", "txlistinternal", "tokentx"):
                    row[f"etherscan_{action}"] = es_has_activity(chainid, name, addr, action, key)
            rows.append(row)
            print("  ".join(f"{k}={v}" for k, v in row.items() if k != "direccion"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / "barrido_redes.csv"
    fields = list(rows[0])
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\n[+] Resumen guardado en {out}")
    print("[+] Redes con actividad (nonce>0, saldo>0 o tx en Etherscan):")
    for r in rows:
        act = (isinstance(r["nonce_tx_enviadas"], int) and r["nonce_tx_enviadas"] > 0) or \
              (isinstance(r["saldo_nativo"], float) and r["saldo_nativo"] > 0) or \
              any(r.get(f"etherscan_{a}") == "SI" for a in ("txlist", "txlistinternal", "tokentx"))
        if act:
            print(f"    - {r['red']} (chainid {r['chainid']}): {r['rol']}")


if __name__ == "__main__":
    main()
