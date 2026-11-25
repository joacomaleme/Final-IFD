# Ejercicio 1 - Detalle de hallazgos

Detalle técnico de los hallazgos que resume el informe (`informe.pdf`). Las cifras surgen de los datos de `datos/` y las capturas, de `evidencia/capturas/`.

**Direcciones analizadas:** presunto estafador `0xDe83cf15d27eb4795d4e1D33852bf14CAeBd2b47`; denunciante `0x0f776cc057622f0da2f257d2b987a7cf3386b7cc`.

## Identificación de las direcciones

**1. Checksum.** La dirección del estafador tiene un checksum EIP-55 válido (`scripts/eip55.py`): no hay error de transcripción. La del denunciante se recibió en minúsculas; su forma con checksum es `0x0f776CC057622F0Da2F257d2B987A7Cf3386b7Cc`.

**2. Barrido de redes** (`datos/barrido_redes.csv`; respuestas crudas en `evidencia/raw/sweep/`). Se consultaron las dos direcciones en 11 redes EVM, por RPC público y por la API de Etherscan. El estafador es una cuenta común (EOA, sin código de contrato) con actividad en tres redes:

| Red | Tx enviadas (nonce) | Saldo nativo (25/11/2026) |
|---|---|---|
| Ethereum | 605 | 0,0903 ETH |
| Polygon | 93 | 1.505,70 POL |
| BSC | 30 | 0,0038 BNB |

No tiene actividad en Arbitrum, Optimism, Base, Avalanche, Sepolia, Linea ni Scroll.

**3. Perfil del denunciante.** Según el mismo barrido, su dirección registra 187.241 tx enviadas en Ethereum, 208.500 en BSC y 56.615 en Polygon, tiene actividad en 8 redes (además, Arbitrum, Optimism, Base, Avalanche y Sepolia) y saldos altos (21,97 ETH, 12.784 POL, 9,12 BNB y 103,6 AVAX). Ese volumen es incompatible con una persona: corresponde a una wallet automatizada o institucional. Por eso no se descargó su historial completo (más de 450.000 tx): sus interacciones con el estafador se extrajeron del historial del estafador.

**4. El denunciante retiró desde una plataforma** (`capturas/etherscan_victima.webp`). La dirección no tiene etiqueta pública, la fondeó "Binance 20" (wallet operativa de Binance), tiene 192.428 tx desde febrero de 2025 y opera cada pocos minutos: envíos de USDT y USDC a muchas direcciones distintas, swaps en Uniswap y depósitos en Binance. Es la wallet operativa de un servicio custodial (exchange, broker o procesador de pagos). El denunciante retiró fondos desde su cuenta en esa plataforma hacia el estafador; su identidad consta en los registros (KYC) de la plataforma.

**5. Perfil del estafador** (`capturas/etherscan_estafador.webp`). EOA sin etiqueta pública, con 994 tx. Su primer gas vino de `0xCa068D3c...d18Bb4F8a` (hallazgo 15). En las tx visibles aparecen ingresos desde la plataforma del denunciante y desde varios remitentes distintos, y salidas frecuentes de USDT. La etiqueta *Fake_Phishing* y la advertencia que muestra Etherscan corresponden a envenenamiento de direcciones hecho por terceros contra esta wallet (hallazgo 12).

## Flujos del estafador

**6. De la plataforma al estafador** (`datos/analisis/victima_estafador.csv`). Hay 200 transferencias en Ethereum, todas en un solo sentido, entre el 28/07/2025 y el 09/01/2026: 131 en USDT (164.789,50 USDT) y 69 en ETH (38,71 ETH). En BSC se suma 1,58 BNB (hallazgo 24).
- La primera (28/07/2025, 997,35 USDT) es la primera entrada de toda la historia de la wallet del estafador.
- No hay aprobaciones (`approve`) a favor del estafador: se descarta un robo por permisos de gasto (*drainer*).
- 200 retiros en cinco meses y medio encajan con varios clientes de la misma plataforma retirando hacia la misma dirección, o con retiros sucesivos de un mismo cliente presionado por el estafador. On-chain no es posible distinguir cuáles corresponden al denunciante.

**7. Cuenta de paso.** En Ethereum entraron 1.310.678 USDT, 252.649 USDC y 198,6 ETH, y salieron 1.310.482 USDT, 252.648 USDC y 198,5 ETH. En Polygon entraron y salieron 117.013 USDC. Todo lo que entra sale. Es el perfil de una cuenta recolectora y de paso, con fondos de múltiples orígenes (ver hallazgo 24 para el total en las tres redes).

**8. Velocidad de salida** (método FIFO: lo primero que entra se toma como lo primero que sale).
- USDT: permanencia mediana de 19,6 h; el 58,8 % salió en menos de 24 h y el 90 %, antes de 90 h.
- Fondos llegados desde la plataforma: mediana de 52,7 h; el 48,3 % salió en menos de 24 h.
- **Abandono:** el último ingreso desde la plataforma es del 09/01/2026 y la última transacción propia, del 30/01/2026. Desde entonces la wallet está inactiva.

**9. Destino de los fondos de la plataforma** (FIFO; `datos/analisis/trazabilidad_fondos_victima.csv`).
- USDT: 91.114 a `0x5e3c322c...cb12`, 24.733 a `0xb924e19c...e4e2` (Binance, hallazgo 13), 6.321 a `0xf68a87a5...1cdf` y 4.830 a `0x0dd40e36...fd55`; el resto, en montos menores.
- ETH: 21,75 a `0xf68a87a5...1cdf`, 7,16 a 1inch (swap a stablecoin) y 4,01 a `0x187fe1a8...2386`.

**10. Destinos presentes en varias redes.** `0xf68a87a5...1cdf`, `0xbf7aa1d5...f9ab`, `0xb0818381...b76e` y `0xd53e8c08...81d4` reciben fondos del estafador en Ethereum y en Polygon, y algunos también en BSC (hallazgo 24). Una misma dirección EOA en varias redes es la misma clave privada: son nodos de un mismo controlador. Además, el primer fondeo de Polygon (8.458,13 POL desde `0xe1fabf4b...b87c`, 26/08/2025) se reenvió completo a `0xf68a87a5...1cdf`.

**11. Saltos entre redes y servicios.**
- **Bridge:** la tx `0x9bb80d47...4468` (21/10/2025 15:49:23 UTC) llama a LI.FI Diamond (`0x1231deb6...4eae`). Decodificada, indica el bridge Relay, la red destino 137 (Polygon), el receptor = la misma dirección y el integrador `tangem`. Diez segundos después ingresan 803,89 USDC en Polygon desde `0xf70da978...dbef`, la dirección que entrega los fondos del lado de Relay, por un valor equivalente a los 0,2 ETH enviados.
- **Swaps:** 1inch Router V6 (14 swaps; 35,81 ETH por 185.314 USDT), LI.FI (de ETH a USDT) y dos contratos de swap sin etiqueta (por ejemplo, 19.998 USDT por 20.002 USDC).
- **Indicio de atribución:** el campo `integrator=tangem` indica que las operaciones se hicieron desde la app de la wallet Tangem.
- **Mixers:** no hay interacción directa con Tornado Cash ni con otros mixers conocidos.

**12. Envenenamiento de direcciones dirigido a la wallet.** En Ethereum y Polygon se registran 866 contratos de tokens falsos (muchos imitan USDT o USDC con caracteres cirílicos, como `UЅDС`), 19.302 eventos espurios y 553 direcciones imitadoras que copian el prefijo y el sufijo de las contrapartes reales. Ejemplo: el 21/10/2025 a las 15:56:13 el estafador envía 500 USDC a `0x61672c7f...`, y 34 segundos después un token falso registra un envío idéntico hacia la imitadora `0x6167ff92...`. El estafador nunca envió fondos reales a una imitadora. Estos eventos son ataques de terceros contra la wallet y se excluyeron del análisis. Explican el ingreso desde `Fake_Phishing2257606` (`0xbf7ac487...f9ab`, 1 gwei, que imita a `0xbf7aa1d5...f9ab`).

## Atribución (salto 1)

**13. Binance** (`capturas/etherscan_salto1_0xb924e19c.webp`). `0xb924e19c...e4e2` está etiquetada por Etherscan como "Binance Dep: 0xb924e1...D7E4e2" (Deposit Address) y la fondeó "Binance: Deposit Funder". Recibió 263.780 USDT del estafador, de los cuales 24.733 se atribuyen por FIFO a fondos llegados desde la plataforma del denunciante. Binance puede identificar al titular de la cuenta.

**14. Probable depósito en WestWallet** (`capturas/etherscan_salto1_0x5e3c322c.webp`). `0x5e3c322c...cb12` no tiene etiqueta pública, pero la fondeó "WestWallet 1" (wallet operativa del servicio custodial WestWallet) a fines de julio de 2025. Tiene 62 tx normales, saldo cero y recibió 302.718 USDT del estafador, que luego salieron. Ese patrón (gas pagado por el custodio, recepción y barrido) es el de una dirección de depósito de un cliente de WestWallet. Es el principal destino de los fondos de la plataforma (91.114 USDT por FIFO). Confianza: media.

**15. El financiador del estafador** (`capturas/etherscan_salto1_0xca068d3c.webp`). `0xca068d3c...4f8a` tiene 12 tx y su único fondeo fueron 6 retiros desde la misma plataforma del denunciante. Con esos fondos pagó el primer gas del estafador (0,4847 ETH, 01/08/2025) e hizo 3 envíos a `0x4cb1b943...1053`. El estafador, a su vez, envió gas dos veces a `0x4cb1b943...1053` (0,046 ETH el 01/09/2025 y 0,030 ETH el 06/11/2025). El financiador, el estafador y `0x4cb1b943...1053` forman un clúster de un mismo operador, que también retira fondos desde la plataforma.

**16. Clúster de `0xf68a87a5...1cdf`** (`capturas/etherscan_salto1_0xf68a87a5.webp`). Sin etiqueta; la fondeó `0x016606ac...49ee`, el segundo mayor remitente del estafador (164.183 USDT + 19.212 USDC en 15 envíos). El dinero circula dentro del grupo (`0x0166...` fondea a `0xf68a...` y le paga al estafador, y el estafador reenvía fondos a `0xf68a...`): es un patrón de estratificación (*layering*). Su última tx enviada es de fines de octubre de 2025.

**17. `0xbf7aa1d5...f9ab`** (`capturas/etherscan_salto1_0xbf7aa1d5.webp`). Sin etiqueta. Fondeada el 28/10/2025, con 2.761 tx y actividad hasta el 05/10/2026. Es blanco masivo de envenenamiento (`Fake_Phishing4404725`). Se analizó como salto 2 (hallazgo 18).

## Salto 2: la wallet sucesora

**18. Rotación de la wallet recolectora** (`datos/analisis_0xbf7aa1d5/`). `0xbf7aa1d5...f9ab` opera del 27/10/2025 al 05/10/2026. En Polygon la fondeó `0xe1fabf4b...b87c`, el mismo que fondeó al estafador en esa red. Se activa cuando el estafador se apaga: el estafador opera de agosto de 2025 a enero de 2026, y la sucesora de noviembre de 2025 a junio de 2026. Por ella pasaron 6.416.977 USDT, 2.136.605 USDC y 624,7 ETH en Ethereum, y 297.364 USDC y 41.322 USDT0 en Polygon (más de USD 8,8 M en stablecoins), de 157 remitentes en Ethereum y 14 en Polygon. El saldo reconstruido es aprox. 0 y la permanencia mediana, de unas 45 h.

**19. Misma organización.** Ocho direcciones pagaron a las dos wallets:
- la plataforma del denunciante (164.789 USDT al estafador y 6.372 USDT a la sucesora);
- `0x016606ac...49ee` (183.395 y 338.639 USDT);
- `0x58b70406...5023`, `0xee7ae85f...4055`, `0xb23360cc...c460`, `0x3dada329...bbad`, `0x9696f59e...6976` (Binance) y `0xe1fabf4b...b87c`.

Además, el estafador le transfirió a la sucesora 94.463 USDT, 4.500 USDC y 24,45 ETH en Ethereum, 53.957 USDC en Polygon y 168.549 USDT en BSC.

**20. Destino FIFO de lo que el estafador pasó a la sucesora.** USDT: 61.586 a `0xa22d26f4...7c09`, 20.414 a `0x884d8141...4fe3` y 12.463 a `0x3c8a66a0...3580`. ETH: 16,25 a `0x3e4d93d7...a7b0`. USDC en Polygon: 43.957 a `0x04772a33...a255`. El 73,9 % salió en menos de 24 h.

**21. Principales destinos de la sucesora.** `0x3c8a66a0...3580` (5.853.719 USDT y 110,4 ETH en 29 envíos, del 28/01/2026 al 30/06/2026), `0x884d8141...4fe3` (851.594 USDT) y `0x4581427e...a20d` (831.935 USDC). La sucesora no conserva saldo relevante en Ethereum ni en Polygon.

## Salto 3

**22. Distribuidora activa** (`capturas/etherscan_salto2_0x3c8a66a0.webp`). `0x3c8a66a0...3580` no tiene etiqueta y la fondeó `0x811382A5...016231c32` en diciembre de 2025. Tiene 1.108 tx, retira USDT y USDC varias veces por día y seguía activa en noviembre de 2026, con saldo bajo. No es una dirección de depósito de exchange: es otra capa de la red, todavía en uso.

**23. Wallets gemelas por activo** (`capturas/etherscan_salto2_0x884d8141.webp`, `..._0x4581427e.webp`). `0x884d8141...4fe3` recibió de la sucesora solo USDT y `0x4581427e...a20d`, solo USDC. Las dos se crearon el mismo día (13/11/2025) y ese día recibieron su primer envío de la sucesora, con 45 minutos de diferencia. Reciben de los mismos remitentes (`0x64Bd83Be...20628bd`, `0x425F4737...FfC421`, `0x59891E6b...6628c1`) y quedaron inactivas en junio y agosto de 2026. Son wallets desechables del mismo clúster, creadas para separar los flujos de cada moneda.

## BSC y fuentes externas

**24. Actividad en BSC** (`evidencia/bsc/*.csv`, exportación de bscscan; `datos/analisis_bsc/`). Hay 42 tx normales (30 firmadas por el estafador), del 21/08/2025 al 06/01/2026.
- Entraron y salieron 434.246 USDT (BSC-USD) y 10,35 BNB, de 12 remitentes hacia 17 destinatarios.
- La plataforma del denunciante también le envió 1,58 BNB (25/08/2025).
- Los destinos son los del clúster: la sucesora (168.549 USDT), `0xd53e8c08...81d4` (105.656 USDT + 5,48 BNB) y `0xf68a87a5...1cdf` (10.309 USDT + 3,03 BNB); además, `0x3533ffa4...e0da` (71.182 USDT), `0x7a0dfe1b...0efe` (46.000) y `0x5e2c80bf...ad22` (19.218).
- Hay 1.436 eventos de tokens falsos o polvo, de 139 contratos.
- **Total en las tres redes:** aprox. USD 2,12 M en stablecoins, 170 remitentes distintos y 349 destinatarios.

**25. Principal origen sin etiqueta.** `0x8792423850...d842` le pagó al estafador 88.577 USDT + 18.415 USDC en Ethereum (21 pagos) y 361.986 USDT en BSC (96 pagos): 468.978 USD en 117 pagos de montos variados. El patrón es igual al de la plataforma del denunciante: probablemente otra wallet operativa de una plataforma de la que retiran otros pagadores. Confianza: media.

**26. MetaSleuth** (`capturas/externas/metasleuth_*`).
- **Validación:** reproduce los mismos flujos y montos (por ejemplo, 1.569,37 USDT de la plataforma el 09/01/2026, 12.462,56 USDT a la sucesora el 21/01/2026 y 0,2711 ETH el 30/01/2026).
- **Etiquetas:** identifica dos wallets operativas de Binance (`0x9696f59e...6976` y `0xdfd5293d...963d`), que hicieron 15 retiros directos al estafador (17.553 USDT y 1,01 ETH), y una MultiSig de BitGo (`0xa4d65fd5...757c`), que envió 196,93 USDT el 28/02/2026, después del abandono. Ese monto es el saldo residual que sigue en la wallet.
- **La plataforma del denunciante** tampoco tiene etiqueta en MetaSleuth. Su grafo muestra pagos a terceros, como "Roobet: Deposit Address", e ingresos grandes desde `0xcacebc09...ef70`, lo que confirma que es un servicio custodial de uso general.
- Muestra el mismo ruido de envenenamiento que se filtró (hallazgo 12).

**27. Chainabuse** (`capturas/externas/chainabuse_*.png`). No hay denuncias registradas para el estafador, la sucesora ni el financiador.
