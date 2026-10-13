# SUPER1200 / Kestra — Enmienda operativa 1.0.1
- Fecha: 2026-10-13 UTC
- Rama: `custosz/super-1200-implementation-20261007`
- Alcance autorizado: Kestra como supervisor y despachador acotado; CUSTOSZ V7 continúa como trabajador material autorizado.
- Autoridad: `Louksna.md`
- Estado: cambio de contrato y flujo en rama candidata; importación en el runtime persistente pendiente de verificar.
- Política: EXTEND_DO_NOT_REPLACE · APPEND_ONLY · FAIL_CLOSED · NO_SILENT_OPERATIONS.
- `main` no se modifica.

## Decisión operativa

MetaOS queda aplazado y no es prerequisito para continuar SUPER1200. La condición histórica `metaos_ready == true` queda expresamente sustituida para la continuación material, no borrada como antecedente histórico. Ningún flujo puede activar MetaOS sin su validación propia posterior.

Kestra puede despachar `super1200-continuation-lrb-live.yml` solamente cuando el checkpoint no esté bloqueado, el estado sea `ACTIVE` o `READY_FOR_CONTINUATION`, el trabajador material esté marcado como listo, exista el siguiente punto y haya un ejecutor D04 registrado distinto del dispatcher recursivo. El workflow de GitHub conserva su propia compuerta independiente de existencia de archivo y pruebas conductuales.

Antes de despachar, Kestra consulta la API de GitHub para ejecuciones de ese workflow y esa rama en estados `in_progress` y `queued`. Si cualquiera existe, registra SAFE_HOLD y no despacha otra misión. Si las consultas de GitHub fallan o la respuesta no se puede analizar, la ejecución falla de forma cerrada: no se autoriza el despacho por ausencia de evidencia. El workflow mantiene su grupo de concurrencia con `cancel-in-progress: false`.

## Credenciales y límites

La integración utiliza exclusivamente el secreto local de Kestra `GITHUB_TOKEN`; el token no se almacena en Git ni en los artefactos. Debe tener únicamente el permiso de GitHub Actions necesario para el despacho y lectura de contenido en este repositorio. Ausencia, expiración o permisos insuficientes producen fallo cerrado, no un bypass. No se habilita ejecución arbitraria de scripts, autorreparación irrestricta, fusión ni promoción a `main`.

## Verificación y aceptación

La edición del flujo y del validador no demuestra por sí sola que la instancia persistente haya importado la revisión nueva. La activación real requiere evidencia fechada del runtime de Kestra con: (1) flujo actualizado importado; (2) secreto `GITHUB_TOKEN` válido sin exponerlo; (3) ciclo programado que detecta la ejecución de 12 horas ya activa y registra SAFE_HOLD sin duplicarla; (4) después de finalizar aquella ejecución, exactamente un despacho exitoso; (5) siguiente ciclo que detecta la nueva ejecución; (6) logs/IDs de ejecución y hashes vinculados al SHA candidato.

Se conserva la ejecución en curso `38469912731` y no se inicia una segunda misión mientras siga activa o encolada. G23 y G24 siguen siendo compuertas separadas y obligatorias para certificar únicamente el alcance probado. La certificación global SUPER1200 permanece `NOT_CERTIFIED`; no hay propagación automática ni promoción a `main`.

## Rollback

El rollback se limita a revertir o reimportar la revisión anterior del flujo en esta rama de trabajo, preservando los logs y artefactos. No exige ni autoriza cambios a `main`, alteraciones del estado canónico Louksna o eliminación de evidencia.
