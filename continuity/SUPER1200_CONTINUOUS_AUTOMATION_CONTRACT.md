# SUPER1200 — Contrato de automatización continua

- ID: SUPER1200-CONTINUOUS-AUTOMATION-001
- Versión: 1.0.0
- Estado: CANDIDATE / NOT CERTIFIED
- Rama autorizada: `custosz/super-1200-implementation-20261007`
- Autoridad: `Louksna.md`
- Coordinador: Kestra
- Trabajador autorizado: CUSTOSZ V7
- Runtime complementario: MetaOS, solo después de validar el WASM
- Política: EXTEND_DO_NOT_REPLACE · APPEND_ONLY · FAIL_CLOSED · NO_SILENT_OPERATIONS
- Prohibición explícita: no modificar, fusionar ni promover cambios a `main`.

## 1. Objetivo operativo

Automatizar la continuación de SUPER1200 desde el último checkpoint válido hasta completar las capacidades, conservando evidencia verificable por unidad. Kestra coordina; CUSTOSZ V7 ejecuta solo tareas materiales autorizadas; MetaOS se habilita únicamente tras validar el artefacto WASM exacto, su hash, procedencia y aislamiento; GitHub Actions valida cambios, ejecuta pruebas y produce telemetría.

Un workflow en SUCCESS no demuestra que una habilidad esté terminada. Cada capacidad requiere implementación material, pruebas conductuales, validación reproducible y evidencia ligada al commit exacto.

## 2. Continuidad sin duplicación

1. Antes de trabajar, leer el checkpoint, el mapa de ejecutores, el registro de capacidades, el progreso por dominio y las evidencias previas.
2. Fijar el SHA candidato y calcular hashes de entradas y artefactos relevantes.
3. Reutilizar resultados previos solo si coinciden capacidad, SHA de origen, hashes, versiones de herramientas, pruebas y estado de validación.
4. Aplicar una clave idempotente estable por misión/dominio/capacidad/SHA/versión del contrato. Si existe evidencia válida para esa clave, omitir el trabajo material repetido.
5. Si la evidencia es contradictoria, incompleta o pertenece a otra revisión, mantenerla para auditoría y bloquear la transición que dependa de ella; nunca corregirla silenciosamente.
6. Crear checkpoint antes de mutaciones y registrar intentos, fallos, recuperación y resultado en forma append-only.

## 3. Diagnóstico y autorreparación acotada

Los fallos deben producir telemetría, diagnóstico basado en evidencia, una reparación mínima y pruebas posteriores. La reparación automática solo puede modificar archivos de la rama candidata dentro del alcance aprobado, con causa identificada, checkpoint, rollback verificable, pruebas conductuales, no-regresión y procedencia comprobadas.

No se permite que la reparación cambie autoridad, IDs canónicos, estados de certificación, permisos, secretos o alcance de ejecución. No se permiten bucles infinitos: reintentos acotados, backoff y ninguna repetición del mismo fallo con los mismos hashes sin nueva evidencia o decisión registrada. Si una reparación segura no está demostrada, parar esa operación, preservar la evidencia y registrar el bloqueo y la siguiente acción.

## 4. Reglas de ejecución

- CUSTOSZ V7 debe vincularse a un ejecutor material concreto, revisado y probado; la presencia del paquete o la supervisión de tiempo/estado no acredita ejecución material.
- D04 debe tener un ejecutor explícito en `continuity/EXECUTORS.json`, un archivo existente en la rama candidata y pruebas conductuales no autorreferenciales.
- Prohibido registrar el dispatcher como su propio ejecutor o permitir recursión.
- MetaOS permanece deshabilitado hasta superar validación estándar WASM, verificación de hash/procedencia, pruebas aisladas y revisión independiente.
- Prohibido marcar capacidades EVIDENCED por generar wrappers, archivos o pruebas que solo validen el propio wrapper. Las pruebas deben demostrar el comportamiento anunciado.
- La continuación material y la certificación son etapas distintas. G23 no debe usarse como requisito circular para iniciar el trabajo que produce su evidencia; sigue siendo obligatorio antes de G24. La ejecución previa a G23 requiere checkpoint, ejecutor, runtime y permisos válidos.

## 5. Cadencias y automatización

- Kestra: supervisión continua de checkpoint, ejecutores, estado del runtime, cola, bloqueos, resultados y recuperación; ciclo cada cinco minutos mientras el servicio persistente esté activo.
- GitHub Actions: validación/pruebas en cambios relevantes y auditoría de estado cada 12 horas, además de ejecución manual para diagnóstico autorizado.
- La telemetría debe incluir SHA candidato, checkpoint, siguiente dominio, capacidades con evidencia válida, trabajo omitido por idempotencia, intentos/fallos, reparaciones, pruebas, hash de artefactos, disponibilidad de CUSTOSZ V7 y MetaOS, G23/G24 y último evento.
- GitHub ejecuta eventos schedule desde la rama predeterminada. Por tanto, añadir un schedule únicamente a esta rama candidata no garantiza ejecución cada 12 horas mientras main siga intacta. El schedule solo se declarará activo después de observar ejecuciones reales; no se autoriza tocar main para habilitarlo.
- No afirmar progreso nocturno, ejecución material ni persistencia real del host sin telemetría fechada que lo demuestre.

## 6. Evidencia y trazabilidad

Cada operación registra `operation_id`, `idempotency_key`, secuencia, timestamp UTC, actor/ejecutor y versión, rama/SHA, checkpoint de entrada, capacidad/dominio, hashes y tamaños de entrada/salida, pruebas, validación, referencia de rollback y estado/motivo final. No registrar secretos.

Cadena obligatoria: `SOURCE → INPUT → OPERATION → OUTPUT → TEST → VALIDATION → INDEPENDENT_VALIDATION → CERTIFICATION`. Si falta un eslabón, se bloquea la certificación de esa unidad. Telemetría de Kestra, CI verde o un JSON de resultados no sustituyen pruebas de comportamiento.

## 7. G23, G24 y promoción

- G23: validación independiente, separada del generador, sobre el mismo SHA y hashes de artefactos.
- G24: certificación posterior a G23, con evidencia completa, no-regresión y rollback verificados sobre la misma revisión.
- Prohibida la propagación automática de certificación. SUCCESS no equivale a G23 ni G24.
- No fusionar ni promover a main hasta autorización explícita y aprobación documentada de ambas puertas.

## 8. Estado inicial y aceptación

Este contrato no abre por sí solo los bloqueos existentes. El estado inicial registrado sigue bloqueado: D04 sin ejecutor material válido, CUSTOSZ V7 sin ejecutor material vinculado, MetaOS rechazado por la validación WASM registrada, y G23/G24 pendientes. La automatización debe detectarlo y producir telemetría, sin simular desbloqueo.

El contrato solo podrá declararse implementado cuando exista evidencia de: (1) ciclos persistentes reales de Kestra; (2) auditoría GitHub Actions de 12 horas observada sin tocar main; (3) CUSTOSZ V7 enlazado a un ejecutor material; (4) MetaOS validado y aislado; (5) reanudación idempotente; (6) D04 y pruebas conductuales sin recursión; (7) reparación y rollback probados; (8) telemetría completa en un SHA; (9) G23 PASS y después G24 PASS en ese SHA; (10) no-regresión verificada.

**Certificación:** NOT CERTIFIED hasta cumplir la evidencia y validación independiente exigidas.
