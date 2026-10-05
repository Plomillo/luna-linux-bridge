# MISSION_ORIGINAL — LOUKSNA ZONA DIRECTIVA candidate hardening

MISSION_ID = MIS-LOUKSNA-ZD-CANDIDATE-20261005
MISSION_CLASS = LOUKSNA_ZONA_DIRECTIVA_HARDENED_CANDIDATE_V1
WORKER = CUSTOSZ_V7
RUNTIME = CUSTOSZ_RUNTIME_V1
GOVERNOR = MetaOS
AUTHORITY = Louksna.md
ASSURANCE = PUAC2.md
SOURCE_BRANCH = louksna-zona-directiva-v0.2-hardened
SOURCE_COMMIT_SHA = 94f999f28f6ac371e1a768312a69704af96fd7a7
WORK_BRANCH = work/louksna-zona-directiva-candidate-20261005
EXECUTION_LOCATION = GITHUB_HOSTED_ONLY
NO_INTERRUPTION = TRUE
CANCEL_IN_PROGRESS = FALSE
NO_SILENT_OPERATIONS = TRUE
FAIL_CLOSED = TRUE
TRACEABILITY_REQUIRED = TRUE
PROVENANCE_REQUIRED = TRUE
AUDITABILITY_REQUIRED = TRUE
ROLLBACK_REQUIRED = TRUE
NON_REGRESSION_REQUIRED = TRUE
CERTIFICATION_PROPAGATION = FORBIDDEN
AUTHORITY_TRANSFER = FORBIDDEN
CANONICAL_MUTATION = FORBIDDEN
IDENTITY = LOUKSNA_ONLY
REQUIRED_CAPABILITIES = FORENSIC_AUDIT, HARDENING, MATERIAL_EXECUTION, TELEMETRY, EVIDENCE, ROLLBACK, NON_REGRESSION, DEBIAN_PACKAGING

## Orden

CUSTOSZ V7, conjuntamente con CUSTOSZ_RUNTIME_V1, debe auditar materialmente el proyecto
LOUKSNA ZONA DIRECTIVA — GitHub Interface Skeleton V0.2 HARDENED presente en el commit
fuente indicado arriba y comenzar la construcción del candidato real endurecido.

Debe conservar exactamente el mismo producto y la misma identidad: LOUKSNA únicamente.
No se autorizan identidades aditivas, cambios de autoridad, reinterpretación del alcance,
sustitución de las seis referencias visuales ni mutación del branch fuente.

La ejecución debe ocurrir exclusivamente en GitHub-hosted compute. No utilizar el PC del
propietario, no usar runners self-hosted, no consumir RAM del dispositivo local y no
interrumpir workflows ya operativos. Usar un concurrency group exclusivo y
cancel-in-progress=false.

## Alcance material autorizado en el work branch

1. Verificar byte/hash/estructura de:
   - Louksna.md
   - PUAC2.md
   - SKELETON_CANONICO_REFERENCIA.txt
   - LOUKSNA_ZONA_DIRECTIVA_PACKAGING_MONOLITH.md
   - las seis imágenes canónicas y su ASSET_MANIFEST/SHA256SUMS.
2. Producir auditoría forense y matriz de brechas.
3. Endurecer la especificación sin reemplazarla.
4. Crear un candidato real y ejecutable en:
   LOUKSNA_ZONA_DIRECTIVA_GITHUB_INTERFACE_V0.2_HARDENED/candidate/
5. Stack objetivo:
   - Tauri 2
   - Rust
   - TypeScript
   - React/Vite
   - SQLite contract
   - libsecret contract
   - GitHub REST API contract
   - Debian 13 amd64 .deb
6. Implementar las seis secciones, sin agregar otras identidades:
   - Centro de mando
   - Repositorios
   - Pull Requests
   - Evidencia
   - Chat / Llamada
   - Configuración
7. Mantener telemetría visible en logs de GitHub Actions y producir:
   - candidate/evidence/TELEMETRY.jsonl
   - candidate/evidence/CURRENT_STATE.json
   - candidate/evidence/AUDIT_REPORT.md
   - candidate/evidence/HARDENING_MATRIX.json
   - candidate/evidence/CUSTOSZ_RUNTIME_RESULT.json
8. Verificar CUSTOSZ V7 con v07-status y v07-selftest.
9. Verificar CUSTOSZ_RUNTIME_V1 con selftest y EvidenceJournal.
10. Ejecutar la materialización sólo mediante SR-EXEC-BOUND-FME-01.
11. Construir frontend, ejecutar validaciones y, si las dependencias del runner lo permiten,
    producir un .deb candidato. Un fallo de build debe quedar como evidencia; no puede
    convertirse silenciosamente en PASS.
12. No declarar G23, G24, CERTIFIED ni ACTIVE.

## Invariantes

- SOURCE_BRANCH permanece intacta.
- Work branch solamente.
- No force-push.
- No merge automático.
- No borrado de artifacts existentes.
- No modificación de main.
- No modificación de otros branches.
- No secrets impresos.
- No token persistence fuera del checkout que necesita push.
- No auto-certificación.
- GitHub success != mission success.
- CUSTOSZ selftest != certification.
- Runtime selftest != certification.
- Candidato construido != certificado.

## Estado terminal esperado de esta primera misión

El primer objetivo es demostrar materialmente que:
- CUSTOSZ V7 está ejecutándose;
- CUSTOSZ_RUNTIME_V1 está ejecutándose;
- el runtime ha enlazado un executor material;
- la auditoría del proyecto ha comenzado;
- el candidato real ha comenzado a materializarse;
- la telemetría está activa;
- ningún flujo operativo existente fue cancelado o sustituido.

Después continuar hasta agotar el alcance autorizado o alcanzar un bloqueo fail-closed.
