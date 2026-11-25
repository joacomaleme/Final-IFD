"""Utilidades comunes del Ejercicio 2: rutas, hashing y manifiesto de evidencia.

Principio forense (ISO/IEC 27037): toda pieza adquirida se guarda tal cual llegó
(bytes exactos), con su SHA-256, la hora UTC de adquisición, la URL de origen y
los encabezados HTTP de la respuesta, en evidencia/manifest.jsonl.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # ejercicio2/
EVID_DIR = BASE_DIR / "evidencia"
DATA_DIR = BASE_DIR / "datos"
MANIFEST = EVID_DIR / "manifest.jsonl"
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/131.0 Safari/537.36 forensic-acquisition")


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(path: Path, meta: dict) -> dict:
    """Agrega una entrada al manifiesto para un archivo ya escrito."""
    data = path.read_bytes()
    entry = dict(meta)
    entry.update(file=str(path.relative_to(BASE_DIR)).replace(os.sep, "/"),
                 bytes=len(data), sha256=sha256_bytes(data))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry
