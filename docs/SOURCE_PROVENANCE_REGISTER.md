# Packaged source provenance register — louksna-linux-bridge 0.4.0-3

**Status:** OPEN / HOLD. This register separates files actually installed by Debian packaging from legal claims not yet evidenced. It is not a license grant and does not certify authorship.

## Packaging-derived file coverage

The entries below are derived from `debian/rules` and `docs/PACKAGE_COMPONENT_INVENTORY.md`.

| Source path / glob | Installed destination | What repository evidence establishes | What remains unproven | Closure evidence |
|---|---|---|---|---|
| `bridge/*.py` | `/usr/lib/louksna/bridge/` | These Python files are copied by `debian/rules`. | Rights holder, creation years, per-file authorship, copied/adapted code, license. | File-level history review + authorized declaration/license. |
| `bridge/*.json` | `/usr/lib/louksna/bridge/` | JSON files are copied by `debian/rules`. | Original/derived status, embedded third-party text/data, copyright and license. | Per-file inspection + provenance references + authorization. |
| `scripts/provision-mtls-local.sh` | `/usr/lib/louksna/bridge/provision-mtls-local.sh` | Script is installed with mode 0750. | Authoritative copyright, license and upstream origin. | File history + authorized declaration/license. |
| `bridge/deploy/*.service.in`, `*.timer.in` | `/usr/share/louksna/deploy/` | Templates are copied by `debian/rules`. | Rights holder, copied snippets, applicable license. | File-level review + authorization. |
| `bridge/MTLS_READONLY_GATEWAY.md`, `bridge/LIVE_TRANSPORT.md`, `bridge/README.md` | `/usr/share/louksna/` | These documents are installed by packaging. | Rights holder and terms covering documentation. | Authorized declaration/license. |
| `bridge/CONTRACT.v0.json` | Package documentation location, per component inventory | Contract is part of package documentation. | Whether terms govern interface only or also copyright/redistribution. | Rights-holder decision; do not treat the contract as a software license by implication. |

## External dependencies

Current declared build dependencies: `build-essential`, `debhelper-compat (= 13)`, `dpkg-dev`, `python3`, `openssl`. Runtime dependencies: `python3 (>= 3.10)`, `openssl`, `util-linux`; `systemd` is recommended.

The reviewed packaging rules do not copy these Debian dependency binaries or their license texts into the package; they are installed from Debian repositories. This is not a substitute for checking imports, vendored material, generated output, or any files not covered by the inspected rules.

## Explicit third-party / asset check

- Voice/TTS model or voice assets: the current packaging rules and component inventory do not identify such an artifact as included in this .deb. Do not apply a separate voice asset's license to the bridge.
- Python third-party packages: the component inventory reports no root `requirements.txt` or `requirements.lock` under the inspected `bridge/` scope and no copied `site-packages`; runtime imports still require verification.
- Embedded snippets, copied/adapted code, documentation excerpts, icons, fonts, data, and generated code: **not yet exhaustively cleared**. No blanket “none” claim is made.

## Required reproducible provenance review

1. Enumerate the exact packaged file list from a built .deb and map each file to its source path.
2. For each source file, inspect its full Git history/blame and initial introduction; record commit SHA, author/committer metadata, and any upstream URL. Commit metadata is attribution evidence only, not proof of legal ownership.
3. Search source contents for copyright notices, SPDX identifiers, license text, external URLs, vendored markers, and copied code. Record both positive and negative findings by path.
4. Inspect Python imports and build outputs for vendored/generated dependencies; compare with Debian dependency declarations.
5. Reconcile all results against an authorized rights-holder statement and any upstream license/CLA/assignment.
6. Generate `debian/copyright` in DEP-5 only when file coverage, copyright statements, and license text are supported. Run Lintian and independent review; preserve the report and hashes.

## Current gate

No repository evidence located so far establishes the rights holder, applicable copyright years, redistribution license, or all third-party obligations. `debian/copyright` must remain absent rather than contain invented legal data. Release, merge, and redistribution remain blocked until evidence closes the gate.


## Git-history evidence review — 2026-10-09 UTC

Review performed against candidate HEAD `3d4ed85aecd43dd58274082e6441be84cf51fded`, using the repository's per-path commit history. This is a bounded review of packaged paths, not proof of legal ownership.

### First recorded introduction found

The following packaged paths currently return the same first/only history entry in the queried branch history: commit `099ae35cb5ced2dde74d49545f57223b52102d30`, dated 2026-10-07 18:01:44 UTC, message `feat(louksna): materialize P02 LRB_APP 0.4 typed protocol`. GitHub marks the commit signature as **unsigned** (`verified=false`, reason `unsigned`). Its recorded author/committer is `custosz-v7-runtime-bot <custosz-v7-runtime-bot@users.noreply.github.com>`; this is commit metadata, not a legal person, assignment, or proof of authorship.

- Python modules: `bridge/apc_inventory.py`, `bridge/app_protocol.py`, `bridge/continuous_assurance.py`, `bridge/elastic_automation.py`, `bridge/elastic_tick.py`, `bridge/external_gates.py`, `bridge/github_adapter.py`, `bridge/global_scope_register.py`, `bridge/live_link.py`, `bridge/lrb_core.py`, `bridge/mtls_gateway.py`, `bridge/virtual_brain.py`.
- Other packaged paths: `bridge/CONTRACT.v0.json`, `bridge/README.md`, `bridge/deploy/louksna-elastic-readonly.service.in`, `bridge/deploy/louksna-elastic-readonly.timer.in`, `bridge/deploy/louksna-live-socket.service.in`, and `bridge/deploy/louksna-remote-bridge-observer.service.in`.

The checked source headers for `bridge/lrb_core.py`, `bridge/mtls_gateway.py`, `bridge/live_link.py`, `bridge/app_protocol.py`, and `bridge/virtual_brain.py` contain module descriptions/imports but no visible copyright, SPDX identifier, or license grant in the inspected opening sections. `bridge/CONTRACT.v0.json` and `bridge/README.md` also do not grant a software license in the inspected content. This is a finding about those inspected contents, not proof that no applicable external instrument exists.

### Paths with subsequent human-attributed commits

- `bridge/deploy/louksna-mtls-readonly.service.in` has later commits by `Plomillo <diegonorambuenamiranda2@gmail.com>` on 2026-10-09, including `19b87f448fa3e6295411c1780c390e80e9335d55`, `ceb77b8ec0444d7226cf3937d943cb22c4909690`, and `f3f0ccdbdf9168ef042547c0b50a82892dad4178`. Those commits are also unsigned. They establish recorded editing activity, not exclusive authorship or rights to all material in the file.
- `scripts/provision-mtls-local.sh` has subsequent edits attributed to `Plomillo <diegonorambuenamiranda2@gmail.com>`, including `7d23af61901e28477273c7bb71ae6da0141dabb1`, `cd1d9a9123055969c508de099bb66725f2e6eb57`, and `aa7c64b277e1c01976c0f81c08d28df8ad2f2bac`; those commits are unsigned as well. The script's first-introduction record and any source material it may derive from still need review before claiming sole authorship.

### Consequence

The history supports the narrower statement that the core packaged implementation was first recorded in this repository in an unsigned bot-attributed commit, followed by some unsigned human-attributed edits. It does **not** establish who legally owns the generated/edited material, whether any prompt or source terms affect it, whether all authors had authority, or whether third-party material is absent. Therefore the license and copyright gate remains **HOLD**. Do not infer a license from the bot account, repository control, or subsequent edits.
