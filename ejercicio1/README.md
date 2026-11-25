# Ejercicio 1 - Investigación de estafa con criptomonedas

- Informe: [`informe.pdf`](informe.pdf)
- Detalle de hallazgos: [`hallazgos.md`](hallazgos.md)
- Registro de evidencia: [`cadena_custodia.md`](cadena_custodia.md)
- Grafo del flujo de fondos (versión ampliable): [`grafo_flujo.svg`](grafo_flujo.svg)

| Carpeta | Contenido |
|---|---|
| `evidencia/raw/sweep/` | Respuestas crudas del barrido de 11 redes (RPC y Etherscan) |
| `evidencia/raw/fetch/` | Respuestas crudas de la API de Etherscan (estafador y wallet sucesora) |
| `evidencia/bsc/` | Exportación CSV de bscscan (BSC) |
| `evidencia/capturas/` | Capturas de Etherscan, MetaSleuth, Chainabuse y bscscan |
| `datos/consolidado/` | Historial consolidado por red, dirección y tipo de transacción |
| `datos/analisis*/` | Movimientos reales, contrapartes, trazabilidad FIFO, envenenamiento, tokens falsos y saldos |
| `scripts/` | `eip55.py`, `sweep.py`, `fetch.py`, `analyze.py`, `analyze_bsc.py`, `graph.py`, `hash_evidence.py` |
