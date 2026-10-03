# CONSULTA — CAPACIDAD DE INGESTAR UNA CARPETA DEL HOST HACIA EL REPOSITORIO

MISSION_ID = DESKTOP_PRIORITY_FOLDER_INGESTION_CONSULT_20261003
MISSION_CLASS = CUSTOSZ_READ_ONLY_ARCHITECTURAL_CONSULTATION
AUTHORITY = Louksna.md

USER_AUTHORIZATION = EXPLICIT
CONSULTATION_ONLY = TRUE
RESEARCH_AUTHORIZED = TRUE
MATERIAL_EXECUTION_AUTHORIZED = FALSE
MUTATION_AUTHORIZED = FALSE
DOWNLOAD_AUTHORIZED_NOW = FALSE
INSTALL_AUTHORIZED_NOW = FALSE
EXTERNAL_RESEARCH_EXECUTION_AUTHORIZED_NOW = FALSE

HARD_CEILING_SECONDS = 60
FAILURE_POSTURE = FAIL_CLOSED
NO_SILENT_OPERATIONS = ABSOLUTE
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
CERTIFICATION_PROPAGATION = FORBIDDEN
SELF_CERTIFICATION = FORBIDDEN

## CONTEXTO CORRECTO

La carpeta objetivo NO está actualmente dentro de GitHub, NO está dentro del checkout del workflow y NO debe buscarse allí como precondición.

Actualmente está en el host/escritorio del usuario, por ejemplo:

`$HOME/PROYECTOS/1. PROYECTOS PRIORITARIOS`

El objetivo futuro sería poder llevar/absorber/ingerir esa carpeta DESDE EL HOST hacia el repositorio/proyecto gobernado, preservando estructura, identidad, procedencia, trazabilidad, auditabilidad y no-regresión.

## CONSULTA

Determinar si CUSTOSZ/Louksna/el sistema ya posee una capacidad real y gobernada para:

HOST/DESKTOP FOLDER
→ INGESTION / ABSORPTION
→ GOVERNED REPOSITORY / PROJECT SURFACE

sin que la mera presencia de la carpeta otorgue autoridad canónica, y sin mutar Louksna.md.

### SI LA CAPACIDAD YA EXISTE

Responder:
- CAN_ABSORB_HOST_FOLDER = TRUE
- mecanismo exacto;
- componente/entrypoint;
- límites;
- tamaño/escala soportable;
- cómo preserva estructura;
- cómo preserva provenance/traceability/auditability;
- qué artefactos produciría;
- qué autorización material futura requeriría.

### SI NO EXISTE O ES INSUFICIENTE

Investigar conceptualmente y responder:
- CAN_ABSORB_HOST_FOLDER = FALSE | HOLD
- qué componente falta;
- qué adaptador/importador falta;
- qué dependencias/herramientas serían necesarias;
- qué manifiesto/esquema/índice/storage/runtime se requiere;
- qué validaciones y rollback se requieren;
- qué permisos se requieren.

Además, evaluar si la capacidad gobernada de descarga disponible en la raíz `main` podría servir POSTERIORMENTE para obtener esas dependencias, si fueran necesarias.

NO usar esa capacidad ahora.
NO descargar nada.
NO instalar nada.
NO mutar main.
NO modificar la carpeta.
NO ejecutar ingestión.

## SALIDA OBLIGATORIA

CAN_ABSORB_HOST_FOLDER = TRUE | FALSE | HOLD
CURRENT_CAPABILITY
EXACT_EXISTING_MECHANISM
MISSING_COMPONENTS
DEPENDENCIES_REQUIRED
MAIN_GOVERNED_DOWNLOAD_APPLICABLE = TRUE | FALSE | UNKNOWN
RISKS_AND_LIMITS
MINIMUM_NEXT_AUTHORIZED_STEP
HUMAN_ACTION_REQUIRED
EVIDENCE_BASIS
