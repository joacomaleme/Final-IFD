"""Genera o verifica evidencia/hashes.sha256 (formato compatible con `sha256sum -c`).

Uso:
    python3 scripts/hash_evidence.py            # (re)genera el listado
    python3 scripts/hash_evidence.py --verify   # verifica integridad
"""
import hashlib
import sys
from pathlib import Path

from common import BASE_DIR, EVID_DIR

LIST = EVID_DIR / "hashes.sha256"
SKIP = {LIST.name, ".gitkeep"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def files():
    return sorted(p for p in EVID_DIR.rglob("*") if p.is_file() and p.name not in SKIP)


def generate():
    lines = [f"{sha256_file(p)}  {p.relative_to(BASE_DIR).as_posix()}" for p in files()]
    LIST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[+] {len(lines)} archivos hasheados -> {LIST.relative_to(BASE_DIR)}")


def verify():
    bad = 0
    listed = set()
    for line in LIST.read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        listed.add(rel)
        p = BASE_DIR / rel
        if not p.exists():
            print(f"FALTA     {rel}"); bad += 1
        elif sha256_file(p) != digest:
            print(f"ALTERADO  {rel}"); bad += 1
    for p in files():
        if p.relative_to(BASE_DIR).as_posix() not in listed:
            print(f"NUEVO (no listado)  {p.relative_to(BASE_DIR).as_posix()}")
    print("[+] Integridad OK" if not bad else f"[x] {bad} problemas de integridad")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else generate()
