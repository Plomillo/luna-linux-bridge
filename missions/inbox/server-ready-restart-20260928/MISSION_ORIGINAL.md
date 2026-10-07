========================================================================
MISIÓN FINAL DE INGENIERÍA
SYMPHYLAX R1 — SERVER READY PARA LUNA R4
CUSTOSZ V7 + CUSTOSZ_RUNTIME_V1 + METAOS
========================================================================

MISSION_CLASS = FORENSIC_OPERATIONAL_SERVER_HARDENING
PRIORITY = MAXIMUM
GLOBAL_WALLCLOCK_MAX_SECONDS = 1200
START = RECEIPT_VERIFIED
STOP = EARLY_IF_SUCCESS
FAILURE_POSTURE = FAIL_CLOSED
DOCTRINE = EXTEND_DO_NOT_REPLACE
OUTPUT_LOCATION = GITHUB
CONTAINER_SEMANTIC = DEFERRED_NOT_BLOCKING

OBJETIVO ÚNICO:

Dejar SYMPHYLAX R1 y su cadena
CUSTOSZ V7 -> CUSTOSZ_RUNTIME_V1 -> MetaOS
técnicamente preparados, endurecidos, trazables,
auditables, recuperables y gobernables para ejecutar
posteriormente la instalación controlada de LUNA R4.

Esta misión NO tiene como objetivo producir otra
investigación documental.

La investigación es únicamente un medio.

El producto final exigido es:

SERVER_READY_FOR_CONTROLLED_LUNA_R4_EXECUTION = PASS

o, únicamente si existe una imposibilidad técnica real:

SERVER_READY = HOLD
SINGLE_ROOT_BLOCKER = <evidencia exacta y reproducible>

No se aceptan bloqueos vagos ni múltiples pendientes
sin determinar la causa raíz.

========================================================================
0. ESTADO HEREDADO — NO REPETIR TRABAJO YA DEMOSTRADO
========================================================================

Tomar como evidencia previa válida:

- CUSTOSZ V7 recibió misión nativa real.
- Workspace LUNA_PROJECT fue resuelto.
- Heartbeat SUPERVISORY_ACTIVE fue demostrado.
- CUSTOSZ v07-status = PASS.
- CUSTOSZ v07-selftest = PASS.
- Runtime selftest = PASS.
- Runtime EvidenceJournal = PASS.
- Material dispatch = PASS.
- global_step_gate = 1.
- material_execution_proven = TRUE.
- Cadena de evidencia material existente.
- A0 fue identificado y hasheado.
- A1 fue identificado y hasheado.
- PUAC2 fue identificado y hasheado.
- MetaOS fue identificado y hasheado.
- Skeleton R4 fue identificado y hasheado.
- Misión fue identificada y hasheada.
- Firefox ya fue desinstalado.

No repetir estas pruebas salvo que un cambio realizado
durante esta misión pueda haberlas invalidado.

CONTENEDOR SEMÁNTICO:

CONTAINER_WORK = FROZEN
CAS_TRANSFER = OUT_OF_SCOPE
248_OBJECTS_PENDING = ACCEPTED_DEFERRED_STATE

El contenedor NO bloquea SERVER_READY en esta misión.

Registrar su estado y continuar.

========================================================================
1. USO OBLIGATORIO DEL CONOCIMIENTO YA ACUMULADO
========================================================================

Antes de investigar externamente:

Reunir y correlacionar TODO el expediente existente:

- Issue #5.
- PR #1–#6 aplicables.
- Runs anteriores de GitHub Actions.
- README_CONCLUSIONES_CUSTOSZ_V7.md.
- RESEARCH_EVIDENCE.json.
- CUSTOSZ_RUNTIME_R4_RESULT.json.
- F-2 / F-2.1 / F-2.2.
- Skeleton R4.
- Louksna.md.
- LOUKSNAMEJORADA.md.
- PUAC2.md.
- Manifiestos CUSTOSZ/Runtime/MetaOS.
- Evidencias del runner luna-aux.
- Evidencias de SYMPHYLAX R1.

Construir un único CURRENT_TRUTH_STATE.

Cada afirmación debe clasificarse:

OBSERVED
VERIFIED
INFERRED
EXTERNAL_SUPPORT
CONTRADICTED
UNKNOWN

No degradar evidencia ya confirmada a UNKNOWN.

No elevar inferencias a VERIFIED.

========================================================================
2. INVESTIGACIÓN EXTERNA — SOLO PARA AUMENTAR CERTIDUMBRE
========================================================================

La investigación externa está autorizada.

Objetivo:

Buscar patrones, casos iguales o comparables,
fallos conocidos y soluciones probadas que permitan
fortalecer el servidor existente.

NO utilizar investigación externa para sustituir
la arquitectura del proyecto.

NO incorporar una tecnología únicamente porque sea
popular o superior en abstracto.

ORDEN DE AUTORIDAD DE FUENTES:

TIER 0:
Evidencia propia ejecutada y reproducible.

TIER 1:
Documentación oficial y repositorios upstream.

TIER 2:
Implementaciones maduras comparables.

TIER 3:
Issues, discusiones técnicas y casos de campo.

TIER 4:
Fuentes comunitarias no verificadas.

Una modificación operacional necesita:

TIER 0 + TIER 1

o

TIER 0 + múltiples fuentes TIER 2 convergentes.

TIER 3/4 pueden generar hipótesis,
nunca autoridad por sí solas.

========================================================================
3. GITHUB — INVESTIGACIÓN OBLIGATORIA
========================================================================

Examinar principalmente:

GitHub Actions runner oficial.
Self-hosted runner security.
Runner authentication.
Ephemeral/JIT runners.
Persistencia y service lifecycle.
Runner groups y aislamiento.
Job-token lifecycle.
Permission minimization.
Workflow pinning.
Supply-chain hardening.
Recovery after failed jobs.
External evidence/log persistence.
Comparable agent/job supervisors.

Examinar también repositorios maduros relevantes cuando
aporten soluciones a problemas concretos de SYMPHYLAX.

Preguntas a resolver:

- ¿Cómo evitar contaminación entre jobs?
- ¿Cómo limitar el blast radius del runner?
- ¿Cómo conservar evidencia fuera del rollback?
- ¿Cómo autenticar una misión y su executor?
- ¿Cómo impedir que un push implique autorización humana?
- ¿Cómo restaurar automáticamente un servicio fallido?
- ¿Cómo manejar jobs huérfanos?
- ¿Cómo demostrar idempotencia?
- ¿Cómo demostrar continuidad después de una caída?
- ¿Cómo separar supervisor, executor y authority?
- ¿Cómo hacer que los tokens sean mínimos y temporales?

EXTERNAL_PATTERN != ARCHITECTURAL_AUTHORITY

Los patrones encontrados pueden fortalecer
SYMPHYLAX/CUSTOSZ/MetaOS.

No pueden reemplazarlos.

========================================================================
4. HUGGING FACE — INVESTIGACIÓN DE SOPORTE
========================================================================

Investigar únicamente aspectos que puedan fortalecer
el servidor o sus artefactos:

- revision/commit pinning.
- snapshot integrity.
- cache completeness.
- offline recovery.
- local_files_only behavior.
- artifact provenance.
- incomplete snapshot detection.
- reproducible downloads.
- GGUF/model metadata si aplica.
- safetensors/serialization safety si aplica.
- repositorios comparables de runtimes locales
  exclusivamente cuando tengan relación directa
  con un componente real de LUNA R4.

NO seleccionar un nuevo cerebro/modelo en esta misión.

NO cambiar el backend cognitivo salvo defecto
demostrado del existente.

HF_RESEARCH_ROLE = SUPPORTING_EVIDENCE_ONLY

========================================================================
5. BLOQUEADOR PRIORITARIO — RUNTIME IDENTITY
========================================================================

Resolver primero:

STAGING_RUNTIME_SHA256 =
a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67

SKELETON_RUNTIME_SHA256 =
4e9bf0e799487ea0fd6a6d32359176bdce996010e33ed151ce0f186155d11df0

Determinar exactamente:

A. Son variantes legítimas distintas.
B. El Skeleton referencia una versión anterior.
C. Existe el runtime original del pin Skeleton.
D. El staging es una reconstrucción posterior.
E. Existe un error de procedencia.
F. Existe una sustitución no documentada.

Reconstruir:

SOURCE
COMMIT
TIMESTAMP
BUILD
INPUT_HASH
OUTPUT_HASH
PARENT_VERSION
CHANGESET
PROVENANCE_CHAIN

No modificar silenciosamente el Skeleton.

No cambiar el pin para conseguir un PASS.

Resultado obligatorio:

RUNTIME_IDENTITY_RECONCILED = PASS

o evidencia exacta de por qué no es posible.

========================================================================
6. CORRECCIÓN ADITIVA DEL SERVIDOR
========================================================================

Se autorizan dentro de esta misión correcciones
ADITIVAS, REVERSIBLES y NO DESTRUCTIVAS exclusivamente
sobre la capa de servidor SYMPHYLAX/CUSTOSZ/Runtime/MetaOS.

Toda corrección requiere checkpoint previo.

No tocar:

Windows.
EFI.
GPT.
Particiones.
PROYECTOS.
Datos personales.
F3-DISK.
Arquitecturas canónicas congeladas.
Contenedor semántico.

Áreas a corregir y validar:

A. PERSISTENCIA

- Inicio correcto del supervisor.
- Inicio correcto de los componentes dependientes.
- Orden de dependencias.
- Restart policy.
- Detección de proceso muerto.
- Recuperación de proceso huérfano.
- Estado tras restart del servicio.

B. RESOURCE GOVERNANCE

Definir y comprobar límites para:

RAM.
CPU.
Número de procesos.
Tiempo.
I/O cuando sea viable.
Concurrencia.

La corrección no debe convertir LOUKSNA
en una máquina dedicada exclusivamente al servidor.

C. EXECUTOR BINDING

Demostrar:

MISSION
-> AUTHORIZATION
-> EXECUTOR
-> RUNTIME
-> MATERIAL EFFECT
-> VALIDATION
-> EVIDENCE

No permitir EXECUTOR=UNBOUND como estado SERVER_READY.

D. AUTHENTICATION / AUTHORIZATION

Una misión debe quedar ligada a:

MISSION_ID
SOURCE_COMMIT
MISSION_HASH
ACTOR
SCOPE
EXPIRATION
EXECUTOR
POLICY
CHECKPOINT

Un push, comentario, issue, workflow o temporizador
no debe convertirse por sí mismo en autorización humana.

E. SECRET HYGIENE

Verificar:

OAuth temporales.
Tokens.
GITHUB_TOKEN.
Variables de entorno.
Logs.
Archivos temporales.
Permisos.
Limpieza posterior.

Resolver el defecto previamente identificado
en authorize_cas_drive.sh si sigue presente,
aunque CAS continúe fuera de alcance.

La corrección del defecto de seguridad no implica
reanudar el contenedor.

F. EVIDENCE PERSISTENCE

La evidencia crítica debe sobrevivir a:

rollback.
restart de servicio.
fallo parcial.
workspace cleanup.

No almacenar la única copia de la evidencia
dentro del ámbito que será revertido.

G. RECOVERY

Probar de manera controlada:

executor failure.
runtime failure.
timeout.
dependency failure simulada.
invalid authorization.
wrong hash.
missing artifact.
stale mission.
process termination.

Resultado esperado:

FAIL_CLOSED
+
DIAGNOSIS
+
RECOVERY_OR_SAFE_HOLD

========================================================================
7. PRUEBA OPERACIONAL DEL SERVIDOR
========================================================================

No basta SELFTEST.

Ejecutar una misión material inocua y reversible
utilizando el servidor real.

Debe demostrar como mínimo:

1. misión recibida;
2. identidad validada;
3. autorización válida;
4. executor bound;
5. runtime activo;
6. límite de recursos activo;
7. efecto material controlado;
8. evidencia persistida;
9. post-validation;
10. rollback;
11. comprobación de rollback;
12. segundo lanzamiento idempotente;
13. rechazo de misión inválida;
14. recuperación después de matar el proceso del executor;
15. continuidad del supervisor.

No efectuar ninguna operación destructiva.

La prueba material puede crear únicamente
artefactos temporales de ensayo explícitamente
marcados TEST_ONLY.

========================================================================
8. RELACIÓN A0 / A1 / PUAC2
========================================================================

No intentar completar en veinte minutos
una auditoría semántica exhaustiva de millones de bytes
si no es necesaria para SERVER_READY.

Sí comprobar:

A0 authority preserved.
A1 identity preserved.
PUAC2 candidate status preserved.
No silent authority transfer.
No runtime rewrite of architecture.
No G23/G24 fabrication.

Construir únicamente los contratos mínimos
que el servidor necesita para operar respetando
las tres fuentes.

A0_A1_FULL_SEMANTIC_ADMISSION puede permanecer
como trabajo arquitectónico separado siempre que
no bloquee técnicamente SERVER_READY.

========================================================================
9. CERTIDUMBRE Y METACOGNICIÓN
========================================================================

Toda conclusión tendrá:

CLAIM
EVIDENCE
SOURCE
CONFIDENCE
COUNTEREVIDENCE
OPERATIONAL_IMPACT

CONFIDENCE:

C0 = UNKNOWN
C1 = PLAUSIBLE
C2 = SUPPORTED
C3 = VERIFIED
C4 = INDEPENDENTLY_REPRODUCED

SERVER_READY exige C3 en todos los gates técnicos críticos.

No rellenar ausencia de evidencia mediante inferencia.

No investigar indefinidamente.

Si tres fuentes independientes convergen y la prueba
local confirma el comportamiento:

STOP_RESEARCH
START_VALIDATION

========================================================================
10. PRESUPUESTO DE 20 MINUTOS
========================================================================

Existe un solo reloj global.

MAX = 1200 segundos.

NO reiniciar el reloj por:

retry.
workflow.
continuation.
nuevo mission_id.
nuevo executor.
nuevo job.

Prioridad temporal:

EVIDENCE_EXISTING
-> ROOT_BLOCKERS
-> TARGETED_EXTERNAL_RESEARCH
-> CORRECTIVE_PATCH
-> OPERATIONAL_TEST
-> ROLLBACK_TEST
-> FINAL_REPORT

La investigación externa debe cerrarse tan pronto
como exista evidencia suficiente para actuar.

RESERVAR como mínimo los últimos 240 segundos
para:

validation.
rollback.
evidence consolidation.
README final.

Si quedan menos de 240 segundos:

STOP_RESEARCH_IMMEDIATELY

========================================================================
11. GATES DE SERVER READY
========================================================================

GATE_01_WORKSPACE_RESOLUTION = PASS
GATE_02_CUSTOSZ_IDENTITY = PASS
GATE_03_RUNTIME_IDENTITY = PASS
GATE_04_METAOS_INTERFACE = PASS
GATE_05_EXECUTOR_BOUND = PASS
GATE_06_AUTHENTICATED_MISSION = PASS
GATE_07_RESOURCE_LIMITS = PASS
GATE_08_SERVICE_PERSISTENCE = PASS
GATE_09_FAILURE_RECOVERY = PASS
GATE_10_EVIDENCE_PERSISTENCE = PASS
GATE_11_ROLLBACK = PASS
GATE_12_IDEMPOTENCY = PASS
GATE_13_NEGATIVE_AUTH_TEST = PASS
GATE_14_NO_CANONICAL_MUTATION = PASS
GATE_15_HOST_SAFETY = PASS

SERVER_READY =
AND(GATE_01..GATE_15)

No promedios.

No PASS parcial.

No "mostly ready".

========================================================================
12. G23 / G24
========================================================================

Separar:

TECHNICAL_READY
INDEPENDENTLY_VALIDATED
CERTIFIED

El servidor puede alcanzar:

SERVER_TECHNICAL_READY = PASS

antes de una certificación externa si todos
los gates técnicos están demostrados.

Pero:

CERTIFIED = FALSE

mientras G23/G24 no hayan emitido decisiones válidas.

Si G23 y G24 pueden ejecutarse dentro del alcance
y tiempo disponible, hacerlo después del PASS técnico.

No autocertificar.

========================================================================
13. README FINAL OBLIGATORIO
========================================================================

Publicar en GitHub:

README_SERVER_READY_FINAL.md

Debe contener:

MISSION_ID
START_UTC
END_UTC
ELAPSED_SECONDS

SOURCE_COMMITS
SOURCE_HASHES

SERVER_STATE_BEFORE
CHANGES_APPLIED
SERVER_STATE_AFTER

EXTERNAL_SOURCES_USED
WHY_EACH_SOURCE_MATTERED

GATES_01_15

TESTS_EXECUTED
TEST_RESULTS
NEGATIVE_TEST_RESULTS

RESOURCE_MEASUREMENTS

FAILURES_FOUND
FAILURES_CORRECTED

ROLLBACK_TEST

RUNTIME_PROVENANCE_DECISION

KNOWN_RESIDUAL_RISKS

G23_STATUS
G24_STATUS

SERVER_TECHNICAL_READY = TRUE/FALSE
SERVER_CERTIFIED = TRUE/FALSE

SINGLE_ROOT_BLOCKER =
NONE
o evidencia exacta.

NO mezclar hechos con recomendaciones.

========================================================================
14. CRITERIO TERMINAL
========================================================================

SUCCESS solamente si:

SERVER_TECHNICAL_READY = TRUE

AND

CUSTOSZ_TO_RUNTIME_MATERIAL_PATH = PASS

AND

EXECUTOR_BOUND = TRUE

AND

AUTHENTICATION = PASS

AND

RESOURCE_GOVERNANCE = PASS

AND

RECOVERY = PASS

AND

ROLLBACK = PASS

AND

EVIDENCE_PERSISTENCE = PASS

AND

NO_CANONICAL_MUTATION = TRUE

AND

NO_PROYECTOS_MUTATION = TRUE

AND

NO_WINDOWS_DISK_MUTATION = TRUE

El contenedor semántico no forma parte del SUCCESS
de esta misión.

WINDOWS_REMOVAL no forma parte de esta misión.

Esta misión deja preparado el servidor
que posteriormente ejecutará las fases autorizadas
de LUNA R4.

========================================================================
FIN
========================================================================