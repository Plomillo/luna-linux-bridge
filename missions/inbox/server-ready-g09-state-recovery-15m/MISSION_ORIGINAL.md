# MISIÓN DE CONTINUACIÓN QUIRÚRGICA — G09 STATE RECOVERY

MISSION_ID = SR-G09-STATE-RECOVERY-15M-V1
DESTINATARIO = CUSTOSZ_V7
RUNTIME = CUSTOSZ_RUNTIME_V1
SUPERVISOR = SYMPHYLAX_R1
GOVERNOR = MetaOS
AUTHORITY = Louksna.md
ISSUE = #7 SERVER_READY
MISSION_CLASS = TARGETED_G09_STATE_RECOVERY_REMEDIATION
GLOBAL_WALLCLOCK_MAX_SECONDS = 900
START = RECEIPT_VERIFIED
STOP_EARLY_IF_SUCCESS = TRUE
FAILURE_POSTURE = FAIL_CLOSED
DOCTRINE = EXTEND_DO_NOT_REPLACE
NO_REPEAT_CLOSED_WORK = TRUE
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
ROLLBACK = REQUIRED
NON_REGRESSION = REQUIRED
METACOGNITIVE_LAYER = REQUIRED

## CHECKPOINT HEREDADO — NO REPETIR

SOURCE_COMMIT = d1b5b7af30613a79568401a0b96fd557e2afab20
SOURCE_RUN = 36499676844

G08 = PASS
G09 = HOLD
ROOT_BLOCKER = STATE_RECOVERY_NOT_PROVEN
G23 = HOLD
G24 = HOLD
SERVER_CERTIFIED = FALSE
SERVER_READY_FINAL = HOLD

Evidencia material ya demostrada en G09:
- executor_kill_recovery = true
- process_termination_recovery = true
- runtime_failure_recovery = true
- dependency_failure = SAFE_HOLD
- timeout = SAFE_HOLD
- no_orphan_process = true
- evidence_survives_restart = true
- state_recovery = false

NO repetir reboot.
NO re-registrar runner.
NO ejecutar ./run.sh manualmente.
NO repetir G08.
NO tocar Windows, EFI, GPT, particiones, PROYECTOS, F3-DISK ni arquitecturas canónicas.
NO modificar Louksna.md.
NO false PASS.
NO propagar certificación.

## HIPÓTESIS TÉCNICA — NO TRATAR COMO HECHO

Existe una hipótesis fuerte de carrera/frescura del observador:
el verificador puede aceptar un health.json HEALTHY anterior al restart y luego compararlo con el MainPID nuevo.

Esta hipótesis DEBE ser probada o refutada mediante evidencia temporal y causal.
No elevarla a VERIFIED sin ejecución material.

## LOS SIETE PASOS OBLIGATORIOS

### 1. Retomar exactamente desde el checkpoint
Usar G08=PASS y todo trabajo cerrado como evidencia heredada válida.
No repetir pruebas cerradas salvo evidencia concreta de invalidación.

### 2. Corregir/verificar únicamente state_recovery
Inspeccionar la lógica de observación posterior a restart y corregirla de forma aditiva, reversible y mínima.
No ampliar el alcance de la misión.

### 3. Exigir evidencia fresca posterior al restart
state_recovery sólo puede ser TRUE si, DESPUÉS del instante de restart, se demuestra conjuntamente:
- heartbeat_utc posterior al restart;
- heartbeat_seq/progress observable posterior;
- health.status = HEALTHY;
- health.pid == systemd MainPID;
- MainPID > 0;
- servicio active;
- exactamente un proceso esperado y ningún huérfano;
- evidencia persistida fuera del ámbito de rollback.

La frescura temporal debe quedar registrada explícitamente.
Un health.json previo al restart NO es evidencia válida para cerrar state_recovery.

### 4. Reejecutar G09 materialmente
Ejecutar únicamente la prueba necesaria para cerrar G09.
Resultado permitido:
- PASS con evidencia material completa; o
- HOLD con SINGLE_ROOT_BLOCKER exacto y reproducible.

No usar plantilla para fabricar resultado.
No transformar UNKNOWN en PASS.

### 5. Si G09=PASS, recalcular los 15 gates y congelar un único bundle
Recomputar GATE_01..GATE_15.
SERVER_TECHNICAL_READY = PASS únicamente si todos son PASS.
Verificar rollback y non-regression.
Congelar un único candidato con hashes, manifiesto y cadena de evidencia.

Si G09 != PASS, detener promoción y conservar checkpoint.

### 6. Ejecutar G23 independiente sobre el mismo bundle congelado
G23 debe ser fresh/read-only, sin repair, sin mutar candidato y sin ejecutar código candidato cuando pueda tratarse como datos.
Debe verificar integridad, reproducibilidad, rollback, non-regression, runtime identity, evidencia y ausencia de findings críticos.

Si G23 != PASS, G24 queda bloqueado.

### 7. Sólo con G23=PASS, ejecutar G24 sobre exactamente el mismo candidato/digest
G24 no puede certificar otro artefacto, digest o estado.
No hay certificación por workflow green.
No hay propagación automática.
PASS terminal sólo si:
G08=PASS
AND G09=PASS
AND ALL_15_GATES=PASS
AND ROLLBACK=PASS
AND NON_REGRESSION=PASS
AND G23=PASS
AND G24=PASS.

## CAPA METACOGNITIVA OBLIGATORIA

Para cada decisión crítica registrar:
CLAIM
EVIDENCE
SOURCE
TIMESTAMP_UTC
OBJECT_HASH
CONFIDENCE
COUNTEREVIDENCE
ASSUMPTIONS
LIMITATIONS
CAUSAL_RELATION
OPERATIONAL_IMPACT

Estados permitidos de confianza:
C0 = UNKNOWN
C1 = PLAUSIBLE
C2 = SUPPORTED
C3 = VERIFIED
C4 = INDEPENDENTLY_REPRODUCED

No degradar evidencia ya demostrada.
No elevar inferencia o hipótesis a VERIFIED.
Separar siempre:
OBSERVED
VERIFIED
INFERRED
CONTRADICTED
UNKNOWN

## PUAC2 / GOBERNANZA

Aplicar, dentro del alcance pertinente:
PUAC.C25 alcance/afirmaciones
PUAC.C26 evidencia/argumentación
PUAC.C27 independencia estructural
PUAC.C28 seguridad/riesgo
PUAC.C29 integridad/reproducibilidad
PUAC.C30 integración/no regresión
PUAC.C31 reversibilidad
PUAC.C32 vigencia/reevaluación

PUAC2 no sustituye G23 ni G24.
G23 no sustituye G24.
GitHub Actions success no equivale a misión PASS.
Heartbeat no equivale a progreso.
Restart exitoso no equivale por sí solo a state_recovery demostrado.

## EVIDENCIA MÍNIMA DE SALIDA

Publicar en GitHub, vinculada por SHA-256:
- G09_STATE_RECOVERY_EVIDENCE.json
- G09_FAILURE_RECOVERY_EVIDENCE.json actualizado
- detalle temporal/causal del restart y heartbeat
- inventario PID/proceso posterior
- TERMINAL_GATES.json si procede
- FROZEN_BUNDLE_MANIFEST.json si procede
- G23_RESULT.json si procede
- G24_RESULT.json si procede
- README_SERVER_READY_FINAL.md actualizado

README final debe declarar:
START_UTC
END_UTC
ELAPSED_SECONDS
SOURCE_COMMIT
SOURCE_RUN
CHANGES_APPLIED
TESTS_EXECUTED
OBSERVED_RESULTS
G08
G09
G23
G24
SERVER_TECHNICAL_READY
SERVER_CERTIFIED
SERVER_READY_FINAL
SINGLE_ROOT_BLOCKER
KNOWN_LIMITATIONS
NEXT_AUTHORIZED_ACTION

## PRESUPUESTO

MAX = 900 segundos brutos desde RECEIPT_VERIFIED.
Terminar antes si se alcanza un resultado concluyente.
No esperar artificialmente.
No reiniciar el reloj mediante retry, nuevo job, nuevo mission_id o continuation.
Si el tiempo se agota sin PASS:
persistir checkpoint + blocker exacto + evidencia + siguiente verificación requerida.
El agotamiento del tiempo NO autoriza false PASS.

## CRITERIO DE CIERRE

SUCCESS únicamente con evidencia material completa y cadena G23 -> G24 válida.

Si no se demuestra state_recovery:
G09 = HOLD
SERVER_READY_FINAL = HOLD
y conservar evidencia reproducible.

Ejecutar desde ahora.
