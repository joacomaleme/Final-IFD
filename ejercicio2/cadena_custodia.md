# Ejercicio 2 - Registro de evidencia y cadena de custodia

**Caso:** presunta creación o modificación posterior del Boletín AFA Nº 6625 ("pasillo de reconocimiento").
**Documento cuestionado:** `https://assets1.afa.com.ar/2025/Boletin-Resoluciones-6625-(12-02-2025).pdf`.

Las piezas web se adquirieron con `scripts/acquire.py`, que solo hace pedidos GET. Cada pieza se guardó sin modificar, junto con los encabezados HTTP de la respuesta (`headers.json`), y figura en `evidencia/manifest.jsonl` con su URL, la hora UTC y su SHA-256. El listado completo de hashes está en `evidencia/hashes.sha256` y se verifica con `python3 scripts/hash_evidence.py --verify`.

| N.º | Pieza | Origen / modo de obtención | Fecha UTC | SHA-256 | Ubicación |
|---|---|---|---|---|---|
| 1 | Artículo de Infocielo (HTML + encabezados) | GET, `acquire.py` | 25/11/2026 13:39 | manifiesto | `evidencia/web/articulo_infocielo/` |
| 2 | Artículo de Bolavip (HTML + encabezados + captura) | GET, `acquire.py` | 25/11/2026 13:38 | manifiesto | `evidencia/web/articulo_bolavip/` |
| 3 | Artículo de El Liberal (HTML + encabezados + captura) | GET, `acquire.py` | 25/11/2026 13:39 | manifiesto | `evidencia/web/articulo_elliberal/` |
| 4 | Imágenes publicadas por Infocielo (contenido del 6625, propiedades del PDF, listado web) | GET, `acquire.py` | 25/11/2026 13:39 | manifiesto | `evidencia/web/img_infocielo_*/` |
| 5 | PDF oficial actual del Boletín 6625 (MD5 = ETag del servidor) | GET, `acquire.py` | 25/11/2026 14:35 | `953ba7d768e1bf6460dce4e43f50d54a3150d130a0b28475bf7ab788c33f80d1` | `evidencia/pdf/boletin_6625/` |
| 6 | Grupo de control: 24 boletines de la AFA, incluido el 6661 | GET, `acquire.py` (URLs en `scripts/control_urls.txt`) | 25/11/2026 14:50 – 15:46 | manifiesto | `evidencia/pdf/control_*/` |
| 7 | Consultas de disponibilidad del Wayback Machine | GET, `acquire.py` (API de archive.org) | 25/11/2026 13:40 – 15:46 | manifiesto | `evidencia/wayback/wb_available_*/` |
| 8 | Índice CDX del Wayback para la URL del 6625 | Descarga desde web.archive.org con navegador | 25/11/2026 | `37541f6c4c215a9567ea0f555edc02cd38235a88b16eea30f54925edc40ac08a` | `evidencia/wayback/manual/cdx_6625.json` |
| 9 | Versión original del 6625: capturas `id_` 20251124185559 y 20251125003210 (idénticas entre sí) | Descarga desde web.archive.org con navegador | 25/11/2026 | `c671048f416ab8b699b064847b617e1499815aacf6e20abe0b321486741b0165` | `evidencia/wayback/manual/` |

Los datos derivados (`datos/`) y la figura del informe se generan a partir de esta evidencia con los scripts de `scripts/`, sin modificarla.
