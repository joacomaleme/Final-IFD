"""Utilidades comunes: HTTP, preservación de respuestas crudas y manifiesto.

Solo usa la biblioteca estándar de Python (>= 3.9) para que pueda correrse
en cualquier máquina sin instalar dependencias.

Principio forense: cada respuesta de red se guarda TAL CUAL llegó (bytes
exactos), junto con su SHA-256, la hora UTC de la consulta y la URL usada
(con la API key censurada). Así cualquier dato del informe puede rastrearse
hasta su fuente y verificarse su integridad.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # ejercicio1/
EVID_DIR = BASE_DIR / "evidencia"
RAW_DIR = EVID_DIR / "raw"
DATA_DIR = BASE_DIR / "datos"
MANIFEST = EVID_DIR / "manifest.jsonl"

USER_AGENT = "forensic-research-script/1.0 (python-urllib)"

ADDRESSES = {
    "estafador": "0xde83cf15d27eb4795d4e1d33852bf14caebd2b47",
    "victima": "0x0f776cc057622f0da2f257d2b987a7cf3386b7cc",
}


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def redact(url: str) -> str:
    return re.sub(r"(apikey=)[^&]+", r"\1REDACTED", url, flags=re.I)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def http_request(url: str, payload: dict | None = None, timeout: int = 30):
    """GET (payload=None) o POST JSON. Devuelve (status, bytes)."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, json.dumps({"_client_error": str(e)}).encode()


def preserve(raw: bytes, rel_path: str, meta: dict) -> Path:
    """Guarda bytes crudos en evidencia/raw/<rel_path> y agrega una línea al manifiesto."""
    out = RAW_DIR / rel_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    entry = dict(meta)
    entry.update({
        "file": str(out.relative_to(BASE_DIR)).replace(os.sep, "/"),
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
    })
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return out


def stamp() -> str:
    """Marca de tiempo apta para nombres de archivo."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def sleep_rate(seconds: float = 0.4):
    time.sleep(seconds)
