# MISIÓN — RECUPERACIÓN VIVA DROPBOX → GITHUB

MISSION_ID = MIS-CUSTOSZ-DROPBOX-LIVE-RECOVERY-20261007
MISSION_CLASS = CUSTOSZ_DROPBOX_TRANSFER_LIVE_RECOVERY_V1

AUTHORITY = Louksna.md
ASSURANCE = PUAC2.md
WORKER = CUSTOSZ_V7
RUNTIME = CUSTOSZ_RUNTIME_V1
GOVERNOR = MetaOS
SUPERVISOR = SYMPHYLAX_R1

REPOSITORY = Plomillo/luna-linux-bridge
TRANSFER_BRANCH = staging/dropbox-github-cloud-partitioned-20261005
CONTROL_BRANCH = staging/custosz-mission-mailbox-20260928

FAILURE_POSTURE = FAIL_CLOSED
NO_SILENT_OPERATIONS = ABSOLUTE
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
ROLLBACK = REQUIRED
NON_REGRESSION = REQUIRED
DESKTOP_COMMANDER = FORBIDDEN
CODEX = FORBIDDEN
RESTART_FROM_ZERO = FORBIDDEN
AUTO_CERTIFICATION = FORBIDDEN
CERTIFICATION_PROPAGATION = FORBIDDEN

CURRENT_RECONCILED_STATE:
- VERIFIED_PROGRESS = 5/8
- COMPLETED = 2,3,4,6,7
- PENDING = 1,5,8
- LAST_FAILED_RUN = 37653596452
- LAST_DURABLE_CHECKPOINT = CP-37653596452-000008
- LAST_DURABLE_CHECKPOINT_SHA256 = c10e2a15127576d9f0884a6e64b72ba4e897fd4037cfdb7b62d9828a11a91c04
- CURRENT_BLOCKER_IDENTITY = 6af31081a3ae592c678a06396745f8f3d6a617223f2b9796f53c7828102c0722
- CURRENT_BLOCKER = GOVERNED_INVENTORY_EMPTY_AFTER_API_PUBLIC_AND_FROZEN
- ARTIFACT_STORAGE_QUOTA = EXHAUSTED_AT_LAST_RUN
- MATERIAL_BYTE_FLOW_NEW_BYTES = NOT_YET_PROVEN

OBJECTIVE:
Garantizar arquitectónicamente que la transferencia Dropbox→GitHub de los pendientes 1,5,8 vuelva a estar viva y continúe exactamente desde el estado durable preservado.
NO se exige completar 8/8 en esta misión.
El objetivo inmediato y suficiente es demostrar reanudación material real y estable.

SUCCESS_GATE:
1. RESUME_FROM_VERIFIED_CHECKPOINT = TRUE
2. SOURCE_PENDING ∈ {1,5,8}
3. MATERIAL_BYTE_FLOW = TRUE
4. OBSERVED_BYTES > 0
5. los bytes son nuevos y atribuibles al flujo Dropbox→GitHub, no a instalación, cache, artifact download ni evidencia histórica.
6. al cumplirse el gate, STOP_MUTATION = TRUE y dejar que la transferencia siga su curso.

EXECUTION:
- CUSTOSZ V7 debe monitorizar en tiempo real GitHub Actions, logs, checkpoints, commits y estado de transferencia.
- CUSTOSZ_RUNTIME_V1 ejecuta las operaciones materiales autorizadas.
- MetaOS gobierna estados, seguridad, checkpoint, rollback y límites.
- Utilizar GitHub como transporte, telemetría, control, evidencia y plano de reparación.
- Reconciliar siempre estado declarado contra evidencia real antes de mutar.
- Reparar sólo la causa activa; no reescribir subsistemas sanos.
- No perder ni invalidar 2,3,4,6,7.
- No reiniciar desde cero.
- No declarar flujo por heartbeat, runner activo o paso "in_progress".
- Si aparece un nuevo bloqueo, diagnosticar causalmente, aplicar el mínimo delta, verificar rollback y reanudar desde el último checkpoint válido.
- No depender de GitHub Actions artifacts como único canal mientras la cuota esté agotada; usar logs, commits de texto e Issue #7 como evidencia persistente.

RAR_TEXT_GATE:
Si aparece cualquier archivo .rar:
1. calcular y preservar SHA-256 del RAR;
2. NO interpretar el RAR directamente como evidencia;
3. exigir/producir un documento de texto UTF-8 con inventario, rutas, tamaños, hashes y contenido legible pertinente;
4. contrastar y reconciliar ese texto con el RAR;
5. sólo después usar la información en diagnóstico o reparación.
RAR_WITHOUT_TEXT_RECONCILIATION = HOLD.

KNOWN_FAILURE_REPAIR_SCOPE:
Priorizar el descendiente:
6af31081a3ae592c678a06396745f8f3d6a617223f2b9796f53c7828102c0722
No aceptar como solución:
- children=[] falso;
- empty-folder falso;
- PASS sin bytes;
- repetir ciegamente el mismo intento;
- degradar identidad sin evidencia;
- perder checkpoint.
Se permite investigar y corregir el mecanismo de inventario/materialización específico, usar proveedores GitHub/Dropbox ya autorizados y agregar código aditivo estrictamente necesario.

TERMINAL_REPORT:
Cuando exista flujo real, registrar:
- RUN_ID
- checkpoint origen
- pending source activo
- primer evento material
- observed_bytes
- timestamp UTC
- método/proveedor
- prueba de que los bytes son nuevos
- STOP_MUTATION=TRUE
- TRANSFER_ALIVE=TRUE
No continuar modificando después de demostrar flujo vivo salvo que la transferencia vuelva a fallar antes de estabilizarse.
