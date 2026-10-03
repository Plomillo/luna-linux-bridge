# CONSULTA — RCLONE PARA INGESTAR CARPETA DEL HOST HACIA GITHUB

CONSULTA_ID = RCLONE_HOST_FOLDER_TO_GITHUB_20261003
KIND = CONSULTA
AUTHORITY = Louksna.md

CONSULTATION_ONLY = TRUE
RESEARCH_AUTHORIZED = TRUE
REPOSITORY_FULL_REVIEW_AUTHORIZED = TRUE
PUBLIC_DOCUMENTATION_RESEARCH_IF_NEEDED = TRUE

EXECUTION_AUTHORIZED = FALSE
MUTATION_AUTHORIZED = FALSE
UPLOAD_AUTHORIZED = FALSE
INSTALL_AUTHORIZED = FALSE
MAIN_MUTATION_AUTHORIZED = FALSE

HARD_CEILING_SECONDS = 120
FAILURE_POSTURE = FAIL_CLOSED
NO_SILENT_OPERATIONS = ABSOLUTE
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
CERTIFICATION_PROPAGATION = FORBIDDEN

## CONTEXTO

La carpeta NO está actualmente en GitHub. Está en el host/escritorio del usuario, por ejemplo:

`$HOME/PROYECTOS/1. PROYECTOS PRIORITARIOS`

Queremos saber si existe una vía real, segura y gobernada para llevar esa carpeta desde el host hacia un repositorio GitHub.

## PREGUNTA PRINCIPAL

¿Puede hacerse con `rclone`, y de ser viable, cuál sería la configuración/topología exacta?

No asumir que GitHub es un remote nativo de rclone. Verificarlo contra la arquitectura y mecanismos observados.

Revisar TODO el repositorio versionado relevante, incluyendo la rama actual de consultas y `main`, en busca de mecanismos ya existentes para:

- host -> GitHub;
- importación/ingestión;
- Git/GitHub push;
- Git LFS;
- GitHub API / gh;
- releases;
- artifacts;
- almacenamiento intermedio;
- recovery/download root de main;
- provenance, hashes, checkpoints y rollback.

Distinguir claramente:

1. copiar bytes a un almacenamiento;
2. subir assets/artifacts;
3. versionar archivos dentro de un Git repository;
4. manejar archivos grandes o una carpeta de gran tamaño.

Si rclone puede ser sólo auxiliar, indicar exactamente dónde encaja y qué componente debe completar la operación Git/GitHub.

Si faltan dependencias, enumerarlas y decir si la capacidad gobernada de descarga disponible en `main` podría obtenerlas posteriormente mediante una MISIÓN separada y autorizada.

## NO HACER

- no subir la carpeta;
- no instalar rclone ni otras dependencias;
- no descargar binarios;
- no hacer push;
- no mutar main;
- no mutar Louksna.md;
- no promover esta consulta a misión;
- no inventar soporte que no exista.

## RESPUESTA OBLIGATORIA

CAN_RCLONE_UPLOAD_DIRECTLY_TO_GITHUB_REPOSITORY = TRUE | FALSE | HOLD
CAN_RCLONE_BE_USED_AS_AUXILIARY = TRUE | FALSE | HOLD
EXACT_RCLONE_TOPOLOGY_OR_CONFIG
EXISTING_REPOSITORY_MECHANISMS
MAIN_RECOVERY_DOWNLOAD_RELEVANCE
REQUIRED_DEPENDENCIES
FILE_SIZE_AND_REPOSITORY_LIMITS
PROVENANCE_AND_ROLLBACK_MODEL
RISKS
RECOMMENDED_PATH
EVIDENCE_BASIS
EXACT_NEXT_ACTION
