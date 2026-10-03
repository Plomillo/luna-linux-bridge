# CONSULTA — CAPACIDAD DE ABSORBER UNA CARPETA DE PROYECTO

MISSION_ID = PRIORITY_PROJECTS_FOLDER_ABSORPTION_CONSULT_20261003
MISSION_CLASS = CUSTOSZ_READ_ONLY_CAPABILITY_CONSULTATION
AUTHORITY = Louksna.md

USER_AUTHORIZATION = EXPLICIT
CONSULTATION_ONLY = TRUE
MATERIAL_EXECUTION_AUTHORIZED = FALSE
MUTATION_AUTHORIZED = FALSE
DOWNLOAD_AUTHORIZED = FALSE
INSTALL_AUTHORIZED = FALSE
EXTERNAL_RESEARCH_AUTHORIZED = FALSE

HARD_CEILING_SECONDS = 60
FAILURE_POSTURE = FAIL_CLOSED
NO_SILENT_OPERATIONS = ABSOLUTE
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
ROLLBACK = NOT_APPLICABLE_READ_ONLY
CERTIFICATION_PROPAGATION = FORBIDDEN
SELF_CERTIFICATION = FORBIDDEN

## CONSULTA

Determinar si el sistema/CUSTOSZ/Louksna actualmente posee una capacidad real y gobernada para ABSORBER o INGRESAR una carpeta completa, por ejemplo:

`$HOME/PROYECTOS/1. PROYECTOS PRIORITARIOS`

como proyecto/corpus/artefacto operativo, preservando estructura, identidad, procedencia, trazabilidad, auditabilidad, límites de autoridad y no-regresión.

No realizar la absorción. No modificar la carpeta. No indexarla materialmente. No descargar ni instalar nada.

### SI LA CAPACIDAD YA EXISTE

Indicar con precisión:
- mecanismo o componente exacto;
- entrypoint/comando/interfaz;
- dónde vive;
- qué límites tiene;
- qué evidencia requiere;
- qué produciría;
- si puede operar sobre una carpeta grande;
- si puede hacerlo sin introducir autoridad canónica ni mutar Louksna;
- qué pasos mínimos serían necesarios para usarla después con autorización separada.

### SI LA CAPACIDAD NO EXISTE O ES INSUFICIENTE

Indicar exactamente qué falta:
- dependencia;
- adaptador/importador;
- manifiesto;
- esquema;
- motor;
- almacenamiento;
- indexación;
- runtime;
- permisos;
- contratos;
- validación;
- cualquier otro componente requerido.

No investigar externamente. No instalar. No descargar.

Existe una capacidad de recuperación/continuidad en `main` que puede permitir descargas gobernadas cuando exista autorización material posterior. Evaluar únicamente si esa capacidad sería aplicable para obtener dependencias faltantes; NO usarla ahora.

## RESPUESTA OBLIGATORIA

CAN_ABSORB_FOLDER = TRUE | FALSE | HOLD
CURRENT_CAPABILITY
EXACT_EXISTING_MECHANISM
MISSING_COMPONENTS
DEPENDENCIES_REQUIRED
MAIN_DOWNLOAD_CAPABILITY_APPLICABLE = TRUE | FALSE | UNKNOWN
RISKS_AND_LIMITS
MINIMUM_NEXT_AUTHORIZED_STEP
HUMAN_ACTION_REQUIRED
EVIDENCE_BASIS
