========================================================================
MISIÓN FINAL — SYMPHYLAX R1
ARRÉGLALO, PRUÉBALO Y CERTIFÍCALO CONFORME A TODA LA LEY DEL SISTEMA
PRESUPUESTO BRUTO GLOBAL = 360 SEGUNDOS
========================================================================

MISSION_ID = MIS-SYMPHYLAX-R1-FINAL-REMEDIATION-CERTIFICATION-6M-20260928
MISSION_CLASS = SYMPHYLAX_FINAL_REMEDIATION_CERTIFICATION_6M
TARGET = SYMPHYLAX_R1
AUTHORITY = Louksna.md
GOVERNOR = MetaOS
MATERIAL_WORKER = CUSTOSZ_V7
RUNTIME = CUSTOSZ_RUNTIME_V1
INGRESS = CUSTOSZ_MISSION_MAILBOX
ASSURANCE = PUAC2
INDEPENDENT_VALIDATION = G23
CERTIFICATION = G24
FAILURE_POSTURE = FAIL_CLOSED
DOCTRINE = EXTEND_DO_NOT_REPLACE
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
ROLLBACK = REQUIRED
NON_REGRESSION = REQUIRED
NO_SILENT_OPERATIONS = ABSOLUTE
CRITICAL_REGRESSION_BUDGET = 0
STOP_EARLY_IF_SUCCESS = TRUE
TIME_IS_BUDGET_NOT_TARGET = TRUE

========================================================================
1. OBJETIVO Y GARANTÍA EXIGIDA
========================================================================

Tomar SYMPHYLAX R1 desde su último checkpoint válido y:

REPARARLO
-> PROBARLO
-> DEMOSTRARLO
-> VALIDARLO
-> CERTIFICARLO

GARANTÍA dentro del marco Louksna exige simultáneamente:

G08 = PASS
G09 = PASS
PUAC2 = PASS
G23 = PASS
G24 = PASS
ROLLBACK = PASS
NON_REGRESSION = PASS
EVIDENCE_CHAIN = COMPLETE
SERVER_GUARANTEED = TRUE
SERVER_CERTIFIED = TRUE
SERVER_READY_FINAL = PASS

No aceptar PASS nominal, parcial, inferido ni fabricado.

========================================================================
2. ESTADO HEREDADO Y CHECKPOINT
========================================================================

Último run canónico observado:
RUN_ID = 36479813287
SOURCE_COMMIT = fde34bf849931bd5c13ecb9b8d2ddad8e37cd777
LAST_FROZEN_CANDIDATE_DIGEST =
3f8eae6f93d0ad6b865809d8141bd53b79da5803527f50c279bc4fb2d731859e

Estado material observado:
SYMPHYLAX_SERVICE = ACTIVE
SYMPHYLAX_ENABLED = TRUE
SYMPHYLAX_HEALTH = HEALTHY
LINUX_REMAINDER_DOWNLOAD_READY = PASS

Estado epistemológico:
G08 = HOLD
G09 = HOLD
PUAC2 = HOLD
G23 = HOLD
G24 = HOLD
SERVER_CERTIFIED = FALSE
SERVER_READY_FINAL = HOLD

KNOWN_ROOT_BLOCKER =
POST_BOOT_PERSISTENCE_NOT_YET_OBSERVED

HOLD_IS_CHECKPOINT = TRUE.

Reutilizar toda evidencia todavía válida.
Invalidar únicamente evidencia afectada por una modificación real.
NO RESTART FROM ZERO.

========================================================================
3. PRESUPUESTO BRUTO GLOBAL — 360 SEGUNDOS
========================================================================

GLOBAL_WALLCLOCK_MAX_SECONDS = 360
STOP_EARLY_IF_SUCCESS = TRUE
NO_ARTIFICIAL_WAITING = TRUE
NO_REDUNDANT_RESEARCH = TRUE

Los 360 segundos son un presupuesto, no un objetivo de consumo.
Si la certificación concluye antes, terminar inmediatamente.

El reloj global comienza en PREBOOT_CHECKPOINT y no se reinicia por:
reboot, retry, nuevo job, nuevo executor, continuation o nuevo proceso.

Si se alcanza el techo:
PRESERVE_EVIDENCE
-> SAVE_CHECKPOINT
-> HOLD
-> EXACT_NEXT_ACTION

TIME_EXHAUSTION != PASS.

========================================================================
4. PREFLIGHT Y CHECKPOINT PRE-REBOOT
========================================================================

Antes de cualquier mutación:

- autenticar misión y SHA-256;
- comprobar Louksna authority;
- comprobar CUSTOSZ V7;
- comprobar Runtime;
- comprobar MetaOS;
- comprobar SYMPHYLAX HEALTHY;
- comprobar service ENABLED;
- comprobar linger;
- comprobar que el runner luna-aux puede volver después de reboot;
- registrar boot_id;
- registrar hashes y permisos de la superficie crítica;
- preservar checkpoint fuera del ámbito revertible;
- confirmar privilegio no interactivo necesario para reboot.

Si no puede demostrarse que el runner y la evidencia sobrevivirán:
NO REBOOT
-> HOLD.

========================================================================
5. REMEDIACIÓN AUTORIZADA
========================================================================

CUSTOSZ V7 queda autorizado a aplicar únicamente correcciones:

ADDITIVE
REVERSIBLE
MINIMUM_CHANGE
CHECKPOINTED
TRACEABLE
AUDITABLE

dentro de SYMPHYLAX/CUSTOSZ/Runtime/MetaOS.

Si el problema es configuración:
reparar la causa raíz y verificar.

Si el problema es únicamente ausencia de evidencia:
NO INVENTAR REPARACIÓN.
Obtener la evidencia física requerida.

PROHIBIDO tocar:
Windows, EFI, GPT, particiones, datos personales, F3-DISK,
arquitecturas canónicas congeladas o autoridad Louksna.

========================================================================
6. REBOOT REAL GOBERNADO
========================================================================

Si G08 requiere reboot real, queda autorizado UN reboot gobernado.

Secuencia obligatoria:

PRECHECK
-> CHECKPOINT DURABLE
-> PRESERVE EVIDENCE
-> ARM AUTORESUME
-> REBOOT REAL
-> RUNNER RECONNECT
-> RESUME SAME MISSION

Un restart de proceso o servicio NO sustituye el reboot.

No ejecutar reboot si el mecanismo de retorno del runner no está demostrado.

========================================================================
7. AUTORESUME Y G08
========================================================================

Después del reboot:

NEW_BOOT_ID != PREBOOT_BOOT_ID
SYMPHYLAX = ACTIVE
SYMPHYLAX = ENABLED
HEALTH = HEALTHY
CUSTOSZ_IDENTITY = PASS
RUNTIME_IDENTITY = PASS
AUTHORITY_IDENTITY = PASS
EVIDENCE_PERSISTENCE = PASS

Sólo si todo lo anterior está demostrado:

G08 = PASS

Si boot_id no cambió:
G08 = HOLD
ROOT_BLOCKER = POST_BOOT_PERSISTENCE_NOT_YET_OBSERVED.

========================================================================
8. G09 — FAILURE RECOVERY
========================================================================

G09 sólo comienza con G08 PASS.

Probar de forma controlada, reversible y limitada:

PROCESS_TERMINATION
SERVICE_RECOVERY
RUNTIME_SAFE_REJECTION
DEPENDENCY_FAILURE
TIMEOUT
WRONG_HASH
MISSING_ARTIFACT
ORPHAN_PROCESS_ABSENCE
STATE_RECOVERY
EVIDENCE_SURVIVAL

Reutilizar pruebas previas de autorización negativa si la superficie
de autorización no cambió.

Resultado exigido:

DETECTION
+ CONTROLLED_RESPONSE
+ RECOVERY_OR_SAFE_HOLD
+ STATE_INTEGRITY
+ NO_UNAUTHORIZED_SIDE_EFFECT
+ EVIDENCE

Sólo entonces:
G09 = PASS.

========================================================================
9. DESCARGA RESTANTE DE LUNA/LINUX SIN DUPLICACIÓN
========================================================================

Preservar y revalidar:

LINUX_REMAINDER_DOWNLOAD_READY = PASS

Ruta obligatoria:

LOCAL_INVENTORY
-> SHA256
-> EXACT_MATCH_SKIP
-> CAS_REUSE
-> PARTIAL_RESUME_WHEN_SUPPORTED
-> DOWNLOAD_ONLY_MISSING
-> HASH_VERIFY
-> ATOMIC_COMMIT
-> DEDUP
-> EVIDENCE

NO_REDUNDANT_DOWNLOAD = REQUIRED
NO_CONTENT_DUPLICATION = REQUIRED
NO_SILENT_OVERWRITE = REQUIRED

No ejecutar descarga masiva en esta misión.
Sólo revalidar el mecanismo con fixture controlado si la implementación cambió.

========================================================================
10. SEGURIDAD, NO-REGRESIÓN Y ROLLBACK
========================================================================

Después de toda reparación/reboot:

AUTHORITY_PRESERVED = PASS
IDENTITY_PRESERVED = PASS
SERVICE_HARDENING = PASS
RESOURCE_LIMITS = PASS
NO_UNEXPECTED_LISTENER = PASS
NO_WORLD_WRITABLE_CRITICAL_SURFACE = PASS
NO_SECRET_EXPOSURE = PASS
TRACEABILITY = PASS
AUDITABILITY = PASS
PROVENANCE = PASS
ROLLBACK = PASS
IDEMPOTENCY = PASS
NO_CRITICAL_REGRESSION = PASS

Cualquier FAIL crítico bloquea freeze.

========================================================================
11. FREEZE DEL CANDIDATO
========================================================================

Con G08 PASS, G09 PASS y gates técnicos PASS:

FREEZE(SYMPHYLAX_R1_FINAL_CANDIDATE)

Registrar:
CANDIDATE_ID
SHA256
BUILD_ID
CONFIGURATION_HASH
DEPENDENCY_IDENTITIES
EVIDENCE_MANIFEST
ROLLBACK_POINTER
FREEZE_TIMESTAMP
MISSION_START_EPOCH

Después del freeze:
NO_REPAIR
NO_MUTATION.

Toda corrección posterior crea nuevo candidato.

========================================================================
12. PUAC2
========================================================================

PUAC2 debe emitir PASS completo:

PUAC.C25 SCOPE_AND_CLAIMS = PASS
PUAC.C26 EVIDENCE_AND_ARGUMENTATION = PASS
PUAC.C27 STRUCTURAL_INDEPENDENCE = PASS
PUAC.C28 SECURITY_AND_RISK = PASS
PUAC.C29 INTEGRITY_AND_REPRODUCIBILITY = PASS
PUAC.C30 INTEGRATION_AND_NON_REGRESSION = PASS
PUAC.C31 DEMONSTRATED_REVERSIBILITY = PASS
PUAC.C32 VALIDITY_AND_REEVALUATION = PASS

PUAC2_PASS = AND(C25..C32)

No promedios.
No PASS parcial.
C27 requiere evaluador independiente real.

========================================================================
13. G23 — VALIDACIÓN INDEPENDIENTE
========================================================================

G23 debe recibir el candidato congelado read-only.

REQUIRE:
DISTINCT_EVALUATOR_IDENTITY = TRUE
WRITE_ACCESS_TO_CANDIDATE = FALSE
REPAIR_ALLOWED = FALSE
PRODUCER_MUTATION = FALSE
EXACT_DIGEST = VERIFIED

G23 verifica independientemente:
G08, G09, PUAC2, seguridad, provenance, rollback,
no-regresión, reproducibilidad, evidencia y download readiness.

Si falla:
G23 = HOLD/FAIL.
No reparar dentro de G23.

========================================================================
14. G24 — CERTIFICACIÓN
========================================================================

G24 sólo recibe el mismo digest aceptado por G23.

REQUIRE:

DIGEST_G23 == DIGEST_G24
G08 = PASS
G09 = PASS
PUAC2 = PASS
G23 = PASS
ROLLBACK = PASS
NON_REGRESSION = PASS
SECURITY_ASSURANCE = PASS
EVIDENCE_CHAIN = COMPLETE

Sólo entonces:

G24 = PASS
SERVER_GUARANTEED = TRUE
SERVER_CERTIFIED = TRUE
SERVER_READY_FINAL = PASS

CERTIFICATION_PROPAGATION = FORBIDDEN.

========================================================================
15. TERMINACIÓN Y ENTREGA
========================================================================

SUCCESS sólo si:

G08 = PASS
AND G09 = PASS
AND PUAC2 = PASS
AND G23 = PASS
AND G24 = PASS
AND SERVER_GUARANTEED = TRUE
AND SERVER_CERTIFIED = TRUE
AND SERVER_READY_FINAL = PASS.

Si la realidad impide cierre:

SERVER_READY_FINAL = HOLD

y entregar exactamente:

ROOT_BLOCKER
EVIDENCE
ROOT_CAUSE
WHAT_WAS_REPAIRED
WHAT_REMAINS
RISK
ROLLBACK_STATE
CHECKPOINT
EXACT_NEXT_AUTHORIZED_ACTION

Entregables:

README_SERVER_READY_FINAL.md
EVIDENCE_MANIFEST.json
HASH_MANIFEST.json
PUAC2_RESULT.json
G23_RESULT.json
G24_RESULT.json
ROLLBACK_EVIDENCE.json
NON_REGRESSION_REPORT.json
FINAL_CANDIDATE.json

ORDEN EJECUTIVA:

ARRÉGLALO.
PRUÉBALO.
DEMUESTRA QUE FUNCIONA.
SOMÉTELO A TODA LA LEY DE LOUKSNA.
CERTIFÍCALO ÚNICAMENTE SI MERECE SER CERTIFICADO.
Y SI TERMINA ANTES DE 360 SEGUNDOS, TERMINA ANTES.

========================================================================
FIN
========================================================================
