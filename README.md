# Examen final - Introducción a la Forensia Digital

Evidencia, datos y scripts de los dos ejercicios del examen final. Los informes están en la carpeta de cada ejercicio.

| Ejercicio | Informe | Detalle de hallazgos | Registro de evidencia |
|---|---|---|---|
| 1. Investigación de estafa con criptomonedas | [`ejercicio1/informe.pdf`](ejercicio1/informe.pdf) | [`ejercicio1/hallazgos.md`](ejercicio1/hallazgos.md) | [`ejercicio1/cadena_custodia.md`](ejercicio1/cadena_custodia.md) |
| 2. Análisis de metadatos del Boletín AFA 6625 | [`ejercicio2/informe.pdf`](ejercicio2/informe.pdf) | [`ejercicio2/hallazgos.md`](ejercicio2/hallazgos.md) | [`ejercicio2/cadena_custodia.md`](ejercicio2/cadena_custodia.md) |

## Estructura

```
ejercicioN/
  informe.pdf          informe entregado
  hallazgos.md         detalle técnico de cada hallazgo citado en el informe
  cadena_custodia.md   registro de las piezas de evidencia (origen, fecha, hash, ubicación)
  evidencia/           evidencia original sin modificar
    manifest.jsonl     una línea por pieza adquirida: URL, hora UTC, SHA-256
    hashes.sha256      hash de cada archivo de evidencia
  datos/               datos derivados de la evidencia (CSV / JSON)
  scripts/             código usado para adquirir y analizar
```

## Verificación de integridad

Desde la carpeta de cada ejercicio:

```
python3 scripts/hash_evidence.py --verify
```

También es compatible con `sha256sum -c evidencia/hashes.sha256`.

## Reproducción

Los scripts usan Python 3.9 o superior. Los comandos de cada ejercicio están en el anexo de su informe.

- Ejercicio 1: `fetch.py` y `sweep.py` necesitan una API key gratuita de Etherscan (variable `ETHERSCAN_API_KEY`); `graph.py` necesita Graphviz. Los análisis (`analyze.py`, `analyze_bsc.py`) trabajan sobre los datos incluidos y no requieren conexión.
- Ejercicio 2: exiftool, qpdf, poppler-utils y `pikepdf`.
