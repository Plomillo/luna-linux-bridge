# LOUKSNAPG2 — reparación de motores y estado operativo V3

**Tipo:** revisión documental aditiva; V1 y V2 permanecen preservadas.
**Rama de trabajo:** `louksnapg2/puac2-alternative-20261029`.
**Commit base de la revisión:** `4630ad44544dd39adf5686129e4f0d015c8328bf`.
**Trabajador principal:** `vendor/CUSTOSZV9.pyz`, SHA-256 `667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3`.
**Límite máximo de distribución:** `490000000` bytes. Esta revisión no cambia el techo.
**Política:** `APPEND_ONLY / FAIL_CLOSED / NO_AUTOMATIC_PROMOTION`.

## 1. Alcance y lectura de antecedentes

`LOUKSNAPG2.md` es un artefacto de distribución generado por GitHub Actions; no es el documento fuente que gobierna el proceso. Los artefactos de configuración, runtime, reparación, evaluación, registro y workflows son las fuentes versionadas.

V1 documenta la infraestructura inicial y una modalidad remota selectiva. V2 rectifica el rol del trabajador y separa la evaluación CPU/offline de la reparación GPU. La mención histórica de `LOUKSNAPG_REMOTE_MODE=selective` en V1 no constituye la política operativa actual. La evaluación de la rama activa se ejecuta local/offline; la inferencia diagnóstica CPU no prueba reparación GPU ni certifica modelos.

Esta V3 no borra ni reescribe V1/V2. Fija el estado observado y los cambios aditivos de esta revisión.

## 2. CUSTOSZ V9: rol y límite verificable

El workflow comprueba el hash del paquete local y CRFU self-test 12/12. El trabajador anterior hacía inventario de fuentes y construcción del candidato; declaraba explícitamente `repair_execution_performed=false` y `model_inference_performed=false`. Por tanto, un job con `success` no equivalía a reparación de pesos.

La extensión de esta revisión añade una acción primaria acotada de construcción y pruebas del motor Foma entre inventario y empaquetado. Esa acción ejecuta `make -j1 check` sobre una copia temporal del código fuente y una prueba de lookup sintética `cat → dog`. La fuente Cajita no se modifica. El informe se adjunta a la evidencia del trabajador.

Esta compilación prueba que la herramienta Foma se construye y ejecuta; no repara GPT-OSS, Whisper, SeamlessM4T, Docling ni Qwen3. Tampoco prueba traducción latina/griega. El trabajador sigue sin autoridad para G23/G24, promoción canónica o certificación global.

## 3. Foma y traducción de lenguas antiguas

El motor Foma está materializado desde `foma-master.zip`: 72 archivos, 797.405 bytes. El código fuente incluye Makefile para construir `foma`, `flookup`, `cgflookup` y `libfoma`.

La ruta antigua anterior dirigía el texto a GPT-OSS con un prompt especialista. Esa ruta no era un motor de traducción antiguo independiente. La revisión sustituye ese consumidor por `LOUKSNAPG2_FOMA_ANCIENT_TRANSLATION_ADAPTER/1.0`, que utiliza `flookup` sobre transductores Foma binarios fijados por hash y manifiesto.

El repositorio no contiene actualmente transductores aprobados para latín o griego antiguo. Por ello el manifiesto empieza vacío y el runtime devuelve `FOMA_TRANSLATION_RESOURCES_NOT_PROVISIONED`; no hay fallback a GPT-OSS ni a SeamlessM4T. La disponibilidad del motor se registra como presente, mientras la capacidad lingüística queda HOLD hasta provisionar recursos reales y validar ejemplos conocidos.

## 4. Whisper: defecto de empaquetado de evidencia

En la ejecución `41499840413`, los artefactos Q4/Q5 se descargaron con un subdirectorio `artifact/` debido al ancestro común de las rutas que GitHub Actions cargó. El evaluador esperaba `fullrank_manifest.json` directamente en la raíz descargada y falló antes de la inferencia. Esa ejecución no proporciona una medición WER válida para Q4/Q5.

El evaluador se amplía para reconocer tanto la disposición directa como `artifact/fullrank_manifest.json`. Si ambas existen, rechaza la ambigüedad. El workflow debe volver a ejecutarse para generar evidencia WER real. Los experimentos históricos R29/R64/R96/R192 siguen rechazados y no deben repetirse sin hipótesis nueva.

## 5. Granite Docling

El candidato Q4 reconstruyó 470 tensores y produjo 103.540.310 bytes, con error relativo de Frobenius `0.1697312603`. La inferencia bajo 1 GiB generó 256 signos de exclamación; la calidad semántica falló. El sondeo del modelo original también cargó el modelo, pero generó texto incoherente y falló semánticamente.

La siguiente prueba requerida es una comparación apareada del modelo original FP16 y Q4 con el mismo procesador, imagen, prompt, resolución, configuración de generación y límites de recursos. Debe separar errores de cuantización/reconstrucción, carga del modelo y preprocesamiento visual. El error de Frobenius no sustituye la prueba funcional. La promoción permanece bloqueada.

## 6. Otros motores

- GPT-OSS-120B: rank-1, error relativo documentado `0.998336`; adaptador de reparación no implementado.
- Qwen3-14B: rank-12, error relativo aproximado `0.996409`; adaptador de reparación no implementado.
- SeamlessM4T v2 large: salida de traducción degenerada/repetitiva; adaptador de reparación no implementado.
- Whisper large-v3-turbo: intentos de rango previos no aprobaron WER; la evaluación reciente Q4/Q5 necesita repetirse tras corregir el path de artefacto.

No se han presentado pesos reparados con evaluación semántica independiente aprobada para esos dominios. No se deben degradar criterios ni certificar por identidad/hash o por construcción del paquete.

## 7. Gate de distribución e integración

El límite técnico de distribución se mantiene en 490.000.000 bytes. La construcción debe medir el paquete completo y G23/G24 deben verificar el mismo artefacto, commit y digest. Ningún resultado de un workflow experimental separado se considera integrado hasta que sus salidas, manifiestos, bindings, runtime y pruebas se ejecuten sobre el paquete exacto.

## 8. Estado de cierre

`Foma source/build`: requiere evidencia de ejecución de CUSTOSZ V9; transductores lingüísticos no provisionados.
`Docling semantic`: FAIL; comparación FP16/Q4 pendiente.
`Whisper Q4/Q5`: evaluación anterior inválida por layout; rerun pendiente.
`GPT-OSS / SeamlessM4T / Qwen3`: reparación funcional no demostrada.
`G23`: valida integridad y estructura, no calidad semántica.
`G24`: HOLD hasta que todos los dominios y pruebas independientes pasen sobre el candidato exacto.
`Global certification`: NOT GRANTED.
`Canonical promotion`: NOT AUTHORIZED.

