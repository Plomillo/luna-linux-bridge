# MISIÓN — PROMOCIÓN CANÓNICA ENDURECIDA DEL MAIN RECOVERY ROOT

MISSION_ID = MAIN_RECOVERY_ROOT_PROMOTE_HARDENED_20261002
MISSION_CLASS = MAIN_RECOVERY_ROOT_HARDENED_PROMOTION
AUTHORITY = Louksna.md
ASSURANCE_REFERENCE = PUAC2.md
SOURCE_CANDIDATE_BRANCH = staging/main-recovery-root-48b42b6bc985-37076800748
SOURCE_CANDIDATE_SHA = 2a5057a2b47c122476a8fc90b756fdf8d942ebc5
EXPECTED_MAIN_SHA = 48b42b6bc985450c380c601d07ac1285e1e755f5

USER_AUTHORIZATION = EXPLICIT
PROMOTION_TO_MAIN_AUTHORIZED = TRUE
DIRECT_MAIN_UPDATE_AUTHORIZED = TRUE_IF_AND_ONLY_IF_PRECOMMIT_GATES_PASS
MATERIAL_IMPLEMENTATION_AUTHORIZED = TRUE
MERGE_SCOPE = recovery/
RESEARCH_EVIDENCE_IN_MAIN = FORBIDDEN
DOCTRINE = EXTEND_DO_NOT_REPLACE
CONSTRUCTION = ADDITIVE_ONLY
FAILURE_POSTURE = FAIL_CLOSED
NO_SILENT_OPERATIONS = ABSOLUTE
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
ROLLBACK = REQUIRED
NON_REGRESSION = REQUIRED
G23_PRE = REQUIRED
G24_PRE = REQUIRED
G23_POST = REQUIRED
G24_POST = REQUIRED
CERTIFICATION_PROPAGATION = FORBIDDEN
AUTHORITY_TRANSFER = FORBIDDEN
SELF_CERTIFICATION = FORBIDDEN
TOCTOU_GUARD = REQUIRED

## 1. PROMOCIÓN CRIPTOGRÁFICAMENTE CERRADA

El único candidato fuente admisible es exactamente:
2a5057a2b47c122476a8fc90b756fdf8d942ebc5

El único baseline de main inicialmente autorizado es exactamente:
48b42b6bc985450c380c601d07ac1285e1e755f5

Congelar y registrar hashes, diff, alcance, actor, permisos, checkpoint y provenance antes de cualquier actualización de main.
Cualquier divergencia de candidato o baseline obliga ABORT/HOLD.
Louksna.md permanece autoridad única; PUAC2.md permanece referencia de aseguramiento subordinada.

## 2. HARD GATE PRE-INTEGRACIÓN

La integración candidato -> main es un sujeto nuevo de aseguramiento y NO hereda G23/G24 del candidato.

Antes de tocar main:
- reconstruir una promotion candidate derivada byte-exactamente del EXPECTED_MAIN_SHA;
- incorporar exclusivamente recovery/ desde SOURCE_CANDIDATE_SHA;
- excluir recovery-evidence/ y toda infraestructura temporal;
- ejecutar selftests, negative tests, boundary/scope checks, provenance, trazabilidad, auditabilidad, no-regresión y rollback verificable;
- demostrar Louksna.md y PUAC2.md sin mutación;
- ejecutar G23 independiente;
- ejecutar G24 únicamente después de G23=PASS.

Si cualquier gate obligatorio != PASS: PROMOTION_DENIED.

## 3. COMMIT TRANSACCIONAL ATÓMICO

Sólo después de G23_PRE=PASS y G24_PRE=PASS:
- comprobar nuevamente que remote main == EXPECTED_MAIN_SHA;
- prohibir force-push;
- promover únicamente el commit certificado por fast-forward;
- si main cambió entre precheck y commit: ABORT por TOCTOU;
- no arrastrar ramas, evidencia temporal, permisos o artefactos fuera de recovery/.

Fallo:
FAIL -> ABORT -> RESTORE/RETAIN_CHECKPOINT -> VERIFY_RESTORATION -> RECORD_FAILURE -> AUDIT.
Ningún commit parcial entra ACTIVE.

## 4. CERTIFICACIÓN TERMINAL DEL ESTADO VIVO

Después de la actualización:
- el sujeto pasa a ser el SHA real de main;
- ejecutar selftests y negative tests sobre ese SHA;
- demostrar que sólo recovery/ cambió respecto del checkpoint;
- demostrar Louksna.md y PUAC2.md idénticos al baseline;
- verificar rollback local reproducible al checkpoint;
- ejecutar G23_POST independiente;
- ejecutar G24_POST terminal;
- verificar live state == certified state.

Sólo:
ALL_REQUIRED_GATES=PASS AND LIVE_STATE_MATCH=TRUE AND ROLLBACK=PASS AND NON_REGRESSION=PASS
=> MAIN_RECOVERY_ROOT=ACTIVE

En cualquier otra combinación:
HOLD_OR_ABORT; ACTIVE=FALSE; preservar evidencia.

## SALIDA OBLIGATORIA

MISSION_RECEIVED
SOURCE_CANDIDATE_SHA
CHECKPOINT_MAIN_SHA
PROMOTION_CANDIDATE_SHA
PRECHECK_RESULT
SELFTEST_RESULT
NEGATIVE_TEST_RESULT
ROLLBACK_RESULT
NON_REGRESSION_RESULT
G23_PRE_RESULT
G24_PRE_RESULT
MAIN_UPDATE_RESULT
LIVE_MAIN_SHA
G23_POST_RESULT
G24_POST_RESULT
LIVE_VERIFY_RESULT
MAIN_RECOVERY_ROOT = ACTIVE | HOLD | ABORT
EXACT_NEXT_ACTION
HUMAN_ACTION_REQUIRED

FIN DE MISIÓN.
