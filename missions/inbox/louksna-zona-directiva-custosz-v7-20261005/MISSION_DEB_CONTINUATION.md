# MISIÓN DE CONTINUACIÓN — LOUKSNA ZONA DIRECTIVA / CANDIDATO .DEB

MISSION_ID = MIS-LOUKSNA-ZD-DEB-HARDENING-20261005
WORKER = CUSTOSZ_V7
RUNTIME = CUSTOSZ_RUNTIME_V1
AUTHORITY = Louksna.md
ASSURANCE = PUAC2.md
WORK_BRANCH = work/louksna-zona-directiva-candidate-20261005
MAIN_ROOT_OBSERVED_AT_DISPATCH = a7d430a7f9f94eb82c017bf62c3b456ca5b0cdf9
EXECUTION_LOCATION = GITHUB_HOSTED_ONLY
MAIN_MODE = READ_ONLY_SYNCHRONIZED_REFERENCE
CANCEL_IN_PROGRESS = FALSE
NO_INTERRUPTION = TRUE
FAIL_CLOSED = TRUE
NO_SILENT_OPERATIONS = TRUE
IDENTITY = LOUKSNA_ONLY
CERTIFICATION_PROPAGATION = FORBIDDEN
G23 = EXTERNAL_REQUIRED
G24 = EXTERNAL_REQUIRED

## Orden exacta

CUSTOSZ V7 y CUSTOSZ_RUNTIME_V1 deben continuar el mismo proyecto LOUKSNA ZONA DIRECTIVA,
partiendo del candidato material ya demostrado, y avanzar inmediatamente sobre lo pendiente:

1. Sincronizarse en lectura con la raíz MAIN vigente al inicio del run y registrar su SHA.
2. No modificar MAIN, no hacer merge, no force-push, no cancelar ni reemplazar otros workflows.
3. Verificar CUSTOSZ V7 y CUSTOSZ_RUNTIME_V1 antes de ejecutar trabajo material.
4. Re-materializar de forma determinista el mismo candidato desde las referencias canónicas,
   preservando identidad LOUKSNA_ONLY y las seis imágenes aprobadas.
5. Ejecutar build frontend de producción.
6. Ejecutar build Tauri/Rust real.
7. Generar candidato Debian amd64 .deb.
8. Validar estructuralmente el .deb con dpkg-deb y SHA-256.
9. Ejecutar lintian cuando esté disponible; registrar sus hallazgos sin convertir warnings en PASS.
10. Hacer prueba de instalación aislada/sandbox cuando sea técnicamente viable en el runner;
    si no lo es, registrar BLOCKED_BY_ENVIRONMENT y no fingir validación.
11. Producir evidencia de:
    - MAIN_ROOT_SHA
    - CUSTOSZ selftest
    - Runtime selftest
    - frontend build
    - Tauri/Rust build
    - .deb path, bytes, SHA-256
    - dpkg metadata
    - lintian
    - pending gates
12. Preservar outputs como GitHub artifact.
13. No declarar G23, G24, CERTIFIED ni ACTIVE.
14. Continuar sin perjudicar los procesos concurrentes que ya estén ejecutándose en MAIN.

## Gate siguiente esperado

DEB_CANDIDATE_MATERIALIZED -> DEB_STRUCTURAL_VALIDATION -> INSTALLABILITY_VALIDATION
-> PUAC2 -> NON_REGRESSION -> ROLLBACK -> G23 -> G24.

GitHub success != certification.
.deb built != installed.
installed != validated.
validated != certified.
certified != active.
