# Lunita / CUSTOSZ V9 recovery status
Snapshot: 2026-10-20 UTC. Additive recovery track; no frozen G06/G08 object is replaced.

## Verified
- Dedicated branch: `recovery/lunita-custoszv9-operational-20261020` in `Plomillo/luna-linux-bridge`.
- Dropbox URL provided is a `/home/...` navigation URL, not a direct shared link. Connected Dropbox root shows only `/ChatGPT_Transfers`; search for `LUNITA_MATERIALIZATION` returned zero matches; shared-link metadata lookup returned `SHARED_LINK_NOT_FOUND`. No Dropbox downloads were performed.
- Frozen G06 rootfs is absent from its declared location. Expected tree hash `26949ca5cf3dccc4009cfaf40077b317d09b3be552d5cdd9dc9fec5018d0d3d7`, size 7,325,200,083 bytes, 380,622 entries. Existing `LUNITA.squashfs` is only 671,130 bytes and is not a substitute.
- Candidate `G06_REBUILD_CANDIDATE_R1` has a verified Ubuntu base archive, hash `094dc0afc6ded1c3e5ce71f7d0b48d5db922155097bc8fb1ec19db2ebdd17ece`. Candidate status remains `WAITING_FOR_RUNTIME_REBUILD_INPUTS`; certification `NOT_GRANTED`.
- Local `lunita.py.pre-G05` hash `dc7d673b16a578c5cc94999856ed4b70d0b039702155779660a1083e2da54066` differs from frozen launcher hash `502f28c2398ee3129f7d4df42bf5117797c19cf59d27cbff218b36bbd271c319`. Treat it only as a possible derived beta source, never as the frozen original.
- Permission checkpoint `state/checkpoints/LUNITA_V9_PREPERMISSION_20261020T170630Z` records before/after metadata. `state.json` is UID 1000 mode 0600; `BUILD_PLAN.json` UID 1000 mode 0400; `BASE_REBUILD_RECEIPT.json` unchanged UID 1000 mode 0640. Hashes did not change. UID 1000 probe passed state read/write directory access, plan read, and plan write denied.
- User service `custosz-continuity-v1.service` was active as PID 188434 at inspection time. Liveness is not mission progress; memory peaked at 272.7 MiB against `MemoryHigh=256M`.

## Correct sequence
1. Preserve checkpoints and current evidence.
2. Keep `state.json` writable only to the service UID; keep `BUILD_PLAN.json` service-readable and service-unwritable.
3. Recover exact original only from a resolvable shared link or approved path. Never treat the navigation URL as a direct download.
4. If original remains unavailable, build an explicitly versioned beta from verified existing base and local inputs. Reuse already present files; do not redownload or duplicate.
5. Track `ACCESS_DENIED`, `FILE_MISSING`, `INVALID_JSON`, `IDENTITY_MISMATCH`, `RUNTIME_INPUTS_MISSING`, and functional test failures as distinct states.
6. A blocked action remains pending. Heartbeats, rescan operations, and `PASS_FOR_SUBTASK_ONLY` are not mission progress.
7. Require launcher, model, browser/Brújula, R, Jamovi, JASP, failure-injection, inventory, restart-recovery and independent-validation evidence before certifying any beta.

## Limits
Repository CI can validate this recovery contract and tests; it cannot fetch Dropbox, install host packages, execute the host rootfs or certify Lunita. Host evidence and independent validation remain mandatory.