# LOUKSNAPG: audit integral de ejecución, 26 de octubre de 2026

**Decisión:** `HOLD_NOT_CERTIFIED`  
**Contrato:** `LOUKSNAPG-AC-001` — SHA-256 `45ca9f13edda4df26755e8cc91db9784f2652fdcc1e82a7722e6381351579064`  
**Commit exacto del candidato:** `59bedb1c47739e577068eeb31576ddea21b21467`  
**Ejecución de fábrica:** [40302483781](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40302483781)  
**Auditoría auxiliar de seis obligaciones:** [40305342081](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40305342081)

## Identidad y presupuesto

El candidato `LOUKSNAPG.md` mide **371.947.709 bytes** y tiene SHA-256 `515b6e9c164c0e5add32ea7968c2ef00aab3a849eb756f76448c4e47f97e40a8`. La verificación de integridad del contenedor pasó y el tamaño queda por debajo del tope de distribución de **479.000.000 bytes**. El límite separado del runtime Cajita continúa en **470.000.000 bytes**. Esto demuestra integridad y cumplimiento de tamaño, no calidad funcional.

## Resultado de las seis obligaciones

| Obligación contractual | Resultado | Evidencia |
|---|---|---|
| C1 — trabajadores coordinados | **HOLD** | CUSTOSZ V9 tiene recibo de ejecución y produjo el candidato. Kestra no se ejecutó: faltan `KESTRA_URL` y `KESTRA_API_TOKEN`; no hay execution ID ni estado terminal. |
| C2 — reparación con fuentes oficiales | **HOLD** | El catálogo de cinco fuentes/modelos tiene revisiones fijadas a nivel de metadatos (`PASS_METADATA_PIN_CHECK`), pero hay **cero reparaciones materiales verificadas** de pesos y cinco pruebas de calidad fallidas. |
| C3 — funciones primitivas | **HOLD** | La cobertura funcional acreditada de tareas de consumidor es 5/21; pasan 0 pruebas de calidad y fallan 5. La inferencia terminó, pero las salidas son incorrectas. |
| C4 — telemetría y auditoría | **PASS_TRACEABILITY_WITH_RELEASE_HOLD** | Se recomputaron 11/11 eventos, los hashes de contenido y del sobre, y los vínculos al commit, al contrato y al candidato. La telemetría declara `INCOMPLETE_HOLD`. |
| C5 — cadena de certificación | **HOLD** | G23 de integridad del paquete pasó; G23 funcional no está establecido, Kestra no fue ejecutado, G24 no fue concedido y faltan pruebas completas de host, no-regresión y rollback. |
| C6 — prohibiciones y recuperación | **PASS_PROHIBITIONS_OBSERVED** | Peso de modelos pesados descargado: 0. Remote Commander usado: no. Mutación canónica: no. Evidencia sintética usada como prueba del producto: no. |

El total es **2 obligaciones aprobadas y 4 en HOLD**. La auditoría es no certificante por diseño; su decisión final es `HOLD_NOT_CERTIFIED`.

## Resultados funcionales exactos

Los cinco procesos devolvieron código de salida 0 y `PASS_FUNCTIONAL_EXECUTION`, pero **las cinco aserciones semánticas fallaron**:

| Objetivo | Comprobación | Resultado observado | SHA-256 de pesos compactos |
|---|---|---|---|
| `D01_CEREBRO_ROOT` | Respuesta sobre contenido de un repositorio | `ron amongronronron among amongron amongssronron` | `e2516453d09285581bd6f3bf45a4c3a9fa6431bdc3dff56e7249d30e4e294ae0` |
| `D03_TRANSCRIPCION_ROOT` | Audio conocido “hello world” | `daughterziest manuscript ele` | `67ee70beb2fb3529270a8169fbb6bd0f538912a064a6a303bec238647b4a5f5f` |
| `D04_TRADUCCION_GENERAL` | Saludo inglés→español | `te te te apres te te te te who te te` | `630aad9958f9c78603852c29c382b0fe9d63e64772e21dc6367875a91dc6a28f` |
| `D05_DOCLING` | Extraer total de factura 133,45 | `onationonationonation underrated underrated underrated shitty underrated` | `4a13b916b63b682a28c8fe89fc608b90d3bf5a8a77cb0988e1e19131c64ebc88` |
| `D06_ANALISIS_AVANZADO` | Aritmética 2 + 2 | `irts airways` | `01eba827b9dd001a2352f0fd28a0bea229d3a5b3a78a41f3ea3e7c6c21995f56` |

Los seis smoke tests de motores fuente-anclados también pasaron (`PASS_TARGET_ENGINE_E2E_SCOPE_ONLY`), pero son pruebas limitadas de arranque/ejecución; no reemplazan las tareas de consumidor ni certifican las funciones primitivas. Las pruebas de comportamiento usan fixtures sintéticos fijos: sirven para detectar que las salidas fallan, no para demostrar equivalencia con los modelos originales.

El gate funcional informó `HOLD`, `eligible_for_g24=false` y 34 fallos. No se concedió G24.

## Telemetría verificable

El informe de contrato registró SHA-256 `45ca9f13edda4df26755e8cc91db9784f2652fdcc1e82a7722e6381351579064`. El archivo de telemetría pre-auditoría tiene SHA-256 `f18153a4b54852725b859b4fd05b19d50e124c72b94f195ad63bf7f231d86a34` y su digest interno es `3edf39b784ea6dcce89cb8b2d4d24193931b0abc36c6a2a526c4b0ed91849b15`. La comprobación de C4 validó 11 eventos y sus enlaces al commit y al candidato; no elevó el estado de lanzamiento.

## Bloqueos de liberación

1. Kestra no dispone de endpoint/token configurados; falta su recibo real.
2. Los cinco modelos cargan y ejecutan inferencia, pero fallan sus verificaciones de calidad.
3. Solo hay cinco tareas de modelo observadas; no existe cobertura funcional certificada para los 21 objetivos.
4. No hay evidencia de reparación material de pesos con hashes anterior/posterior y calidad aprobada. Los pesos compactos actuales no incluyen la información de los componentes de rango descartados; no se descargaron pesos pesados para intentar reconstruirlos.
5. G23 funcional, G24 separado y autorizado, matriz de hosts, no-regresión completa y rollback no están acreditados.

**Conclusión gobernada:** conservar el candidato como artefacto de integridad validada, pero impedir su promoción y mantener `HOLD_NOT_CERTIFIED`. El informe JSON contiguo conserva los hashes, los recuentos y las seis decisiones en formato legible por máquina.
