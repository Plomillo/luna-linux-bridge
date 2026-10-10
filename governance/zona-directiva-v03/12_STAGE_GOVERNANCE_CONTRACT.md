# CONTRATO DE GOBERNANZA OPERACIONAL — ZONA DIRECTIVA V0.3
CONTRACT_ID = LOUKSNA-ZD-V03-12-STAGE-GOVERNANCE-20261009
AUTHORITY = Louksna.md
ASSURANCE = PUAC2.md
TARGET_REPOSITORY = Plomillo/luna-linux-bridge
TARGET_WORK_BRANCH = work/louksna-zona-directiva-v0.3-functional-20261006
GOVERNANCE_BRANCH = governance/louksna-zd-v03-12-stage-gates-20261009
DOCTRINE = EXTEND_DO_NOT_REPLACE
FAILURE = FAIL_CLOSED
NO_MAIN_MUTATION = TRUE
NO_AUTO_MERGE = TRUE
NO_AUTO_CERTIFICATION = TRUE
NO_SILENT_OPERATIONS = TRUE
EVIDENCE_REQUIRED = TRUE
TRACEABILITY_REQUIRED = TRUE
ROLLBACK_REQUIRED = TRUE
G23_INDEPENDENT_VALIDATION_REQUIRED = TRUE
G24_CERTIFICATION_REQUIRED = TRUE
ACTIVE = FALSE

## 1. OBJETO Y ALCANCE

Este contrato impone un flujo operacional secuencial para completar la misión MIS-LOUKSNA-ZD-V03-FUNCTIONAL-20261006. No reemplaza la misión original, Louksna.md, PUAC2.md, el baseline V0.2 ni el trabajo existente. La rama V0.3 sigue siendo candidata de desarrollo hasta que se completen validación independiente G23 y certificación G24 sobre artefactos exactos y evidencia suficiente.

El contrato gobierna el orden, los checkpoints, los criterios de entrada/salida, la telemetría y la detención por fallo. No afirma que una función esté implementada o probada solo porque exista código, documentación, un workflow o un artefacto compilado.

## 2. REGLAS INNEGOCIABLES

1. Ejecutar las etapas en orden 01→12. No iniciar la etapa N+1 antes de que el checkpoint CP-N haya sido evaluado PASS para el mismo candidato/digest.
2. Cada checkpoint requiere evidencia material, ligada al SHA del commit candidato y a los hashes de los artefactos examinados. Una etiqueta textual PASS sin evidencia verificable no satisface el gate.
3. HOLD, FAIL, evidencia ausente, inconsistencia de hashes, workflow cancelado o resultado ambiguo impiden avanzar. No se permite auto-promover HOLD/FAIL a PASS.
4. No modificar `main`, la autoridad canónica, ni el baseline V0.2. No hacer merge automático. No activar ni certificar automáticamente.
5. Todo cambio de etapa produce evento de telemetría con timestamp UTC, contract_id, mission_id, stage_id, checkpoint_id, branch, commit SHA, run ID/URL cuando exista, resultado, pruebas, artefactos/hash, bloqueos y rollback pointer.
6. No registrar secretos, tokens, contenido sensible ni credenciales en logs, artefactos o manifiestos.
7. Los trabajos deben ser idempotentes cuando sea posible; concurrencia serializada; un cambio del commit candidato invalida los checkpoints posteriores ligados al digest anterior.
8. Los artefactos de evidencia se conservan con retención explícita y enlace al run. No se infiere instalación física en equipo real desde una prueba en contenedor.
9. El sistema se detiene ante una condición no contemplada y requiere diagnóstico, checkpoint nuevo y evidencia; no realiza reparación destructiva silenciosa.
10. G23 debe ser independiente del productor. G24 solo puede evaluar un candidato congelado y con G23 favorable. Certificación no implica activación.

## 3. SECUENCIA CANÓNICA Y CHECKPOINTS

### ETAPA 01 — Auditoría forense de mecanismos del repositorio
Objetivo: auditar ramas, protecciones disponibles, workflows, triggers, permisos, concurrency, artefactos, logs, rutas de misión, pruebas y riesgos de mutación.
Evidencia mínima: snapshot de commit/base/branch; inventario de workflows y triggers; permisos y condiciones observables; estado de PR; rutas críticas y hashes; riesgos y hallazgos con severidad.
CP-01 PASS: auditoría reproducible y hallazgos priorizados. HOLD si no se pudo verificar una propiedad de GitHub que requiere permisos/API no disponibles.

### ETAPA 02 — Contrato y plan de ejecución vinculados
Objetivo: comprobar que el contrato y el plan de 12 etapas están versionados y referenciados desde la misión/PR sin alterar autoridad canónica.
Evidencia mínima: hash del contrato, commit, branch, relación con misión, comprobación de no mutación de main/baseline.
CP-02 PASS: vínculo de gobernanza y plan secuencial comprobados.

### ETAPA 03 — Backend, SQLite y ledger de evidencia
Objetivo: verificar persistencia, escritura del ledger, orden, errores, integridad y fallos inducidos.
CP-03 PASS: pruebas de runtime positivas y negativas y eventos ligados a operaciones; error de evidencia impide declarar éxito.

### ETAPA 04 — Credenciales, GitHub READ-ONLY y puente remoto
Objetivo: comprobar Secret Service, eliminación verificable del token, permisos mínimos, API real, límites HTTPS/timeout/tamaño, lista de destinos permitidos y validación de esquema.
CP-04 PASS: pruebas reales sin exposición de secretos; el bridge remoto requiere round-trip con endpoint autorizado.

### ETAPA 05 — Estado real y telemetría de interfaz
Objetivo: vincular el estado UI con health probes y ledger reales; evitar estados estáticos que aparenten actividad.
CP-05 PASS: estados PASS/DEGRADED/FAIL/UNVERIFIED demostrados mediante pruebas de fallo.

### ETAPA 06 — Funciones actuales y adjuntos
Objetivo: verificar offline, persistencia, chat local y, si se implementa, ciclo de adjuntos, hashes, límites, asociación a mensajes y limpieza.
CP-06 PASS: pruebas end-to-end de cada función declarada activa. Toda función incompleta queda marcada no implementada/no verificada.

### ETAPA 07 — Voz end-to-end y regresión de seguridad
Objetivo: probar captura, permisos, transporte y respuesta de voz reales si la función se habilita; ejecutar regresiones, pruebas adversariales y privacidad.
CP-07 PASS: evidencia de extremo a extremo; si la pila de voz no existe o no se puede probar, la etapa no puede declarar voz activa y se documenta el gate abierto. La certificación global queda bloqueada si voz es requisito obligatorio.

### ETAPA 08 — Build y paquete Debian reproducible
Objetivo: compilar frontend/Rust, construir .deb, revisar dependencias, lintian, metadatos, tamaño y SHA-256.
CP-08 PASS: build reproducible o variación explicada y aceptada; no ocultar errores de lintian con `|| true` como si fueran éxito.

### ETAPA 09 — Instalación, ejecución y rollback en Debian 13 KDE
Objetivo: instalar, iniciar y probar en entorno declarado; comprobar desinstalación/reversión y recuperación.
CP-09 PASS: evidencia real del entorno y alcance exacto. Un contenedor no se presenta como prueba de GUI física KDE.

### ETAPA 10 — Expediente y freeze candidato
Objetivo: consolidar manifiesto de evidencias, hashes, SBOM/dependencias disponibles, resultados, riesgos residuales y rollback pointer; congelar el digest exacto.
CP-10 PASS: expediente íntegro, consistente, auditable y ligado al candidato congelado.

### ETAPA 11 — G23 validación independiente
Objetivo: revisión independiente del digest congelado, contrato, pruebas, artefactos, evidencia y no-regresión.
CP-11 PASS: dictamen independiente favorable, hallazgos cerrados o explícitamente bloqueantes. El productor no puede autoaprobarse.

### ETAPA 12 — G24 certificación y decisión de liberación
Objetivo: verificar cadena completa, G23 favorable, evidencia íntegra, rollback y alcance de certificación.
CP-12 PASS: certificación formal vinculada al digest y alcance declarado. ACTIVE continúa FALSE salvo autorización operacional separada y explícita.

## 4. MODELO DE CHECKPOINT

Cada checkpoint debe guardar un documento JSON inmutable o versionado con:
- contract_id, mission_id, stage_id, checkpoint_id;
- candidate_branch, candidate_commit_sha, candidate_tree_sha cuando esté disponible;
- workflow_name, run_id, run_url, timestamp_utc;
- status: PASS | HOLD | FAIL;
- requirements, tests, test_results, evidence_paths, evidence_sha256;
- findings, severity, unresolved_blockers;
- previous_checkpoint_sha256 y rollback_pointer;
- validator_identity y si la validación es independiente;
- next_authorized_stage (solo N+1 si status=PASS; de lo contrario NONE).

La telemetría debe diferenciar EVENT_STARTED, EVENT_PROGRESS, CHECKPOINT_PASS, CHECKPOINT_HOLD, CHECKPOINT_FAIL y RUN_ABORTED. No emitir CHECKPOINT_PASS por la mera creación del archivo.

## 5. AUTORIZACIÓN Y DETENCIÓN

La automatización puede inspeccionar, ejecutar pruebas no destructivas, construir artefactos de candidato y producir evidencias. No puede hacer merge, desplegar, activar funciones no probadas, cambiar la autoridad, omitir checkpoints ni emitir certificación por sí misma.

Si una etapa falla: registrar el fallo, conservar logs y artefactos seguros, detener etapas dependientes, permitir corrección en la rama de trabajo y exigir nueva ejecución. La corrección invalida checkpoints posteriores si cambia el digest examinado.

## 6. ESTADO INICIAL

Este contrato recién creado no constituye evidencia de que CP-01 haya pasado. El primer workflow debe ejecutar la auditoría real y registrar su resultado. El estado inicial es:
CURRENT_STAGE = 01
CURRENT_CHECKPOINT = CP-01
STATUS = PENDING_EXECUTION
NEXT_STAGE = NONE_UNTIL_CP01_PASS

## 7. CRITERIO DE CIERRE

Solo puede declararse completado el proceso si las doce etapas y sus doce checkpoints se encuentran ligados al mismo candidato o a una secuencia explícita de nuevos digests, con invalidación correcta de evidencias obsoletas, sin mutación no autorizada y con G23/G24 documentados.
