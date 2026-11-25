# Ejercicio 1 - Registro de evidencia y cadena de custodia

**Caso:** presunta estafa con criptomonedas.
**Direcciones:** presunto estafador `0xDe83cf15d27eb4795d4e1D33852bf14CAeBd2b47`; denunciante `0x0f776cc057622f0da2f257d2b987a7cf3386b7cc`.

Las respuestas de las API se guardaron sin modificar. Cada una figura en `evidencia/manifest.jsonl` con su URL (la clave de la API está censurada), la hora UTC de la consulta, el bloque de referencia y su SHA-256. El listado de hashes de toda la evidencia está en `evidencia/hashes.sha256` y se verifica con `python3 scripts/hash_evidence.py --verify`.

| N.º | Pieza | Origen / modo de obtención | Fecha UTC | Integridad | Ubicación |
|---|---|---|---|---|---|
| 1 | Barrido de las dos direcciones en 11 redes EVM (código, nonce, saldo y existencia de transacciones) | RPC públicos y API v2 de Etherscan, `scripts/sweep.py` | 25/11/2026 17:41 – 17:48 | SHA-256 por respuesta (manifiesto) | `evidencia/raw/sweep/` |
| 2 | Historial del presunto estafador en Ethereum y Polygon (tx normales, internas, ERC-20, ERC-721 y ERC-1155) | API v2 de Etherscan, `scripts/fetch.py`; bloques de referencia ETH #26.486.335 y Polygon #97.889.199 | 24/11/2026 16:53 – 16:55 | SHA-256 por respuesta (manifiesto) | `evidencia/raw/fetch/` |
| 3 | Historial de la wallet sucesora `0xbf7aa1d5...f9ab` en Ethereum y Polygon | API v2 de Etherscan, `scripts/fetch.py`; bloques ETH #26.486.516 y Polygon #97.890.686 | 24/11/2026 17:29 – 17:32 | SHA-256 por respuesta (manifiesto) | `evidencia/raw/fetch/` |
| 4 | Exportación CSV de BSC del presunto estafador (tx normales, BEP-20 e internas) | Descarga desde bscscan.com, sin editar | 24/11/2026 | `hashes.sha256` | `evidencia/bsc/` |
| 5 | Capturas de Etherscan: denunciante, estafador y nodos de los saltos 1 y 2 | Captura de pantalla del explorador | 24 – 25/11/2026 | `hashes.sha256` | `evidencia/capturas/` |
| 6 | Capturas de MetaSleuth (Ethereum y Polygon), Chainabuse (estafador, sucesora y financiador) y bscscan | Captura de pantalla | 24/11/2026 | `hashes.sha256` | `evidencia/capturas/externas/` |

Los datos derivados (`datos/`) se generan a partir de las piezas 1 a 4 con los scripts de `scripts/`, sin modificar la evidencia.
