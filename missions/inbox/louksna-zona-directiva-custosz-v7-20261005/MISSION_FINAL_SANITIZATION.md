# MISIÓN FINAL DE SANEAMIENTO — LOUKSNA ZONA DIRECTIVA

MISSION_ID = MIS-LOUKSNA-ZD-FINAL-SANITIZATION-20261005
WORKER = CUSTOSZ_V7
RUNTIME = CUSTOSZ_RUNTIME_V1
AUTHORITY = Louksna.md
ASSURANCE = PUAC2.md
WORK_BRANCH = work/louksna-zona-directiva-candidate-20261005
MAIN_MODE = READ_ONLY_SYNCHRONIZED_REFERENCE
EXECUTION_LOCATION = GITHUB_HOSTED_ONLY
CANCEL_IN_PROGRESS = FALSE
NO_INTERRUPTION = TRUE
FAIL_CLOSED = TRUE
IDENTITY = LOUKSNA_ONLY

## Pendientes a cerrar

1. Regenerar correctamente DEBIAN/md5sums después de todo endurecimiento.
2. Corregir la fecha RFC822/day-of-week del changelog.
3. Repetir lintian y bloquear si persisten los defectos conocidos:
   - md5sum-mismatch
   - file-missing-in-md5sums
   - debian-changelog-has-wrong-day-of-week
   - malformed-contact
   - missing-dependency-on-libc
   - no-changelog
   - no-copyright-file
   - unstripped-binary-or-object
4. Repetir instalación real en Debian 13 efímero.
5. Repetir rollback/desinstalación con comprobación inequívoca de que el paquete ya no está instalado.
6. Ejecutar no-regresión, seguridad, procedencia y anti-parálisis de segundo orden.
7. Congelar un nuevo candidato exacto con nuevo SHA-256/digest.
8. Entregar el candidato al validador independiente MAIN-controlled.
9. Repetir G23 y G24 exclusivamente sobre el nuevo digest.
10. Mantener ACTIVE separado: G24 no autoactiva.
11. Preparar el .deb y evidencia necesarios para la prueba física posterior en Debian 13 KDE del propietario;
    esa prueba física no debe fingirse desde GitHub.

## Regla

No tocar MAIN salvo lectura de autoridad/trust-root ya existente.
No interferir otros workflows.
No reutilizar G23/G24 del digest anterior.
Cualquier cambio al .deb obliga a nuevo digest, nuevo G23 y nuevo G24.
