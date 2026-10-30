# LOUKSNAPG2 — infraestructura endurecida de reparación V1

**Estado:** candidata, append-only, fail-closed.  
**Rama:** `repair/louksnapg2-custoszv9-kestra-20261029`.  
**Trabajador principal:** `vendor/CUSTOSZV9.pyz`, SHA-256 `667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3`.  
**Orquestador:** Kestra. Supervisa el flujo, no sustituye a CUSTOSZ V9 ni certifica.

## Diez componentes aplicados

1. **CUSTOSZ V9 como trabajador principal.** El workflow verifica el hash del paquete local, versión y CRFU selftest 12/12. `tools/louksnapg2_custoszv9_repair_worker.py` ejecuta una misión acotada, inventaría fuentes y fabrica un candidato separado. No emite G23/G24 ni promueve.
2. **Recuperación e identidad de fuentes.** Se validan cinco pesos compactos y sus módulos de dominio mediante `verify_integrity`. La política remota mantiene revisiones/huellas para GPT-OSS, Whisper, SeamlessM4T y Qwen3.
3. **Registro de reparadores por arquitectura.** `repair/LOUKSNAPG2_MODEL_REPAIR_ADAPTER_REGISTRY_V1.json` identifica el estado y método requerido por modelo. Adaptadores no implementados permanecen bloqueados. Whisper conserva intentos fallidos; no se repiten rangos sin nueva evidencia.
4. **Sandbox aislado.** CUSTOSZ escribe solo bajo `out/louksnapg2-worker/`; el builder trabaja en un candidato separado y no sobreescribe pesos fuente. Se mide RAM/disco y concurrencia.
5. **Reconstrucción del runtime.** Se conserva la fábrica existente. Se añade la ruta `D05_DOCLING` al router/servicio de LOUKSNAPG2. Se agrega `LOUKSNAPG_REMOTE_MODE=selective`: cuatro dominios con gateway requerido se ejecutan remotamente sin fallback local; D05 se evalúa explícitamente en el runner.
6. **Regresión semántica.** La suite exige 13 casos agrupados en seis dominios: Cerebro, análisis, traducción general, traducción antigua, transcripción y Docling. No confunde ejecución de ruta con calidad.
7. **Gate de candidato.** Integridad del bundle, tamaño, identidad del commit, hashes y validación independiente del contenedor deben coincidir. Construir no equivale a certificar.
8. **Ledger de evidencia y rollback.** Los JSON enlazan commit, hashes, worker, recursos, candidato, pruebas y blockers. El rollback elimina solo el candidato aislado y conserva los originales.
9. **Rebuild reproducible.** CUSTOSZ V9 invoca el builder sobre el checkout con SHA inmutable. El paquete y su informe quedan retenidos como artefactos de Actions.
10. **Certificación independiente automatizada.** G23 y G24 corren en jobs separados y runners distintos. Ambos informes se attestean con GitHub OIDC/Sigstore (`actions/attest` fijado a SHA); G24 verifica la attestation G23 mediante `gh attestation verify`, y exige el mismo commit/digest, todos los casos semánticos y adaptadores reparadores aprobados. No se necesitan PEM manuales ni auto-certificación.

## Auditoría local frente a LOUKSNAPG2

No se encontró un archivo `LOUKSNAPG2.md` suelto en la carpeta local inspeccionada. La distribución es un artefacto generado por GitHub Actions. El último paquete observado correspondía a la ejecución 40906522918.

En `1. PROYECTO LUNA/NOSABE/CARPETA DE MODELOS PESADOS` hay pesos originales:
- GPT-OSS: 15 fragmentos `model-00000-of-00014` a `model-00014-of-00014.safetensors`.
- Qwen3: ocho fragmentos `model-00001-of-00008` a `model-00008-of-00008.safetensors`.
- SeamlessM4T: dos fragmentos `model-00001-of-00002.safetensors`, `model-00002-of-00002.safetensors`, además de archivos `.pt`.
- Whisper: `model.safetensors` de 1,617,824,864 bytes.
- Granite Docling: candidatos GGUF, proyector multimodal y wheel Docling.

Esos pesos están presentes localmente, pero no figuran como motores externalizados en `cajita-luna-runtime/EXTERNALIZED_ASSET_PLACEMENT.json`. Ese placement enumera diez dependencias de infraestructura (Jena, Playwright, ONNX Runtime, Dagger, OPA, Rqlite, SQLite, CMake, Avalonia y Tauri), no pesos de los modelos principales. El manifiesto local `EXTERNALIZATION_MANIFEST.json` enumera 30 activos auxiliares con `external_binding=PENDING_VALIDATION` y `functional_equivalence=NOT_ESTABLISHED`; no acredita externalización funcional de los pesos originales.

La distribución sí contiene pesos compactos de seis artefactos. Eso no equivale a haber desplegado fuera del paquete los motores originales. La política remota fija cuatro identidades de modelo, pero un policy pin no demuestra que el endpoint GPU exista ni que haya ejecutado inferencia.

## Límites observados

En el equipo local, la raíz estaba al 100% (3.5 GB libres), la memoria disponible era aproximadamente 1.47 GiB y no se detectó GPU NVIDIA. No se cargaron modelos, descargaron pesos ni ejecutaron entrenamientos allí.

Kestra local 1.3.45 estaba en ejecución, pero la API no respondió durante la verificación. Se añade el flujo a `/var/lib/kestra/flows`, que es la ruta vigilada configurada. La carga/ejecución efectiva debe confirmarse en Kestra. No se observó GitHub token en el entorno de ese proceso; por ello el flujo nuevo es supervisor de solo lectura y no hace dispatch.

## Resultado y bloqueos

La infraestructura de ejecución, reconstrucción, evidencia y gates queda formalizada en esta rama. **No se afirma que los motores estén reparados ni certificados.**

El registro todavía marca GPT-OSS, SeamlessM4T, Docling y Qwen3 sin adaptadores de reparación implementados; Whisper mantiene experimentos fallidos; traducción antigua carece de recurso fuente independiente. Tampoco hay gateway GPU remoto confirmado.

Por diseño, el worker puede completar auditoría y construir un candidato; G24 permanece en `HOLD` hasta que todos los adaptadores, endpoints, pruebas semánticas y rollback pasen. G23 solo valida estructura/identidad. G24 es la única puerta de certificación; ni G23 ni G24 hacen merge o transfieren autoridad canónica.
