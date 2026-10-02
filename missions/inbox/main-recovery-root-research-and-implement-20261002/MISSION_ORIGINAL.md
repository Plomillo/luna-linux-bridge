# MISIÓN — INVESTIGAR, ACLARAR E IMPLEMENTAR RECOVERY ROOT DE MAIN

MISSION_ID = MAIN_RECOVERY_ROOT_RESEARCH_AND_IMPLEMENT_20261002
MISSION_CLASS = MAIN_RECOVERY_ROOT_GOVERNED_IMPLEMENTATION
AUTHORITY = Louksna.md
SOURCE_CONSULTA_ID = CONSULTA-293B2030898DFA7D046E
SOURCE_CONSULTA_SHA256 = 293b2030898dfa7d046e153f7ddf002297c22b04fce5ba1a98ee8f9f3fe7f87a
SOURCE_CONSULTA_CHANNEL_RUN = 37075176968
SOURCE_CONSULTA_RESPONSE_STATE = ANSWERED
SOURCE_RECEIPT_G23 = PASS
SOURCE_RECEIPT_G24 = PASS
SOURCE_RECEIPT_G24_SCOPE = CONSULTA_RECEIPT_AND_RESPONSE_PRESENCE_ONLY
SOURCE_RECEIPT_G24_ARTIFACT_DIGEST = sha256:85da27e312c682597fff0e9a05641e9d99fa9119c7e6e6b0f77e9de45d770e0f

USER_AUTHORIZATION = EXPLICIT
RESEARCH_AUTHORIZED = TRUE
CLARIFICATION_RESEARCH_AUTHORIZED = TRUE
MATERIAL_IMPLEMENTATION_AUTHORIZED = TRUE
IMPLEMENTATION_TARGET = NEW_BRANCH_DERIVED_FROM_MAIN
DIRECT_MAIN_MUTATION_AUTHORIZED = FALSE
MERGE_TO_MAIN_AUTHORIZED = FALSE

DOCTRINE = EXTEND_DO_NOT_REPLACE
FAILURE_POSTURE = FAIL_CLOSED_WITH_CONTINUATION
NO_SILENT_OPERATIONS = ABSOLUTE
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
EVIDENCE = REQUIRED
ROLLBACK = REQUIRED
NON_REGRESSION = REQUIRED
G23 = REQUIRED
G24 = REQUIRED
CERTIFICATION_PROPAGATION = FORBIDDEN
AUTHORITY_TRANSFER = FORBIDDEN
SELF_CERTIFICATION = FORBIDDEN

## 0. ACTO AUTORIZATIVO

El usuario autoriza explícitamente promover la consulta anterior a una MISIÓN nueva y trazable.

La consulta original NO se muta.
La consulta original conserva su SHA-256 e identidad.
Esta misión es un nuevo acto autorizativo derivado de ella.

## 1. ORDEN DE EJECUCIÓN

FASE_A = INVESTIGAR
FASE_B = ACLARAR_LO_NECESARIO
FASE_C = VALIDAR_EVIDENCIA_SUFICIENTE
FASE_D = IMPLEMENTAR_EN_RAMA_NUEVA_DESDE_MAIN
FASE_E = VERIFICAR
FASE_F = G23_INDEPENDIENTE
FASE_G = G24
FASE_H = DEVOLVER_RESULTADO_Y_NEXT

No saltar fases.

## 2. INVESTIGACIÓN OBLIGATORIA PREVIA

Cerrar, como mínimo, los cuatro puntos que CUSTOSZ declaró pendientes:

1. fresh physical state
2. current project identity
3. current resource leases
4. provider readiness

Además, aclarar cualquier otro blocker material que aparezca durante la investigación.

Si falta evidencia:
- buscar evidencia adicional por canales autorizados;
- registrar HOLD sólo cuando exista blocker real;
- exponer NEXT exacto;
- no fabricar PASS.

## 3. IMPLEMENTACIÓN AUTORIZADA

Cuando la evidencia sea suficiente, implementar materialmente una raíz mínima y endurecida de recuperación/continuidad en una NUEVA rama derivada de `main`.

La raíz debe actuar como:
- TRUST_ROOT
- RECOVERY_ROOT
- CONTINUITY_ROOT

Mínimo requerido:
- recovery contract;
- recovery state machine;
- manifest;
- checkpoint pre-mutation;
- rollback verificable;
- provider registry/equivalence;
- anti-parálisis acotado;
- promoción sólo por canal autorizado;
- live-state verification;
- HOLD informativo y reanudable;
- NEXT gobernado por gates;
- selftests deterministas;
- negative tests;
- evidence/provenance/traceability/auditability.

## 4. RESTRICCIONES

- NO modificar `main` directamente.
- NO fusionar a `main`.
- NO mutar `Louksna.md`.
- NO elevar `PUAC2.md` a autoridad canónica.
- NO heredar certificaciones.
- NO sustituir G23 por productor.
- NO sustituir G24 por productor o G23.
- NO reducir garantías por el antiguo HTTP 403.
- NO convertir workflow success en mission success.
- NO ampliar permisos silenciosamente.

## 5. RECUPERACIÓN / HOLD / NEXT

HOLD != DEAD_END
HOLD != START_OVER
HOLD != RETRY_FOREVER

Todo HOLD debe registrar:
BLOCKER
CAUSE
EVIDENCE
LAST_VALID_CHECKPOINT
FAILED_METHOD
FAILED_METHOD_HASH
ALTERNATIVES_AVAILABLE
ALTERNATIVES_ALREADY_TRIED
NEXT_AUTHORIZED_ACTION
RESUME_CONDITION
HUMAN_ACTION_REQUIRED
RESUME_FROM
NEXT_TARGET

NEXT sólo será válido si:
CURRENT_STEP_COMPLETE = TRUE
POST_VALIDATION = PASS
NON_REGRESSION = PASS
G23 = PASS
G24 = PASS
LIVE_STATE_MATCHES_CERTIFIED_STATE = TRUE
UNRESOLVED_CRITICAL_HOLD = FALSE

## 6. SALIDA OBLIGATORIA

RESEARCH_RESULT
EVIDENCE_GAPS
CLARIFICATIONS_RESOLVED
CAN_IMPLEMENT = TRUE | FALSE | HOLD
IMPLEMENTATION_BRANCH
IMPLEMENTATION_COMMIT_SHA
IMPLEMENTED_COMPONENTS
FORBIDDEN_COMPONENTS_PRESERVED
SELFTEST_RESULT
NEGATIVE_TEST_RESULT
ROLLBACK_RESULT
NON_REGRESSION_RESULT
PROVENANCE_RESULT
TRACEABILITY_RESULT
AUDIT_RESULT
G23_RESULT
G24_RESULT
LIVE_VERIFY_RESULT
MAIN_UNCHANGED = TRUE | FALSE
EXACT_NEXT_ACTION
HUMAN_ACTION_REQUIRED

## 7. CRITERIO DE ÉXITO

SUCCESS sólo si:
- investigación cerrada con evidencia suficiente;
- implementación material existe en rama nueva derivada de main;
- main permanece intacta;
- pruebas funcionales y negativas pasan;
- rollback y no-regresión pasan;
- G23 independiente pasa;
- G24 pasa;
- live verification coincide con el estado certificado;
- no existe HOLD crítico sin resolver.

FIN DE MISIÓN.
