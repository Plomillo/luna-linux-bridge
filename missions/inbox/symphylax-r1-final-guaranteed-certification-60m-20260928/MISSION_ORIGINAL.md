========================================================================
MISIÓN MONOLÍTICA FINAL — SYMPHYLAX R1
AUDITORÍA FORENSE -> DIAGNÓSTICO -> REMEDIACIÓN -> G08 -> G09 -> PUAC2 -> G23 -> G24
TECHO BRUTO GLOBAL = 3600 SEGUNDOS
========================================================================

MISSION_ID = MIS-SYMPHYLAX-R1-FINAL-GUARANTEED-CERTIFICATION-60M-20260928
MISSION_CLASS = SYMPHYLAX_FINAL_GUARANTEED_CERTIFICATION_60M
PRIORITY = MAXIMUM
AUTHORITY = Louksna.md
GOVERNOR = MetaOS
WORKER = CUSTOSZ_V7
RUNTIME = CUSTOSZ_RUNTIME_V1
INGRESS = CUSTOSZ MISSION MAILBOX
SUPERVISOR = SYMPHYLAX_R1
ASSURANCE = PUAC2
INDEPENDENT_VALIDATION = G23
CERTIFICATION = G24
MONITORING = LOUKSNA_LAB_WATCH
GLOBAL_WALLCLOCK_MAX_SECONDS = 3600
FAILURE_POSTURE = FAIL_CLOSED
DOCTRINE = EXTEND_DO_NOT_REPLACE
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
ROLLBACK = REQUIRED
NON_REGRESSION = REQUIRED
NO_SILENT_OPERATIONS = ABSOLUTE
CERTIFICATION_PROPAGATION = FORBIDDEN
CANONICAL_MUTATION = FORBIDDEN
REMOTE_DESKTOP_COMMANDER = AUXILIARY_ONLY
CUSTOSZ = MATERIAL_WORKER

========================================================================
0. GARANTÍA EXIGIDA
========================================================================

GUARANTEE_REQUIRED = TRUE

GARANTÍA significa, dentro del marco Louksna:
- identidad y autoridad preservadas;
- auditoría completa y reproducible;
- trazabilidad completa;
- provenance completa;
- gobernanza efectiva;
- PUAC2 aprobado;
- G08 PASS;
- G09 PASS;
- G23 PASS por evaluador independiente sin reparación;
- G24 PASS sobre el mismo candidato congelado;
- rollback verificado;
- no-regresión crítica;
- evidencia persistente;
- ausencia de blockers críticos conocidos dentro del alcance;
- monitoring enlazado;
- SERVER_CERTIFIED = TRUE;
- SERVER_READY_FINAL = PASS.

No aceptar PASS nominal, parcial, inferido o fabricado.

OBJETIVO TERMINAL:
SERVER_GUARANTEED = TRUE
SERVER_CERTIFIED = TRUE
SERVER_READY_FINAL = PASS
PUAC2 = PASS
G08 = PASS
G09 = PASS
G23 = PASS
G24 = PASS

Si la realidad no permite demostrarlo dentro del alcance:
SERVER_READY_FINAL = HOLD
y entregar un único ROOT_BLOCKER exacto, evidencia, causa, riesgo, remediation y checkpoint.
HOLD no autoriza a inventar PASS.

========================================================================
1. CHECKPOINT HEREDADO — NO REINICIAR DESDE CERO
========================================================================

CURRENT_GATE = G08
G08 = HOLD
G09 = HOLD
G23 = HOLD
G24 = HOLD
ROOT_BLOCKER = POST_BOOT_PERSISTENCE_NOT_YET_OBSERVED
SERVER_CERTIFIED = FALSE
SERVER_READY_FINAL = HOLD
HOLD_IS_CHECKPOINT = TRUE

Reutilizar toda evidencia previa todavía válida.
Invalidar únicamente aquello afectado por cambios posteriores.
NO repetir trabajo cerrado sin una razón de validez.

========================================================================
2. ORDEN EPISTÉMICO Y OPERACIONAL OBLIGATORIO
========================================================================

OBSERVE
-> RECONSTRUCT_CURRENT_TRUTH
-> FORENSIC_AUDIT
-> SEARCH_UNKNOWN_UNKNOWNS
-> SECURITY_RISK_HUNT
-> DIFFERENTIAL_DIAGNOSIS
-> CHALLENGE_DIAGNOSIS
-> PRECHANGE_SIMULATION
-> AUTHORIZE_MINIMUM_INTERVENTION
-> CHECKPOINT
-> REMEDIATE_ROOT_CAUSE
-> VERIFY
-> REGRESSION_TEST
-> ROLLBACK_TEST
-> G08
-> G09
-> FREEZE
-> PUAC2_ASSURANCE
-> G23
-> G24
-> POST_CERTIFICATION_READONLY_ASSURANCE
-> FINAL_REPORT

INTELLIGENCE != AUTHORITY
REASONING != EVIDENCE
EXECUTION != VALIDATION
VALIDATION != CERTIFICATION
AUTO_IMPROVEMENT != AUTO_AUTHORIZATION

========================================================================
3. AUDITORÍA FORENSE INICIAL
========================================================================

Antes de reparar, reconstruir el estado real y auditar como mínimo:

- SYMPHYLAX_R1 identity, hashes, version and source commit;
- STATE_MACHINE, DEPLOYMENT_CONTRACT, CLEANUP_CONTRACT and policy;
- systemd unit, enablement, restart semantics, linger and boot dependencies;
- CUSTOSZ V7 identity/status/selftest;
- Runtime identity/selftest/state;
- MetaOS identity/interface;
- mailbox identity/routing;
- checkpoints and prior evidence;
- G08/G09 prior state;
- service health and process identity;
- file ownership, permissions and symlink boundaries;
- resource envelopes: RAM, CPU, tasks and time;
- evidence storage and persistence;
- rollback surface;
- dependency and supply-chain identity;
- authorization boundaries;
- token/secret exposure risk;
- network listener exposure;
- unexpected execution paths;
- protected scopes;
- canonical authority preservation;
- monitoring and drift controls.

La arquitectura DEBE complementar esta lista.
UNKNOWN_UNKNOWN_SEARCH = REQUIRED.
No asumir que la lista humana de riesgos es completa.

Cada conclusión:
CLAIM
EVIDENCE
SOURCE
CONFIDENCE
COUNTEREVIDENCE
OPERATIONAL_IMPACT

UNKNOWN nunca equivale a PASS.

========================================================================
4. BÚSQUEDA ACTIVA DE PELIGROS
========================================================================

Buscar de forma adversarial, entre otros:

CRITICAL_SECURITY
PRIVILEGE_BOUNDARY_FAILURE
PERSISTENCE_FAILURE
RECOVERY_FAILURE
STATE_CORRUPTION
UNAUTHORIZED_MUTATION
SUPPLY_CHAIN_DRIFT
DEPENDENCY_DRIFT
IDENTITY_DRIFT
CONFIGURATION_DRIFT
RACE_CONDITION
SILENT_FAILURE
FALSE_HEALTH_SIGNAL
FALSE_PASS
ROLLBACK_FAILURE
RESOURCE_EXHAUSTION
PERMISSION_DRIFT
SERVICE_ORDERING_FAILURE
DATA_LOSS_RISK
EVIDENCE_INVALIDATION
UNCONTROLLED_NETWORK_SURFACE
UNEXPECTED_EXECUTION_PATH
CROSS_DOMAIN_SIDE_EFFECT
CERTIFICATION_BYPASS
SECRET_LEAK
WORLD_WRITABLE_CRITICAL_FILE
UNPINNED_CRITICAL_ARTIFACT
ORPHAN_PROCESS
STALE_AUTHORIZATION

Para cada hallazgo:
OBSERVATION -> EVIDENCE -> SEVERITY -> IMPACT -> ROOT_CAUSE_HYPOTHESIS -> DISCRIMINATING_TEST -> REMEDIATION.

Si un peligro crítico está confirmado y dentro de alcance:
CONTAIN -> PRESERVE_EVIDENCE -> CHECKPOINT -> FIX_ROOT_CAUSE -> VERIFY -> REGRESSION -> ROLLBACK_VERIFY.

No ocultar problemas críticos con mitigaciones cosméticas.

========================================================================
5. DIAGNÓSTICO DIFERENCIAL
========================================================================

Separar:
SYMPTOM
ROOT_CAUSE
CONTRIBUTING_FACTOR
CORRELATED_NON_CAUSAL
UNKNOWN
UNVERIFIED_HYPOTHESIS

POST_BOOT_PERSISTENCE_NOT_YET_OBSERVED es evidencia faltante, no prueba automática de fallo.

Determinar:
1. hecho físico exacto faltante;
2. observación que prueba persistencia;
3. observación que la refuta;
4. causas alternativas;
5. prueba mínima que discrimina;
6. ruta mínima segura hacia cierre.

MINIMUM_MISSING_EVIDENCE_FIRST = TRUE.
MINIMUM_CHANGE_BIAS = TRUE.

Antes de intervenir, criticar el diagnóstico y buscar contradicciones.
Usar shadow/pre-change simulation cuando sea pertinente.

========================================================================
6. REMEDIACIÓN
========================================================================

Sólo reparar después de diagnóstico sustentado.

Toda mutación:
PRE-COMMIT -> CHECKPOINT -> CHANGE -> POST-VALIDATION -> EVIDENCE -> ROLLBACK_POINTER.

Ámbito autorizado:
capa SYMPHYLAX/CUSTOSZ/Runtime/MetaOS y artefactos TEST_ONLY necesarios para certificación.

PROHIBIDO:
Windows, EFI, GPT, particiones, datos personales, F3-DISK, arquitecturas canónicas congeladas,
mutación silenciosa de PROYECTOS, sustitución silenciosa de autoridad y certificación por propagación.

========================================================================
7. G08 — PERSISTENCIA REAL
========================================================================

G08 sólo pasa con evidencia material fresca de persistencia post-boot.

Distinguir inequívocamente:
SERVICE_RUNNING_NOW
vs
SERVICE_SURVIVED_OR_RESTORED_CORRECTLY_AFTER_REAL_BOOT.

No aceptar simulación de boot, restart parcial presentado como reboot, workflow verde,
timestamp ambiguo ni evidencia histórica presentada como observación nueva.

Si hace falta un reboot real:
preparar checkpoint durable y mecanismo de reanudación gobernada antes del reboot.
No perder la misión ni la evidencia.
Tras boot, reanudar desde G08 y no desde cero.

========================================================================
8. G09 — RECUPERACIÓN CONTROLADA
========================================================================

Sólo después de G08 PASS.

Probar de forma controlada y reversible:
- executor/process termination;
- service failure;
- runtime rejection/failure;
- dependency failure;
- timeout;
- invalid authorization;
- wrong hash;
- missing artifact;
- stale mission;
- orphan-process absence;
- state recovery;
- evidence survival.

Resultado:
DETECTION + RECOVERY_OR_SAFE_HOLD + STATE_INTEGRITY + NO_DATA_LOSS + NO_UNAUTHORIZED_SIDE_EFFECT.

G09 no puede inferirse desde G08.

========================================================================
9. DESCARGA RESTANTE DE LINUX SIN DUPLICACIÓN
========================================================================

El servidor final debe quedar capaz de descargar lo restante del Linux/Luna sin repetir bytes ya válidos.

LINUX_REMAINDER_DOWNLOAD_READY = PASS es requisito de producto.

Implementar o verificar una ruta content-addressed y reanudable:

LOCAL_INVENTORY
-> PENDING_MANIFEST
-> IDENTITY/HASH
-> EXACT_EXISTING_MATCH_SKIP
-> CAS_LOOKUP
-> PARTIAL_RESUME_WHEN_SUPPORTED
-> DOWNLOAD_ONLY_MISSING_BYTES
-> HASH_VERIFY
-> ATOMIC_COMMIT
-> DEDUP_REUSE
-> POST_VERIFY
-> EVIDENCE

Reglas:
- no descargar nuevamente un objeto cuyo hash exacto ya exista;
- no crear duplicados por nombre distinto si el contenido SHA-256 es idéntico;
- no sobrescribir silenciosamente un destino con hash diferente;
- conservar .part sólo si es reanudable y verificable;
- Range/HTTP resume cuando la fuente lo soporte;
- fallback seguro cuando no lo soporte;
- cada objeto con provenance, source URL/revision, expected hash, size, result y timestamp;
- manifestar pendientes y completados;
- UNKNOWN hash de objeto crítico => HOLD;
- massive downloads fuera de pruebas se ejecutan sólo cuando estén autorizados por manifest.

Probar el motor con fixtures controlados y demostrar deduplicación real antes de declararlo listo.

========================================================================
10. NO REGRESIÓN, ROLLBACK Y FREEZE
========================================================================

CRITICAL_REGRESSION_BUDGET = 0.

Confirmar:
identity preserved;
authority preserved;
expected functionality preserved;
security posture >= baseline;
traceability preserved;
auditability preserved;
provenance preserved;
rollback works;
no silent mutations;
no uncontrolled exposure;
no unexplained critical warnings.

Cuando G08 y G09 estén PASS y los gates técnicos estén PASS:
FREEZE(SYMPHYLAX_R1_FINAL_CANDIDATE).

Registrar digest exacto, build, config, dependencies, evidence set y rollback pointer.
Después del freeze, NO REPAIR.
Toda mutación produce un nuevo candidato.

========================================================================
11. PUAC2
========================================================================

PUAC2 es obligatorio y debe cubrir como mínimo:

PUAC.C25 = SCOPE_AND_CLAIMS
PUAC.C26 = EVIDENCE_AND_ARGUMENTATION
PUAC.C27 = STRUCTURAL_INDEPENDENCE
PUAC.C28 = SECURITY_AND_RISK
PUAC.C29 = INTEGRITY_AND_REPRODUCIBILITY
PUAC.C30 = INTEGRATION_AND_NON_REGRESSION
PUAC.C31 = DEMONSTRATED_REVERSIBILITY
PUAC.C32 = VALIDITY_AND_REEVALUATION

PUAC2 = PASS requiere todos los controles PASS.
C27 no puede ser autoasignado por el productor.
El candidato debe permanecer read-only durante assurance independiente.

========================================================================
12. G23
========================================================================

G23 se ejecuta en aislamiento efectivo respecto del productor.

Requisitos:
- distinct evaluator role/identity;
- frozen digest;
- read-only candidate;
- no repair permission;
- no mutation;
- verify all gates, hashes, rollback, no-regression, security, provenance, PUAC2 and download-dedup readiness;
- reject unknown/contradicted evidence.

Si G23 detecta fallo:
G23 = HOLD/FAIL.
No reparar dentro de G23.
La reparación crea un nuevo candidato y nueva cadena.

========================================================================
13. G24
========================================================================

G24 sólo evalúa el MISMO DIGEST aceptado por G23.

G24 requiere:
PUAC2 = PASS
G23 = PASS
G08 = PASS
G09 = PASS
ALL_TECHNICAL_GATES = PASS
ROLLBACK = PASS
NON_REGRESSION = PASS
SECURITY_ASSURANCE = PASS
MONITORING_BINDING = PASS
LINUX_REMAINDER_DOWNLOAD_READY = PASS
COMPLETE_EVIDENCE_CHAIN = PASS

Sólo entonces:
SERVER_GUARANTEED = TRUE
SERVER_CERTIFIED = TRUE
SERVER_READY_FINAL = PASS

========================================================================
14. PRESUPUESTO DE 60 MINUTOS
========================================================================

GLOBAL_BUDGET = 3600 segundos.
Es un presupuesto único, no seis relojes independientes.

Redistribuir automáticamente el tiempo no utilizado.
NO BUSY WORK.
No investigar lo ya demostrado salvo invalidación.
Priorizar pruebas con mayor poder discriminante.

Orden de prioridad:
CORRECTNESS
-> SAFETY
-> EVIDENCE
-> CRITICAL_PATH
-> CERTIFICATION
-> POST_CERTIFICATION_ASSURANCE
-> QUALITY_OF_LIFE
-> OPTIMIZATION.

Si se certifica antes:
NO MUTAR EL ARTEFACTO CERTIFICADO.

Usar el tiempo restante en:
read-only health checks;
drift detection;
monitoring validation;
log review;
rollback verification;
safe recovery drills;
documentation;
operator quality-of-life;
warning reduction;
future risk discovery;
future optimization proposals.

Toda mejora material posterior debe ir a un nuevo candidato.

========================================================================
15. COMPUTE Y AISLAMIENTO
========================================================================

HEAVY_COMPUTE = GITHUB_HOSTED_OR_EXPLICIT_CLOUD
USER_HOST_HEAVY_COMPUTE = FORBIDDEN
HOST_BOUND_EVIDENCE = SELF_HOSTED_LUNA_AUX_ONLY
MINIMUM_SUFFICIENT_RESOURCES = TRUE

Productor, G23 y G24 deben usar superficies separadas.
Mismo repositorio permitido sólo con separación efectiva demostrada.

========================================================================
16. ENTREGA OBLIGATORIA
========================================================================

Publicar evidencia machine-readable y README final con:

WHAT_WAS_FOUND
WHAT_WAS_UNKNOWN
WHAT_WAS_DANGEROUS
WHAT_WAS_FIXED
WHAT_WAS_NOT_FIXED
WHY
TIMELINE
CHANGES
TESTS
NEGATIVE_TESTS
SECURITY_FINDINGS
PUAC2_CONTROLS
G08
G09
G23
G24
FINAL_DIGEST
ROLLBACK
NON_REGRESSION
MONITORING
LINUX_REMAINDER_DOWNLOAD_READY
DUPLICATION_STATUS
RESIDUAL_RISKS
SERVER_GUARANTEED
SERVER_CERTIFIED
SERVER_READY_FINAL
ROOT_BLOCKER

========================================================================
17. REGLA TERMINAL
========================================================================

El objetivo no es conseguir un PASS.
El objetivo es demostrar si SYMPHYLAX_R1 merece el PASS.

Si lo merece:
certificar, garantizar dentro del marco Louksna y congelar.

Si no lo merece:
detenerse donde la realidad lo exija,
preservar evidencia y checkpoint,
y declarar la ruta mínima restante.

========================================================================
FIN
========================================================================
