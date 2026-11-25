"""Fases 3, 4, 5 y 7 - Análisis del historial descargado por fetch.py.

Lee datos/consolidado/*.json (no toca evidencia/) y genera en datos/analisis/:

  movimientos.csv        libro de movimientos REALES (nativo, interno, stablecoins y
                         tokens movidos por tx firmadas por la wallet analizada)
  contrapartes.csv       totales por contraparte (entradas/salidas, primera/última vez)
  victima_estafador.csv  todas las transferencias entre víctima y presunto estafador
  envenenamiento.csv     direcciones "look-alike" (address poisoning) detectadas
  tokens_falsos.csv      contratos de tokens falsos / spam que emiten eventos espurios
  saldo_diario.csv       saldo acumulado por activo y día (reconstruido)
  trazabilidad_fondos_victima.csv  destino FIFO de los fondos llegados desde la víctima
  resumen.json           métricas clave (múltiples remitentes, permanencia, volúmenes)

Criterio forense para separar ruido de movimientos reales:
  * Un token "oficial" (USDT, USDC, ...) con valor > 0 entrante es dinero real.
  * Una SALIDA solo es real si la tx fue firmada por la wallet analizada o es un
    token oficial (que no puede moverse sin firma/aprobación del titular).
  * Los eventos de tokens no oficiales que la wallet NO firmó son spoofing:
    cualquiera puede desplegar un contrato que emita Transfer(from=víctima, ...).
  * Transferencias de valor 0 o "polvo" desde direcciones que imitan el prefijo y
    sufijo de una contraparte real son address poisoning.

Uso:
    python3 scripts/analyze.py [--address 0x...] [--chains 1,137]
"""
import argparse
import bisect
import collections
import csv
import datetime as dt
import json
import statistics

from common import ADDRESSES, DATA_DIR

# Contratos oficiales (verificados) de activos de valor, por red.
OFFICIAL_TOKENS = {
    1: {
        "0xdac17f958d2ee523a2206206994597c13d831ec7": "USDT",
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH",
        "0x6b175474e89094c44da98b954eedeac495271d0f": "DAI",
        "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0": "MATIC",
    },
    137: {
        "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359": "USDC",
        "0x2791bca1f2de4661ed88a30c99a7a9449aa84174": "USDC.e",
        "0xc2132d05d31c914a87c6611c10748aeb04b58e8f": "USDT0",
        "0x7ceb23fd6bc0add59e62ac25578270cff1b9f619": "WETH",
    },
}
NATIVE = {1: "ETH", 137: "POL", 56: "BNB"}
STABLES = {"USDT", "USDC", "USDC.e", "USDT0", "DAI"}

# Etiquetas públicas conocidas (verificables en el explorador) + roles del caso.
KNOWN_LABELS = {
    "0x111111125421ca6dc452d289314280a0f8842a65": "1inch: Aggregation Router V6 (DEX/swap)",
    "0x9696f59e4d72e237be84ffd425dcad154bf96976": "Binance: hot wallet (etiqueta MetaSleuth)",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance: hot wallet (etiqueta MetaSleuth)",
    "0xa4d65fd5017bb20904603f0a174bbbd04f81757c": "MultiSig BitGo (etiqueta MetaSleuth)",
    "0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae": "LI.FI Diamond (agregador swap/bridge)",
    "0xdac17f958d2ee523a2206206994597c13d831ec7": "Tether: USDT",
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "Circle: USDC",
    ADDRESSES["victima"]: "Denunciante (wallet operativa de plataforma, ver H-04)",
    "0xb924e19c9ef3b197ea004d3a1336ca7b59d7e4e2": "Binance: dirección de depósito (etiqueta Etherscan)",
    "0x5e3c322ccd5095e7e5cfa3ff1655cef39c4fcb12": "Sin etiqueta; fondeada por WestWallet 1 (posible depósito custodial)",
    "0xca068d3cffbf879e3041fa3e1d29f68d18bb4f8a": "Financiador del estafador (fondeado por la plataforma)",
    "0x4cb1b943e5e71b97dd2b3ab6630654ea079e1053": "Wallet hermana (fondeada por el financiador y por el estafador)",
    ADDRESSES["estafador"]: "Presunto estafador",
}

DUST_USD = 1.0  # transferencias de stablecoin menores a esto se consideran "polvo"
DUST_NATIVE = {1: 0.0001, 137: 0.01}  # idem para la moneda nativa (ETH / POL)


def ts(x):
    return dt.datetime.fromtimestamp(int(x), dt.timezone.utc)


def iso(x):
    return ts(x).strftime("%Y-%m-%d %H:%M:%S")


def load(chain, addr, action):
    p = DATA_DIR / "consolidado" / f"{chain}_{addr}_{action}.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))["items"]


def lookalike_key(a):
    a = a.lower()[2:]
    return a[:4] + "…" + a[-4:]


def build(chain, A):
    tx, itx, tt = load(chain, A, "txlist"), load(chain, A, "txlistinternal"), load(chain, A, "tokentx")
    sent = {t["hash"] for t in tx if t["from"] == A}
    official = OFFICIAL_TOKENS.get(chain, {})
    nat = NATIVE.get(chain, "NATIVE")
    moves, spoof = [], collections.Counter()
    spoof_meta = {}

    for t in tx:
        v = int(t["value"])
        if v == 0 or t["isError"] != "0":
            continue
        moves.append(dict(chain=chain, ts=int(t["timeStamp"]), hash=t["hash"], tipo="nativo",
                          activo=nat, monto=v / 1e18, desde=t["from"], hacia=t["to"],
                          firmada=t["from"] == A, metodo=t.get("functionName", "")[:40]))
    for t in itx:
        v = int(t["value"])
        if v == 0 or t.get("isError", "0") != "0":
            continue
        moves.append(dict(chain=chain, ts=int(t["timeStamp"]), hash=t["hash"], tipo="interna",
                          activo=nat, monto=v / 1e18, desde=t["from"], hacia=t["to"],
                          firmada=t["hash"] in sent, metodo="internal"))
    for t in tt:
        v = int(t["value"])
        dec = int(t["tokenDecimal"] or 0)
        c = t["contractAddress"]
        is_off = c in official
        signed = t["hash"] in sent
        if is_off and v > 0:
            sym = official[c]
        elif signed and v > 0:
            sym = t["tokenSymbol"]  # token no oficial pero movido por la propia wallet
        else:
            spoof[c] += 1
            spoof_meta[c] = (t["tokenSymbol"], t["tokenName"])
            continue
        moves.append(dict(chain=chain, ts=int(t["timeStamp"]), hash=t["hash"], tipo="token",
                          activo=sym, monto=v / 10 ** dec, desde=t["from"], hacia=t["to"],
                          firmada=signed, metodo="transfer", contrato=c))

    for m in moves:
        m["direccion"] = "ENTRADA" if m["hacia"] == A else "SALIDA" if m["desde"] == A else "OTRA"
        m["contraparte"] = m["desde"] if m["direccion"] == "ENTRADA" else m["hacia"]
        m["polvo"] = (m["activo"] in STABLES and m["monto"] < DUST_USD) or \
                     (m["activo"] == nat and m["monto"] < DUST_NATIVE.get(chain, 0))
    moves.sort(key=lambda m: (m["ts"], m["hash"]))

    # Todas las direcciones que aparecen (incluido ruido) para detectar look-alikes.
    every = collections.Counter()
    for t in tx + itx + tt:
        for k in ("from", "to"):
            if t[k] and t[k] != A:
                every[t[k]] += 1
    return moves, spoof, spoof_meta, every, tx


def poisoning(moves, every, A):
    """Direcciones que imitan prefijo/sufijo de contrapartes reales (o de la propia wallet)."""
    genuine = {m["contraparte"] for m in moves
               if (m["direccion"] == "SALIDA" and m["firmada"]) or (not m["polvo"] and m["direccion"] == "ENTRADA")}
    genuine.add(A)
    by_key = collections.defaultdict(set)
    for g in genuine:
        by_key[lookalike_key(g)].add(g)
    rows = []
    for addr, n in every.items():
        k = lookalike_key(addr)
        targets = by_key.get(k, set()) - {addr}
        if targets and addr not in genuine:
            rows.append(dict(direccion_imitadora=addr, imita_a=";".join(sorted(targets)),
                             patron=k, eventos=n))
    # ¿La wallet analizada envió fondos reales a una imitadora? (cayó en el envenenamiento)
    imitadoras = {r["direccion_imitadora"] for r in rows}
    caidas = [m for m in moves if m["direccion"] == "SALIDA" and m["firmada"] and m["contraparte"] in imitadoras]
    return rows, caidas


def dwell_fifo(moves, A):
    """Tiempo de permanencia (FIFO) por activo: cuánto tarda cada unidad entrante en salir."""
    res = {}
    by_asset = collections.defaultdict(list)
    for m in moves:
        if m["direccion"] in ("ENTRADA", "SALIDA") and not m["polvo"]:
            by_asset[(m["chain"], m["activo"])].append(m)
    for key, ms in by_asset.items():
        q = collections.deque()  # [ts, restante]
        samples = []  # (horas, monto)
        for m in ms:
            if m["direccion"] == "ENTRADA":
                q.append([m["ts"], m["monto"]])
            else:
                need = m["monto"]
                while need > 1e-12 and q:
                    take = min(need, q[0][1])
                    samples.append(((m["ts"] - q[0][0]) / 3600, take))
                    q[0][1] -= take
                    need -= take
                    if q[0][1] <= 1e-12:
                        q.popleft()
        if not samples:
            continue
        total = sum(w for _, w in samples)
        srt = sorted(samples)
        acc, pct = 0, {}
        for h, w in srt:
            acc += w
            for p in (50, 75, 90):
                if p not in pct and acc >= total * p / 100:
                    pct[p] = h
        res[f"{key[0]}:{key[1]}"] = dict(
            monto_rastreado=round(total, 4),
            permanencia_mediana_h=round(pct.get(50, 0), 2),
            p75_h=round(pct.get(75, 0), 2), p90_h=round(pct.get(90, 0), 2),
            pct_salido_en_24h=round(100 * sum(w for h, w in samples if h <= 24) / total, 1),
        )
    return res


def taint_fifo(moves, source):
    """Atribución FIFO: a qué destinos fueron los fondos que entraron desde `source`.

    Cada salida consume las entradas más antiguas del mismo activo; la porción que
    proviene de `source` se imputa al destino de esa salida. Es una heurística estándar
    de trazabilidad (FIFO taint), no una certeza: el dinero es fungible.
    """
    dest = collections.defaultdict(lambda: collections.defaultdict(float))
    detalle = []
    by_asset = collections.defaultdict(list)
    for m in moves:
        if m["direccion"] in ("ENTRADA", "SALIDA") and not m["polvo"]:
            by_asset[(m["chain"], m["activo"])].append(m)
    for (chain, act), ms in by_asset.items():
        q = collections.deque()  # [ts, restante, origen]
        for m in ms:
            if m["direccion"] == "ENTRADA":
                q.append([m["ts"], m["monto"], m["contraparte"]])
                continue
            need = m["monto"]
            while need > 1e-12 and q:
                take = min(need, q[0][1])
                if q[0][2] == source:
                    dest[f"{chain}:{act}"][m["contraparte"]] += take
                    detalle.append(dict(chain=chain, activo=act, monto=round(take, 6),
                                        entrada_utc=iso(q[0][0]), salida_utc=m["fecha_utc"] if "fecha_utc" in m else iso(m["ts"]),
                                        horas=round((m["ts"] - q[0][0]) / 3600, 2), destino=m["contraparte"],
                                        hash_salida=m["hash"]))
                q[0][1] -= take
                need -= take
                if q[0][1] <= 1e-12:
                    q.popleft()
    return dest, detalle


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    fields = fields or (list(rows[0]) if rows else ["sin_datos"])
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", default=ADDRESSES["estafador"])
    ap.add_argument("--chains", default="1,137")
    ap.add_argument("--source", default=ADDRESSES["victima"],
                    help="origen cuyos fondos se rastrean (FIFO) y cuyas transferencias se aíslan. "
                         "Default: la víctima. Para el salto 2 usar el presunto estafador.")
    args = ap.parse_args()
    A = args.address.lower()
    V = args.source.lower()
    out = DATA_DIR / ("analisis" if A == ADDRESSES["estafador"] else f"analisis_{A[:10]}")
    chains = [int(c) for c in args.chains.split(",")]

    all_moves, all_poison, all_caidas, spoof_rows, resumen = [], [], [], [], {"direccion": A, "redes": {}}
    for chain in chains:
        moves, spoof, meta, every, tx = build(chain, A)
        if not tx:
            continue
        pz, caidas = poisoning(moves, every, A)
        for r in pz:
            r["chain"] = chain
        all_moves += moves
        all_poison += pz
        all_caidas += caidas
        for c, n in spoof.most_common():
            sym, name = meta[c]
            spoof_rows.append(dict(chain=chain, contrato=c, simbolo=sym, nombre=name, eventos=n,
                                   no_ascii=any(ord(ch) > 127 for ch in sym + name)))

        real_in = [m for m in moves if m["direccion"] == "ENTRADA" and not m["polvo"]]
        real_out = [m for m in moves if m["direccion"] == "SALIDA"]
        vol = collections.defaultdict(lambda: [0.0, 0.0])
        for m in real_in:
            vol[m["activo"]][0] += m["monto"]
        for m in real_out:
            vol[m["activo"]][1] += m["monto"]
        resumen["redes"][chain] = {
            "primera_tx_utc": iso(tx[0]["timeStamp"]),
            "ultima_tx_utc": iso(tx[-1]["timeStamp"]),
            "tx_totales": len(tx),
            "tx_firmadas": sum(t["from"] == A for t in tx),
            "financiada_por": next((t["from"] for t in tx if t["to"] == A and int(t["value"]) > 0), None),
            "remitentes_unicos_reales": len({m["contraparte"] for m in real_in}),
            "destinatarios_unicos": len({m["contraparte"] for m in real_out}),
            "volumen_por_activo": {k: {"entrada": round(a, 4), "salida": round(b, 4)} for k, (a, b) in vol.items()},
            "eventos_spoofing_tokens_falsos": sum(spoof.values()),
            "contratos_token_falsos": len(spoof),
            "direcciones_imitadoras": len(pz),
            "salidas_a_imitadoras": len(caidas),
        }
        resumen["redes"][chain]["permanencia_fifo"] = dwell_fifo(moves, A)

    # Libro de movimientos
    fields = ["chain", "fecha_utc", "bloque_ts", "hash", "direccion", "tipo", "activo", "monto",
              "contraparte", "etiqueta", "firmada", "polvo", "metodo"]
    for m in all_moves:
        m["fecha_utc"] = iso(m["ts"])
        m["bloque_ts"] = m["ts"]
        m["etiqueta"] = KNOWN_LABELS.get(m["contraparte"], "")
    write_csv(out / "movimientos.csv", all_moves, fields)

    # Víctima <-> estafador
    vm = [m for m in all_moves if m["contraparte"] == V]
    write_csv(out / "victima_estafador.csv", vm, fields)
    vv = collections.defaultdict(lambda: [0, 0.0])
    for m in vm:
        vv[f"{m['chain']}:{m['activo']}:{m['direccion']}"][0] += 1
        vv[f"{m['chain']}:{m['activo']}:{m['direccion']}"][1] += m["monto"]
    resumen["victima_estafador"] = {
        "transferencias": len(vm),
        "primera_utc": vm[0]["fecha_utc"] if vm else None,
        "ultima_utc": vm[-1]["fecha_utc"] if vm else None,
        "por_activo": {k: {"cantidad": n, "monto": round(s, 4)} for k, (n, s) in vv.items()},
    }

    # Trazabilidad FIFO de los fondos que llegaron desde la víctima
    dest, det = taint_fifo(all_moves, V)
    write_csv(out / "trazabilidad_fondos_victima.csv", det,
              ["chain", "activo", "monto", "entrada_utc", "salida_utc", "horas", "destino", "hash_salida"])
    resumen["destino_fondos_victima_fifo"] = {
        k: sorted(((a, round(v, 2)) for a, v in d.items()), key=lambda x: -x[1])[:10] for k, d in dest.items()}
    if det:
        hs = sorted(d["horas"] for d in det)
        resumen["permanencia_fondos_victima_h"] = {
            "mediana": round(statistics.median(hs), 2),
            "pct_salido_en_24h": round(100 * sum(d["monto"] for d in det if d["horas"] <= 24)
                                       / sum(d["monto"] for d in det), 1)}

    # Contrapartes
    cp = {}
    for m in all_moves:
        if m["direccion"] not in ("ENTRADA", "SALIDA") or m["polvo"]:
            continue
        k = (m["chain"], m["contraparte"])
        r = cp.setdefault(k, dict(chain=m["chain"], contraparte=m["contraparte"],
                                  etiqueta=KNOWN_LABELS.get(m["contraparte"], ""),
                                  n_entradas=0, n_salidas=0, primera_utc=m["fecha_utc"]))
        r["ultima_utc"] = m["fecha_utc"]
        d = "entrada" if m["direccion"] == "ENTRADA" else "salida"
        r[f"n_{d}s"] += 1
        col = f"{d}_{m['activo']}"
        r[col] = round(r.get(col, 0) + m["monto"], 6)
    cps = sorted(cp.values(), key=lambda r: -sum(v for k, v in r.items()
                                               if k.split("_")[-1] in STABLES and isinstance(v, float)))
    cols = sorted({k for r in cps for k in r if k.startswith(("entrada_", "salida_"))})
    write_csv(out / "contrapartes.csv", cps,
              ["chain", "contraparte", "etiqueta", "n_entradas", "n_salidas", "primera_utc", "ultima_utc"] + cols)

    write_csv(out / "envenenamiento.csv", all_poison,
              ["chain", "direccion_imitadora", "imita_a", "patron", "eventos"])
    write_csv(out / "tokens_falsos.csv", spoof_rows)
    resumen["salidas_reales_a_imitadoras"] = [
        dict(chain=m["chain"], fecha=m["fecha_utc"], hash=m["hash"], activo=m["activo"], monto=m["monto"],
             hacia=m["contraparte"]) for m in all_caidas]

    # Saldo diario reconstruido (solo movimientos reales; no incluye comisiones de gas)
    bal, rows = collections.defaultdict(float), []
    by_day = collections.OrderedDict()
    for m in all_moves:
        if m["direccion"] not in ("ENTRADA", "SALIDA"):
            continue
        key = (m["chain"], m["activo"])
        bal[key] += m["monto"] if m["direccion"] == "ENTRADA" else -m["monto"]
        by_day[(m["fecha_utc"][:10], key)] = bal[key]
    for (day, (ch, act)), b in by_day.items():
        rows.append(dict(fecha=day, chain=ch, activo=act, saldo=round(b, 6)))
    write_csv(out / "saldo_diario.csv", rows)

    # Top contrapartes para verificación manual de etiquetas
    top = []
    for chain in chains:
        sub = [r for r in cps if r["chain"] == chain]
        ins = sorted(sub, key=lambda r: -sum(r.get(f"entrada_{s}", 0) for s in STABLES))[:10]
        outs = sorted(sub, key=lambda r: -sum(r.get(f"salida_{s}", 0) for s in STABLES)
                      - r.get(f"salida_{NATIVE.get(chain)}", 0) * 3000)[:10]
        top.append({"chain": chain,
                    "top_remitentes": [(r["contraparte"], round(sum(r.get(f'entrada_{s}', 0) for s in STABLES), 2),
                                        round(r.get(f"entrada_{NATIVE.get(chain)}", 0), 4)) for r in ins],
                    "top_destinos": [(r["contraparte"], round(sum(r.get(f'salida_{s}', 0) for s in STABLES), 2),
                                      round(r.get(f"salida_{NATIVE.get(chain)}", 0), 4)) for r in outs]})
    resumen["top_contrapartes"] = top

    (out / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(f"\n[+] Resultados en {out}")


if __name__ == "__main__":
    main()
