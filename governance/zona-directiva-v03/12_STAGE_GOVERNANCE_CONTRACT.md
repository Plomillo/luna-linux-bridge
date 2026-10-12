# CONTRATO DE GOBERNANZA OPERACIONAL — ZONA DIRECTIVA V0.3
CONTRACT_ID = LOUKSNA-ZD-V03-12-STAGE-GOVERNANCE-20261009
AUTHORITY = Louksna.md
ASSURANCE = PUAC2.md
TARGET_REPOSITORY = Plomillo/luna-linux-bridge
TARGET_WORK_BRANCH = work/louksna-zona-directiva-v0.3-functional-20261006
GOVERNANCE_BRANCH = governance/louksna-zd-v03-12-stage-gates-20261009
DOCTRINE = EXTEND_DO_NOT_REPLACE
FAILURE = FAIL_CLOSED
NO_MAIN_MUTATION = TRUE
NO_AUTO_MERGE = TRUE
NO_AUTO_CERTIFICATION = TRUE
NO_SILENT_OPERATIONS = TRUE
EVIDENCE_REQUIRED = TRUE
TRACEABILITY_REQUIRED = TRUE
ROLLBACK_REQUIRED = TRUE
G23_INDEPENDENT_VALIDATION_REQUIRED = TRUE
G24_CERTIFICATION_REQUIRED = TRUE
ACTIVE = FALSE

## 1. OBJETO Y ALCANCE

Este contrato impone un flujo operacional secuencial para completar la misión MIS-LOUKSNA-ZD-V03-FUNCTIONAL-20261006. No reemplaza la misión original, Louksna.md, PUAC2.md, el baseline V0.2 ni el trabajo existente. La rama V0.3 sigue siendo candidata de desarrollo hasta que se completen validación independiente G23 y certificación G24 sobre artefactos exactos y evidencia suficiente.

El contrato gobierna el orden, los checkpoints, los criterios de entrada/salida, la telemetría y la detención por fallo. No afirma que una función esté implementada o probada solo porque exista código, documentación, un workflow o un artefacto compilado.

## 2. REGLAS INNEGOCIABLES

1. Ejecutar las etapas en orden 01→12. No iniciar la etapa N+1 antes de que el checkpoint CP-N haya sido evaluado PASS para el mismo candidato/digest.
2. Cada checkpoint requiere evidencia material, ligada al SHA del commit candidato y a los hashes de los artefactos examinados. Una etiqueta textual PASS sin evidencia verificable no satisface el gate.
3. HOLD, FAIL, evidencia ausente, inconsistencia de hashes, workflow cancelado o resultado ambiguo impiden avanzar. No se permite auto-promover HOLD/FAIL a PASS.
4. No modificar `main`, la autoridad canónica, ni el baseline V0.2. No hacer merge automático. No activar ni certificar automáticamente.
5. Todo cambio de etapa produce evento de telemetría con timestamp UTC, contract_id, mission_id, stage_id, checkpoint_id, branch, commit SHA, run ID/URL cuando exista, resultado, pruebas, artefactos/hash, bloqueos y rollback pointer.
6. No registrar secretos, tokens, contenido sensible ni credenciales en logs, artefactos o manifiestos.
7. Los trabajos deben ser idempotentes cuando sea posible; concurrencia serializada; un cambio del commit candidato invalida los checkpoints posteriores ligados al digest anterior.
8. Los artefactos de evidencia se conservan con retención explícita y enlace al run. No se infiere instalación física en equipo real desde una prueba en contenedor.
9. El sistema se detiene ante una condición no contemplada y requiere diagnóstico, checkpoint nuevo y evidencia; no realiza reparación destructiva silenciosa.
10. G23 debe ser independiente del productor. G24 solo puede evaluar un candidato congelado y con G23 favorable. Certificación no implica activación.

## 3. SECUENCIA CANÓNICA Y CHECKPOINTS

### ETAPA 01 — Auditoría forense de mecanismos del repositorio
Objetivo: auditar ramas, protecciones disponibles, workflows, triggers, permisos, concurrency, artefactos, logs, rutas de misión, pruebas y riesgos de mutación.
Evidencia mínima: snapshot de commit/base/branch; inventario de workflows y triggers; permisos y condiciones observables; estado de PR; rutas críticas y hashes; riesgos y hallazgos con severidad.
CP-01 PASS: auditoría reproducible y hallazgos priorizados. HOLD si no se pudo verificar una propiedad de GitHub que requiere permisos/API no disponibles.

### ETAPA 02 — Contrato y plan de ejecución vinculados
Objetivo: comprobar que el contrato y el plan de 12 etapas están versionados y referenciados desde la misión/PR sin alterar autoridad canónica.
Evidencia mínima: hash del contrato, commit, branch, relación con misión, comprobación de no mutación de main/baseline.
CP-02 PASS: vínculo de gobernanza y plan secuencial comprobados.

### ETAPA 03 — Backend, SQLite y ledger de evidencia
Objetivo: verificar persistencia, escritura del ledger, orden, errores, integridad y fallos inducidos.
CP-03 PASS: pruebas de runtime positivas y negativas y eventos ligados a operaciones; error de evidencia impide declarar éxito.

### ETAPA 04 — Credenciales, GitHub READ-ONLY y puente remoto
Objetivo: comprobar Secret Service, eliminación verificable del token, permisos mínimos, API real, límites HTTPS/timeout/tamaño, lista de destinos permitidos y validación de esquema.
CP-04 PASS: pruebas reales sin exposición de secretos; el bridge remoto requiere round-trip con endpoint autorizado.

### ETAPA 05 — Estado real y telemetría de interfaz
Objetivo: vincular el estado UI con health probes y ledger reales; evitar estados estáticos que aparenten actividad.
CP-05 PASS: estados PASS/DEGRADED/FAIL/UNVERIFIED demostrados mediante pruebas de fallo.

### ETAPA 06 — Funciones actuales y adjuntos
Objetivo: verificar offline, persistencia, chat local y, si se implementa, ciclo de adjuntos, hashes, límites, asociación a mensajes y limpieza.
CP-06 PASS: pruebas end-to-end de cada función declarada activa. Toda función incompleta queda marcada no implementada/no verificada.

### ETAPA 07 — Voz end-to-end y regresión de seguridad
Objetivo: probar captura, permisos, transporte y respuesta de voz reales si la función se habilita; ejecutar regresiones, pruebas adversariales y privacidad.
CP-07 PASS: evidencia de extremo a extremo; si la pila de voz no existe o no se puede probar, la etapa no puede declarar voz activa y se documenta el gate abierto. La certificación global queda bloqueada si voz es requisito obligatorio.

### ETAPA 08 — Build y paquete Debian reproducible
Objetivo: compilar frontend/Rust, construir .deb, revisar dependencias, lintian, metadatos, tamaño y SHA-256.
CP-08 PASS: build reproducible o variación explicada y aceptada; no ocultar errores de lintian con `|| true` como si fueran éxito.

### ETAPA 09 — Instalación, ejecución y rollback en Debian 13 KDE
Objetivo: instalar, iniciar y probar en entorno declarado; comprobar desinstalación/reversión y recuperación.
CP-09 PASS: evidencia real del entorno y alcance exacto. Un contenedor no se presenta como prueba de GUI física KDE.

### ETAPA 10 — Expediente y freeze candidato
Objetivo: consolidar manifiesto de evidencias, hashes, SBOM/dependencias disponibles, resultados, riesgos residuales y rollback pointer; congelar el digest exacto.
CP-10 PASS: expediente íntegro, consistente, auditable y ligado al candidato congelado.

### ETAPA 11 — G23 validación independiente
Objetivo: revisión independiente del digest congelado, contrato, pruebas, artefactos, evidencia y no-regresión.
CP-11 PASS: dictamen independiente favorable, hallazgos cerrados o explícitamente bloqueantes. El productor no puede autoaprobarse.

### ETAPA 12 — G24 certificación y decisión de liberación
Objetivo: verificar cadena completa, G23 favorable, evidencia íntegra, rollback y alcance de certificación.
CP-12 PASS: certificación formal vinculada al digest y alcance declarado. ACTIVE continúa FALSE salvo autorización operacional separada y explícita.

## 4. MODELO DE CHECKPOINT

Cada checkpoint debe guardar un documento JSON inmutable o versionado con:
- contract_id, mission_id, stage_id, checkpoint_id;
- candidate_branch, candidate_commit_sha, candidate_tree_sha cuando esté disponible;
- workflow_name, run_id, run_url, timestamp_utc;
- status: PASS | HOLD | FAIL;
- requirements, tests, test_results, evidence_paths, evidence_sha256;
- findings, severity, unresolved_blockers;
- previous_checkpoint_sha256 y rollback_pointer;
- validator_identity y si la validación es independiente;
- next_authorized_stage (solo N+1 si status=PASS; de lo contrario NONE).

La telemetría debe diferenciar EVENT_STARTED, EVENT_PROGRESS, CHECKPOINT_PASS, CHECKPOINT_HOLD, CHECKPOINT_FAIL y RUN_ABORTED. No emitir CHECKPOINT_PASS por la mera creación del archivo.

## 5. AUTORIZACIÓN Y DETENCIÓN

La automatización puede inspeccionar, ejecutar pruebas no destructivas, construir artefactos de candidato y producir evidencias. No puede hacer merge, desplegar, activar funciones no probadas, cambiar la autoridad, omitir checkpoints ni emitir certificación por sí misma.

Si una etapa falla: registrar el fallo, conservar logs y artefactos seguros, detener etapas dependientes, permitir corrección en la rama de trabajo y exigir nueva ejecución. La corrección invalida checkpoints posteriores si cambia el digest examinado.

## 6. ESTADO INICIAL

Este contrato recién creado no constituye evidencia de que CP-01 haya pasado. El primer workflow debe ejecutar la auditoría real y registrar su resultado. El estado inicial es:
CURRENT_STAGE = 01
CURRENT_CHECKPOINT = CP-01
STATUS = PENDING_EXECUTION
NEXT_STAGE = NONE_UNTIL_CP01_PASS

## 7. CRITERIO DE CIERRE

Solo puede declararse completado el proceso si las doce etapas y sus doce checkpoints se encuentran ligados al mismo candidato o a una secuencia explícita de nuevos digests, con invalidación correcta de evidencias obsoletas, sin mutación no autorizada y con G23/G24 documentados.

## Enmienda operativa CP-09 — ejecución integrada en VM desechable (2026-10-10)

Autorización explícita del usuario para ejecutar la prueba integrada CP-09 dentro del mismo workflow de GitHub Actions mediante una máquina virtual QEMU desechable con Debian 13 y KDE Plasma/Xorg.

- La prueba instala el paquete Debian producido por CP-08 en la misma ejecución, verifica el entorno invitado, intenta iniciar el ejecutable instalado y verifica la desinstalación/rollback.
- El informe debe identificar `runtime_environment = DISPOSABLE_QEMU_VM` y `virtual_runtime_verified = true` únicamente cuando instalación, inicio y rollback pasen y la evidencia corresponda al SHA y run exactos.
- La VM es evidencia real de ejecución en un sistema invitado Debian 13 KDE/Xorg, pero NO se presenta como prueba de GPU, monitor, audio, micrófono ni GUI física en hardware dedicado.
- CP-10 puede consumir esta evidencia virtual del mismo run si sus hashes, estado, SHA del candidato, paquete CP-08 y log coinciden. CP-11/G23 y CP-12/G24 siguen siendo puertas independientes; no hay certificación ni activación automática.
- La prueba de contenedor continúa siendo suplementaria y no sustituye a la VM.

Esta enmienda modifica el modo de ejecución de CP-09 de forma explícita y trazable; no afirma ni hereda una certificación de hardware físico.


## 8. ADENDA CONTROLADA — VOZ OBLIGATORIA Y PIPELINE REAL (2026-10-10)

VOICE_REQUIRED_FOR_TERMINAL_CERTIFICATION = TRUE
VOICE_GATE_STATUS = OPEN_UNTIL_REAL_E2E_EVIDENCE
VOICE_SIMULATION_ALLOWED = FALSE
NO_MAIN_MUTATION = TRUE
NO_AUTO_MERGE = TRUE
NO_AUTO_CERTIFICATION = TRUE

La decisión de alcance autorizada establece que la voz end-to-end es requisito obligatorio de la certificación terminal general. La implementación de código no cierra CP-07. CP-07 sólo puede pasar con evidencia del mismo candidato que demuestre captura real desde micrófono, transcripción, transporte de solicitud/respuesta, síntesis y reproducción audible; debe registrar dispositivo/entorno, versiones, hashes de modelos, timestamps, resultados y fallos. Los dobles de prueba, audio sintético y las comprobaciones estáticas no satisfacen el gate.

La ruta implementada para Linux es: ALSA `arecord` (captura limitada a 8 s) → `whisper-cli` de whisper.cpp → endpoint local Ollama (por defecto `http://127.0.0.1:11434/api/chat`) → Piper TTS → ALSA `aplay`. El backend tiene preflight explícito, límites temporales, validación de endpoint HTTP local/HTTPS, límites de texto, archivos temporales con limpieza best-effort y eventos de ledger que no almacenan transcripción ni respuesta. El resultado de una ejecución se denomina `E2E_EXECUTED_NOT_CERTIFIED`; no activa ni certifica el sistema.

Dependencias declaradas: `alsa-utils`, `whisper-cli` (whisper.cpp), modelo Whisper local, `piper`, modelo de voz Piper local, servicio Ollama local y modelo Ollama. El manifiesto de release deberá registrar origen confiable, versión y SHA-256 de cada binario/modelo. No se descargan modelos ni ejecutables silenciosamente y el repositorio no los incorpora. `wait-timeout` limita los procesos externos.

CP-07 permanece OPEN hasta que el pipeline se ejecute en un equipo con micrófono/salida de audio real y la evidencia sea revisada. QEMU, tests unitarios, preflight, compilación y mocks de UI no prueban hardware de audio. CP-10, CP-11/G23 y CP-12/G24 deben seguir bloqueados mientras falte evidencia CP-07. Cualquier cambio posterior del candidato invalida checkpoints ligados al SHA anterior.


## 9. ENMIENDA ADITIVA AUTORIZADA — CP-07 ESTÍMULO ACÚSTICO AUTOMATIZADO (2026-10-12)

AUTHORIZATION = EXPLICIT_USER_APPROVAL
CHANGE_TYPE = APPEND_ONLY
LEGACY_LIVE_OPERATOR_MODE = PRESERVED
AUTOMATED_HUMAN_RECORDED_STIMULUS_MODE = AUTHORIZED
PHYSICAL_SPEAKER_TO_PHYSICAL_MICROPHONE = REQUIRED
SYNTHETIC_INPUT = FORBIDDEN
VIRTUAL_LOOPBACK_OR_NULL_AUDIO = FORBIDDEN
USER_REPEAT_UTTERANCE = NOT_REQUIRED
VOICE_MODEL = es_ES-sharvard-medium.onnx
PIPER_SPEAKER_ID = 1
PROJECT_WORKLOAD_MEMORY_MAX_BYTES = 1073741824
NO_MAIN_MUTATION = TRUE
NO_AUTO_MERGE = TRUE
NO_AUTO_CERTIFICATION = TRUE
FAIL_CLOSED = TRUE

### 9.1 Scope and non-replacement

Esta enmienda se añade al contrato sin borrar ni reescribir el criterio histórico de CP-07. Mantiene la modalidad de operador en vivo como ruta válida y añade una modalidad de estímulo acústico automatizado, basada en una grabación de voz humana con licencia y procedencia verificables. La autorización expresa recibida el 2026-10-12 permite desarrollar esta ruta aditiva. No autoriza cambiar otros checkpoints, rebajar umbrales, declarar PASS por anticipado, fusionar la PR ni modificar main.

La modalidad automatizada demuestra una ruta acústica física de entrada/salida; no se etiqueta como una locución en vivo del usuario. El estímulo debe ser una grabación humana publicada con licencia permisiva verificable (preferentemente CC0), obtenida de una fuente fijada por URL/release, con texto de referencia, licencia, idioma, tamaño y SHA-256 comprobados. No se acepta voz generada por TTS como estímulo de entrada ni una fuente sin procedencia verificable.

### 9.2 Required chain

1. Verificar el SHA del candidato, la procedencia/licencia/hash del clip y el manifiesto del runtime antes de activar el audio.
2. Verificar que la captura y la reproducción seleccionadas son endpoints físicos reales; rechazar dispositivos virtuales, monitor/loopback, null o dummy.
3. Reproducir el clip humano por el altavoz físico mientras arecord captura simultáneamente por el micrófono físico. La transcripción debe proceder de esa captura física, no directamente del archivo fuente.
4. Comparar la transcripción capturada con el texto de referencia mediante un umbral de contenido conservador; un fallo de idioma, señal, contenido o hash deja CP-07 en HOLD/FAIL.
5. Pasar el texto reconocido por el endpoint de respuesta local permitido; exigir respuesta no vacía y éxito HTTP.
6. Sintetizar la respuesta usando el modelo de voz preservado es_ES-sharvard-medium.onnx con speaker_id=1; reproducirla por el altavoz físico.
7. Capturar de nuevo con el micrófono físico durante la reproducción y validar energía acústica, transcripción de salida y solapamiento de contenido. La reproducción por comando/exit code sola no prueba la ruta acústica.
8. Imponer y medir un límite combinado de memoria del workload de 1 GiB. Si la métrica desaparece, no puede leerse o rebasa el límite, abortar el turno y mantener CP-07 en HOLD; nunca inferir un PASS por ausencia de telemetría.
9. Verificar limpieza de archivos temporales; conservar solo manifiestos/logs no sensibles, hashes y evidencia mínima, sin audio crudo, transcripción ni respuesta en el expediente.
10. Enlazar todos los resultados al SHA exacto del candidato, run, timestamp UTC, versiones, fuentes, hashes de modelos/binarios, IDs de dispositivos y hash del log. Cualquier nuevo commit invalida la evidencia anterior.

### 9.3 Evidence semantics and gate

La modalidad automatizada puede producir evidencia física candidata y un resultado de ejecución, pero no una attestation humana de audibilidad ni una certificación independiente. El artefacto debe identificar explícitamente stimulus_mode=HUMAN_RECORDED_PHYSICAL_ACOUSTIC, live_user_utterance=false, physical_microphone_capture=true y physical_speaker_playback=true, junto con la procedencia del clip. La ausencia de cualquier prueba material mantiene CP-07 OPEN/HOLD. G23 sigue siendo independiente y G24 no puede ejecutarse sin G23 favorable y expediente CP-10 válido.

La primera ejecución tras esta modificación es exploratoria y no certificadora. El cambio de código y el cambio de contrato crean un nuevo SHA candidato; ninguna evidencia anterior se hereda automáticamente.


### 9.4 Fixture inicial fijado por procedencia

- Fuente/atribución: Hola_fer.wav, por leoncillo; licencia CC0-1.0; página de origen: https://freesound.org/people/leoncillo/sounds/423843/.
- URL del preview de origen: https://cdn.freesound.org/previews/423/423843_3215099-lq.mp3.
- SHA-256 del preview MP3 verificado antes de normalización: 1aa9fcf9a210c256a15a6f8682eeda65b17fd86ba3e37873303d5b9a60b972cf.
- Referencia textual mínima verificada desde el título/descripción de origen: hola. Esta referencia es un ancla de contenido de una sola palabra, no una transcripción completa del clip.
- La etapa hosted normaliza el preview a WAV PCM16, mono, 16 kHz, sin metadatos; el SHA-256 de esa forma normalizada se calcula por ejecución y se transmite junto al artefacto al runner físico. La manifestación liga ambos hashes al candidato y al run.
- La fuente se usa solo como estímulo de entrada. La respuesta de Louksna debe seguir recorriendo modelo local, Piper con es_ES-sharvard-medium.onnx/speaker_id=1, altavoz físico, recaptura por micrófono físico y comprobación de contenido.


### 9.5 Deterministic fixture preparation

El preview CC0 de origen dura aproximadamente 0,473 s. Para mejorar la oportunidad de reconocimiento sin fabricar voz, la etapa hosted repite la grabación humana tres veces, limita la secuencia a 1,5 s y la normaliza a PCM16 mono 16 kHz. La repetición no es TTS ni una señal sintética. Se verifican y registran por separado el SHA-256 del MP3 de origen y el SHA-256 del WAV normalizado; el manifiesto contiene la transformación, versión de ffmpeg, duración, tamaño y SHA del candidato/run. La evidencia final validada conserva el manifiesto.
