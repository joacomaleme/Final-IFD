"""Validación de checksum EIP-55 de direcciones EVM (sin dependencias).

Implementa Keccak-256 (la variante original usada por Ethereum, distinta de
SHA3-256 de hashlib) en Python puro.

Uso:
    python3 scripts/eip55.py 0xDe83cf15d27eb4795d4e1D33852bf14CAeBd2b47 [...]
"""
import sys

_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
_M = (1 << 64) - 1


def _rol(v, n):
    return ((v << n) | (v >> (64 - n))) & _M if n else v


def _keccak_f(A):
    for rc in _RC:
        C = [A[x][0] ^ A[x][1] ^ A[x][2] ^ A[x][3] ^ A[x][4] for x in range(5)]
        D = [C[(x - 1) % 5] ^ _rol(C[(x + 1) % 5], 1) for x in range(5)]
        A = [[A[x][y] ^ D[x] for y in range(5)] for x in range(5)]
        B = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                B[y][(2 * x + 3 * y) % 5] = _rol(A[x][y], _ROT[x][y])
        A = [[B[x][y] ^ ((~B[(x + 1) % 5][y]) & B[(x + 2) % 5][y]) for y in range(5)]
             for x in range(5)]
        A[0][0] ^= rc
    return A


def keccak256(data: bytes) -> bytes:
    rate = 136
    msg = bytearray(data) + b"\x01"
    msg += b"\x00" * ((-len(msg)) % rate)
    msg[-1] |= 0x80
    A = [[0] * 5 for _ in range(5)]
    for off in range(0, len(msg), rate):
        block = msg[off:off + rate]
        for i in range(rate // 8):
            A[i % 5][i // 5] ^= int.from_bytes(block[i * 8:(i + 1) * 8], "little")
        A = _keccak_f(A)
    out = b"".join(A[i % 5][i // 5].to_bytes(8, "little") for i in range(4))
    return out


def to_checksum(addr: str) -> str:
    a = addr.lower().removeprefix("0x")
    if len(a) != 40 or any(c not in "0123456789abcdef" for c in a):
        raise ValueError(f"dirección inválida: {addr}")
    h = keccak256(a.encode()).hex()
    return "0x" + "".join(c.upper() if c.isalpha() and int(h[i], 16) >= 8 else c
                          for i, c in enumerate(a))


def check(addr: str) -> str:
    cs = to_checksum(addr)
    body = addr.removeprefix("0x")
    if body == body.lower() or body == body.upper():
        estado = "SIN checksum (todo minúsculas/mayúsculas): no verificable, formato válido"
    elif addr == cs:
        estado = "checksum EIP-55 VÁLIDO"
    else:
        estado = "checksum EIP-55 INVÁLIDO (posible error de tipeo o alteración)"
    return f"{addr}\n  checksum correcto: {cs}\n  resultado: {estado}"


if __name__ == "__main__":
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert to_checksum("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed") == "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
    for arg in sys.argv[1:] or ["0xDe83cf15d27eb4795d4e1D33852bf14CAeBd2b47",
                                "0x0f776cc057622f0da2f257d2b987a7cf3386b7cc"]:
        print(check(arg))
