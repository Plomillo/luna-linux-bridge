# CUSTOSZ V9 — Lunita recovery bridge

This branch stores the scoped CUSTOSZ V9 bridge and versioned derived Lunita beta launchers. The frozen G06 original is still a distinct, unreplaced source of authority.

## Current derived launcher

- `lunita_beta_v1_7.py` is the current candidate launcher. SHA-256: `46efd711729c344e7efba9ce2503127c48f0b88207cc5a17311ff1d555b075b2`.
- `BETA_PROVENANCE_v1_7.json` binds that SHA, the pre-G05 source hash, the exact JASP/ Jamovi Flathub commits, and the current validation boundary.
- `test_lunita_beta_v1_7.py` checks the commit-pin correction, compilation, fail-closed sandbox behavior, writable Brújula test HOME, bounded Qwen invocation, and provenance.
- `custoszv9_lunita_bridge.py` is the existing bounded V9 adapter. It audits by default; its mutating mode runs one checkpointed continuation tick and appends evidence.

## Verified candidate runtime status

S31 runtime smoke checks pass for launcher start, Brújula, R 4.6.1, existing hash-bound Qwen load/inference evidence, 11/11 fault-injection tests, the exact Jamovi/JASP commit pins, and both apps in the standard Flatpak bubblewrap sandbox. The sandbox was not disabled. The host Flatpak runner was pointed at the already installed candidate via `FLATPAK_SYSTEM_DIR`; no packages or models were downloaded or duplicated.

The v1.6 JASP pin omitted the `79` segment in the exact installed commit. v1.7 corrects it to the observed installed deployment and includes a reconciliation receipt. Jamovi reports 28.13.0.0 and its installed commit matches its pin.

## Open gates — not certified

- S32 independent validation remains blocked by reproducibility differences between several bundled JASP project reference outputs and the installed JASP build. The application and JASPEngine execute, but reference comparisons differ; these findings are not labelled as passing regressions.
- A full independent inventory/dependency closure of the candidate rootfs remains pending.
- The canonical frozen G06 rootfs and its certification manifest are not available at the recorded path. The versioned candidate is not the frozen original and must never inherit its certification. Original-source recovery remains a separate blocker for canonical G06/G08 closure.
- The supplied Dropbox URL is a navigation URL. The connected Dropbox account returned `SHARED_LINK_NOT_FOUND` / `FILE_NOT_FOUND` for that target, so nothing was downloaded.

## Local invocation

From the CUSTOSZ operator project:

```bash
python3 integrations/lunita-custoszv9/custoszv9_lunita_bridge.py --audit
python3 integrations/lunita-custoszv9/custoszv9_lunita_bridge.py --self-test
python3 integrations/lunita-custoszv9/custoszv9_lunita_bridge.py --run-one-step
```

`--audit` is read-only; `--self-test` uses synthetic tasks; `--run-one-step` is the only mutating mode and is limited to one checkpointed continuation tick. Consult MISION1.txt and the current checkpoint before changing state.

The assigned branch is `recovery/lunita-custoszv9-operational-20261020`. CI passing certifies the repository contract tests only, not the live rootfs or the canonical G06/G08 artifacts. Certification remains `NOT_GRANTED`; no automatic propagation, main-branch change, merge, force-push, or workflow dispatch is authorized.


## Persistent mission control and anti-stall correction

The assigned branch now mirrors the actual local continuation controller and supervisor source, plus the scoped V9 governor and standard-library contract tests. The raw local `MISION1.txt` is not copied verbatim into this public repository; `MISION1_CONTROL_V1.json` records its SHA-256 and a non-verbatim operational control projection.

The fail-closed controller rejects a step result whose status is blocked even when the handler omitted `step_completion: false`. This directly addresses the prior fail-open condition in which source-missing and dependency-blocked S26–S30 results could be written as completed. Historical progress records are preserved; this patch does not rewrite history or grant certification.

A separately checkpointed **Cajita priority lane** is invoked before the sequential Lunita S32 backoff return. Its mission hash is checked every tick. It inventories the existing Qwen3 BF16 model and exact pinned converter/quantizer, then provisions an isolated CPU conversion environment, performs a converter dry-run, converts to a versioned GGUF candidate, quantizes that candidate, and records receipts and hashes. Source model weights remain read-only. The lane does not certify the output or integrate it into Cajita automatically.

The S32 JASP regression discrepancy and full independent rootfs/dependency inventory remain explicitly pending. They no longer prevent the independent Cajita lane from running, and they cannot be marked passed by heartbeat, retries, or the existence of artifacts. The live supervisor must be restarted to load the locally patched controller; its subsequent heartbeat/invocation and the Cajita lane state/child-process receipt provide the evidence that the runtime consumed the patch.

New branch contract tests cover fail-closed status handling, exact Qwen3 BF16 model inventory, source-weight immutability, and the requirement that the Cajita lane be invoked before a blocked serial return. These are contract tests, not model-quality validation or certification.

## Fail-closed coordinator overlay (2026-10-20)

The active local coordinator is checkpoint-bound before applying the fail-closed overlay:

- Base coordinator SHA-256: `fc067c31f10f5c99fe4eee4fe3cf145b8be1d73949b6d7d0e3622b39f2fb5fac`
- Staged candidate SHA-256: `cb1eac90562aaf1908ff81bf011cb73e9559707f4d4d68bd04bffdbc5d58dcdf`
- Overlay patch SHA-256: `3266f74e4c5f4343760a1e13d3a8eaa54d5d967f977626f6a554c5967ba5c79e`
- Patch file: `patches/custosz_mision1_continuation_v1.failclosed-overlay.patch`

The overlay is derived from the recorded local checkpoint and retains the existing `continuous_governor.result_blocks_step` guard and the independent Cajita priority lane. It adds a per-step success allowlist, requires explicit `step_completion: true` for S31/S32, validates the independent report against its SHA-256 and runtime-report binding, and appends adjudications for historical false-completion claims without deleting or rewriting the old rows. S28 advances only for its exact source-present recheck status. S30 may advance only when the versioned fallback candidate is explicitly created with the exact R1 identity, matching rootfs path and both frozen-G06/G08 mutation guards false; a pending rebuild remains pending and is not certification. The candidate passed Python compilation, seven focused coordinator tests, eight existing continuous-governor tests, and the coordinator self-test. The overlay passed `patch --dry-run` against the pinned base checkpoint.

The overlay is a versioned patch artifact. It is not proof that the active supervisor has loaded the candidate. Apply only when the live file SHA-256 equals the pinned base hash, checkpoint the current runtime and state first, then run the complete tests and verify the new process PID, loaded script hash and fresh invocation receipt. Do not restart a supervisor while its current child job is running.

## Independent Cajita lane and Python 3.13 converter recovery (2026-10-20)

The local runtime's continuation can back off on Lunita S32; the persistent supervisor now performs one bounded Cajita-lane tick on service cycles where the serial continuation did not already tick it. This avoids duplicate lane ticks within a cycle while keeping Cajita progress independent from the S32 retry timer. A Cajita-lane fault is recorded separately and is not allowed to suppress Lunita processing.

Versioned patches on this assigned branch:

- `patches/custosz_continuity_supervisor_v3.parallel-cajita-lane.patch`
  - SHA-256: `8a16049eddc11f6638dcdb9bdb8254ef2ab7484773f3de977606036b0f5b8189`
  - Pinned live supervisor source SHA-256 after application: `af129eb0b9771786589606c4debd3db2d87412114ab3cabdab44dee29c9a71c9`
- `patches/custoszv9_continuous_governor_v2.compatibility-overlay.patch`
  - SHA-256: `d5bcd9c91e35f0ab93275bb093f4c82c2bec8156cef642db5f832009231448ad`
  - Pinned live governor source SHA-256 after application: `b1181debf4e41f99334eb37ce95c98fa2302337f693b5b117c75dee647f30348`
- `patches/test_custoszv9_continuous_governor_v2.compatibility-overlay.patch`
  - SHA-256: `fdb7d4077791e3f87d937d2ec2cf831bbf02f0142bc3d8ae2cc797fc7cc7d424`

The Python 3.13 route is selected only if the saved failed install receipt and matching log prove that the old command tried `numpy~=1.26.4` and failed on the NumPy source distribution with `metadata-generation-failed`. The recovery attempt is single-shot, retains both original failed receipts, validates the pinned llama.cpp source metadata, and derives a versioned requirements file pinning `numpy==2.2.6`. It does not modify source model weights or certify the candidate.

Regression evidence: the local governor compatibility suite passes 12/12; the local parallel-lane scheduler suite passes 3/3; the supervisor self-test passes. The assigned branch's complete Python test suite passes 57/57 at commit `40c6afe1bfb79275fe75f0f19a6b16da89afe680`. The subsequent README-only update documents those already-verified artifacts. These are test/operational checks, not Lunita or Cajita certification.

## Requirements-profile permission recovery (2026-10-20)

A second evidence-bound recovery handles the actual requirements-directory failure. The service account could not create its versioned profile because `state/tools/requirements` was owned by `root:root` with mode `0700`; the previous generic profile was `root:root` with mode `0600`. The directory owner is corrected to the service account while the old file remains byte-identical and root-owned. The resolver never overwrites that file; it creates a new profile, `llama-cpp-converter-python313-6a1a922d2699-numpy226-v2.txt`.

The recovery handler runs only when the saved error is exactly a `PermissionError` mentioning that requirements directory, the directory is now writable by the service identity, and the pinned source metadata files exist. It records the previous error hash, transitions back to `PROVISION_ENV` once, and refuses to replay the repair. An unrelated permission error or a second recovery attempt remains blocked.

Versioned patch artifacts:

- `patches/custoszv9_continuous_governor_v2.requirements-permission-recovery.patch`
  - SHA-256: `1698d276a397ebeab38ba7ee30d4ac1078fbf21885e3de29c6f55eb1fbd90bc9`
- `patches/test_custoszv9_continuous_governor_v2.requirements-permission-recovery.patch`
  - SHA-256: `80180e89bb294f7cab310f6ecccac88a4d7f7c19dea46d6a059f06699b55bf07`

The current local governor compatibility and permission-recovery suite passes 15/15. The assigned branch's complete test suite passes 58/58 at commit `c72a41da1ed5c9f05fa27d26226b057b9d9a6b6c`. These checks prove the recovery policy and patch contract; they do not certify Lunita, Cajita, or any quantized model.


## Continuous Lunita 1.7 certification acquisition lane (2026-10-20)

custosz_lunita_stability_certification_lane_v1.py is a separate, persistent sidecar for continuous evidence acquisition and the transition from beta-v1.7 toward a derived, versioned LUNITA_STABLE_1_7 release. It does not replace or restart the existing CUSTOSZ supervisor and does not participate in Cajita's model conversion process. The local service has its own user-unit, resource limits, state, and receipts.

The sidecar rechecks the mission hash every cycle; watches for the active Cajita heavy worker before scheduling any work that would compete for memory or I/O; runs the pinned JASP packaged-fixture regression cases in the existing network-unshared Flatpak sandbox; runs a strict Death Penalty save/reopen check against a temporary copy; verifies the installed JASP commit; and creates a full candidate-rootfs JSONL inventory with file SHA-256 values and an installed-package dependency check once the heavy lane is idle. It does not download packages, change Flatpak sandbox restrictions, or modify the packaged reference fixture. Original fixture identity and unchanged SHA-256 are required for the strict round-trip check to pass. JASP outputs, return codes, command provenance, and hashes are retained as receipts.

The sidecar updates BETA_INDEPENDENT_VALIDATION.json through a versioned history archive. The inventory gate and all four JASP cases are conjunctive: a missing report, failed return code, unresolved declared dependency, output/cardinality difference, source hash mismatch, or unbound report keeps S32 blocked. JASP's Bayesian result differences are not normalized away and expected outputs are not rewritten. Failed case evidence is added to state/lunita_certification_evidence/jasp_remediation_queue.json, where later evidence supersedes earlier receipts without silently deleting them.

LUNITA_STABLE_1_7 is emitted only after every required independent check passes and S32 produces a candidate-bound certification receipt whose independent-report SHA-256 matches the current report. The release receipt records version 1.7.0 and the scope VERSIONED_DERIVED_CANDIDATE_ONLY. It does not confer status on frozen G06 or canonical G08 and never propagates certification automatically.

Current known blockers are the unresolved JASP regression outputs (including changed Death Penalty model count/results and reliability/weight-gain precision differences) and the full candidate rootfs/dependency inventory, which waits while Cajita's heavy conversion/dry-run job is active. Therefore the sidecar's initial status is CERTIFICATION_SEARCH_ACTIVE / NOT_GRANTED, not Stable or certified.

Contract tests:
~~~bash
PYTHONPATH=recovery/lunita-custoszv9 python3 -m unittest discover -s recovery/lunita-custoszv9 -p 'test_lunita_stability_certification_lane_v1.py' -v
python3 recovery/lunita-custoszv9/lunita_stability_certification_lane_v1.py --self-test
~~~

These tests prove the fail-closed policy and sidecar contract, not live Lunita certification.
