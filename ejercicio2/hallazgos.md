# Ejercicio 2 - Detalle de hallazgos

Detalle técnico de los hallazgos que resume el informe pericial (`informe.pdf`). La secuencia completa de hechos está en `datos/linea_tiempo.md`.

**Documento cuestionado:** `Boletin-Resoluciones-6625-(12-02-2025).pdf`, publicado por la AFA en `https://assets1.afa.com.ar/2025/`.

## Fuentes de la consigna

**1. Artículos** (`evidencia/web/articulo_*`: HTML, encabezados HTTP y capturas). Bolavip (actualizado el 24/11/2025 20:47 ART), Infocielo (24/11/2025 16:04) y El Liberal (24/11/2025 21:38) coinciden en que el PDF del 6625 aparecía como creado el 23/11/2025 a las 19:21. Infocielo afirma que el boletín "hasta el domingo no figuraba en la web oficial", y El Liberal atribuye la detección a usuarios de X que descargaron el PDF del sitio oficial.

**2. Captura de propiedades difundida por la prensa** (`evidencia/web/img_infocielo_WhatsApp_15.54.24/`). Es el panel "Propiedades del documento" de `Boletin-Resoluciones-6625-(12-02-2025).pdf`: 115 KB, autor AFA, creado el 23/11/25 a las 19:21:16 y modificado a las 19:21:18, con Acrobat PDFMaker 25 para Word y Adobe PDF Library 25.1.201, PDF 1.6, una página en tamaño oficio.

**3. Contenido.** "Boletín Nº 6625, Resoluciones de la Mesa Directiva del 12.02.2025". Tiene tres secciones: renuncias en la Cámara Nacional de Resolución de Disputas, "Homenaje a los clubes campeones" (el "pasillo de reconocimiento") y licencias de clubes 2025, con plazo al 10/03/2025.

**4. Comunicado de la AFA.** Sostiene que la numeración de los boletines es correlativa y que el Boletín 6661 (03/04/2025) incluye al 6625 entre las resoluciones aprobadas. Es internamente inconsistente: cita "Boletín 6625 del 12.02.2025" y, más abajo, "del 12.04.2025". Además, la correlación de números no prueba cuándo se generó el archivo publicado.

**5. Fuente secundaria sobre el 6661.** La Nación y Los Andes informaron que el Boletín 6661, que la AFA cita como respaldo, fue generado con Adobe PDF Library 25.1.211. Se verificó sobre el archivo oficial (hallazgo 14).

## Wayback Machine

**6. Rutas de febrero.** No hay capturas del 6625 en las rutas donde la AFA alojaba los boletines de febrero de 2025 (`media/DANI/FEB-25/` y la raíz). En cambio, el 6630 (14/02/2025), de la misma carpeta, está archivado desde el 01/05/2025, y el 6624, desde el 23/01/2025 (`evidencia/wayback/wb_available_*`).

**7. Ruta real.** La URL real del 6625 (carpeta `2025/`) tiene su primera captura el 24/11/2025 a las 18:55:59 UTC. No hay ninguna anterior al partido.

**8. Índice CDX** (`evidencia/wayback/manual/cdx_6625.json`). Registra 10 capturas, todas con HTTP 200:
- las 4 primeras (24/11/2025 18:55:59, 20:20:53 y 20:40:00, y 25/11/2025 00:32:10 UTC) tienen el digest `BOBUGAW3XNITIRVWFGS62TDSPGTEDJVG`;
- las 6 siguientes (desde el 25/11/2025 02:16:10 UTC hasta el 10/12/2025) tienen `OD7OJUUH6Q2TZRGOXRUF2UL6N3CRBSCS`.

El SHA-1 en base32 de la versión original (hallazgo 10) es `BOBUGAW3...`, y el del PDF que hoy sirve la AFA (hallazgo 9), `OD7OJUUH...`. Hay exactamente dos versiones, y su orden en el tiempo lo prueba un tercero independiente. La captura de las 00:32 UTC del 25/11 todavía muestra la versión original aunque el servidor ya tenía la nueva: se explica por la caché de Cloudflare.

## Las dos versiones del PDF

**9. Versión actual** (`evidencia/pdf/boletin_6625/`). Pesa 115.282 bytes y su MD5 es igual al ETag del servidor (`9a70fb52a8aa1678405af7af891dbd4c`), así que la copia es idéntica al objeto publicado. Su `Last-Modified` es el 24/11/2025 a las 23:09:57 GMT (20:09 ART). Sus metadatos internos (Info y XMP coinciden) son:

| Campo | Valor |
|---|---|
| CreateDate | 2025-02-12 19:21:37 -03:00 |
| ModifyDate / MetadataDate | 2025-02-12 19:21:42 -03:00 |
| SourceModified (documento de Word, UTC) | D:20250212222121 (= 19:21:21 -03:00) |
| Creator / Producer | Acrobat PDFMaker 25 para Word / Adobe PDF Library 25.1.201 |
| Estructura | PDF 1.6, linealizado, 1 página, 612 × 1008 pt, etiquetado, idioma ES-AR |
| DocumentID | uuid:368dc2f6-1337-464e-8b3d-db81344dffcd |

No quedan restos de otra versión dentro del archivo: tiene un solo flujo XMP, ninguna fecha de noviembre y ninguna actualización incremental.

**10. Versión original** (`evidencia/wayback/manual/wb_20251124185559_6625.pdf`, recuperada del Wayback con el modificador `id_`, que entrega el archivo sin alterar). Pesa 117.254 bytes.

| Campo | Versión original | Versión actual |
|---|---|---|
| CreateDate | 2025-11-23 19:21:16 -03:00 | 2025-02-12 19:21:37 -03:00 |
| ModifyDate | 2025-11-23 19:21:18 -03:00 | 2025-02-12 19:21:42 -03:00 |
| SourceModified (Word, UTC) | D:20251123222018 (= 19:20:18 -03) | D:20250212222121 (= 19:21:21 -03) |
| Creator / Producer | PDFMaker 25 / PDF Library 25.1.201 | Igual |
| DocumentID | uuid:a1d24754-d30d-4d51-9b7c-b8250088e031 | uuid:368dc2f6-1337-464e-8b3d-db81344dffcd |
| /ID del trailer | 1a485fd1... / 32e59f8e... | f7869b60... / 118a6c3e... |
| Objetos / bytes | 80 / 117.254 | 75 / 115.282 |
| Texto | Idéntico palabra por palabra (incluido el error "en la la Liga"), con distintos cortes de línea | |

**11. Reemplazo antedatado.** La versión original se generó el 23/11/2025 a las 19:21 ART, al terminar el partido (inicio a las 17:30). La versión que la reemplazó se subió el 24/11/2025 a las 23:09 UTC, pero todas sus marcas de tiempo, incluido el guardado del documento de Word, dicen 12/02/2025. No es una edición de metadatos: es una nueva exportación desde Word, con otro DocumentID, otros identificadores y otra diagramación del mismo texto. Un archivo "creado en febrero" que reemplaza a otro creado en noviembre solo se explica si se exportó con el reloj del equipo atrasado. Incluso se reprodujo la hora del día (19:21).

## Grupo de control

**12. Anacronismo de software** (`datos/metadatos_pdf.csv`). Se analizaron 24 boletines de la AFA, de agosto de 2024 a febrero de 2026, generados con el mismo flujo (de Word a PDF con Acrobat PDFMaker). La versión de la herramienta cambia con el tiempo:

| Período | Boletines | Herramienta |
|---|---|---|
| Sep 2024 | 6550 | PDFMaker 24 / PDF Library 24.3.144 |
| Dic 2024 – Ene 2025 | 6604, 6611, 6616 | PDFMaker 24 / 24.5.96 |
| 14 – 15 Feb 2025 | 6630, 6631, 6632 | PDFMaker 24 / 24.5.175 |
| Jul 2025 | 6722 | PDFMaker 25 / 25.1.51 (primera aparición de la versión 25) |
| Sep 2025 | 6757, 6759 | PDFMaker 25 / 25.1.213 |
| Oct – Nov 2025 | 6772, 6776, 6788 | PDFMaker 25 / 25.1.20x |
| Dic 2025 – Feb 2026 | 6806, 6814, 6828 | PDFMaker 25 / 25.1.5 y 25.1.119 |

El 6625 declara haberse generado el 12/02/2025 con PDFMaker 25, mientras que los boletines de dos y tres días después, de la misma oficina, usan la versión 24. Un archivo realmente exportado el 12/02/2025 tendría PDFMaker 24.

**13. Ubicación en el servidor.** Los boletines de enero y febrero de 2025 están en `media/DANI/ENE-25/`, `media/DANI/FEB-25/` o en la raíz. El 6625 está en `2025/`, la carpeta que la AFA usa desde octubre de 2025 (6772, 6788, 6814). Esa ubicación es coherente con una subida en noviembre de 2025.

**14. Boletín 6661** (`evidencia/pdf/control_6661/`). Su texto lista al 6625 entre las "Resoluciones publicadas en Boletines anteriores". Sin embargo:
- su `Last-Modified` es el 25/11/2025 a las 01:58:58 GMT, en plena polémica y tres horas después del reemplazo del 6625;
- declara haberse creado el 04/04/2025 con PDF Library 25.1.211, una versión que no aparece en ningún otro boletín de esa época;
- su primera captura en el Wayback es del 25/11/2025.

Por eso no constituye una prueba independiente de que el 6625 existiera en febrero.

**15. Indicios descartados.** Las advertencias de `qpdf` sobre tablas de *hint* inconsistentes, los dos `/ID` distintos del trailer y la cadena `19:21:16` del campo XMPToolkit (la fecha de compilación de la biblioteca de Adobe) aparecen en todos los PDF de PDFMaker de la AFA, así que no se usaron como indicios.

**16. Fecha de publicación de las versiones de Adobe.** No se encontró una fuente oficial de Adobe con la fecha de publicación de Adobe PDF Library 25.1.201. El anacronismo se fundamenta en el corpus propio de la AFA (hallazgo 12), que refleja las herramientas que usaba la misma oficina.
