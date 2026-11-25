"""Genera comparacion_versiones.png (figura incluida en el informe): las dos versiones del Boletín 6625 lado a lado,
con sus metadatos clave y el SHA-1 en base32 (el mismo "digest" que publica el Wayback Machine).

Uso:
    python3 scripts/figura_comparacion.py
"""
import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import BASE_DIR, EVID_DIR

ORIG = EVID_DIR / "wayback" / "manual" / "wb_20251124185559_6625.pdf"
CURR = sorted((EVID_DIR / "pdf" / "boletin_6625").glob("*/body.pdf"))[-1]
OUT = BASE_DIR / "comparacion_versiones.png"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def meta(pdf):
    ex = json.loads(subprocess.run(["exiftool", "-j", "-a", "-G1", str(pdf)],
                                   capture_output=True, text=True).stdout)[0]
    sha1 = base64.b32encode(hashlib.sha1(pdf.read_bytes()).digest()).decode()
    return {
        "CreateDate": ex.get("PDF:CreateDate", ""),
        "ModifyDate": ex.get("PDF:ModifyDate", ""),
        "SourceModified (UTC)": ex.get("PDF:SourceModified", ""),
        "Creator": ex.get("PDF:Creator", ""),
        "Producer": ex.get("PDF:Producer", ""),
        "DocumentID": ex.get("XMP-xmpMM:DocumentID", ""),
        "Tamaño": f"{pdf.stat().st_size:,} bytes".replace(",", "."),
        "SHA-1 base32 (digest)": sha1,
    }


def render(pdf, tmp):
    base = Path(tmp) / pdf.parent.name
    subprocess.run(["pdftoppm", "-r", "70", "-png", "-singlefile", str(pdf), str(base)], check=True)
    return Image.open(str(base) + ".png").convert("RGB")


def main():
    f, fb, fs = ImageFont.truetype(FONT, 16), ImageFont.truetype(FONTB, 19), ImageFont.truetype(FONT, 15)
    cols = [("VERSIÓN ORIGINAL · Wayback 24/11/2025 18:55 UTC", ORIG, (183, 28, 28)),
            ("VERSIÓN ACTUAL · servidor AFA, subida 24/11/2025 23:09 UTC", CURR, (21, 101, 192))]
    with tempfile.TemporaryDirectory() as tmp:
        imgs = [render(p, tmp) for _, p, _ in cols]
        metas = [meta(p) for _, p, _ in cols]
    pw, ph = imgs[0].size
    colw, pad, top, mh = max(pw, 800), 30, 64, 270
    W, H = 2 * colw + 3 * pad, top + mh + ph + 2 * pad + 60
    canvas = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(canvas)
    for i, ((title, _, color), img, m) in enumerate(zip(cols, imgs, metas)):
        x = pad + i * (colw + pad)
        d.rectangle([x, 10, x + colw, 48], fill=color)
        d.text((x + 10, 17), title, font=fb, fill="white")
        y = top
        for k, v in m.items():
            d.text((x, y), k + ":", font=fs, fill=(90, 90, 90))
            d.text((x + 210, y), str(v), font=f, fill=color if k.startswith(("Create", "Modify", "Source", "SHA")) else "black")
            y += 31
        canvas.paste(img, (x + (colw - pw) // 2, top + mh))
        d.rectangle([x + (colw - pw) // 2, top + mh, x + (colw - pw) // 2 + pw, top + mh + ph], outline=(160, 160, 160))
    d.text((pad, H - 52), "Texto idéntico palabra por palabra; cambian la diagramación (cortes de línea), el DocumentID y TODAS las marcas de tiempo.", font=fs, fill=(60, 60, 60))
    d.text((pad, H - 30), "Los digests SHA-1 coinciden con los del CDX del Wayback Machine (4 capturas de la original; 6 de la actual).", font=fs, fill=(60, 60, 60))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT)
    print(f"[+] {OUT}")


if __name__ == "__main__":
    main()
