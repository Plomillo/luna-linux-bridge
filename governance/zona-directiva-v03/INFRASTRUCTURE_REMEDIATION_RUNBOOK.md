# Infraestructura pendiente — plan operativo automatizado

**Alcance:** rama candidata de gobernanza; no modifica `main`, no instala ni activa la aplicación, no certifica y no reemplaza el contrato de 12 etapas.

## Qué se automatiza en este cambio

- GitHub Actions ejecuta una auditoría estática reproducible de los controles de infraestructura.
- Se ejecutan pruebas negativas que comprueban que CP-09, voz real, CP-10, G23 y G24 no se declaran aprobados por inferencia.
- Se publica un informe JSON ligado al SHA del candidato y al ID/intento del workflow; se conserva como artefacto durante 90 días.
- El informe distingue controles estáticos presentes de dependencias externas que requieren evidencia real.
- El estado `HOLD` es un resultado válido y fail-closed; no se convierte en certificación ni activa etapas posteriores.

Workflow: `.github/workflows/louksna-infrastructure-readiness.yml`  
Auditor: `scripts/missions/louksna_infrastructure_readiness_audit.py`  
Pruebas: `tests/test_louksna_infrastructure_readiness.py`

## Bloqueos que la automatización no puede resolver desde un workflow hospedado

### CP-09 — anfitrión real Debian 13 + KDE

1. Crear una VM desechable Debian 13 con KDE Plasma. No usar el equipo de uso diario, una máquina con credenciales ni un contenedor como sustituto.
2. Crear una cuenta exclusiva para el runner. Conceder solo el `sudo -n` necesario para instalar y retirar el paquete durante la prueba.
3. En GitHub, abrir **Settings → Actions → Runners → New self-hosted runner** y seguir las instrucciones generadas por GitHub. El token de registro es temporal: no guardarlo en Git, issues, artefactos ni logs.
4. Aplicar las etiquetas adicionales exactas `debian-13`, `kde`, `disposable` (GitHub añade `self-hosted` y `linux`).
5. Iniciar `./run.sh` desde una terminal dentro de la sesión KDE activa, de forma que el runner herede `DISPLAY`, `DBUS_SESSION_BUS_ADDRESS`, `XDG_RUNTIME_DIR`, `XDG_CURRENT_DESKTOP` y `KDE_FULL_SESSION`.
6. Confirmar que aparece online en **Settings → Actions → Runners**. No proporcionar secretos del repositorio a ese runner.
7. Reejecutar el workflow gobernado. CP-09 debe instalar, lanzar y desinstalar el paquete exacto producido por CP-08; guardar el informe de host y los logs. Destruir o reimaginar la VM al terminar.

**No se debe** crear un archivo PASS manual, introducir un fallback hospedado ni cambiar etiquetas para hacer que el job pase.

### Voz real — CP-07 y coherencia de CP-10

La prueba Chromium con un doble de Tauri IPC valida la interfaz dentro de ese alcance; no demuestra captura real de micrófono, permisos, transporte de audio ni respuesta de voz remota.

- Ejecutar una prueba E2E en el entorno autorizado que pruebe la cadena completa: permiso → captura → transporte → respuesta → reproducción/estado → errores y cancelación.
- Adjuntar evidencia con commit SHA, versión/configuración del servicio, marcas de tiempo, hashes y resultados positivos/negativos; redactar datos personales y secretos.
- Si el stack real no está disponible, mantener voz inactiva y el gate abierto. Si se pretende excluir voz del alcance de la liberación, hace falta una modificación explícita, revisada y autorizada del contrato y de los criterios CP-10. No se permite cambiar el requisito en silencio.

### CP-10 — expediente y congelación del candidato

El manifiesto debe descargar y validar evidencia del mismo run para CP-01…CP-09, verificar cada JSON y hash, comprobar que el commit y los artefactos coinciden, enumerar resultados, limitaciones, SBOM/dependencias, riesgos y rollback. Debe invalidar evidencias posteriores si cambia el digest del candidato.

La presencia de un artefacto no significa que su checkpoint sea PASS. CP-10 debe detenerse ante faltantes, hashes incorrectos, informes de otro commit, estados HOLD/FAIL o alcance de voz sin resolver.

### G23 / CP-11 — validación independiente

- Designar un validador que no haya producido el candidato ni la evidencia evaluada.
- Registrar identidad verificable, método de revisión y digest exacto del candidato y del expediente.
- Exigir un informe independiente firmado o verificable criptográficamente, con dictamen, hallazgos y riesgos residuales.
- Sin identidad e informe vinculados al mismo digest: HOLD. El productor de CI no puede autoaprobarse.

### G24 / CP-12 — certificación

Solo después de un G23 favorable, revisar integridad de la cadena de evidencia, rollback, no-regresión, alcance y riesgos residuales. Emitir un registro formal ligado al commit y al informe G23. Certificación y activación son decisiones distintas; este workflow no debe activar la aplicación.

## Controles transversales requeridos

- Permisos mínimos de GitHub Actions y acciones externas fijadas a SHA completo.
- Dependencias bloqueadas por lockfiles; builds limpios y reproducibles; SBOM y revisión de vulnerabilidades/licencias.
- Artefactos con retención definida, hash SHA-256 y procedencia ligada al commit/run.
- Logs sin secretos; tokens de checkout no persistentes cuando no se necesitan.
- Pruebas negativas: hash incorrecto, evidencia ausente/obsoleta, candidato cambiado después del freeze, runner perdido, instalación fallida, rollback fallido, identidad G23 ausente y G24 con digest incorrecto.
- Nada de merge, release, despliegue, certificación ni activación automáticos.

## Criterio de cierre

La infraestructura solo puede declararse lista cuando haya evidencia material para los gates aplicables, CP-09 haya corrido en el anfitrión físico declarado, el alcance de voz esté resuelto sin ambigüedad, CP-10 haya congelado el digest, G23 sea independiente y G24 esté formalmente documentado. El workflow de auditoría es una ayuda de observabilidad y prevención; no reemplaza esos hitos.
