# LOUKSNAPG — registro forense de progreso y reparación

- Fecha de registro: 2026-10-28 UTC.
- Rama de continuación: `louksnapg/phase4-resume-20261028`.
- Candidato de fases 1–3 preservado: `66f0f0d22f5e7f7d207b191b39e997d1253a3866`.
- Checkpoint de diagnóstico de fase 4: ejecución GitHub Actions `40684041184`.
- Decisión vigente: `GLOBAL_CERTIFICATION=NOT_GRANTED`.
- Política: reutilizar evidencia válida; no reiniciar fases 1–3; no publicar pesos privados; no mutar el runtime canónico sin un candidato reparado y verificable.

## 1. Defecto de política del entorno de pruebas identificado y corregido

El ejecutor `tools/louksnapg_phase2_functional.py` aplicaba un límite fijo de 1 GiB de RSS a la inferencia ejecutada en el runner hospedado. Ese límite corresponde a la inspección ligera de la PC, no al entorno de ejecución del repositorio. La evidencia previa registra para Cerebro un pico de `1,148,502,016` bytes; por tanto, el umbral local podía rechazar un ensayo en la nube aunque este hubiera sido autorizado allí.

El commit `894581c2c63f6fbdd80788a53cd758f4ecf43fed` corrige exclusivamente este control de recursos:
- exige `GITHUB_ACTIONS=true` antes de iniciar trabajo pesado;
- calcula un presupuesto de RSS del runner a partir de `MemTotal` y del límite de cgroup efectivo, dejando un 25 % de margen;
- permite un límite explícito de runner mediante `LOUKSNAPG_HOSTED_RUNNER_RSS_CAP_BYTES`, validado y registrado;
- separa `execution_pass`, `quality_pass` y `resource_pass` en la evidencia;
- registra la fuente y el valor del presupuesto y deja explícito `local_inspection_budget_applied=false`.

La corrección no cambia los pesos, no rebaja los criterios de calidad y no convierte los resultados previos en aprobados. Se añadió una prueba unitaria de admisión/contabilidad de recursos que no carga modelos ni realiza inferencia; debe pasar en GitHub Actions antes de que se considere validada esta corrección.

## 2. Evidencia funcional retenida

La ejecución de fases 2–3 `40614237594` y su evidencia siguen ligadas al candidato `66f0f0d22f5e7f7d207b191b39e997d1253a3866`. Los resultados de calidad observados fueron:
- Cerebro: salida degenerada; comprobación de respuesta fallida.
- Qwen: salida que no resuelve la aritmética de prueba; comprobación fallida.
- Traducción general: salida degenerada; comprobación fallida.
- Whisper: transcripción que no coincide con el audio conocido; comprobación fallida.
- Traducción de lenguas antiguas: no se ejecutó la función nativa; adaptador de tarea no registrado.

Los tests del enrutador pasaron en el alcance estático/estructural, pero la integración efectiva de la ruta de lenguas antiguas no quedó demostrada. El informe sintético no establece equivalencia semántica amplia ni certifica los motores.

## 3. Evidencia de pesos y referencias

El inventario privado de la PC, fingerprint `f33f25eabed2ccbe07e8917a6b69d446de2831ba6a93a7e4eb39fcfbdad1e9a1`, confirma candidatos locales V4 con identidad propia verificada por su manifiesto:
- Cerebro: 148,477,400 bytes; SHA-256 `935d226a65faca9b59a7742c7c31208ef0ba671509d475c1a4e2f3489cecc19e`; 254 pares de factores, todos de rango 1.
- Whisper: 34,877,948 bytes; SHA-256 `6f4541536bfca7899d74e962c277b7fbcd1cbc4fb7f8d101c69bcd1ea2560aa3`; 236 pares de rango 29.
- SeamlessM4T v2: 20,256,147 bytes; SHA-256 `a2ba25feb33c68b7a5ea27ff8aadeaf96f67d80fc74d169c075e14d1ff363bf5`; 864 pares, 861 de rango 4.
- Qwen3: 52,950,152 bytes; SHA-256 `9d5c2ec7d88583c016a7d48f29695915ecfe0619cbca49bdfa8708f6cf6a4604`; 282 pares de rango 12.

La alineación por metadatos entre estos candidatos y los modelos fuente es parcial en los cuatro dominios. No se leyeron tensores completos ni se calcularon hashes completos de los pesos de referencia; la inspección no ejecutó inferencia en la PC. Los manifiestos muestran identidad/integridad de los candidatos, no calidad funcional. No se promueven automáticamente al artefacto público ni sustituyen a los pesos V9 fallidos.

La auditoría anterior, ligada a otra revisión histórica, registra error relativo agregado de reconstrucción de `0.9983363410727844` para el factorizado de rango 1 de Cerebro y `0.9964088220513415` para el candidato Qwen3 de rango 12. Son evidencia de pérdida material importante, no prueba aislada de la causa única. La conclusión operativa es que volver a empaquetar los factores no recupera información descartada; se requiere una variante experimental con procedencia verificable y evaluación funcional en runner.

## 4. Traducción de lenguas antiguas

El manifiesto del dominio dice `consumer_adapter_registration.status=NOT_REGISTERED`. El inventario no encontró transductores compilados ni un recurso léxico/transductor que permita ejecutar una prueba nativa de traducción; sólo se validó la integridad del archivo `foma-master.zip`. No se reemplaza el motor por el traductor general. La reparación requiere localizar/crear un adaptador para la implementación existente y disponer de un transductor/diccionario real, seguido de una prueba conocida que compruebe la traducción producida.

## 5. Estado de la continuidad de fases

- Fases 1–3: conservar el checkpoint; no reiniciar.
- Fase 4: diagnóstico completado, causa raíz no exclusiva.
- Fase 5: bloqueada; falta `evidence/louksnapg/phase4-repair-candidate.json`, candidato privado con hashes/procedencia y secretos autenticados de descarga.
- Fase 6: pendiente de que pasen las pruebas focalizadas de fase 5.
- Fase 7: pendiente de integración y validación independiente.
- Fase 8: liberación bloqueada, incluidos G23/G24.
- Fase 9: sólo puede registrar el bloqueo; no concede certificación.

La última ejecución verificada de continuación fue [40755138299](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40755138299). El gate de admisión terminó correctamente como comprobación de control, pero su decisión fue `BLOCKED_FAIL_CLOSED`; las fases 5–7 se omitieron. Eso no es una certificación ni una reparación funcional.

## 6. Kestra, CUSTOSZ y recursos locales

Kestra está activo como servicio local, pero no hay evidencia de que la nueva definición `integrations/kestra/louksnapg_phase4_to9_supervisor.yml` esté registrada y activa en su runtime. El intento previo de registro fue rechazado con HTTP 401; el monitor que está ejecutándose corresponde a una revisión antigua y no prueba que haya lanzado fases 4–9. No se reporta ninguna ejecución de Kestra inexistente.

No se ejecutó CUSTOSZ en esta misión: en la PC se observó un servicio antiguo que apunta a CUSTOSZ V7, versión expresamente prohibida, y no se verificó un ejecutable activo e independiente de CUSTOSZ V9 con un contrato de misión trazable. La presencia de scripts o de colas de V9 no equivale a un trabajador autorizado en ejecución.

La PC se usó sólo para consultas de metadatos y estado. No se cargaron modelos, no se ejecutó inferencia, no se descargaron pesos grandes y no se modificó el runtime canónico local. La telemetría previa mostraba el volumen raíz con aproximadamente 1.63 % libre y cero inodos libres; no se hicieron limpiezas, reinicios ni escrituras de recuperación en ese dispositivo.

## 7. Defectos, consecuencia, reparación y prueba posterior

| Defecto | Consecuencia | Corrección registrada / necesaria | Verificación exigida |
|---|---|---|---|
| Presupuesto local de 1 GiB aplicado a inferencia en runner | Puede rechazar una ejecución en nube que supera el límite exclusivo de inspección local | Corregido en `894581c2...`: presupuesto de runner dinámico y estado de recursos separado del de calidad | Prueba unitaria de política en GitHub Actions; inspección de la evidencia para confirmar presupuesto registrado |
| Salidas de calidad fallidas en cuatro motores | No cumplen las tareas mínimas demostradas | No reparado todavía; requiere un candidato con pesos/procedencia verificados y cambios sólo si se localiza un defecto concreto adicional | Reejecutar únicamente los cuatro casos conocidos en el candidato exacto y comprobar calidad, hashes y memoria |
| Adaptador de traducción antigua ausente | No existe ruta nativa demostrada | Registrar adaptador sin sustituir motor; requiere transductor/diccionario real | Traducción conocida de extremo a extremo a través de la ruta del artefacto |
| Falta de manifiesto y bundle privado de reparación | La fase 5 no puede arrancar de manera verificable | Proporcionar un manifiesto genuino, hashes de origen/transformación y bundle privado autenticado; sin inventar datos | Admisión fase 4 pasa sobre el artefacto exacto, descarga y hashes de bundle coinciden |
| Kestra supervisor no registrado | Monitoría real desde Kestra no demostrada | Registro autenticado y comprobación de ID de ejecución, sólo con credenciales autorizadas | Recibo de ejecución de Kestra que observe SHA de rama y estados exactos de las fases |
| G23/G24 ausentes | La liberación integral no puede concederse | Validación independiente firmada y certificación separada ligada al mismo candidato | Verificar sujeto/hash exacto, secuencia G23 → G24, no regresión y rollback |

## Decisión

`HOLD_NOT_CERTIFIED`. La corrección de la política de RSS es una reparación real del controlador de pruebas, no de los motores. La siguiente dependencia material sigue siendo un candidato reparado con hashes y procedencia verificables, servido mediante almacenamiento privado autenticado. La certificación global sólo cambiará tras pruebas funcionales posteriores aprobadas, integración, validación independiente G23 y certificación separada G24.
