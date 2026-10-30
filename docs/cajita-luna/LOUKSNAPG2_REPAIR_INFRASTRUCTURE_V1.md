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

Kestra local 1.3.45 estaba en ejecución, pero la API no respondió durante la verificación. El flujo supervisor quedó versionado en `integrations/kestra/flows/louksnapg2_custoszv9_repair_supervisor.yml`. La copia a `/var/lib/kestra/flows` falló con `ENOSPC` (sin espacio disponible), así que no está desplegado ni cargado en la instancia local. No se observó GitHub token en el entorno de ese proceso; el flujo es supervisor de solo lectura y no hace dispatch.

## Resultado y bloqueos

La infraestructura de ejecución, reconstrucción, evidencia y gates queda formalizada en esta rama. **No se afirma que los motores estén reparados ni certificados.**

El registro todavía marca GPT-OSS, SeamlessM4T, Docling y Qwen3 sin adaptadores de reparación implementados; Whisper mantiene experimentos fallidos; traducción antigua carece de recurso fuente independiente. Tampoco hay gateway GPU remoto confirmado.

Por diseño, el worker puede completar auditoría y construir un candidato; G24 permanece en `HOLD` hasta que todos los adaptadores, endpoints, pruebas semánticas y rollback pasen. G23 solo valida estructura/identidad. G24 es la única puerta de certificación; ni G23 ni G24 hacen merge o transfieren autoridad canónica.


## Reanudación de reparación funcional — 2026-10-30

### Evidencia real de la última ejecución

La ejecución GitHub Actions `40999883137` sobre `33b011c80d2146c347c2246a9a8e50d35735810c` confirmó:
- CUSTOSZ V9: worker y construcción de candidato PASS.
- Unit tests de rutas/gates: PASS.
- G23: decisión estructural PASS; el attestation falló porque el workflow identificó un predicado JSON custom como SLSA provenance.
- Evaluación semántica: bloqueada en la instalación global de paquetes Python (`Permission denied: /usr/local/lib/python3.12/dist-packages/mpmath`).
- G24: HOLD por falta de evidencia funcional y fallo de attestation G23; no hubo certificación.

### Correcciones añadidas en la rama de remediación

- Instalación del runtime Docling en venv aislado CPython 3.13, alineado con el lock; no se escribe en site-packages global.
- La falta de endpoints remotos ya no suprime la prueba CPU independiente de Docling; los dominios remotos continúan en BLOCKED.
- Se genera evidencia funcional de bloqueo si el evaluador termina sin escribir su JSON, evitando que G24 falle por ausencia de archivo sin explicación.
- G23/G24 usan tipos de predicado custom propios y archivos de predicado asociados; no declaran falsamente que esos JSON sean SLSA provenance.
- G24 descarga cada artefacto en una ruta estable y usa exactamente las mismas rutas para verificar la attestation G23 y leer su evidencia.

### Estado de despliegue GPU verificado

La cuenta Hugging Face conectada se autentica como `Plomazo`, pero no había jobs en ejecución. La prueba mínima de disponibilidad de GPU mediante HF Jobs devolvió `402 Payment Required`; no se creó ningún job, no se descargaron modelos y no se produjo consumo. En el equipo local no hay GPU NVIDIA ni Docker y la raíz del disco estaba al 100%.

La última evaluación de GitHub tampoco encontró los ocho secretos `LOUKSNAPG_REMOTE_*_URL` y `LOUKSNAPG_REMOTE_*_KEY_HEX`. Por tanto, aunque la política de modelos fija repositorios y revisiones originales, todavía no existe evidencia de que los cuatro gateways GPU estén accesibles desde GitHub Actions.

### Siguiente gate

El nuevo workflow probará primero la ejecución CPU de Granite Docling y corregirá el enlace de attestations. Los dominios GPT-OSS, Whisper, SeamlessM4T y Qwen3 seguirán FAIL-CLOSED hasta que los endpoints originales sean accesibles desde GitHub Actions y pasen inferencia semántica. G24 no puede certificar mientras esos requisitos o los adaptadores de reparación sigan bloqueados.
