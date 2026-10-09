# Debian 13 — perfil transversal de pruebas para los CP

STATUS = PROPOSED_FOR_REVIEW
AUTHORITY = Louksna.md
DOCTRINE = EXTEND_DO_NOT_REPLACE
FAILURE_POLICY = FAIL_CLOSED
CERTIFICATION = NOT_GRANTED
ACTIVATION = NOT_AUTHORIZED_BY_THIS_DOCUMENT

## 1. Propósito y persistencia

Este contrato hace que Debian 13 esté considerado desde la planificación de cada CP posterior, en vez de descubrir su utilidad cuando el CP ya está en ejecución. Debe consultarse al abrir, retomar o cambiar materialmente el alcance de cualquier CP del repositorio.

No redefine los requisitos originales de ningún CP, no cambia su orden ni declara que todos deban ejecutarse en Debian. Es una obligación de evaluación de aplicabilidad, no una sustitución universal del entorno de destino.

## 2. Regla de entrada obligatoria por CP

Antes de implementar un CP, registrar en su issue/PR o expediente:

- `CP_ID` y requisito de aceptación original.
- `DEBIAN13_APPLICABILITY`: `APPLICABLE`, `PARTIAL`, `NOT_APPLICABLE_JUSTIFIED` o `UNKNOWN`.
- `TEST_PROFILE`: `PACKAGE`, `RUNTIME_SERVICE`, `SECURITY_PERMISSIONS`, `GUI_KDE_XORG`, `OFFLINE_RECOVERY`, `INTEGRATION`, `PHYSICAL_HARDWARE` o combinación justificada.
- Prueba concreta que Debian 13 puede ejecutar, evidencia esperada y criterio de aprobación.
- Brecha que exige runner dedicado, anfitrión físico, otro SO o validador independiente.
- Evidencia de origen: commit completo, artefacto y SHA-256 cuando corresponda.
- Estado separado: `PLANNED`, `EXECUTED`, `VALIDATED`, `INDEPENDENTLY_VALIDATED`, `CERTIFIED`. No saltar estados.

Si el CP todavía no tiene especificación suficiente, mantener `UNKNOWN` y pedir aclaración; no inventar requisitos. `NOT_APPLICABLE_JUSTIFIED` exige una razón vinculada a los criterios originales del CP.

## 3. Perfiles de prueba disponibles

| Perfil | Uso permitido | Límite que debe declararse |
|---|---|---|
| PACKAGE | Instalar, inspeccionar, actualizar y retirar un .deb; revisar dependencias y residuos | No prueba por sí solo corrección funcional completa |
| RUNTIME_SERVICE | Arranque, salud, logs, reinicio, recuperación e idempotencia | No prueba continuidad del anfitrión físico |
| SECURITY_PERMISSIONS | Usuarios/grupos, privilegios, permisos, superficies de ejecución | No constituye una auditoría de seguridad completa |
| GUI_KDE_XORG | Sesión gráfica virtual, proceso de aplicación y smoke tests | No demuestra GPU, pantalla, audio ni micrófono físicos |
| OFFLINE_RECOVERY | Ejecución con artefactos precargados, integridad y recuperación | Debe demostrarse aislamiento real de la red para llamarse offline |
| INTEGRATION | Contratos, dependencias entre componentes, orden de arranque y regresión | Solo cubre las interfaces efectivamente ejercitadas |
| PHYSICAL_HARDWARE | Pruebas que dependen de dispositivos, firmware, arranque real o periféricos | Requiere entorno físico autorizado; la VM no lo sustituye |

Los perfiles son opciones de prueba, no nuevas obligaciones funcionales por sí mismas.

## 4. Uso operacional de la VM CP-09

Referencia de implementación: `.github/workflows/louksna-cp09-debian13-kde-vm.yml`.
Contrato de límites: `CP-09-DEBIAN13-KDE-VM-CI.md`.

La VM CP-09 es un entorno desechable para pruebas compatibles con virtualización. No se considera disponible para uso certificado hasta que el workflow se ejecute con un candidato real, fijado por commit y SHA-256, y sus evidencias sean revisadas.

La reutilización por otros CP exige adaptar sus entradas y pruebas explícitamente. No copiar valores de artefactos, hashes, versiones, URLs ni IDs de ejecución de CP-09 a otros CP. No usar el artefacto de un CP como candidato para otro sin trazabilidad y autorización explícitas.

## 5. Evidencia y decisión

Cada ejecución aplicable debe conservar, según proceda:

- CP y requisito cubierto;
- commit de código y origen exacto del artefacto;
- versión de Debian, arquitectura y perfil de ejecución (VM/runner/anfitrión físico);
- comando/prueba, hora UTC, código de salida y logs;
- hashes SHA-256 de los artefactos de entrada y del expediente;
- resultado observado, limitaciones y desviaciones;
- estado de instalación antes/después y evidencia de rollback cuando corresponda.

Una prueba fallida, ausente, contradictoria o no reproducible no puede transformarse en PASS. La evidencia automatizada no concede G23, G24, certificación ni activación. La validación independiente y la autoridad certificadora conservan sus funciones.

## 6. Regla de no regresión y seguridad

- Mantener Debian 13/QEMU como capacidad de pruebas, no como autoridad canónica.
- No cambiar requisitos de CP existentes por comodidad de la VM.
- No ejecutar cambios destructivos en el anfitrión mediante esta automatización.
- Mantener privilegios mínimos; `NOPASSWD:ALL`, si se necesita para bootstrap de la VM desechable, no se traslada a runners persistentes ni al anfitrión.
- No almacenar secretos en imágenes, artefactos ni logs.
- Toda nueva integración debe demostrar impacto, rollback y ausencia de regresiones dentro de su alcance.

## 7. Registro por CP

Este registro se completa con evidencia al planificar cada CP; las entradas no preclasificadas permanecen `UNKNOWN`.

| CP | Aplicabilidad | Perfil | Evidencia/decisión |
|---|---|---|---|
| CP-09 | `PARTIAL` — perfil VM propuesto; ejecución real con candidato aún pendiente de confirmar | PACKAGE, RUNTIME_SERVICE, GUI_KDE_XORG, SECURITY_PERMISSIONS | PR #57; no certificado |
| CP-10 | `UNKNOWN` — evaluar contra requisitos originales al iniciar | Pendiente de análisis | No inferir cobertura desde CP-09 |
| Cada CP restante | `UNKNOWN` hasta revisión de sus criterios | Seleccionar en la entrada del CP | Registrar en issue/PR antes de implementar |

## 8. Condición de cierre de esta incorporación

Este documento queda como propuesta hasta revisión/merge del PR que lo contiene. Su existencia no significa que los CP posteriores ya estén probados, integrados o certificados. En cada CP futuro debe existir una decisión de aplicabilidad trazable antes de avanzar.
