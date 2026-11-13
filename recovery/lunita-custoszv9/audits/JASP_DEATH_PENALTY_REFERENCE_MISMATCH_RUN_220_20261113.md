# Auditoría forense — JASP Death Penalty, run #220

STATUS=BLOCKED_REFERENCE_PROVENANCE_UNKNOWN
ROOT_CAUSE=UNRESOLVED
FUNCTIONAL_CERTIFICATION=NOT_GRANTED

## Identificación de ejecución

Repository: Plomillo/luna-linux-bridge
Operational branch: fix/lunita-v18-rootfs-bound-checkpoint-20261109
Operational HEAD: 3db072d393d62f9b033cdf70832d2d66df7ff534
Workflow: Lunita v1.8 Direct Functional Validation
Workflow run: 43342684248 (#220)
Target/independent job: 131615414711
Candidate: G06_REBUILD_CANDIDATE_R1 / 1.8.0
Workflow URL: https://github.com/Plomillo/luna-linux-bridge/actions/runs/43342684248

## Identidad runtime comprobada

JASP application ID: org.jaspstats.JASP
JASP version observed: 0.98.8
JASP source commit observed: b6cd3b0310be4e18e1b673ac11f14e55615c8fa1
Flatpak deployment commit observed: 83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7
Runtime identity check: PASS
Execution mode: pinned Flatpak sandbox with network unshared

## Fixture original

Packaged source path: Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp
Original fixture SHA-256: fc8b6f8faf0e4437c8e4ab4bd922b3e959a0d4549c813b229bc5708050851895
Original fixture identity matched pin and source remained unchanged: true
Actual JASP process return code: 1
Output marker: The results are different
Original fixture log SHA-256: 2af5fe0b099f01c1ab5b7467fbb7ab4ffc4679955b8dfe30c024f4f881a5463f

### Referencia almacenada

| Modelo | P(M|data) | BF01 |
|---|---:|---:|
| RaceVictim + RaceDefendant + Death + RaceVictim✻RaceDefendant + RaceVictim✻Death | 0.508 | 1.000 |
| RaceVictim + RaceDefendant + Death + RaceVictim✻RaceDefendant + RaceVictim✻Death + RaceDefendant✻Death | 0.394 | 1.289 |
| RaceVictim + RaceDefendant + Death + RaceVictim✻RaceDefendant + RaceVictim✻Death + RaceDefendant✻Death + RaceVictim✻RaceDefendant✻Death | 0.094 | 5.404 |
| RaceVictim + RaceDefendant + Death + RaceVictim✻RaceDefendant | 0.004 | 127.0 |

### Tabla recalculada

| Modelo | P(M|data) | BF01 |
|---|---:|---:|
| RaceVictim + RaceDefendant + Death + RaceVictim✻RaceDefendant + RaceVictim✻Death | 0.514 | 1.000 |
| RaceVictim + RaceDefendant + Death + RaceVictim✻RaceDefendant + RaceVictim✻Death + RaceDefendant✻Death | 0.358 | 1.434 |
| RaceVictim + RaceDefendant + Death + RaceVictim✻RaceDefendant + RaceVictim✻Death + RaceDefendant✻Death + RaceVictim✻RaceDefendant✻Death | 0.127 | 4.043 |
| RaceVictim + RaceDefendant + Death + RaceVictim✻RaceDefendant + RaceDefendant✻Death | 0.002 | 342.3 |

Interpretation: four models exist on each side, but their model terms and statistical values differ. This is a semantic/statistical mismatch, not a formatting discrepancy.

## Replay determinista sobre clon temporal

Original source SHA-256 before and after: fc8b6f8faf0e4437c8e4ab4bd922b3e959a0d4549c813b229bc5708050851895
Temporary seeded clone SHA-256: 4b642cc13549f99f1b386791c3a670e6fb9cc34430f564ad68820bde46af4c2f
Calculated rows SHA-256, save: ef1f4ec4493aea848c9449f6ca96864a1cd95e353544601c6edf52fb284a1a32
Calculated rows SHA-256, rerun: ef1f4ec4493aea848c9449f6ca96864a1cd95e353544601c6edf52fb284a1a32
Deterministic replay: PASS
Reference comparison: BLOCKED_STORED_REFERENCE_MISMATCH
Real save subprocess return code: 1
Real rerun subprocess return code: 1
Stored reference contained four models; replay calculated three rows.
Save log SHA-256: e613a1af36a963b24c5440939ca2630ed5b4f35fa4b926e4bde8f6baecf92bdd
Rerun log SHA-256: 613ac30e6d20ee8f14256edb550894b9d3731184d8e67c43221df4eb2b7a4ebf
Original sample unchanged: true
Temporary clone stable after save/rerun and removed: true

Replay is evidence of repeatability of the seeded copy only. It is not evidence that the original fixture matches the historical stored results.

## Other gates in run #220

Reliability JASP test: PASS, RC=0; log SHA-256 6d59c6ad9dae61a62ac61f2bf5dd6222fbe82214112733058d21284727445e00
WeightGain JASP test: PASS, RC=0; log SHA-256 07267743342fb8f42d099e65b735f3d7af856f4535e44eed9deab3330553826e
Actual target E01-E15 and legacy application smoke tests: PASS
SquashFS package and extraction round-trip: PASS
Independent JASP/rootfs lane: FAILURE
Final candidate certifier: SKIPPED
S32 receipt: NOT_ISSUED
Stable release receipt: NOT_ISSUED
Functional certificate: NOT_ISSUED

Candidate artifact ZIP: ID 14001800226; size 3,873,216,987 bytes; digest sha256:d3beaab9200695cdd47fdb911f84a4da4bb5ba82fcfd5c7d794c0c832ad6225a
Evidence artifact ZIP: ID 14000754132; size 24,501,636 bytes; digest sha256:515b289cce4e60999d934468511ffe8eb935f680fb41a0848816749023ed4a9e
These are GitHub ZIP artifact digests, not the SHA-256 of the internal LUNITA.squashfs image.

## Forensic conclusion

The run proves a mismatch between stored Death Penalty outputs and outputs calculated by the pinned JASP runtime. Runtime identity and fixture integrity pass, so the failure is not explained by an observed JASP deployment/source/version mismatch. The replay copy is deterministic across two invocations but does not reproduce the stored four-model reference. The available logs do not establish the producer version, module build, exact analysis options or seed state that generated the saved reference. Randomness, historical result provenance, changed module behavior and configuration interaction remain hypotheses, not proven causes.

No stored reference was changed, no tolerance was relaxed, and no test was suppressed. The correction path is to obtain authoritative provenance for the stored result and perform an independently reproducible comparison on the exact pinned data/runtime. Any new candidate baseline must be versioned separately while retaining the historical bytes and digest.

Required status until root cause and reference provenance are resolved: JASP_REFERENCE_GATE=BLOCKED; ROOT_CAUSE=UNRESOLVED; REFERENCE_PROVENANCE=UNKNOWN; CERTIFICATION=NOT_GRANTED.