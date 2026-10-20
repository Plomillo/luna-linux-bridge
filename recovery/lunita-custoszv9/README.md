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
