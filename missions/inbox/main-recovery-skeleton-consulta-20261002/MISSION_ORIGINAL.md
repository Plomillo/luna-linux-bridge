# CONSULTA — MUCHACHOS, ¿USTEDES PUEDEN IMPLEMENTARLO?

MISSION_ID = MAIN_RECOVERY_SKELETON_CONSULTA_20261002
MISSION_CLASS = MAIN_RECOVERY_SKELETON_IMPLEMENTATION_CONSULTATION
AUTHORITY = Louksna.md
ASSURANCE_REFERENCE = PUAC2.md
WORKER = CUSTOSZ V7
GOVERNOR = MetaOS
SUPERVISOR = SYMPHYLAX R1
RUNTIME = CUSTOSZ_RUNTIME_V1
INGRESS = CUSTOSZ MISSION MAILBOX
MISSION_MODE = CONSULTATION_ONLY
MATERIAL_IMPLEMENTATION_AUTHORIZED = FALSE
DIRECT_MAIN_MUTATION_AUTHORIZED = FALSE
DOCTRINE = EXTEND_DO_NOT_REPLACE
FAILURE_POSTURE = FAIL_CLOSED_WITH_CONTINUATION
NO_SILENT_OPERATIONS = ABSOLUTE
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
EVIDENCE = REQUIRED
ROLLBACK = REQUIRED
NON_REGRESSION = REQUIRED
G23 = REQUIRED_WHERE_APPLICABLE
G24 = REQUIRED_WHERE_APPLICABLE
CERTIFICATION_PROPAGATION = FORBIDDEN
AUTHORITY_TRANSFER = FORBIDDEN
SELF_CERTIFICATION = FORBIDDEN
BLIND_RETRY = FORBIDDEN
INDEFINITE_HOLD = FORBIDDEN

## 0. CONSULTA

Muchachos: ¿ustedes pueden implementar, de manera real y gobernada, el esqueleto endurecido de recuperación/continuidad para la rama `main` de `Plomillo/luna-linux-bridge`?

Esta misión NO autoriza todavía la implementación material ni la fusión a `main`. Su objeto es responder la consulta con una solución definitiva, ejecutable y demostrable.

## 1. CONTEXTO MATERIAL

Existe la issue #37:
"[MISSION] Implementar recovery root endurecida en main".

El intento de asignarla directamente al GitHub Copilot coding agent falló con:
`HTTP 403 Forbidden`.

Ese fallo NO debe reinterpretarse como imposibilidad de implementación. Debe analizarse como un bloqueo de canal y proponerse una vía alternativa gobernada.

El buzón/bridge de despacho fue reparado y existe evidencia terminal separada para su alcance. No asumir certificación fuera del alcance explícito de esa evidencia.

## 2. OBJETO ARQUITECTÓNICO A IMPLEMENTAR

El objetivo futuro es una raíz mínima y endurecida para `main` que actúe como:

- TRUST_ROOT
- RECOVERY_ROOT
- CONTINUITY_ROOT

Sin convertir `main` en runtime pesado ni en un orquestador total.

Debe cubrir como mínimo:

- recovery contract;
- recovery state machine;
- manifest;
- checkpoint antes de mutación;
- rollback verificable;
- provider registry y equivalencia;
- antiparálisis acotado;
- promoción por canal autorizado;
- verificación de estado vivo;
- HOLD informativo y reanudable;
- NEXT gobernado por gates;
- pruebas/selftests deterministas;
- evidencia, procedencia, trazabilidad y auditoría.

## 3. REGLA DE HOLD

HOLD != DEAD_END
HOLD != SILENCE
HOLD != START_OVER
HOLD != RETRY_FOREVER

Todo HOLD debe exponer:
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

HOLD debe bloquear sólo la transición insegura y permitir diagnóstico seguro, remediación diferencial y reanudación desde el checkpoint.

## 4. REGLA DE ANTIPARÁLISIS

NO_BLIND_RETRY = TRUE
NO_IDENTICAL_RETRY_WITHOUT_NEW_CAUSAL_EVIDENCE = TRUE
NO_INDEFINITE_HOLD = TRUE
NO_FULL_REPLAY_IF_DIFFERENTIAL_RECOVERY_EXISTS = TRUE
CHECKPOINT_CONTINUITY = REQUIRED
MINIMAL_REMEDIATION = REQUIRED
ALTERNATIVE_MUST_BE_EQUIVALENT = TRUE
ALTERNATIVE_MUST_BE_PINNED = TRUE
ALTERNATIVE_MUST_HAVE_PROVENANCE = TRUE
ALTERNATIVE_MUST_BE_HASHED = TRUE
CERTIFICATION_INHERITANCE = FORBIDDEN

## 5. REGLA DE NEXT

NEXT sólo es válido si:
CURRENT_STEP_COMPLETE = TRUE
POST_VALIDATION = PASS
NON_REGRESSION = PASS
REQUIRED_G23 = PASS
REQUIRED_G24 = PASS
LIVE_STATE_MATCHES_CERTIFIED_STATE = TRUE
UNRESOLVED_CRITICAL_HOLD = FALSE

Nunca:
HOLD -> NEXT
FAIL -> NEXT
G23_ONLY -> NEXT
G24_WITHOUT_LIVE_VERIFY -> NEXT

## 6. CONSULTA OBLIGATORIA A RESPONDER

Respondan con evidencia:

1. ¿Pueden ustedes implementar este esqueleto de forma material en una rama nueva derivada de `main`?
2. Si la respuesta es sí, ¿qué canal concreto usarían para construirlo y después proponer su incorporación a `main`?
3. ¿Cómo resuelven el bloqueo `HTTP 403` del canal Copilot sin rebajar ninguna garantía?
4. ¿Qué componentes mínimos construirían y cuáles NO construirían para mantener `main` pequeño?
5. ¿Cómo preservarían Louksna.md como autoridad y el estado declarado de PUAC2.md?
6. ¿Cómo separarían productor, G23, G24, canal de promoción y verificador post-commit?
7. ¿Cómo demostrarían rollback, no regresión, trazabilidad, auditoría, procedencia y evidencia?
8. ¿Cómo implementarían el antiparálisis y el HOLD reanudable para poder continuar a NEXT?
9. ¿Qué pruebas negativas harían?
10. ¿Cuál es la solución definitiva recomendada y cuál es el orden exacto de ejecución?

## 7. SALIDA OBLIGATORIA

La respuesta debe producir, como mínimo:

FEASIBILITY = YES | NO | HOLD
ROOT_CAUSE_OF_CURRENT_BLOCKER
DEFINITIVE_SOLUTION
AUTHORIZED_IMPLEMENTATION_CHANNEL
REQUIRED_COMPONENTS
FORBIDDEN_COMPONENTS
G23_PLAN
G24_PLAN
ROLLBACK_PLAN
NON_REGRESSION_PLAN
PROVENANCE_PLAN
TRACEABILITY_PLAN
AUDIT_PLAN
EVIDENCE_PLAN
ANTI_PARALYSIS_PLAN
HOLD_RESUME_PLAN
NEXT_PLAN
RISKS
EXACT_NEXT_ACTION
HUMAN_ACTION_REQUIRED

Cada afirmación material debe apuntar a evidencia verificable.

## 8. PROHIBICIONES

- No modificar `main` como consecuencia de esta consulta.
- No fusionar nada.
- No mutar Louksna.md.
- No elevar silenciosamente PUAC2.md a autoridad canónica.
- No fabricar PASS.
- No heredar certificaciones.
- No sustituir G23 por el productor.
- No sustituir G24 por el productor o G23.
- No esconder blockers.
- No usar éxito de workflow como prueba de misión completada.
- No ampliar permisos silenciosamente.
- No convertir el 403 en excusa para una ruta menos gobernada.

## 9. CRITERIO DE CIERRE DE ESTA CONSULTA

La consulta se considera respondida sólo cuando exista una respuesta reproducible y trazable que determine:

CAN_IMPLEMENT = TRUE | FALSE | HOLD

y, si CAN_IMPLEMENT = TRUE:

DEFINITIVE_IMPLEMENTATION_PATH = EXPLICIT
EVIDENCE_CHAIN = PRESENT
NEXT_AUTHORIZED_ACTION = EXPLICIT

FIN DE LA CONSULTA.
