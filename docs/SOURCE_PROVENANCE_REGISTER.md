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
