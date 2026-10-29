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

El workflow impuso `memory.max=1073741824` y `cpu.max=100000 100000`; su `memory.peak=983138304` quedó dentro del límite. Los reportes de `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` por tarea incluyeron, por ejemplo, 1.146.601.472 bytes para Cerebro y 1.054.339.072 para Docling. Esos valores de RSS por proceso pueden incluir páginas compartidas y **no son iguales a la memoria cobrada por cgroup**; la fuente autoritativa para el límite de ejecución del contenedor es `memory.peak`. En el mismo run, el gate exterior leyó un pico menor a 1 GiB.

**Defecto de informe.** El harness usaba el RSS de cada proceso como si fuera la medida autoritativa del presupuesto total, creando una condición redundante y con semántica distinta a la de cgroup. No es una causa de las salidas semánticas defectuosas y no debe usarse para convertirlas en aprobadas.

**Corrección ya propuesta en código de la rama.** `tools/cajita_task_e2e.py` separa `task_execution_and_quality_pass` (requiere salida correcta, calidad semántica PASS y hashes) de `process_peak_rss_diagnostics`. El gate agregado se reserva al control externo `memory.peak` y `cpu.max`. Se añadieron dos pruebas: RSS de proceso sobre 1 GiB no invalida por sí solo si el gate cgroup está cubierto; calidad semántica FAIL sigue fallando aunque el RSS esté bajo. Commit de cambio de harness `289fdfa23abc770cfc2395c49bc7c7afc88f8b44`; pruebas adicionales `5b505b90a8c0f1e9d37e0b92756962a64cd1a93c`. Validación CI para estos commits aún debe leerse por SHA exacto; no se declara aprobada antes de ello.

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

### Pruebas CI del contrato de calidad y de la corrección del contador

La suite de pruebas tuvo un fallo transitorio por una importación escrita con los caracteres literales `\\n` en lugar de una nueva línea en `tests/test_cajita_task_e2e.py`. La ejecución que contenía ese error (`40796719130`, commit `5b505b90a8c0f1e9d37e0b92756962a64cd1a93c`) terminó con `SyntaxError` al importar el test; no produjo evidencia de runtime de modelo. La importación se corrigió en el commit `6024b73b56e016318158b1ae5777a3c4abc5a4ba`. En el workflow `40797072765`, job de fabricación, las 133 pruebas de runtime/contratos y las 20 pruebas de bundle/presupuesto, incluida la separación ejecución-calidad y la cobertura de lenguas antiguas, terminaron `OK`. G23 para ese commit se encontraba en ejecución al registrar esta actualización; el G24 de ese commit todavía no había terminado. No se considera validada la función de los motores por el mero éxito de esos tests unitarios.

