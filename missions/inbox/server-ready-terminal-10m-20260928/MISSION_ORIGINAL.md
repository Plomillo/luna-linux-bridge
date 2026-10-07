# MISIÓN TERMINAL DE 10 MINUTOS — OBTENCIÓN DE PASS REAL
MISSION_ID = SR_TERMINAL_10M_20260928
MISSION_CLASS = FINAL_SERVER_READY_CLOSURE_10M
AUTHORITY = Louksna.md
GOVERNOR = MetaOS
WORKER = CUSTOSZ V7
RUNTIME = CUSTOSZ_RUNTIME_V1
SUPERVISOR = SYMPHYLAX R1
INGRESS = CUSTOSZ MISSION MAILBOX
TERMINAL_CHAIN = G08 -> G09 -> G23 -> G24
FAILURE_POSTURE = FAIL_CLOSED
DOCTRINE = EXTEND_DO_NOT_REPLACE
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
ROLLBACK = REQUIRED
NON_REGRESSION = REQUIRED
NO_SILENT_OPERATIONS = ABSOLUTE
NO_SELF_CERTIFICATION = ABSOLUTE
CERTIFICATION_PROPAGATION = FORBIDDEN
UNKNOWN_TO_PASS = FORBIDDEN
WORKFLOW_SUCCESS_NE_MISSION_SUCCESS = TRUE

## 0. OBJETO ÚNICO DE LA MISIÓN

El objeto de esta misión es obtener un PASS real, material, reproducible, trazable,
auditable, gobernado y certificable para la secuencia completa:

G08 = PASS
AND G09 = PASS
AND GATE_01..GATE_15 = PASS
AND G23 = PASS
AND G24 = PASS

Solo esa conjunción autoriza:

SERVER_TECHNICAL_READY = TRUE
SERVER_VERIFIED = TRUE
SERVER_CERTIFIED = TRUE
SERVER_READY_FINAL = PASS

No existe objetivo alternativo, sustitutivo, aproximado ni semánticamente equivalente.

## 1. LÉXICO CANÓNICO Y CONTROL FILOLÓGICO

Los términos siguientes son no intercambiables.

EVIDENCIA:
Registro material persistente que identifica qué fue observado o ejecutado,
por qué método, bajo qué identidad, cuándo, con qué hashes/estado, y cuál fue
el resultado. Una afirmación sin evidencia material no es evidencia.

VERIFICACIÓN:
Comprobación de que un artefacto, identidad, hash, estado o resultado coincide
con un criterio explícito previamente definido. Verificar no equivale a certificar.

VALIDACIÓN:
Demostración de que el comportamiento observado satisface un requisito
operacional definido. La validación exige evidencia; no se deriva de intención.

VALIDACIÓN INDEPENDIENTE / G23:
Revisión de evidencia congelada por un plano que no produjo, reparó ni mutó el
objeto evaluado durante la revisión. G23 no puede autoconcesionarse.

CERTIFICACIÓN / G24:
Acto terminal de atestación formal posterior a evidencia, verificación,
validación e independencia G23. Certificar significa afirmar con base probatoria
suficiente que el objeto cumple el alcance certificado; no significa "el workflow terminó".

PASS REAL:
Estado epistemológico y operacional que existe únicamente cuando el criterio
binario está satisfecho, la evidencia requerida está materializada, no hay
contradicción crítica no resuelta, las pruebas negativas exigibles han pasado,
la identidad y autoridad están verificadas y la cadena probatoria permite
reproducir la conclusión.

PASS ARTIFICIAL:
Cualquier PASS inferido, asumido, propagado, heredado indebidamente,
declarado por ausencia de error, producido por éxito del workflow, fabricado
para satisfacer un plazo, o concedido con evidencia faltante/UNKNOWN/NOT_RUN/
INCONCLUSIVE/CONTRADICTED. PASS_ARTIFICIAL = FORBIDDEN.

HOLD:
Estado no terminal de insuficiencia probatoria o bloqueo recuperable.
HOLD obliga a checkpoint, causa raíz, remediación, prueba de verificación y
continuidad de la misión. HOLD no equivale a fracaso terminal.

FAIL DE GATE:
Contradicción material de un criterio. Obliga a rollback/remediación y nueva
validación. Un FAIL local no autoriza cierre terminal de la misión.

SALIDA TERMINAL:
Cierre semántico global de la misión. Solo se permite con G24=PASS y cadena
completa. El fin de un proceso, job, workflow, runner, reloj o intento no es
SALIDA_TERMINAL.

TECHO:
Límite máximo de tiempo de un intento. El techo limita recursos temporales;
no reduce requisitos epistemológicos, no convierte HOLD en PASS y no autoriza
cierre terminal.

## 2. CONTROL ETIMOLÓGICO OPERACIONAL

VERIFICAR se usa en sentido de hacer comprobable la verdad de una proposición.
VALIDAR se usa en sentido de demostrar suficiencia y validez respecto de un criterio.
CERTIFICAR se usa en sentido de atestar formalmente un estado ya demostrado.
PROCEDENCIA/PROVENANCE se usa para reconstruir el origen y la cadena de transformación.
TRAZABILIDAD se usa para poder recorrer bidireccionalmente requisito -> evidencia
y evidencia -> requisito.

Consecuencia:
VERIFICACIÓN != VALIDACIÓN != G23 != G24.
Ningún término puede sustituir silenciosamente a otro.

## 3. MÁQUINA EPISTÉMICA OBLIGATORIA

Estados permitidos:
DECLARED
-> OBSERVED
-> EVIDENCED
-> VERIFIED
-> VALIDATED
-> INDEPENDENTLY_VALIDATED
-> CERTIFIED

Transiciones prohibidas:
DECLARED -> PASS
OBSERVED -> CERTIFIED
EVIDENCED -> G24
VERIFIED -> G24
VALIDATED -> G24_WITHOUT_G23
UNKNOWN -> PASS
NOT_RUN -> PASS
INCONCLUSIVE -> PASS
WORKFLOW_SUCCESS -> MISSION_SUCCESS

La falta de un eslabón impide el siguiente.

## 4. ESTADO DE PARTIDA DEMOSTRADO

INFRASTRUCTURE_RESOLVED = TRUE
PRECHECK_12 = PASS
SERVER_DEPLOYED = TRUE
SERVER_READY_GATES_PASS = 13_OF_15
G08 = HOLD
G09 = HOLD
G23 = HOLD
G24 = HOLD
SERVER_TECHNICAL_READY = FALSE
SERVER_CERTIFIED = FALSE

No repetir infraestructura cerrada salvo prueba explícita de no regresión.

## 5. PRESUPUESTO TEMPORAL

HARD_CEILING_PER_ATTEMPT_SECONDS = 600
PHASE_A_STUDY_TARGET_SECONDS = 300
PHASE_B_ATTACK_TARGET_SECONDS = 300
NO_ARTIFICIAL_WAITING = TRUE
NO_TIME_PADDING = TRUE

Los dos bloques son objetivos de asignación, no compartimentos rígidos:
si el estudio termina antes, el tiempo restante se transfiere al ataque.
Si el ataque necesita comenzar antes, puede comenzar tan pronto exista
evidencia suficiente.

El vencimiento de 600 segundos:
- termina el intento si la infraestructura impone ese límite;
- NO termina la misión;
- NO autoriza PASS;
- obliga a checkpoint persistente y reanudable;
- conserva CURRENT_GATE, ROOT_BLOCKER, EXACT_REMEDIATION y VERIFICATION_TEST.

## 6. FASE A — ESTUDIO EXHAUSTIVO DE RAÍZ

Objetivo: explicar exactamente por qué G08, G09, G23 y G24 no son PASS y
determinar el camino mínimo suficiente para convertirlos en PASS real.

Analizar obligatoriamente:

G08:
- boot baseline;
- boot_id actual;
- persistencia del servicio;
- enablement;
- linger;
- health;
- evidencia post-boot;
- continuidad después de un arranque real;
- cualquier discrepancia entre "configurado" y "observado".

G09:
- executor/process failure;
- recovery;
- runtime failure;
- process termination;
- dependency failure;
- timeout;
- no orphan process;
- state recovery;
- persistence of evidence;
- límites reales del executor y herramientas disponibles.

G23:
- independencia del reviewer;
- freeze del bundle;
- reproducibilidad;
- integridad/hash;
- los 15 gates;
- rollback;
- no regresión;
- ausencia de repair durante validación.

G24:
- dependencia estricta de G23;
- cadena SPECIFICATION -> EVIDENCE -> VALIDATION -> G23 -> G24;
- autoridad;
- identidad;
- ausencia de mutación canónica;
- ausencia de sustitución silenciosa;
- rollback;
- trazabilidad;
- auditabilidad;
- no regresión.

Salida obligatoria de estudio:
ROOT_CAUSE_G08
ROOT_CAUSE_G09
G23_ELIGIBILITY_GAP
G24_ELIGIBILITY_GAP
MINIMUM_SUFFICIENT_ACTION_SET
CHECKPOINT
ROLLBACK_PLAN
EVIDENCE_PLAN

El estudio no puede gastar el resto del intento en descripción una vez exista
un plan causal suficiente. Debe transferirse al ataque.

## 7. FASE B — ATAQUE DE RAÍZ Y CIERRE SECUENCIAL

ORDEN CANÓNICO:
G08 -> G09 -> FREEZE_15_GATES -> G23 -> G24

### G08 — SERVICE_PERSISTENCE

PASS solo si existe evidencia material de persistencia real, no únicamente
configuración declarada.

Requisitos mínimos:
BOOT_BASELINE_PRESENT = TRUE
BOOT_ID_CHANGED_FROM_BASELINE = TRUE
SERVICE_ENABLED = PASS
SERVICE_ACTIVE = PASS
SERVICE_HEALTHY = PASS
LINGER = ENABLED
PERSISTENT_STATE_SURVIVED_BOOT = TRUE
PERSISTENT_EVIDENCE_SURVIVED_BOOT = TRUE

Si no ocurrió un arranque real posterior al baseline:
G08 = HOLD
PASS = FORBIDDEN
MISSION = ACTIVE

Ningún reboot se presume autorizado por el mero hecho de esta misión.
Si una acción de reboot exige autorización separada, se debe registrar ese
hecho sin degradar los requisitos de G08.

### G09 — FAILURE_RECOVERY

G09 solo comienza materialmente después de G08=PASS.

PASS exige evidencia material de:
EXECUTOR_KILL_RECOVERY = PASS
PROCESS_TERMINATION_RECOVERY = PASS
RUNTIME_FAILURE_RECOVERY = PASS
DEPENDENCY_FAILURE = SAFE_RECOVERY_OR_HOLD
TIMEOUT = SAFE_RECOVERY_OR_HOLD
NO_ORPHAN_PROCESS = PASS
STATE_RECOVERY = PASS
EVIDENCE_SURVIVES_RECOVERY = PASS

Una herramienta que impida una fault injection específica no autoriza sustituir
la prueba por una inferencia. Debe encontrarse un camino gobernado permitido o
mantener G09=HOLD con la misión activa.

### FREEZE — 15 GATES

Solo después de G08=PASS y G09=PASS:
recalcular de forma binaria GATE_01..GATE_15.

SERVER_READY = PRODUCT(GATE_01..GATE_15)

Si cualquier gate != PASS:
SERVER_TECHNICAL_READY = FALSE
G23 = NOT_ELIGIBLE
MISSION = ACTIVE

Si todos PASS:
SERVER_TECHNICAL_READY = TRUE
FREEZE el bundle con hashes y evidence head.

### G23 — INDEPENDENT VALIDATION

Debe ejecutarse en un plano fresco e independiente.
No puede reparar ni reescribir evidencia.

PASS requiere:
INDEPENDENT_VALIDATION = PASS
EVIDENCE_CHAIN_COMPLETE = TRUE
REPRODUCIBILITY = PASS
ALL_15_GATES_REPRODUCED = PASS
ROLLBACK_VERIFIED = TRUE
NON_REGRESSION = PASS
NO_UNRESOLVED_CRITICAL_FINDINGS = TRUE
PRODUCER_MUTATED_BY_G23 = FALSE

Si G23 != PASS:
G24 = DENIED
MISSION = ACTIVE

### G24 — CERTIFICATION

Solo después de G23=PASS.

PASS requiere:
SERVER_TECHNICAL_READY = TRUE
G23 = PASS
AUTHORITY = Louksna.md
CANONICAL_IDENTITY_MUTATION = FALSE
AUTHORITY_TRANSFER = FALSE
EXECUTOR_REASSIGNMENT = FALSE
RUNTIME_SILENT_REPLACEMENT = FALSE
PROVENANCE_LOSS = FALSE
TRACEABILITY_LOSS = FALSE
AUDITABILITY_LOSS = FALSE
ROLLBACK_VERIFIED = TRUE
NON_REGRESSION = PASS

Solo entonces:
G24 = PASS
SERVER_VERIFIED = TRUE
SERVER_CERTIFIED = TRUE
SERVER_READY_FINAL = PASS

## 8. CLÁUSULA DE PASS REAL Y NO-SALIDA

NO_EXIT_WITHOUT_GENUINE_PASS = 1
NO_ARTIFICIAL_PASS = 1
PASS_REQUIRES_MATERIAL_EVIDENCE = 1
TIME_EXHAUSTION_REQUIRES_CHECKPOINT_NOT_COMPLETION = 1
HARD_CEILING_DOES_NOT_AUTHORIZE_TERMINAL_EXIT = 1

PROHIBIDO declarar la misión terminal sin PASS real.
IGUALMENTE PROHIBIDO crear, inferir, asumir, heredar, propagar o fabricar
un PASS para poder terminar.

La única salida terminal autorizada es:

G08=PASS
AND G09=PASS
AND PRODUCT(GATE_01..GATE_15)=1
AND G23=PASS
AND G24=PASS
AND EVIDENCE_CHAIN_COMPLETE=TRUE

Todo otro estado es continuidad activa desde checkpoint.

## 9. TRAZABILIDAD Y ARTEFACTOS

Cada transición debe registrar:
MISSION_ID
MAIL_ID
SOURCE_COMMIT
SOURCE_SHA256
AUTHORITY_SHA256
CUSTOSZ_SHA256
RUNTIME_SHA256
METAOS_SHA256
EXECUTOR_ID
CURRENT_GATE
PREVIOUS_STATE
NEW_STATE
START_UTC
END_UTC
ACTION
RATIONALE
INPUT_HASHES
OUTPUT_HASHES
EVIDENCE
EVIDENCE_HEAD
ROLLBACK_POINTER
RESULT

Artefactos terminales:
BOOT_PERSISTENCE_EVIDENCE.json
G09_FAILURE_RECOVERY_EVIDENCE.json
SERVER_READY_GATES.json
FROZEN_BUNDLE_MANIFEST.json
EVIDENCE_CHAIN.jsonl
ROLLBACK_EVIDENCE.json
NON_REGRESSION_REPORT.json
G23_INDEPENDENT_VALIDATION.md
G23_RESULT.json
G24_CERTIFICATION.md
G24_RESULT.json
README_SERVER_READY_TERMINAL.md

## 10. LÍMITES DE SEGURIDAD Y AUTORIDAD

PROHIBIDO:
- modificar Windows, EFI, GPT, particiones, PROYECTOS o F3-DISK;
- mutar Louksna.md;
- sustituir silenciosamente CUSTOSZ, Runtime, MetaOS, executor o autoridad;
- usar Desktop Commander como trabajador principal o fallback;
- convertir un éxito técnico en certificación;
- ocultar un blocker;
- reinterpretar el techo de tiempo como permiso para degradar evidencia.

## 11. CRITERIO TERMINAL

TERMINAL_PASS_ONLY_IF =
G08_PASS
* G09_PASS
* PRODUCT(GATE_01..GATE_15)
* G23_PASS
* G24_PASS
* EVIDENCE_CHAIN_COMPLETE

Si TERMINAL_PASS_ONLY_IF = 1:
SERVER_VERIFIED = TRUE
SERVER_CERTIFIED = TRUE
SERVER_READY_FINAL = PASS
MISSION_TERMINAL = TRUE

Si TERMINAL_PASS_ONLY_IF = 0:
MISSION_TERMINAL = FALSE
MISSION_ACTIVE = TRUE
CHECKPOINT_REQUIRED = TRUE

FIN DE LA ESPECIFICACIÓN.
