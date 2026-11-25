"""Análisis de la actividad en BSC a partir de los CSV exportados de bscscan.com.

La API gratuita de Etherscan v2 no cubre BSC, por lo que la evidencia son las
exportaciones CSV del explorador (evidencia/bsc/*.csv, hasheadas). Se aplica el
mismo criterio que analyze.py: solo cuentan USDT/USDC oficiales con valor >= 1 y
BNB con valor >= 0,0001; el resto es spoofing / polvo.

Salida: datos/analisis_bsc/{movimientos.csv, contrapartes.csv, resumen.json}

Uso:
    python3 scripts/analyze_bsc.py
"""
import collections
import csv
import datetime as dt
import json

from common import ADDRESSES, BASE_DIR, DATA_DIR

A = ADDRESSES["estafador"]
EV = BASE_DIR / "evidencia" / "bsc"
OUT = DATA_DIR / "analisis_bsc"
OFFICIAL = {
    "0x55d398326f99059ff775485246999027b3197955": "USDT",   # Binance-Peg BSC-USD
    "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d": "USDC",   # Binance-Peg USDC
}


def num(s):
    return float((s or "0").replace(",", "") or 0)


def read(name):
    with (EV / name).open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main():
    tx, tt = read("bsc_txlist.csv"), read("bsc_tokentx.csv")
    sent = {t["Transaction Hash"] for t in tx if t["From"].lower() == A}
    moves, spoof = [], collections.Counter()
    for t in tx:
        v_in, v_out = num(t["Value_IN(BNB)"]), num(t["Value_OUT(BNB)"])
        if t.get("Status") or max(v_in, v_out) < 0.0001:
            continue
        d = "ENTRADA" if v_in > 0 else "SALIDA"
        moves.append(dict(fecha_utc=t["DateTime (UTC)"], ts=int(t["UnixTimestamp"]), hash=t["Transaction Hash"],
                          direccion=d, activo="BNB", monto=v_in or v_out,
                          contraparte=(t["From"] if d == "ENTRADA" else t["To"]).lower(),
                          firmada=t["Transaction Hash"] in sent))
    for t in tt:
        c = t["ContractAddress"].lower()
        v = num(t["TokenValue"])
        if c not in OFFICIAL or v < 1:
            spoof[(c, t["TokenSymbol"])] += 1
            continue
        frm, to = t["From"].lower(), t["To"].lower()
        d = "ENTRADA" if to == A else "SALIDA" if frm == A else None
        if not d:
            continue
        moves.append(dict(fecha_utc=t["DateTime (UTC)"], ts=int(t["UnixTimestamp"]), hash=t["Transaction Hash"],
                          direccion=d, activo=OFFICIAL[c], monto=v,
                          contraparte=frm if d == "ENTRADA" else to, firmada=t["Transaction Hash"] in sent))
    moves.sort(key=lambda m: m["ts"])

    vol = collections.defaultdict(lambda: [0.0, 0.0])
    cp = collections.defaultdict(lambda: collections.defaultdict(float))
    for m in moves:
        vol[m["activo"]][0 if m["direccion"] == "ENTRADA" else 1] += m["monto"]
        cp[(m["contraparte"], m["direccion"])][m["activo"]] += m["monto"]
        cp[(m["contraparte"], m["direccion"])]["n"] += 1

    # Permanencia FIFO del USDT
    q, samples = collections.deque(), []
    for m in moves:
        if m["activo"] != "USDT":
            continue
        if m["direccion"] == "ENTRADA":
            q.append([m["ts"], m["monto"]])
        else:
            need = m["monto"]
            while need > 1e-9 and q:
                take = min(need, q[0][1])
                samples.append(((m["ts"] - q[0][0]) / 3600, take))
                q[0][1] -= take
                need -= take
                if q[0][1] <= 1e-9:
                    q.popleft()
    samples.sort()
    total = sum(w for _, w in samples) or 1
    acc, med = 0, None
    for h, w in samples:
        acc += w
        if med is None and acc >= total / 2:
            med = h

    # Cruce con las contrapartes ya analizadas en Ethereum / Polygon
    known = set()
    for d in ("analisis", "analisis_0xbf7aa1d5"):
        p = DATA_DIR / d / "movimientos.csv"
        if p.exists():
            known |= {r["contraparte"] for r in csv.DictReader(p.open(encoding="utf-8"))}
    known |= {ADDRESSES["victima"], "0xbf7aa1d5e95eb35813d03eacc5c4e9fa3ec6f9ab"}

    rows = []
    for (a, d), vals in sorted(cp.items(), key=lambda x: -x[1].get("USDT", 0)):
        rows.append(dict(contraparte=a, direccion=d, n=int(vals["n"]), usdt=round(vals.get("USDT", 0), 2),
                         bnb=round(vals.get("BNB", 0), 6), tambien_en_eth_o_polygon=a in known))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "movimientos.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(moves[0]))
        w.writeheader()
        w.writerows(moves)
    with (OUT / "contrapartes.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    res = {
        "fuente": "evidencia/bsc/*.csv (exportación de bscscan.com)",
        "primera_utc": moves[0]["fecha_utc"], "ultima_utc": moves[-1]["fecha_utc"],
        "tx_normales": len(tx), "tx_firmadas": len(sent),
        "volumen": {k: {"entrada": round(a, 2), "salida": round(b, 2)} for k, (a, b) in vol.items()},
        "remitentes_unicos": len({m["contraparte"] for m in moves if m["direccion"] == "ENTRADA"}),
        "destinatarios_unicos": len({m["contraparte"] for m in moves if m["direccion"] == "SALIDA"}),
        "permanencia_mediana_usdt_h": round(med or 0, 2),
        "pct_usdt_salido_24h": round(100 * sum(w for h, w in samples if h <= 24) / total, 1),
        "eventos_tokens_falsos_o_polvo": sum(spoof.values()),
        "contratos_falsos": len({c for c, _ in spoof}),
        "contrapartes_compartidas_con_eth_polygon": [r for r in rows if r["tambien_en_eth_o_polygon"]],
    }
    (OUT / "resumen.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
