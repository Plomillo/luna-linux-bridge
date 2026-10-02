# Consultas mailbox

Canal separado de `missions/` para preguntas, investigación, diagnóstico y análisis de factibilidad.

Invariantes:
- CONSULTA != MISIÓN.
- CONSULTA != AUTORIZACIÓN DE EJECUCIÓN MATERIAL.
- `execution_authorized=false` y `mutation_authorized=false` son obligatorios.
- El texto fuente se conserva por SHA-256; el envelope no sustituye ni muta el original.
- Estados terminales: `ANSWERED`, `HOLD`, `REJECTED`.
- Una promoción CONSULTA -> MISIÓN requiere un nuevo acto autorizativo y un nuevo objeto trazable.
- Louksna.md conserva la autoridad.
- EXTEND_DO_NOT_REPLACE, FAIL_CLOSED, NO_SILENT_OPERATIONS.
