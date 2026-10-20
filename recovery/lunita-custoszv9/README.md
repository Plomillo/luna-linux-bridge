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
