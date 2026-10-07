# CONTINUACIÓN MATERIAL P02 — LRB_APP/0.4

MISSION_ID = MIS-LOUKSNA-ZD-V04-P02-20261007
PARENT_MISSION = MIS-LOUKSNA-ZD-V04-MASTER-20261007
PARENT_CHECKPOINT = CHECKPOINT_01
PARENT_EVIDENCE_RUN = 37659470099
AUTHORITY = Louksna.md
SUPPORTING_ASSURANCE = PUAC2.md
EXECUTOR = CUSTOSZ_V7
EXECUTION_GOVERNOR = CUSTOSZ_RUNTIME_V1
TARGET_BRANCH = work/louksna-zd-v04-master-20261007
POINT = P02_LRB_APP_0_4_TYPED_PROTOCOL
DOCTRINE = EXTEND_DO_NOT_REPLACE
FAILURE_POSTURE = FAIL_CLOSED
BLIND_RETRY = FALSE
CANONICAL_MUTATION = FALSE
CERTIFICATION_PROPAGATION = FALSE

## Entrada obligatoria
CHECKPOINT_01.status = PASS_P01_INPUT_RECONCILIATION
CHECKPOINT_01.next_point = P02_LRB_APP_0_4_TYPED_PROTOCOL
REMOTE_BRIDGE_HEAD = ad95248dd78fadf45645774e0338df0f1bbc128b
V03_HEAD = 7a1449a5d6194b6cbc3e083bf1c7ba55533ad196

## Objetivo material
Integrar en la rama V0.4 el sustrato exacto del Remote Bridge congelado y añadir una
capa de protocolo de aplicación LRB_APP/0.4 tipada, versionada y fail-closed.

Tipos mínimos:
- CHAT
- ARTIFACT_TRANSFER
- VOICE_SESSION
- TRANSCRIPT
- TTS
- REASONING_REQUEST
- GITHUB_OPERATION

Cada envelope debe ligar como mínimo:
schema, version, message_type, operation_id, mission_id, session_id, scope,
payload_sha256, payload_size, deadline_utc, replay_nonce, provenance,
evidence_ref y payload.

## Invariantes
1. El Bridge congelado se REUTILIZA byte-exacto como sustrato; no se reescribe desde cero.
2. El POST genérico V0.3 no se convierte en trust path.
3. Ningún tipo autoriza por sí solo ejecución privilegiada, G23, G24 o ACTIVE.
4. Payload y metadata se validan antes de cualquier dispatch.
5. Tipos desconocidos, campos extra, hashes falsos, tamaños falsos, nonce repetido,
   scope vacío, deadline inválido o vencido => HOLD.
6. La capa P02 sólo materializa contrato, validación, replay guard y evidence binding.
7. GITHUB_OPERATION queda tipado pero sus mutaciones siguen sujetas a P09.
8. ARTIFACT_TRANSFER queda tipado pero transferencia material y CAS pertenecen a P05.
9. VOICE_SESSION/TTS/TRANSCRIPT no cambian la voz decidida en P06.
10. REASONING_REQUEST no modifica permisos ni autoridad por perfil de esfuerzo.
11. No se toca main ni Louksna.md.
12. No se marca CERTIFIED ni ACTIVE.

## Anti-parálisis
- Heartbeat de supervisor <= 2 s durante trabajo largo.
- Stale threshold = 10 s.
- Checkpoint por fase: ADMIT, COPY_SUBSTRATE, MATERIALIZE, TEST_TYPED, TEST_REGRESSION,
  PRE_COMMIT, COMMIT, POST_VALIDATE.
- Una falla bloquea sólo la transición dependiente.
- No hay retry idéntico sin nueva evidencia.
- El material incompleto nunca se commitea.
- Evidencia del fallo se conserva y la rama vuelve al último commit verificado.

## PASS P02
Sólo si:
- sustrato Bridge exacto materializado;
- los 7 tipos registrados;
- tests positivos y negativos del protocolo PASS;
- suite previa del Bridge completa PASS;
- hash/provenance/replay/deadline/scope validation PASS;
- no-regresión PASS;
- checkpoint P02 emitido;
- commit aislado creado;
- ACTIVE=false, CERTIFIED=false.

NEXT_POINT = P03_CUSTOSZ_RUNTIME_METAOS_EXECUTION_PLANE
