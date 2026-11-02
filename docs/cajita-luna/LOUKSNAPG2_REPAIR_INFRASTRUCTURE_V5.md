# LOUKSNAPG2 — estado de reparación de motores V5

**Tipo:** revisión documental aditiva; V1, V2, V3 y V4 permanecen intactas.  
**Rama de integración auditada:** `louksnapg2/puac2-alternative-20261029`.  
**Commit de integración examinado:** `a546d7e10713c991cc3850c7bf198ce94fa69d0d`.  
**Rama experimental Docling:** `louksnapg2/docling-q3-reconstruction-20261102`.  
**Techo global de distribución:** `490000000` bytes exactos.  
**Trabajador:** CUSTOSZ V9, artefacto SHA-256 `667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3`.  
**Política:** `APPEND_ONLY / FAIL_CLOSED / NO_AUTOMATIC_PROMOTION`.

## 1. Dictamen actual

CUSTOSZ V9 ejecutó su autoprueba 12/12 y completó inventario, compilación Foma y construcción de un candidato. La evidencia no acredita reparación de pesos: `repair_execution_performed=false`, `model_inference_performed=false`, `worker_status=BLOCKED_NO_REPAIR_EXECUTED`.

El candidato de CUSTOSZ es un `REPACKAGED_UNREPAIRED_BASELINE`, mide 371.986.546 bytes y tiene SHA-256 `976edcf4f7cf8913ecabe87133973ec604fffab2d418ecfc03d10c0a73c48dca`. Su construcción no debe presentarse como reparación funcional.

## 2. Evidencia de la ejecución CUSTOSZ V9

Workflow: [run 41542917882](https://github.com/Plomillo/luna-linux-bridge/actions/runs/41542917882), commit `a546d7e10713c991cc3850c7bf198ce94fa69d0d`.

- CUSTOSZ V9: self-test PASS 12/12.
- Compilación Foma: `make -j1 check` en copia temporal; pruebas upstream PASS.
- Smoke de lookup: `cat → dog`; `PASS_FOMA_ENGINE_LOOKUP_SMOKE`.
- Fuente Foma: árbol SHA-256 `6a026ee03fef685431dc9c352314640c799d61ad9a032840d93e96ab63d3e9e2`, 65 archivos contabilizados en esta ejecución.
- Fuente original de Cajita: no modificada por la compilación temporal.
- Construcción del candidato: PASS como construcción solamente.
- Reparación de modelos: no ejecutada.
- G23/G24: no conceden certificación por estas pruebas.

## 3. Estado por motor

### GPT-OSS-120B

La representación compacta documentada permanece rank-1 con error relativo aproximado 0,998336. La batería semántica previa en el paquete produjo salidas incoherentes para aritmética y problemas verbales. No hay adaptador de reparación ejecutado ni validación semántica aprobada. **Estado: HOLD.**

### Whisper large-v3-turbo

Los experimentos históricos R29/R64/R96/R192 permanecen rechazados. El experimento adicional INT8 del run [41542917732](https://github.com/Plomillo/luna-linux-bridge/actions/runs/41542917732), sobre `a546d7e10713c991cc3850c7bf198ce94fa69d0d`, también falló: WER 3,235294 frente al máximo 0,25. No se promueve y no se repiten rangos antiguos sin hipótesis nueva y evidencia distinta. **Estado: EXPERIMENTAL_FAILED / HOLD.**

### SeamlessM4T v2 large

La representación rank-4 y las salidas de traducción degeneradas permanecen sin reparación funcional demostrada. La batería anterior generó salidas repetitivas y semánticamente inválidas en pares EN/ES y EN/FR. No se dispone de adaptador de reparación aprobado. **Estado: HOLD.**

### Foma — traducción de latín y griego antiguo

El motor existe, está materializado, se compila y supera pruebas upstream y lookup sintético. Su ruta consumidora está conectada y fail-closed. Sin embargo, `foma_transducers/manifest.json` contiene cero transductores: no existen FST latín/griego registrados con procedencia, bytes y SHA-256. El smoke `cat → dog` sólo demuestra funcionamiento del toolkit, no traducción de latín o griego. **Estado: ENGINE BUILD PASS / LANGUAGE RESOURCES NOT PROVISIONED / HOLD.**

### IBM Granite Docling 258M

El experimento separado en [run 41505447857](https://github.com/Plomillo/luna-linux-bridge/actions/runs/41505447857) reconstruyó 470 tensores a 103.540.310 bytes. Fuente: revisión `982fe3b40f2fa73c365bdb1bcacf6c81b7184bfe`, SHA-256 `1cdad234deb1cde18ee6a586f849057f19851daf1fedce2e40aff791dbe46f61`. Candidato Q4 SHA-256 `7761c78a5384b598fad8d73237dccee678d28ffe6f3134a3362af2a053b1adc0`. Error relativo Frobenius: 0,16973126025845653.

En la evaluación aislada de 1 GiB, el candidato generó 256 signos de exclamación; no extrajo los campos de factura. Pico RSS 969.199.616 bytes, fixture SHA-256 `4d27da81310640ccd5a72653596af1cd07765f9f5f7df9c05d9ba52edb94a279`, salida SHA-256 `6bcedd0e1e34dfb98a5df2d2541dcff46f7c4c11d826e5f5b4c6369c2f7ef3bf`. **Calidad semántica: FAIL.**

La comparación FP16/Q4 apareada con exactamente el mismo protocolo sigue pendiente; el sondeo FP16 histórico también cargó y generó salida semánticamente fallida. El resultado no permite aislar aún cuantización, reconstrucción, carga o preprocesamiento visual.

La prueba Docling integrada en el paquete de la rama alternativa, run [41542917950](https://github.com/Plomillo/luna-linux-bridge/actions/runs/41542917950), terminó con `ORIGINAL_CAJITA_RUNTIME_NOT_PASS:TASK_EXECUTION_TIMEOUT`. Es un fallo de ejecución, no prueba de equivalencia semántica ni éxito.

### Qwen3-14B

La representación rank-12 con error relativo aproximado 0,996409 no ha demostrado conservación de razonamiento. La prueba funcional previa produjo texto incoherente. No existe adaptador de reparación ejecutado ni promoción autorizada. **Estado: HOLD.**

## 4. Límite de distribución

El techo autorizado es exactamente 490.000.000 bytes. La rama de reconstrucción Q4 tenía un valor interno divergente de 479.000.000 bytes; la corrección se aplicó separadamente en el commit `5b3801b4a9ece6cfd80d97a73ef8d668d0314f72` de la rama experimental Docling. La prueba de contrato correspondiente se añadió en el commit padre `6fed519ef10e26f005f56f2d6bb95ff24decc730` y el workflow se ejecuta por separado.

Este ajuste alinea el límite numérico; no convierte el candidato Q4 en funcional ni lo integra en el paquete alternativo. Toda proyección y medición final debe contar el artefacto completo, manifiestos y metadatos obligatorios.

## 5. Defecto del workflow de pruebas y corrección

El run CUSTOSZ V9 `41542917882` ejecutó correctamente las pruebas de servicio (9), Foma (5) y resolución de artefactos Whisper (4), pero el paso que construía el resumen terminó con `ValueError: invalid literal for int() with base 10: '${service_rc}'`. La causa fue interpolar variables Bash dentro de un heredoc Python citado.

La V5 añade selección segura del registro V3 con fallback V2/V1, rechazo de symlinks y pruebas específicas. También corrige el traspaso de códigos de salida mediante variables de entorno, para que el resumen no trate texto literal como código numérico.

## 6. Integración y certificación

La rama Q4 Docling continúa separada de `louksnapg2/puac2-alternative-20261029`; su candidato semánticamente fallido no se integra al paquete. El candidato CUSTOSZ de la rama de integración es una republicación del baseline. La evaluación de inferencia debe asociarse al mismo commit, digest y paquete exacto.

G23 sólo puede validar estructura e identidad; no sustituye calidad semántica. G24 permanece HOLD mientras cualquier motor o caso crítico falle, no tenga recursos lingüísticos, o carezca de evidencia de reparación, inferencia y rollback. No hay certificación global ni promoción canónica concedidas por esta revisión.

## 7. Secuencia obligatoria de cierre

`SOURCE_IDENTITY → REPAIR_ADAPTER → REPAIR_EXECUTION → REPAIR_OUTPUT → RUNTIME_OVERLAY → EXACT_PACKAGE_BUILD → INFERENCE_ON_EXACT_PACKAGE → HELD_OUT_SEMANTIC_SUITE → INDEPENDENT_G23 → G24 → ROLLBACK_VERIFICATION`.

La ausencia de cualquiera de esos enlaces mantiene el motor en HOLD. Los pesos originales, manifiestos históricos V1/V2 y documentos V1–V4 no se sustituyen ni eliminan.
