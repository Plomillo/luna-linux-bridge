# LOUKSNAPG — auditoría forense de fallos funcionales y medición de recursos

Fecha de evidencias: 2026-10-29 UTC. Rama examinada: `louksnapg/phase4-resume-20261028`.

## Decisión ejecutiva

`G23=PASS` para la integridad del artefacto en el commit `c7915f9bf4fa9bd9db9d0c91baa55042f5f03ce0`; `G24=NOT_GRANTED`. Se observaron cinco ejecuciones de tareas con código cero, pero **0/5 pasaron las aserciones semánticas**. Los smoke tests 6/6 sólo comprueban interfaces de alcance parcial y no compensan los fallos funcionales. La certificación integral permanece denegada; no se publicó el candidato.

- G23/G24: [workflow #40794248442](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40794248442).
- G23 artifact ZIP: ID `12862903262`, SHA-256 `7c802920bc6f25b360a9f8a5d19e5ef132c7e4f67204f3d8cb8e8c3b1120018f`.
- G24 evidence ZIP: ID `12862594001`, SHA-256 `3d802c1b57d9bd9d83c3e309d6450d5795cc7162428f91fa5636b4a98017b499`.
- G24 telemetry ZIP: ID `12862653924`, SHA-256 `70202ead7115fa1cf4f646fd8ad7e65bba361b26f6953606f3fac80f1875d846`.
- Artefacto `LOUKSNAPG.md` SHA-256: `b7a8d885bd3e6a6c16e09536cab4d564c8f719ecf1cb5d66f1923ce72b733191`.
- Runtime comprimido: 370.889.833 bytes. Documento acompañante: 11.651.408 bytes. Total exacto: 382.541.241 bytes frente al techo combinado de 490.000.000.

## Hallazgo 1 — la representación compacta de GPT-OSS pierde casi toda la señal de las matrices

**Defecto concreto.** El `compression_metadata.json` vigente de `1. Cerebro` registra `rank=1`, método `randomized_truncated_svd_rank1_plus_symmetric_int8_factor_quantization` y `aggregate_relative_frobenius_error_after_int8=0.9983363410727844`. El peso empacado actual es de 40.489.120 bytes, SHA-256 `e2516453d09285581bd6f3bf45a4c3a9fa6431bdc3dff56e7249d30e4e294ae0`. El runtime está construido específicamente para factores de rango 1.

**Consecuencia funcional.** La tarea `e2e-cerebro-text-generation` se ejecutó, pero devolvió `ron amongronronron among amongron amongssronron`; la aserción de respuesta útil falló. El estado de ejecución cero no significa que el modelo razone correctamente.

**Corrección necesaria.** No ajustar parámetros de generación para ocultar esta pérdida. Se necesita una representación/compresión cuya precisión se mida contra los tensores fuente y cuya tarea de razonamiento pase; cualquier candidato debe respetar el techo global medido. No se ha autorizado promover ni reemplazar el peso vigente.

**Verificación posterior.** Repetir la tarea de repositorio conocida sobre el peso exacto integrado; comprobar tanto el resultado semántico como SHA del peso, módulo y bundle. Hasta entonces `D01_CEREBRO=NOT_GRANTED`.

## Hallazgo 2 — Whisper rank 29 mantiene identidad fuente pero no capacidad de transcripción

**Defecto concreto.** `3. Transcripción/compression_metadata.json` registra `rank=29`, factorización INT8 de bajo rango y peso actual de 10.399.882 bytes, SHA-256 `67ee70beb2fb3529270a8169fbb6bd0f538912a064a6a303bec238647b4a5f5f`. La identidad de fuente fijada es `openai/whisper-large-v3-turbo@7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7`.

**Consecuencia funcional.** En G24 la entrada sintética conocida `hello world` produjo `تىdaughterziest manuscript`; la aserción de transcripción falló. La referencia fuente equivalente pasa el audio conocido y el corpus LibriSpeech con WER 0,058824. El resultado integrado no certifica ni la ruta de audio ni la calidad del modelo.

**Corrección necesaria.** No continuar el barrido ciego de rangos: el historial registra fallos en R29/R64/R96 y dos variantes adaptativas R192. La V2 adaptativa midió error de Frobenius agregado 0,6881450, falló el audio sintético y obtuvo WER 1,0 en LibriSpeech. Una nueva variante requiere hipótesis técnica concreta, métricas de los mismos dos audios y presupuesto global real, antes de cualquier promoción.

**Verificación posterior.** Ejecutar audio conocido y muestra real con hashes de entrada fijados, calcular WER y probar el peso exacto empaquetado. `D03_TRANSCRIPCION=NOT_GRANTED`.

## Comprobación de evidencia histórica para traducción general

Se revisó también `docs/cajita-luna/LOUKSNA1_TASK_ADAPTER_EVIDENCE.json`, cuya fuente exacta es el commit `4ea9190df2f39581aa391584ab4ae868da82da79`. La fila histórica `e2e-seamless-translation` sólo declara `status=PASS_FUNCTIONAL_EXECUTION`, `exit_code=0` y `semantic_quality_equivalence=NOT_ESTABLISHED`; no contiene un criterio `quality_acceptance`, ni una salida de traducción verificable contra una referencia. Por tanto, esa evidencia anterior acredita que el proceso ejecutó y devolvió salida, pero **no demuestra que traducción general ya tradujera correctamente**. La tarea G24 actual incorpora una expectativa EN→ES explícita y falla; no se ha descartado ninguna prueba semántica anterior válida porque no se encontró tal aprobación en ese artefacto.

## Hallazgo 3 — traducción general y Qwen tienen ejecución, no calidad útil

| Dominio | Representación declarada en metadata | Peso integrado (bytes) | Resultado observado de G24 | Decisión |
|---|---|---:|---|---|
| Traducción general / SeamlessM4T v2 | Rango 4, SVD bajo rango + INT8 | 11.720.882 | `te te te apres te te te te who te te`; expectativa EN→ES no satisfecha | `NOT_GRANTED` |
| Qwen3 / análisis avanzado | Rango 12, SVD bajo rango + INT8 | 14.956.240 | `irts airways`; `2+2` no devolvió `4` | `NOT_GRANTED` |
| Docling, cobertura extra | Pesos cuantizados compactos | 13.483.380 | salida `onationonationonation underrated ...`; extracción del total incorrecta | Falla extra, no sustituye un dominio obligatorio |

**Corrección necesaria.** Revisar los empaquetados/modelo de cada dominio y la implementación de reconstrucción de los factores frente a su metadato fuente. Los identificadores/hash sí coinciden con los manifiestos: la evidencia actual no señala un simple archivo cambiado, sino que confirma que el payload fijado es el que falla funcionalmente. No promover pesos por superar sólo el loader.

**Verificación posterior.** Tareas de referencia conocidas para traducción, Qwen y extracción adicional, ejecutadas sobre los hashes integrados; salida semántica aprobada, no sólo código cero. No se ha demostrado reparación.

## Hallazgo 4 — la suite ahora cubre el dominio antiguo como bloqueo explícito, no como sustitución

G24 sobre el mismo bundle obtuvo `PASS_ROUTE_IDENTIFIED_FAIL_CLOSED`: los targets seleccionados son `D04_HERMENEUTICA_HG` y `D04_TRADUCCION_LENGUAS_ANTIGUAS`; `general_translation_fallback_selected=false`; `execution_authorized=false`. La función de traducción quedó `BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE`. Esto valida el plan de ruta y el comportamiento fail-closed, no una traducción efectiva. El árbol de Foma tiene código del compilador y ejemplos/tests, pero no un transductor de traducción compilado ni léxico operacional ni adaptador consumidor registrado.

**Corrección necesaria.** Registrar un adaptador dedicado y conseguir un transductor/léxico licenciado con par lingüístico definido. No desviar el target a traducción general.

**Verificación posterior.** Tarea fuente-bound con resultado conocido en el runtime integrado y prueba de desconocidos que debe bloquearse sin fallback.

## Hallazgo 5 — discrepancia entre RSS por proceso y límite cgroup

En el candidato anterior del commit `c7915f9...`, `memory.peak=983138304` quedó dentro del límite. En el G24 definitivo del commit `6024b73b56e016318158b1ae5777a3c4abc5a4ba`, el workflow impuso `memory.max=1073741824`, `cpu.max=100000 100000` y registró `memory.peak=959139840`, también dentro del límite. Los reportes anteriores de `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` por tarea podían superar 1 GiB (por ejemplo, Cerebro en una ejecución previa). Esos valores RSS por proceso no son iguales a la memoria cobrada por cgroup; la fuente autoritativa del límite total es `memory.peak`. La corrección del harness fue validada con pruebas que conservan la decisión semántica independiente del RSS: una salida semánticamente fallida sigue siendo FAIL aunque el proceso esté bajo el límite.

**Defecto de informe.** El harness usaba el RSS de cada proceso como si fuera la medida autoritativa del presupuesto total, creando una condición redundante y con semántica distinta a la de cgroup. No es una causa de las salidas semánticas defectuosas y no debe usarse para convertirlas en aprobadas.

**Corrección verificada en CI.** `tools/cajita_task_e2e.py` separa `task_execution_and_quality_pass` (requiere ejecución exitosa, calidad semántica PASS y hashes) de `process_peak_rss_diagnostics`. El límite de memoria se verifica externamente con `memory.peak` y `cpu.max`. Las pruebas explícitas comprueban que el RSS por proceso no sustituye el cgroup, y que la calidad semántica FAIL continúa siendo FAIL aunque el RSS esté por debajo del límite. En el commit `6024b73b56e016318158b1ae5777a3c4abc5a4ba`, CI pasó 133 pruebas de runtime/contratos y 20 de bundle/presupuesto/métricas; después el G24 real de ese mismo candidato falló, con un pico cgroup dentro del límite.

## PC y Kestra

La terminal confirmó que Kestra está activo, pero el checkpoint local indica `BLOCKED_AUTHENTICATED_FLOW_REGISTRATION_REQUIRED`; la monitoría observada consulta GitHub en modo de sólo lectura y no ejecuta la tarea nueva de refresco de fase. Un intento anterior de registro remoto devolvió HTTP 401. El root local sigue al 99% de uso y los inodos al 100%; por eso no se hizo reparación/escritura ni inferencia local. No se presenta Kestra como orquestador activo de las reparaciones: la evidencia actual sólo acredita monitoría antigua de lectura. CUSTOSZ V9 pasó su autoprueba como helper acotado, sin autoridad G23/G24.

## Decisión final

- G23: PASS de integridad y consistencia estructural de este artefacto exacto.
- G24: NOT_GRANTED; 0/5 tareas modelo pasaron calidad, y traducción antigua sigue bloqueada sin recurso operativo.
- Publicación: omitida por la puerta G24.
- Certificación integral: `NOT_GRANTED`.

No hay evidencia para certificar ningún motor sólo por la carga del modelo o por smoke técnico. La siguiente reparación funcional debe abordar la pérdida de información de la representación comprimida o su consumidor, y verificarse mediante las pruebas conocidas antes de tocar la autoridad de release.

## Auditoría ligera de la PC y estado de la prueba del fix de métrica

Se completó una inspección de sólo lectura de metadatos/rutas del proyecto local y un cálculo SHA-256 en streaming de los seis pesos del manifiesto local `CAJITA_GLOBAL_479M_CANDIDATE_RUNTIME_V4_20261022T233541Z`. La operación de hash utilizó afinidad de CPU a un único núcleo y `RLIMIT_AS=1,073,741,824`; sólo leyó los archivos en bloques de 1 MiB, sin abrir tensores, construir modelos ni inferir.

Los seis hashes/tamaños del manifiesto local V4 coincidieron con sus seis archivos locales:
- GPT-OSS compacto: 148.477.400 bytes, SHA-256 `935d226a65faca9b59a7742c7c31208ef0ba671509d475c1a4e2f3489cecc19e`.
- Whisper compacto R29: 34.877.948 bytes, SHA-256 `6f4541536bfca7899d74e962c277b7fbcd1cbc4fb7f8d101c69bcd1ea2560aa3`.
- SeamlessM4T compacto R4: 20.256.147 bytes, SHA-256 `a2ba25feb33c68b7a5ea27ff8aadeaf96f67d80fc74d169c075e14d1ff363bf5`.
- Docling: 13.483.380 bytes, SHA-256 `4a13b916b63b682a28c8fe89fc608b90d3bf5a8a77cb0988e1e19131c64ebc88`.
- Qwen compacto R12: 52.950.152 bytes, SHA-256 `9d5c2ec7d88583c016a7d48f29695915ecfe0619cbca49bdfa8708f6cf6a4604`.
- ONNX Anti-Alucinaciones: 110.516.001 bytes, SHA-256 `c6a266fe0f7f1f782094ff4b1e7ae3547fa48a22ab44712881cc03bba07bc5b7`.

**Alcance de esta evidencia:** estos hashes sólo confirman integridad del candidato local V4 respecto de su propio manifiesto; no confirman equivalencia funcional ni identidad con el candidato V9 producido por GitHub Actions. Por ejemplo, el GPT-OSS local ocupa 148.477.400 bytes mientras que el peso GPT-OSS integrado en el paquete Git V9 es un payload diferente, de 40.489.120 bytes. Los dos candidatos no deben reconciliarse o mezclarse sin autorización/versionado explícitos.

La inspección de los directorios de motores localizó `model.safetensors.index.json` de GPT-OSS, pero los 15 shards que enumera (`model-00000-of-00014.safetensors` a `model-00014-of-00014.safetensors`) no están presentes allí. También faltan los shards de referencia originales listados en los metadatos de SeamlessM4T (2) y Qwen (8). El peso local de Whisper es el artefacto compacto de 34.877.948 bytes, no coincide con el SHA de la referencia fuente fijado en metadata (`542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1`). En consecuencia, no se dispone en los directorios de referencia examinados de los pesos originales íntegros para realizar una comparación local equivalente. No se descargaron a la PC ni se cargaron pesos originales.

### Resultado final de los gates sobre el candidato exacto

Workflow [#40797072765](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40797072765), source commit `6024b73b56e016318158b1ae5777a3c4abc5a4ba`:

- G23: `PASS` de integridad del paquete, estructura, módulos, hashes de los seis pesos y reconstrucción de recursos externalizados. El archivo `LOUKSNAPG.md` SHA-256 `3f0a37ca93590a2e8c03c37576b5bb8e8a73c0e6bc2d5ae1e9215dda423ec0a0`, 371.947.903 bytes. Runtime comprimido: 370.889.832 bytes, SHA-256 `04cf7410d68e4cbd4f636db117df51fefc4b581b46d7a1887ddce123d2499545`. Documento `Louksna1.md`: 11.651.408 bytes, SHA-256 `f64e6925ff6a22b009fe592da3eda5c373ec788127a5b2dc9b824548bdf1e798`. Total combinado: 382.541.240 bytes de un techo de 490.000.000.
- G24: `NOT_GRANTED`. Evidencia artifact ID `12864557482`, ZIP SHA-256 `bf8179d8726b3a2dd3c8d365b6eaa13303b87e2339a27771f3dc9855e66775f2`. Telemetría artifact ID `12864881598`, ZIP SHA-256 `72de3adb2d2707833b6b15c640ff8df3bff6cb37ad1feccec5973260743b5321`.
- La evidencia corregida informa `task_adapter_execution_success_count=5`, `task_adapter_quality_pass_count=0`, `task_adapter_pass_count=0`, `task_adapter_return_code=3`. Las cinco salidas de calidad fallaron: Cerebro, Whisper, traducción general, Docling (tarea extra) y Qwen. Los seis smoke tests de infraestructura de destino pasaron sólo dentro de su alcance parcial.
- `memory.max=1073741824`, `cpu.max=100000 100000`, `memory.peak=959139840`: los límites de recursos pasaron. No subsanan el fallo semántico.
- La ruta de lenguas antiguas devolvió `PASS_ROUTE_IDENTIFIED_FAIL_CLOSED`, seleccionó `D04_HERMENEUTICA_HG` y `D04_TRADUCCION_LENGUAS_ANTIGUAS`, excluyó el fallback al traductor general y mantuvo `execution_authorized=false`. Estado funcional: `BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE`.
- La etapa de publicación fue `SKIPPED`. `GLOBAL_CERTIFICATION=NOT_GRANTED`.

La primera iteración de la corrección del harness también tuvo un error transitorio de importación con los caracteres literales `\\n` en `tests/test_cajita_task_e2e.py` (run `40796719130`, commit `5b505b90a8c0f1e9d37e0b92756962a64cd1a93c`). La importación fue corregida en `6024b73b56e016318158b1ae5777a3c4abc5a4ba`; las 133 pruebas de runtime/contratos y las 20 de bundle/presupuesto pasaron. Que el harness y G23 pasen acredita el control de la prueba y la integridad, **no** el funcionamiento semántico de los modelos.

