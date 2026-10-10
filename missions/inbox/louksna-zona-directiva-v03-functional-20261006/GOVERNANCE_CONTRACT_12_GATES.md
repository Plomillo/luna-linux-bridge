# CONTRATO DE EJECUCIÓN GOBERNADA — LOUKSNA ZONA DIRECTIVA V0.3
CONTRACT_ID = LOUKSNA-ZD-V03-12GATE-CONTRACT-20261009
MISSION_ID = MIS-LOUKSNA-ZD-V03-FUNCTIONAL-20261006
AUTHORITY = Louksna.md
ASSURANCE = PUAC2.md
BASELINE_BRANCH = work/louksna-zona-directiva-candidate-20261005
BASELINE_COMMIT = 6e34fddaae985bd9041be107b80e056f806092d2
INTEGRATION_BRANCH = work/louksna-zona-directiva-v0.3-functional-20261006
MODE = SEQUENTIAL_CHECKPOINT_GATED
DOCTRINE = EXTEND_DO_NOT_REPLACE
FAILURE = FAIL_CLOSED
MAIN_MUTATION = FORBIDDEN
AUTO_MERGE = FORBIDDEN
AUTO_CERTIFICATION = FORBIDDEN
SILENT_OPERATIONS = FORBIDDEN
CERTIFICATION_PROPAGATION = FORBIDDEN

## 1. Objeto y fuerza operativa

Este contrato gobierna el trabajo de Zona Directiva V0.3 desde el punto 1 hasta el punto 12, en orden cronológico estricto. No sustituye Louksna.md ni PUAC2.md; no modifica retrospectivamente la certificación de V0.2. Es una extensión de gobernanza para esta misión y debe incorporarse a la rama de trabajo mediante revisión trazable.

Una etapa posterior NO queda autorizada por calendario, intención, comentario, compilación aislada ni por el mero hecho de que exista una rama. Sólo queda habilitada cuando su predecesora tiene checkpoint registrado, evidencia verificable, validación aprobada y decisión explícita de continuar.

## 2. Máquina de estados obligatoria

Estados permitidos por etapa:
LOCKED -> READY -> IN_PROGRESS -> EVIDENCE_SUBMITTED -> VALIDATING -> CHECKPOINT_PASS

Ruta de fallo:
ANY_STATE -> BLOCKED -> REMEDIATION_REQUIRED -> REVALIDATING -> (CHECKPOINT_PASS | BLOCKED)

Prohibido:
- saltar una etapa;
- marcar PASS por una prueba estática cuando se exige ejecución real;
- autoconceder G23/G24;
- continuar ante evidencia ausente, contradictoria, inválida o no reproducible;
- fusionar directamente a main;
- modificar o reemplazar la rama/commit base congelados;
- declarar una función operativa si sólo existe una interfaz o stub.

## 3. Regla de ramas

La rama de integración permanece:
`work/louksna-zona-directiva-v0.3-functional-20261006`

Cada punto se trabaja en una rama aislada derivada del último checkpoint aceptado, no de un estado futuro ni de main. Convención:
- `work/zd-v03-p01-backend-evidence-20261009`
- `work/zd-v03-p02-remote-bridge-20261009`
- `work/zd-v03-p03-health-ui-20261009`
- `work/zd-v03-p04-existing-runtime-tests-20261009`
- `work/zd-v03-p05-attachments-20261009`
- `work/zd-v03-p06-voice-20261009`
- `work/zd-v03-p07-security-regression-20261009`
- `work/zd-v03-p08-debian-build-20261009`
- `work/zd-v03-p09-debian13-install-rollback-20261009`
- `work/zd-v03-p10-evidence-dossier-20261009`
- `work/zd-v03-p11-independent-validation-g23-20261009`
- `work/zd-v03-p12-certification-freeze-g24-20261009`

La rama del punto N+1 se crea únicamente después de aprobar el checkpoint N. Cada rama debe tener una PR cuyo destino sea la rama de integración; el destino y el commit base se verifican antes de comenzar. Si GitHub no permite proteger ramas/PR mediante la configuración disponible, el control se mantiene fail-closed por este contrato: no se considera autorizado el avance sin evidencia del gate.

## 4. Esquema obligatorio de cada checkpoint

Cada checkpoint DEBE registrar un archivo JSON versionado bajo:
`missions/inbox/louksna-zona-directiva-v03-functional-20261006/checkpoints/CPNN.json`

Campos obligatorios:
- schema: `LOUKSNA_ZD_V03_CHECKPOINT/1.0`
- contract_id, mission_id, checkpoint_id, stage_number
- predecessor_checkpoint_id y predecessor_commit_sha
- work_branch, pull_request_url, candidate_commit_sha
- started_at_utc, completed_at_utc
- requirements[], tests[] (cada prueba incluye método, comando o procedimiento, resultado, evidencia_uri/hash y entorno)
- evidence_manifest_sha256
- validation_status: PASS | FAIL | BLOCKED
- independent_validation_status: PENDING | PASS | FAIL (obligatorio en puntos 11 y 12)
- unresolved_findings[]
- rollback_reference
- decision: CONTINUE | STOP
- reviewer y review_timestamp_utc

Un checkpoint es inválido si falta un campo, contiene un resultado sin evidencia, no identifica el commit probado, la evidencia no corresponde al artefacto probado o el resultado no es reproducible. No se permiten hashes inventados ni enlaces ficticios.

## 5. Criterio de aprobación

Para aprobar un checkpoint se requiere todo lo siguiente:
1. Criterios de aceptación del punto cumplidos.
2. Pruebas pertinentes ejecutadas en el entorno declarado.
3. Evidencia original conservada, fechada y vinculada al commit exacto.
4. Ningún fallo crítico abierto dentro del alcance del punto.
5. Análisis de impacto/no-regresión completado.
6. Rollback viable y documentado.
7. Revisión explícita del checkpoint.
8. El archivo CP correspondiente validado por un comprobador automatizado y revisado.
9. Decisión CONTINUE registrada.

Una prueba no ejecutada debe declararse NOT_RUN/BLOCKED, nunca PASS. Las pruebas estáticas no sustituyen build, runtime, instalación, integración, rollback ni validación independiente cuando sean aplicables.

## 6. Secuencia cronológica y gates

### P01 — Backend y ledger de evidencia
Rama: `work/zd-v03-p01-backend-evidence-20261009`
Alcance: fallos de escritura de evidencia; política de error; consistencia del ledger; marcas temporales y orden; inyección de fallos; persistencia SQLite; eliminación de credenciales verificada.
Aceptación: una operación crítica no informa éxito si falla la evidencia obligatoria; fallo de escritura observable y gobernado; pruebas de fallo y recuperación; token ausente después de desconexión.
Evidencia: logs de pruebas, resultados de DB, escenarios de fallo, hash del commit.
Checkpoint: CP01.
P02 permanece LOCKED hasta CP01 = PASS.

### P02 — Puente remoto seguro
Rama: `work/zd-v03-p02-remote-bridge-20261009`
Alcance: HTTPS, timeouts, límite de respuesta, lista de destinos permitidos, prevención SSRF/red privada, autenticación, esquema estricto y errores.
Aceptación: round-trip real con endpoint autorizado; casos negativos reproducibles; ninguna respuesta simulada.
Evidencia: configuración saneada, endpoint identificado sin secretos, solicitud/respuesta redactadas, logs y pruebas.
Checkpoint: CP02.

### P03 — Estado de salud conectado a la UI
Rama: `work/zd-v03-p03-health-ui-20261009`
Alcance: reemplazar estados fijos de salud por `runtime_probe` real; estados PASS/DEGRADED/FAIL/UNKNOWN.
Aceptación: fallos inducidos en SQLite/backend se reflejan en UI; no hay estado operativo falso.
Checkpoint: CP03.

### P04 — Verificación end-to-end de las funciones existentes
Rama: `work/zd-v03-p04-existing-runtime-tests-20261009`
Alcance: inicio offline; ajustes persistentes tras reinicio; DB local; GitHub real read-only; repositorios/PR; refresh; eventos; errores de red; desconexión; chat local persistente.
Aceptación: pruebas de runtime, no sólo marcadores de código; secretos no aparecen en SQLite, UI ni logs.
Checkpoint: CP04.

### P05 — Adjuntos end-to-end
Rama: `work/zd-v03-p05-attachments-20261009`
Alcance: selección, validación de tipos/tamaño, nombres y rutas seguras, persistencia, asociación a mensajes, hash, limpieza y transporte autorizado.
Aceptación: ciclo completo probado y casos adversariales. Si no hay transporte remoto real, declarar sólo adjuntos locales y dejar el gate de transporte abierto.
Checkpoint: CP05.

### P06 — Voz end-to-end
Rama: `work/zd-v03-p06-voice-20261009`
Alcance: permisos, captura, inicio/pausa/cancelación, transcripción/voz según pila elegida, transporte, respuesta, privacidad y retención.
Aceptación: captura, transporte y respuesta reales; errores visibles; ninguna acción destructiva por voz; nada simulado.
Checkpoint: CP06.

### P07 — Seguridad y no-regresión
Rama: `work/zd-v03-p07-security-regression-20261009`
Alcance: suite automatizada y adversarial, secretos, red, offline, errores, seis secciones de UI, identidad visible LOUKSNA-only, dependencias y superficie de ataque.
Aceptación: resultados completos; todos los bloqueos críticos resueltos; fallos no críticos documentados y aceptados formalmente sin rebajar requisitos canónicos.
Checkpoint: CP07.

### P08 — Build y paquete Debian
Rama: `work/zd-v03-p08-debian-build-20261009`
Alcance: workflow GitHub Actions, TypeScript, Rust, Tauri, .deb, dependencias, lintian y hashes.
Aceptación: build real verde y paquete identificado por SHA-256; no ocultar errores de lintian con `|| true`; excepciones explícitas y justificadas.
Checkpoint: CP08.

### P09 — Instalación Debian 13 KDE y rollback
Rama: `work/zd-v03-p09-debian13-install-rollback-20261009`
Alcance: instalación, arranque, escenarios runtime, actualización/reversión y limpieza en Debian 13 KDE.
Aceptación: evidencia del entorno real o VM identificada, instalación y rollback exitosos; si el entorno no está disponible, BLOCKED, no PASS.
Checkpoint: CP09.

### P10 — Expediente de evidencia consolidado
Rama: `work/zd-v03-p10-evidence-dossier-20261009`
Alcance: inventario requisito-prueba-evidencia, hashes, versiones, comandos, entornos, salidas, fallos, limitaciones, procedencia y rollback.
Aceptación: cadena completa `SOURCE -> INPUT -> OPERATION -> OUTPUT -> TEST -> VALIDATION -> INDEPENDENT_VALIDATION -> CERTIFICATION`; toda afirmación crítica apunta a evidencia.
Checkpoint: CP10.

### P11 — Validación independiente G23
Rama: `work/zd-v03-p11-independent-validation-g23-20261009`
Alcance: revisor distinto del implementador; verificación de código, artefacto, pruebas, hashes, no-regresión y expediente.
Aceptación: dictamen independiente trazable; discrepancias devuelven la etapa pertinente a remediación.
Checkpoint: CP11. G23 no se hereda ni se presume.

### P12 — Certificación G24 y freeze
Rama: `work/zd-v03-p12-certification-freeze-g24-20261009`
Alcance: comprobar CP01-CP11, resolver hallazgos, generar manifiesto/hash final, congelar artefacto y registrar rollback.
Aceptación: cadena de certificación completa y autorización válida; artefacto, versión y hash congelados; no mutación posterior. Si falta evidencia, G24 = DENIED y V0.3 no se activa.
Checkpoint: CP12. G24 no se infiere de build ni de G23 aislado.

## 7. Protocolo de avance obligatorio

Para cada punto:
1. Verificar que todos los checkpoints anteriores estén PASS.
2. Verificar rama y commit de partida.
3. Ejecutar únicamente el alcance autorizado del punto.
4. Ejecutar las pruebas definidas y conservar salidas originales.
5. Generar el manifiesto de evidencia y su hash.
6. Preparar CP correspondiente.
7. Revisar resultados y no-regresión.
8. Registrar PASS/FAIL/BLOCKED con causa.
9. Si PASS, registrar CONTINUE y habilitar la etapa siguiente.
10. Si FAIL/BLOCKED, STOP, conservar evidencia, abrir remediación y no crear/ejecutar etapa posterior.

No se debe lanzar trabajo concurrente para P01-P12. Sólo tareas de lectura o revisión independientes pueden ejecutarse en paralelo si no alteran artefactos ni saltan gates.

## 8. Ramas, PR y protección de main

- Todas las escrituras de implementación se realizan en ramas de trabajo aisladas.
- Cada etapa presenta cambios por PR y conserva el historial.
- La rama `main` es sólo lectura para esta misión; ningún workflow de esta misión puede escribir o fusionar en ella.
- No habilitar auto-merge ni modificar protecciones del repositorio sin autorización.
- No cerrar la PR #52 ni fusionar cambios por el mero hecho de añadir este contrato.
- La PR #52 sigue siendo draft hasta que su alcance y los gates aplicables tengan evidencia revisada.
- La rama de integración sólo avanza tras aceptar el checkpoint de la etapa correspondiente.

## 9. Responsabilidades y límites

Implementador: ejecuta el alcance, aporta evidencia y declara limitaciones; no se autocertifica.
Validador: contrasta criterios, commits y evidencia; puede rechazar.
Validador independiente G23: no debe ser el implementador de la etapa.
Autoridad de certificación G24: decisión separada y explícita.
Orquestación GitHub: conserva ramas, PR, artefactos y registros; la existencia de automatización no prueba por sí misma corrección funcional.

Si no se dispone de un actor independiente o del entorno de ejecución requerido, el estado es BLOCKED y se informa la dependencia; no se inventa un actor, resultado ni entorno.

## 10. Estado inicial obligatorio

Al aprobar este contrato:
- P01 = READY; P02-P12 = LOCKED.
- Ningún checkpoint se considera aprobado por anticipado.
- El primer trabajo autorizado es P01 en su rama aislada.
- La rama de integración y la PR #52 permanecen sin merge automático.
- V0.3 permanece CANDIDATE / NOT_ACTIVE / NOT_CERTIFIED.
- Estado de ejecución de cada gate debe reflejar evidencia real de GitHub Actions y pruebas, no intención.

## 11. Registro de cambios

Toda modificación del contrato requiere commit visible, motivo, revisión y análisis de impacto. Los requisitos canónicos de Louksna.md no se modifican por este contrato. Ante conflicto, detener y escalar; no reconciliar silenciosamente.

END_CONTRACT
