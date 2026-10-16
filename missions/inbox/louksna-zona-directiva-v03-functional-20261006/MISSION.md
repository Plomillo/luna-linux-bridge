# MISIÓN — LOUKSNA ZONA DIRECTIVA V0.3 FUNCIONAL

MISSION_ID = MIS-LOUKSNA-ZD-V03-FUNCTIONAL-20261006
AUTHORITY = Louksna.md
ASSURANCE = PUAC2.md
BASELINE_BRANCH = work/louksna-zona-directiva-candidate-20261005
BASELINE_COMMIT = 6e34fddaae985bd9041be107b80e056f806092d2
WORK_BRANCH = work/louksna-zona-directiva-v0.3-functional-20261006
DOCTRINE = EXTEND_DO_NOT_REPLACE
FAILURE = FAIL_CLOSED
EXECUTION_LOCATION = GITHUB_HOSTED_ONLY
IDENTITY = LOUKSNA_ONLY
NO_MAIN_MUTATION = TRUE
NO_SILENT_OPERATIONS = TRUE
CANCEL_IN_PROGRESS = FALSE

## OBJETIVO

Convertir el shell V0.2 ya probado físicamente en Debian 13 KDE en una versión V0.3 funcional y verificable sin destruir ni reescribir el candidato certificado anterior.

## PRIORIDAD OPERACIONAL

P0. Mantener intacto el V0.2 certificado.
P1. Backend local real: SQLite, settings persistentes, ledger de evidencia y eventos.
P2. GitHub READ-ONLY real: autenticación explícita, repositorios, PRs y estado de conexión.
P3. Telemetría real: cada refresh y lectura debe producir evidencia local visible.
P4. Configuración real: persistencia, modo offline, repositorio preferido y conexión/desconexión.
P5. Chat gobernado: interfaz textual funcional con persistencia local y transporte preparado para bridge remoto; ninguna mutación silenciosa.
P6. Voz: preparar capacidad sin ejecutar operaciones destructivas por voz; si la pila end-to-end no puede probarse, declarar el gate abierto y no simularlo.
P7. Eliminar de la UI visible nombres internos de worker/runtime. Solo LOUKSNA es identidad visible.
P8. Rebuild .deb, install test Debian 13, rollback, lintian, no-regresión y evidencia.
P9. Sólo después de pasar runtime tests reales: nuevo freeze, nuevo digest, nuevo G23/G24.

## VALIDACIONES MÍNIMAS DEL RUNTIME V0.3

- abre offline;
- settings persisten tras reinicio;
- DB local se crea en ~/.local/share/louksna-zona-directiva/;
- token nunca se muestra ni se escribe en SQLite;
- repositorios GitHub se leen desde API real cuando hay token;
- PRs GitHub se leen desde API real;
- refresh manual observable;
- evidencia registra timestamp, operación, resultado y origen;
- desconexión elimina el secreto almacenado;
- errores de red se muestran como errores, no como datos falsos;
- UI visible conserva exactamente las seis secciones;
- CUSTOSZ/Runtime no aparecen como identidad visible;
- chat local guarda sesión/mensajes y marca con claridad si el bridge remoto aún no está enlazado;
- ningún dato estático puede presentarse como telemetría viva.

## GATE DE VERDAD

No declarar GitHub sincronizado salvo respuesta API real.
No declarar telemetría activa salvo ledger/evento real.
No declarar chat con arquitectura enlazado salvo round-trip real.
No declarar voz enlazada salvo captura/transporte/respuesta demostrados.
No declarar ACTIVE por build ni por G23/G24.
