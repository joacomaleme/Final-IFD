"""Fase 9 - Grafo del flujo de fondos (Graphviz DOT -> SVG/PNG).

Lee datos/analisis/movimientos.csv, resumen.json y envenenamiento.csv y genera
grafo_flujo.svg en la carpeta del ejercicio (requiere Graphviz).

Uso:
    python3 scripts/graph.py [--top 8]
"""
import argparse
import collections
import csv
import json
import shutil
import subprocess
import sys

from common import ADDRESSES, BASE_DIR, DATA_DIR

A = ADDRESSES["estafador"]
V = ADDRESSES["victima"]
AN = DATA_DIR / "analisis"
OUT = BASE_DIR
NATIVE = {"1": "ETH", "137": "POL", "56": "BNB"}
CHAIN_NAME = {"1": "Ethereum", "137": "Polygon", "56": "BSC"}
STABLES = {"USDT", "USDC", "USDC.e", "USDT0", "DAI"}
LABELS = {
    "0x111111125421ca6dc452d289314280a0f8842a65": "1inch Router V6\\n(DEX / swap)",
    "0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae": "LI.FI Diamond\\n(swap / bridge)",
    V: "Denunciante\\n(wallet operativa de plataforma)",
    "0xb924e19c9ef3b197ea004d3a1336ca7b59d7e4e2": "BINANCE · dirección de depósito\\n(etiqueta Etherscan)",
    "0x5e3c322ccd5095e7e5cfa3ff1655cef39c4fcb12": "0x5e3c…cb12 · sin etiqueta\\nfondeada por WestWallet 1\\n(posible depósito custodial)",
    "0xbf7aa1d5e95eb35813d03eacc5c4e9fa3ec6f9ab": "WALLET SUCESORA 0xbf7a…f9ab\\nnov-2025 → jun-2026 · 157 remitentes\\npasaron 6,42 M USDT + 2,14 M USDC + 624,7 ETH",
    "0xf68a87a5bb6b0287554058f4b8de7def5ae31cdf": "0xf68a…1cdf · sin etiqueta\\nfondeada por 0x0166…49ee",
    "0x016606acc6b0cfe537acc221e3bf1bb44b4049ee": "0x0166…49ee\\n(fondeó a 0xf68a…1cdf)",
    "0x8792423850b2dc7ec5a2add96d217eaad23ad842": "0x8792…d842 · sin etiqueta\\npatrón de wallet operativa\\n(117 pagos en ETH y BSC)",
}
# Vínculos de clúster verificados en capturas de Etherscan (H-13 a H-17): (origen, destino, etiqueta)
# Salto 2 (H-18 a H-20): destinos principales de la wallet sucesora
HOP2 = [
    ("0xbf7aa1d5e95eb35813d03eacc5c4e9fa3ec6f9ab", "0x3c8a66a0becaa8f79668067c90910a46103b3580",
     "0x3c8a…3580 · sin etiqueta · ACTIVA\\n5,85 M USDT + 110 ETH (29 envíos)\\ndistribuidora (1.108 tx)", "salto 2"),
    ("0xbf7aa1d5e95eb35813d03eacc5c4e9fa3ec6f9ab", "0x884d8141b19427e80adca2eb6c15a2c1ef744fe3",
     "0x884d…4fe3 · sin etiqueta\\n851.594 USDT (solo USDT)\\ncreada el 13/11/2025", "salto 2"),
    ("0xbf7aa1d5e95eb35813d03eacc5c4e9fa3ec6f9ab", "0x4581427e8f4ec2110aa0bcc043ecb58f9246a20d",
     "0x4581…a20d · sin etiqueta\\n831.935 USDC (solo USDC)\\ncreada el 13/11/2025", "salto 2"),
    ("0x016606acc6b0cfe537acc221e3bf1bb44b4049ee", "0xbf7aa1d5e95eb35813d03eacc5c4e9fa3ec6f9ab",
     None, "338.639 USDT"),
    (V, "0xbf7aa1d5e95eb35813d03eacc5c4e9fa3ec6f9ab", None, "6.372 USDT"),
]
CLUSTER = [
    (V, "0xca068d3cffbf879e3041fa3e1d29f68d18bb4f8a", "6 retiros"),
    ("0xca068d3cffbf879e3041fa3e1d29f68d18bb4f8a", A, "1.ª tx: 0,4847 ETH (gas)\\n01/08/2025"),
    ("0xca068d3cffbf879e3041fa3e1d29f68d18bb4f8a", "0x4cb1b943e5e71b97dd2b3ab6630654ea079e1053", "3 envíos"),
    (A, "0x4cb1b943e5e71b97dd2b3ab6630654ea079e1053", "2 envíos de gas\\n0,076 ETH"),
    ("0x016606acc6b0cfe537acc221e3bf1bb44b4049ee", "0xf68a87a5bb6b0287554058f4b8de7def5ae31cdf", "fondeo inicial"),
]
SERVICES = {"0x111111125421ca6dc452d289314280a0f8842a65", "0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae",
            "0xb924e19c9ef3b197ea004d3a1336ca7b59d7e4e2"}
CLUSTER_MEMBERS = {"0x016606acc6b0cfe537acc221e3bf1bb44b4049ee"}
CLUSTER_NODES = {
    "0xca068d3cffbf879e3041fa3e1d29f68d18bb4f8a": "FINANCIADOR 0xca06…4f8a\\nfondeado solo por la plataforma",
    "0x4cb1b943e5e71b97dd2b3ab6630654ea079e1053": "0x4cb1…1053\\nwallet hermana (gas)",
}
# Contexto externo documentado en las capturas (H-04)
EXTERNAL = [("binance20", "Binance 20\\n(financió a la plataforma)", V)]


def short(a):
    return f"{a[:6]}…{a[-4:]}"


def fmt(d):
    parts = []
    for k, v in sorted(d.items(), key=lambda x: -x[1]):
        if v >= 1:
            parts.append(f"{v:,.0f} {k}" if k in STABLES or v >= 100 else f"{v:,.2f} {k}")
    return "\\n".join(parts[:3])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args()
    res = json.loads((AN / "resumen.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((AN / "movimientos.csv").open(encoding="utf-8")))
    bsc = DATA_DIR / "analisis_bsc" / "movimientos.csv"
    if bsc.exists():  # BSC: exportación CSV de bscscan (analyze_bsc.py)
        for r in csv.DictReader(bsc.open(encoding="utf-8")):
            r.update(chain="56", polvo="False")
            rows.append(r)

    flows = collections.defaultdict(lambda: collections.defaultdict(float))  # (chain, src, dst) -> activo -> monto
    for r in rows:
        if r["polvo"] == "True" or r["direccion"] not in ("ENTRADA", "SALIDA"):
            continue
        src, dst = (r["contraparte"], A) if r["direccion"] == "ENTRADA" else (A, r["contraparte"])
        flows[(r["chain"], src, dst)][r["activo"]] += float(r["monto"])

    def weight(d, chain):
        return sum(v for k, v in d.items() if k in STABLES) + d.get(NATIVE.get(chain, ""), 0) * (
            3000 if chain == "1" else 600 if chain == "56" else 0.2)

    # Direcciones que aparecen en ambas redes (reutilización entre cadenas)
    seen = collections.defaultdict(set)
    for (ch, s, d) in flows:
        seen[s if d == A else d].add(ch)
    imitadoras = {r["direccion_imitadora"] for r in csv.DictReader((AN / "envenenamiento.csv").open(encoding="utf-8"))}
    cross = {a for a, chs in seen.items() if len(chs) > 1 and a not in imitadoras}

    L = ['digraph flujo {',
         '  rankdir=LR; splines=true; nodesep=0.25; ranksep=1.1;',
         '  graph [fontname="Helvetica", fontsize=11, labelloc=t, '
         'label="Flujo de fondos - presunto estafador 0xDe83…2b47 (Ethereum, Polygon y BSC)\\n'
         'Montos agregados; fuentes: Etherscan API v2 (ETH, Polygon) y exportación CSV de bscscan (BSC)"];',
         '  node [fontname="Helvetica", fontsize=9, shape=box, style="rounded,filled", fillcolor="#eeeeee"];',
         '  edge [fontname="Helvetica", fontsize=8, color="#555555"];']
    L.append(f'  "{A}" [label="PRESUNTO ESTAFADOR\\n{short(A)}\\nEOA · ETH + Polygon + BSC", '
             'fillcolor="#e53935", fontcolor="white", penwidth=2];')
    L.append(f'  "{V}" [label="{LABELS[V]}\\n{short(V)}", fillcolor="#1e88e5", fontcolor="white"];')
    for nid, lab, dst in EXTERNAL:
        L.append(f'  "{nid}" [label="{lab}", fillcolor="#fbc02d"];')
        L.append(f'  "{nid}" -> "{dst}" [style=dashed, label="fondeo inicial"];')

    # Los montos van en la etiqueta del NODO (no de la arista) para evitar ambigüedad visual.
    per_node = collections.defaultdict(lambda: {"in": {}, "out": {}})
    totals = collections.defaultdict(float)
    for (ch, s, d), amounts in flows.items():
        a, k = (s, "in") if d == A else (d, "out")
        per_node[a][k][ch] = amounts
        totals[(a, k)] += weight(amounts, ch)

    def pick(kind):
        ranked = sorted((x for x in totals if x[1] == kind), key=lambda x: -totals[x])
        chosen, rest = [], []
        per_chain = collections.Counter()
        for a, _ in ranked:
            chs = per_node[a][kind].keys()
            if a == V or any(per_chain[c] < args.top for c in chs):
                chosen.append(a)
                for c in chs:
                    per_chain[c] += 1
            else:
                rest.append(a)
        return chosen, rest

    def label(a, kind):
        base = LABELS.get(a, short(a))
        lines = [f"{CHAIN_NAME.get(c, c)}: {fmt(d).replace(chr(92) + 'n', ' · ')}"
                 for c, d in sorted(per_node[a][kind].items())]
        return base + "\\n" + "\\n".join(lines)

    declared = set()
    for kind in ("in", "out"):
        chosen, rest = pick(kind)
        for a in chosen:
            nid = a if a not in declared else f"{a}_{kind}"
            if a != V:
                color = ("#b39ddb" if a in SERVICES else "#ffcc80" if a in cross
                         else "#f8bbd0" if a in CLUSTER_MEMBERS else "#eeeeee")
                extra = "\\n(misma dirección en varias redes)" if a in cross else ""
                L.append(f'  "{nid}" [label="{label(a, kind)}{extra}", fillcolor="{color}"];')
                declared.add(a)
            else:
                vlines = "\\n".join(f"{CHAIN_NAME.get(c, c)}: {fmt(d).replace(chr(92) + 'n', ' · ')}"
                                      for c, d in sorted(per_node[V][kind].items()))
                L.append(f'  "{V}" [label="{LABELS[V]}\\n{short(V)}\\n{vlines}", fillcolor="#1e88e5", fontcolor="white"];')
            edge = f'"{nid}" -> "{A}"' if kind == "in" else f'"{A}" -> "{nid}"'
            L.append(f'  {edge} [color="{"#1e88e5" if kind == "in" else "#e53935"}", penwidth=1.4];')
        for ch in sorted({c for a in rest for c in per_node[a][kind]}):
            grp = [a for a in rest if ch in per_node[a][kind]]
            agg = collections.defaultdict(float)
            for a in grp:
                for k, v in per_node[a][kind][ch].items():
                    agg[k] += v
            nid = f"otros_{kind}_{ch}"
            txt = "remitentes" if kind == "in" else "destinatarios"
            L.append(f'  "{nid}" [label="{len(grp)} {txt} más ({CHAIN_NAME.get(ch, ch)})\\n'
                     f'{fmt(agg).replace(chr(92) + "n", " · ")}", shape=folder];')
            edge = f'"{nid}" -> "{A}"' if kind == "in" else f'"{A}" -> "{nid}"'
            L.append(f'  {edge} [style=dashed, color="{"#1e88e5" if kind == "in" else "#e53935"}"];')

    for nid, lab in CLUSTER_NODES.items():
        L.append(f'  "{nid}" [label="{lab}", fillcolor="#f8bbd0"];')
    for a, b, nlab, elab in HOP2:
        if nlab:
            L.append(f'  "{b}" [label="{nlab}", fillcolor="#d7ccc8"];')
        # Los destinos del salto 2 quedan a la derecha de la wallet sucesora; las entradas no fuerzan el orden.
        L.append(f'  "{a}" -> "{b}" [label="{elab}", color="#6d4c41", fontcolor="#6d4c41", style=bold'
                 f'{"" if nlab else ", constraint=false"}];')
    for a, b, lab in CLUSTER:
        L.append(f'  "{a}" -> "{b}" [label="{lab}", color="#ad1457", style=dashed, fontcolor="#ad1457", constraint=false];')

    # Envenenamiento de direcciones (ruido dirigido a la wallet)
    nimit = sum(v["direcciones_imitadoras"] for v in res["redes"].values())
    nfake = sum(v["contratos_token_falsos"] for v in res["redes"].values())
    nev = sum(v["eventos_spoofing_tokens_falsos"] for v in res["redes"].values())
    rb = DATA_DIR / "analisis_bsc" / "resumen.json"
    if rb.exists():  # BSC: contratos falsos y eventos de polvo/spoofing
        b = json.loads(rb.read_text(encoding="utf-8"))
        nfake += b["contratos_falsos"]
        nev += b["eventos_tokens_falsos_o_polvo"]
    L.append(f'  "poison" [label="Address poisoning\\n{nimit} direcciones imitadoras\\n'
             f'{nfake} contratos de tokens falsos\\n{nev:,} eventos espurios", '
             'shape=note, fillcolor="#ffe0b2"];')
    # Salto entre redes verificado (H-11): LI.FI / Relay, ETH -> Polygon
    L.append('  "bridge" [label="Salto entre redes · LI.FI → Relay\\n2025-10-21 15:49 UTC · 0,2 ETH (Ethereum)\\n'
             '→ 803,89 USDC en Polygon 10 s después\\nreceptor = la misma dirección · integrador: tangem", '
             'fillcolor="#b39ddb", penwidth=2];')
    L.append(f'  "{A}" -> "bridge" [color="#6a1b9a", style=bold];')
    L.append(f'  "poison" -> "{A}" [style=dotted, color="#ef6c00", label="0 salidas reales\\na imitadoras"];')
    L.append('  subgraph cluster_ley { label="Referencias"; fontsize=9; style=dashed;'
             ' k1 [label="Rojo: presunto estafador", fillcolor="#e53935", fontcolor=white];'
             ' k2 [label="Azul: denunciante / plataforma", fillcolor="#1e88e5", fontcolor=white];'
             ' k3 [label="Naranja: misma dirección en varias redes", fillcolor="#ffcc80"];'
             ' k4 [label="Violeta: servicio identificado (DEX / bridge / exchange)", fillcolor="#b39ddb"];'
             ' k5 [label="Rosa + línea punteada: vínculo de clúster (fondeo / gas)", fillcolor="#f8bbd0"];'
             ' k6 [label="Marrón: salto 2 (desde la wallet sucesora)", fillcolor="#d7ccc8"]; }')
    L.append("}")

    if not shutil.which("dot"):
        sys.exit("[x] Falta Graphviz (dot).")
    svg = OUT / "grafo_flujo.svg"
    subprocess.run(["dot", "-Tsvg", "-o", str(svg)], input="\n".join(L), text=True, check=True)
    print(f"[+] {svg}")
    if cross:
        print("[+] Direcciones presentes en más de una red:", ", ".join(sorted(cross)))


if __name__ == "__main__":
    main()
