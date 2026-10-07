# MISIÓN MAESTRA V0.4 — LOUKSNA ZONA DIRECTIVA

MISSION_ID = MIS-LOUKSNA-ZD-V04-MASTER-20261007
AUTHORITY = Louksna.md
SUPPORTING_ASSURANCE = PUAC2.md
EXECUTOR = CUSTOSZ_V7
EXECUTION_GOVERNOR = CUSTOSZ_RUNTIME_V1
DOCTRINE = EXTEND_DO_NOT_REPLACE
FAILURE_POSTURE = FAIL_CLOSED
NO_SILENT_OPERATIONS = ABSOLUTE
CERTIFICATION_PROPAGATION = FORBIDDEN
CANONICAL_MUTATION = FORBIDDEN
DESKTOP_COMMANDER = AUXILIAR_ONLY
TARGET = LOUKSNA_ZONA_DIRECTIVA_V0.4

## Owner objective

Ejecutar los doce puntos operativos de V0.4 con auditoría, procedencia, checkpoints,
trazabilidad, metacognición, gobernanza, anti-parálisis de segundo orden, recuperación
y resolución cerrada de errores directos e indirectos. No inventar PASS, permisos,
interfaces, voces, certificaciones ni estados que no estén materialmente demostrados.

La misión debe trabajar en rama aislada. Louksna.md no se modifica. main no se modifica.
Una certificación histórica no se propaga. Un hash, build, test o selftest no equivale
por sí solo a G23, G24 ni autorización operacional.

## Inputs congelados

V03_SOURCE_SHA = 7a1449a5d6194b6cbc3e083bf1c7ba55533ad196
V03_WORKFLOW_RUN = 37486448558
V03_DEB_SHA256 = 789f563bc812498d60d6bff4e5d900c721873f6ce0f04af4424f4d4c85fc1a31
V03_DEB_SIZE_BYTES = 16471156

REMOTE_BRIDGE_HEAD = ad95248dd78fadf45645774e0338df0f1bbc128b
REMOTE_BRIDGE_PR = 31
REMOTE_BRIDGE_CI_RUN = 36755275189
REMOTE_BRIDGE_CI_RESULT = 165/165_PASS

V03_REMOTE_BRIDGE_MERGE_BASE = d7c06ef40141d8865815c18493604655280c2f2a

CUSTOSZ_MAILBOX_REF = staging/custosz-mission-mailbox-20260928
CUSTOSZ_PYZ_SHA256 = dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2
CUSTOSZ_CAPABILITIES = 72
CUSTOSZ_FAMILIES = 9

LOUKSNA_GIT_BLOB = 1a399ab7494d6df5582436819eee557083e753ed
PUAC2_GIT_BLOB = da3b216888c86e588685d384c34dd3c481414b22

## Máquina de estados obligatoria

DECLARED -> EVIDENCED -> VALIDATED -> INDEPENDENTLY_VALIDATED -> CERTIFIED -> ACTIVE

REQUEST -> INTENT -> VALIDATION -> EVIDENCE -> PROPOSAL -> PRE_COMMIT ->
CHECKPOINT -> COMMIT -> POST_VALIDATION -> UPDATE -> ACTIVE

FAIL -> ABORT -> RESTORE_CHECKPOINT -> VERIFY_RESTORATION ->
RECORD_FAILURE -> AUDIT

UNKNOWN, CONFLICT o evidencia ausente nunca equivalen a PASS.

## Anti-parálisis de segundo orden

Ante HOLD o FAIL:
1. preservar checkpoint y evidencia;
2. clasificar la causa;
3. bloquear sólo la transición insegura dependiente;
4. continuar trabajo independiente seguro;
5. diagnosticar delta causal;
6. prohibir retry idéntico sin evidencia nueva;
7. aplicar el menor delta correctivo autorizado;
8. probar efectos directos e indirectos;
9. probar un falsador del diagnóstico;
10. emitir RESUME_RECORD explícito;
11. reanudar desde el último checkpoint verificado.

BLIND_RETRY = FALSE
SILENT_FAILOVER = FALSE
SILENT_SCOPE_EXPANSION = FALSE
SILENT_PROVIDER_CHANGE = FALSE
SILENT_VOICE_CHANGE = FALSE

## Los doce puntos operativos

### P01 — Freeze, reconciliación y admisión material
Verificar por bytes/hash/commit V0.3, Remote Bridge, CUSTOSZ V7, Runtime, Louksna.md
y PUAC2.md. Reconstruir estado vigente desde evidencia material. Los textos históricos
de PR/issues/checkpoints no prevalecen sobre HEAD/bytes/logs. Inspeccionar MetaOS.wasm
antes de atribuirle API o autoridad. Generar CHECKPOINT_01 con inputs, hashes,
dependency graph, claims preservados/invalidados y contradicciones.

PASS sólo si INPUT_SET_LOCKED_AND_RECONCILED.

### P02 — LRB_APP/0.4 tipado
Reutilizar el sustrato del Remote Bridge, no reescribirlo. Registrar CHAT,
ARTIFACT_TRANSFER, VOICE_SESSION, TRANSCRIPT, TTS, REASONING_REQUEST y
GITHUB_OPERATION como tipos versionados. Cada operación liga schema/version,
scope, mission/session identity, hash, deadline, replay state, provenance y evidence.
El POST genérico de V0.3 no es camino de confianza V0.4.

PASS sólo si TYPED_APPLICATION_PROTOCOL_OPERATIONAL.

### P03 — CUSTOSZ V7 + Runtime + límites de MetaOS
CUSTOSZ V7 es trabajador real. Runtime gobierna procesos, checkpoints, budgets,
recovery y cadena de evidencia. CUSTOSZ no es G23/G24. MetaOS sólo recibe las
funciones materialmente demostradas. Toda operación registra actor, executor,
runtime, source SHA, mission SHA, pre/post state, checkpoint, evidence y rollback.
Aplicar anti-parálisis de segundo orden ante cada HOLD.

PASS sólo con ejecución material ligada al CUSTOSZ exacto y no a un mero selftest.

### P04 — Evidencia
Distinguir LOCAL_EVENT_LOG de BRIDGE_EVIDENCE_LEDGER o integrarlos mediante
referencias criptográficas demostrables. UI: LOADING, SUCCESS, NO_CHANGE, ERROR,
UTC y delta de eventos. Probar double-click, out-of-order, refresh concurrente,
disconnect, DB ocupada, stale y respuesta vacía.

PASS sólo si EVIDENCE_UI_CAUSALLY_BOUND.

### P05 — Adjuntos gobernados
Pipeline:
SELECT -> IDENTIFY -> VALIDATE -> HASH -> PROVENANCE -> TRUST_CLASSIFICATION ->
DEDUP -> LOCAL_REGISTER -> PREVIEW -> CONFIRM -> NEGOTIATE -> TRANSFER -> ACK ->
EVIDENCE.

Content-addressed storage, SHA-256, MIME observado, tamaño exacto, procedencia,
trust, remitente, timestamps, idempotencia, retry/resume y límites. Probar MIME falso,
symlink, traversal, corrupción, oversized, parcial, duplicate y ACK perdido.

PASS sólo si ARTIFACT_TRANSFER_EXACT_AND_RECOVERABLE.

### P06 — STT y TTS
STT local: whisper.cpp permanece candidato hasta benchmark material.
PRIMARY_TTS = CHATTERBOX_ES_ES_SELF_HOSTED_API.
LOCAL_OFFLINE_VOICE = SABELA.
PIPER queda fuera de la decisión recuperada.
La implementación exacta de Sabela sólo se congela con modelo/hash/licencia/
dependencias/benchmark demostrados. READ_ALOUD y VOICE_SESSION comparten TTS_ROUTER.
No existe failover vocal silencioso.

PASS exige VOICE_IDENTITY_REPRODUCIBLE, STT_FUNCTIONAL, READ_ALOUD_FUNCTIONAL
y NO_SILENT_TTS_FAILOVER.

### P07 — Llamada E2E
CAPTURE -> VAD -> STT_LOCAL -> TRANSCRIPT -> REASONING_ADAPTER ->
RESPONSE_TEXT -> TTS_ROUTER -> AUDIO_OUTPUT.

Start/stop/mute/interruption/cancellation/timeout/reconnect/session_id/turn identity/
evidence chain. Audio de micrófono permanece local durante STT por defecto.
Chatterbox recibe texto de respuesta. Sabela es continuidad local explícita.
CPAL sólo se fija si gana prueba material. PipeWire virtual para fixtures automáticos.

PASS sólo si VOICE_CALL_END_TO_END_OPERATIONAL.

### P08 — Cinco modos de esfuerzo
Exactamente: Instantáneo, Medio, Alto, Muy alto, Pro. Sólo Chat/Llamada.
Mismo contexto, fuentes, voz, autoridad y permisos. Varía budget gobernado:
retrieval, pasadas, validaciones, revisión adversarial, tiempo/tokens y comprobación
secundaria. No afirmar control de un modo interno de ChatGPT/proveedor.
Formalizar EffortProfile y registrar perfil por turno.

PASS sólo si los cinco perfiles son observables sin drift de autoridad/contexto/voz.

### P09 — 57 capacidades GitHub
Registrar 36 repository + 21 account sin inventar grants. Cada registro:
scope, nivel, endpoint/operación, mutabilidad, riesgo, confirmation policy,
reversibilidad, último probe y evidence ref. Estado permitido:
VERIFIED_AVAILABLE, VERIFIED_DENIED, NOT_GRANTED, UNKNOWN.
Mutaciones sólo en sandbox con CREATE -> VERIFY -> UPDATE -> VERIFY ->
ROLLBACK/DELETE -> VERIFY. El repo canónico no es cobaya.

PASS sólo con censo 57/57 sin colisiones ni permisos inventados.

### P10 — Transporte bidireccional real
Conservar mTLS TLS1.3, cert cliente, pinning, scope, expiry, rate/size limits,
anti-replay, backpressure y EvidenceLedger. El loopback 127.0.0.1 no acredita
off-host. Chat/voz usan frames tipados; artifacts negocian hash/tamaño/tipo y ACK.
Etiquetar egress. Probar cert mismatch/expired, replay, host/boot/source/mission
incorrectos, reconnect, duplicate/reordered/truncated/oversize y network partition.

PASS sólo con OFF_HOST_REALTIME_RELAY materialmente probado entre extremos distintos.

### P11 — Laboratorio y T01-T28
Lanes: unit/integration, Rust/SQLite/migrations/Bridge/fault injection, Tauri GUI,
Debian 13, PipeWire virtual audio, GitHub sandbox y live-host autorizado.
Probar clean install, V0.3->V0.4, restart, offline, errores HTTP, bridge down,
timeouts, DB migration, kill/incomplete commit, rollback, reboot/postboot,
attachments, STT, TTS, llamada, esfuerzo, reconnect y GitHub capabilities.
Ejecutar PUAC2 T01-T28 sobre artefacto exacto, con énfasis T13 y T21-T28.
Ningún incidente se cierra sin diagnóstico, corrección/rollback, verificación,
no-regresión, trazabilidad y revalidación aplicable.

PASS sólo si ALL_CRITICAL_OPERATIONAL_TESTS_PASS.

### P12 — Release, G23/G24 y activación
Congelar SHA final; construir desde él .deb, SBOM, locks, manifest, SHA-256,
tamaños y evidence package. Demostrar no-regresión respecto del V0.3 exacto.
Ejecutar PUAC.C25-C32. G23 independiente sobre el objeto exacto. G24 sólo después
de G23 favorable. Verificar G23_2/G24_2 cuando el perfil reforzado aplique, con
identidades/issuers separados y cronología/scope exactos. Certificación y
autorización operacional son objetos distintos. Ejecutar rollback real y postboot
del mismo build.

ACTIVE únicamente con:
NO_OPEN_CRITICAL_CLAIM
+ ALL_REQUIRED_EVIDENCE
+ VERIFIED_ROLLBACK
+ OPERATIONAL_NON_REGRESSION
+ G23
+ G24
+ VALID_SECOND_ORDER_CHAIN
+ SEPARATE_OPERATIONAL_AUTHORIZATION
+ POSTBOOT_VERIFICATION.

## Obligaciones de evidencia por operación

Cada operación debe registrar como mínimo:
operation_id, mission_id, point_id, actor, tool/version, source commit/hash,
input hashes/sizes, dependency identities, hypothesis/justification,
expected result, actual result, validation result, direct impact,
indirect impact, metacognitive self-audit, uncertainty, regression test,
checkpoint pointer, rollback pointer, timestamps y status.

## Regla terminal

No borrar historia para ocultar errores.
No reescribir Louksna.md.
No usar main como laboratorio.
No propagar certificados.
No marcar ACTIVE desde CI.
No presentar un worker, modelo o asistente como G23/G24.
No continuar una transición insegura sólo para evitar un HOLD.
