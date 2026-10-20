# Lunita / CUSTOSZ V9 Recovery Gate

Status snapshot: 2026-10-20 UTC. Additive recovery track; no frozen G06/G08 object is replaced.

## Verified facts
- Repository: Plomillo/luna-linux-bridge. Dedicated branch: recovery/lunita-custoszv9-operational-20261020.
- The supplied Dropbox URL is a /home/... navigation URL, not a direct shared-folder link. Connected Dropbox root exposed only /ChatGPT_Transfers; LUNITA_MATERIALIZATION search returned zero results; shared-link metadata returned SHARED_LINK_NOT_FOUND. No project files were downloaded from that URL.
- Frozen G06 rootfs is absent at its declared path. Expected tree SHA-256 26949ca5cf3dccc4009cfaf40077b317d09b3be552d5cdd9dc9fec5018d0d3d7, size 7,325,200,083 bytes, 380,622 entries. Existing LUNITA.squashfs is 671,130 bytes and is not a substitute.
- Candidate G06_REBUILD_CANDIDATE_R1 was based on Ubuntu 24.04 archive SHA-256 094dc0afc6ded1c3e5ce71f7d0b48d5db922155097bc8fb1ec19db2ebdd17ece. Candidate has no automatic certification or identity inheritance.
- Frozen launcher expected SHA is 502f28c2398ee3129f7d4df42bf5117797c19cf59d27cbff218b36bbd271c319; local preserved lunita.py.pre-G05 is SHA dc7d673b16a578c5cc94999856ed4b70d0b039702155779660a1083e2da54066. It is not the frozen original and must be represented only as derived beta.
- Permission repair: candidate state.json is UID 1000 mode 0600; BUILD_PLAN.json UID 1000 mode 0400; receipt remains UID 1000 mode 0640. Content hashes were preserved. Real UID 1000 probe confirmed state readable/writable, plan readable/not writable, and atomic candidate-directory write succeeds.
- Continuation script pre-patch SHA d8b2157b3298e87f768b6997e3d653f15e70c87b80f74030fbcea44f57c73737; current patched SHA 22ff8f20748b95cde43fd22c06bacad32f75b34645e945527e0645c46c456397. Checkpoint: state/checkpoints/CUSTOSZ_ANTI_PARALYSIS_PRE_20261020T173429Z. Patch SHA-256 c0be3fbf367c78624ae9385b07614330fca2558fc55e9ee3c474c59a4ca82d45.
- Anti-paralysis was tested against the actual continuation module in isolated temporary state. It proved a blocked step keeps the same index, records attempts, does not append a completed step or falsify last_progress_utc, applies 300-second bounded retry, and only advances 0→1 following a passing result. Six assertions passed.
- R 4.6.1 source hash was verified from local manifest and build started in candidate rootfs with MAKEFLAGS=-j1. At this status snapshot it was still building R recommended packages. This does not yet prove that Rscript works.
- Permission-gate repository unit tests passed 5/5 after a report-key bug was fixed. The branch-hosted GitHub Actions status was not available through queried API responses; hosted CI is not claimed as passing.

## Permission contract
- state.json: CUSTOSZ UID, mode 0600, read/update.
- BUILD_PLAN.json: CUSTOSZ UID, mode 0400, read only.
- BASE_REBUILD_RECEIPT.json: preserve existing service access, mode 0640, not rewritten by the permissions operation.

## Anti-paralysis contract
- Explicit step_completion=false appends an attempt receipt, retains step_index, preserves last_progress_utc, and returns WAITING_FOR_EVENT with a 300-second bounded retry.
- A blocked attempt is not appended to completed_steps.
- S31 requires a candidate-bound functional-test report and exact beta-launcher hash.
- S32 requires a separate independent report hash-bound to the runtime test report and asserts frozen G06/G08 identities have not changed.
- Canonical frozen G06 remains NOT_GRANTED. A beta receipt, if earned, certifies only G06_REBUILD_CANDIDATE_R1 and does not inherit certification.
- Repository patch: recovery/lunita-custoszv9/patches/custosz_mision1_continuation_v1.antiparalysis.patch.

## Remaining implementation gates
Finish R 4.6.1 build and test; install missing Jamovi/JASP payloads only in candidate; resolve llama shared-library behavior; run actual browser/model/R/application/fault-injection tests; create the candidate runtime report; run separate hash-bound independent validation; restart CUSTOSZ and verify it reaches S31/S32 without advancing blocked work. Do not replace frozen original or canonical bindings.
