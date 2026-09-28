# MISIÓN — MATERIALIZACIÓN DEL ECOSISTEMA METACOGNITIVO OPERACIONAL V1

MISSION_ID = MIS-META-ECO-20260928-V1
AUTHORITY = Louksna.md
GOVERNOR = MetaOS
WORKER = CUSTOSZ V7
RUNTIME = CUSTOSZ_RUNTIME_V1
INGRESS = CUSTOSZ MISSION MAILBOX
DOCTRINE = EXTEND_DO_NOT_REPLACE
BUILD = APPEND_ONLY
FAILURE_POSTURE = FAIL_CLOSED
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
ROLLBACK = REQUIRED
NON_REGRESSION = REQUIRED
NO_SILENT_OPERATIONS = ABSOLUTE
CERTIFICATION_PROPAGATION = FORBIDDEN

## Intent

Materializar, probar y endurecer progresivamente la superficie operacional declarada en
`ecosystem/metacognitive-operational-v1/CAPABILITIES.json`, reutilizando primero capacidades reales ya presentes en Louksna, MetaOS, CUSTOSZ V7 y su Runtime.

## Regla absoluta de no duplicación

Antes de implementar cualquier MCAP:
1. reconstruir el censo exacto de las 72 capacidades CUSTOSZ V7 desde una fuente legible/verificable;
2. comparar identidad, función, inputs, outputs, dependencias, dominio y failure modes;
3. si existe equivalencia, crear binding/adaptador al componente existente;
4. sólo una frontera funcional no representada puede convertirse en extensión candidata.

`CUSTOSZ72_EXACT_DIFF_PENDING => NEW_CAPABILITY_CANONICAL_ADMISSION_DENIED`.

## Compute policy

```text
HEAVY_COMPUTE = GITHUB_HOSTED_ONLY_OR_EXPLICIT_EXTERNAL_CLOUD
USER_HOST_HEAVY_COMPUTE = FORBIDDEN
REMOTE_DESKTOP_COMMANDER = AUXILIARY_ONLY
CUSTOSZ = WORKER
```

El runner auxiliar local puede realizar únicamente ingress/routing/receipts livianos bajo el límite existente. No debe procesar corpus masivos, modelos, traducciones gigantes, índices masivos ni feeds de mercado.

## Materialization order

1. Control plane + schemas + validators.
2. Exact CUSTOSZ72 dedup census.
3. Ecosystem contract adapters.
4. Architectural mirror/shadow.
5. Cloud worker scheduler/resource governor.
6. Remote corpus streaming.
7. Massive document map/index.
8. Translation pipeline.
9. High-resolution telemetry/evaluation.
10. Durable workflows + external data plane only when evidenced.
11. Market/stablecoin/labor adapters.
12. General/specific metacognitive operational composition.
13. Training LAST.

Do not reorder training ahead of assurance.

## Corpus rule

Never full-download a massive corpus merely to inspect it. Use source identity, rights check, remote metadata, shards/ranges, streaming/query, ephemeral processing and derived evidence.

## Output policy

Persistent Git output is control-plane only. For each material mission, produce small:
- `README_FINAL.md`
- machine-readable result/evidence manifest
- hashes
- provenance pointers
- unresolved blockers
- rollback pointer

Do not commit full corpus bytes, huge generated translations, model weights or transient worker state.

## G23/G24

This mission cannot self-award G23 or G24. Structural validation is not certification.
G23 must independently validate one frozen digest without repair.
G24 may evaluate only the exact digest accepted by G23.

## Terminal state

PASS is permitted only for the explicitly implemented/materialized subset with complete evidence.
The global 59-capability ecosystem remains `PARTIAL/HOLD` until all admitted capabilities are materially implemented, exact non-duplication is proven, and external G23/G24 complete.

No false global PASS.
