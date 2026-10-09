# Legal and redistribution closure review — louksna-linux-bridge 0.4.0-3

**Review date:** 2026-10-09 UTC  
**Repository:** `Plomillo/luna-linux-bridge`  
**Reviewed ref:** `work/louksna-zd-v04-03-mtls-provisioning-20261008`  
**Reviewed HEAD:** `d1adea8715d724806b9b083e369ab8a1b3208c31`  
**Decision:** `HOLD — DO NOT MERGE FOR RELEASE, PUBLISH PACKAGE, OR REDISTRIBUTE`

This is a technical evidence report, not legal advice, a license, an authorship declaration, or certification. It records what was checked and separates observed facts from unresolved rights.

## Executive outcome

All five closure workstreams were advanced. The source tree, package rules, package inventory, relevant source headers/imports, and per-path Git history were inspected. The review did **not** find a license grant, an authoritative rights-holder statement, or a verified maintainer contact. It did not identify a named external contributor in the reviewed packaged-file history; this is not proof that no third-party material exists.

Do not add a guessed MIT/GPL/Apache license, do not create a fabricated `debian/copyright`, and do not use Git author metadata as proof of ownership. The release gate remains closed.

## 1. File-level provenance and copyright scan

### Exact packaged source coverage

Based on `debian/rules`, the packaged source coverage is:

- 16 Python modules copied from `bridge/*.py`.
- 5 JSON files copied from `bridge/*.json`.
- 5 systemd templates: four `*.service.in` files and one `*.timer.in`.
- 3 installed documents: `bridge/README.md`, `bridge/MTLS_READONLY_GATEWAY.md`, and `bridge/LIVE_TRANSPORT.md`.
- 1 provisioner: `scripts/provision-mtls-local.sh`.

Total reviewed by path group: **30 packaged source files**. This count excludes Debian packaging files themselves and build-only material that is not installed by these copy rules.

### Git history observations

- The queried history for the 16 Python modules and 5 JSON files returns first/only recorded introduction at commit `099ae35cb5ced2dde74d49545f57223b52102d30`, dated 2026-10-07 18:01:44 UTC, message `feat(louksna): materialize P02 LRB_APP 0.4 typed protocol`.
- The same commit is the first recorded entry for the original four service templates, timer, `bridge/README.md`, and `bridge/LIVE_TRANSPORT.md`.
- GitHub reports that commit as unsigned (`verified=false`, reason `unsigned`) and records the author/committer as `custosz-v7-runtime-bot <custosz-v7-runtime-bot@users.noreply.github.com>`. A bot attribution does not identify the natural person who authored the content or establish assignment/ownership.
- `bridge/deploy/louksna-mtls-readonly.service.in` has later edits attributed to `Plomillo <diegonorambuenamiranda2@gmail.com>`, including `f3f0ccdbdf9168ef042547c0b50a82892dad4178`, `ceb77b8ec0444d7226cf3937d943cb22c4909690`, and `19b87f448fa3e6295411c1780c390e80e9335d55`. Those commits are unsigned.
- `bridge/MTLS_READONLY_GATEWAY.md` has later edits attributed to the same commit identity, including `6ad1e16e4c113fb47bd6417294e64f494f345d1e`, `510d99657ee5382bc968adb68560341a2a9d6204`, and `57e03a11c107cd9fa8b129f8874332cea644cbe5`; those commits are unsigned.
- `scripts/provision-mtls-local.sh` has subsequent edits attributed to that same commit identity, with the first observed commit in this review being `601ca79d90527e2d6b286d6491ff046a9d5a7540` and later edits through `7d23af61901e28477273c7bb71ae6da0141dabb1`; these commits are unsigned.
- The reviewed opening sections of Python modules show module descriptions and imports, but no visible copyright notice, SPDX identifier, or license grant. The inspected JSON and systemd templates likewise do not contain copyright/SPDX/license notices. The targeted scan found API endpoint URLs in `bridge/VIRTUAL_BRAIN.json` and `bridge/github_adapter.py`; those identify service endpoints, not source-code origins or license grants.

**Interpretation limit:** Git history establishes recorded change chronology and account metadata only. It cannot prove who wrote the original content, whether it incorporates copied/adapted material, whether a contributor assigned rights, or whether a separate contract/license exists. Negative header scans do not prove absence of third-party material.

## 2. Dependency and third-party component inventory

### Declared Debian dependencies

Build dependencies: `build-essential`, `debhelper-compat (= 13)`, `dpkg-dev`, `python3`, and `openssl`. Runtime dependencies: `python3 (>= 3.10)`, `openssl`, and `util-linux`; `systemd` is recommended.

The reviewed package rules do not embed these Debian dependency binaries or their license texts. They are expected to be supplied by the target Debian system.

### Python imports and remote services

The reviewed runtime modules import Python standard-library modules and local bridge modules. No root `requirements.txt`, `requirements.lock`, `pyproject.toml`, or `setup.py` was found at the checked locations, and the package rules do not copy `site-packages`. This is evidence about the current package layout, not a guarantee that every transitive or generated artifact in every workflow is free of third-party material.

The optional virtual-brain configuration references Groq and Hugging Face API endpoints and environment-variable credentials. The checked package contains endpoint/configuration references, not provider model weights. These service references do not establish rights to provider models or permission to redistribute provider assets. If later package versions download, cache, or bundle models/assets, they require a separate inventory and license review.

### Still requiring review

No exhaustive similarity scan or line-by-line comparison against external code repositories has been completed. Copied/adapted snippets, documentation excerpts, generated code, fonts, icons, data, and materials brought in outside the current Debian copy rules remain unresolved. Do not record “no third-party code” as a conclusion.

## 3. Rights and redistribution decision

Current public GitHub repository metadata reports `license: null`; the reviewed tree has no `LICENSE`, `COPYING`, `NOTICE`, `AUTHORS`, `CONTRIBUTORS`, or `debian/copyright` at the reviewed ref. The project README, bridge README, and contract do not grant a software redistribution license.

The user has explicitly clarified that not all rights belong to them and that third-party material may be present. That instruction is recorded as a scope constraint, not as a rights grant. No person or organization has yet been evidenced as authorized to license all packaged files.

Therefore:
- Do not add a project-wide license based on a guess.
- Do not assert exclusive ownership or blanket authority to redistribute.
- Do not create `debian/copyright` with invented copyright years, holders, or terms.
- Keep the package at HOLD until every packaged file has a defensible rights/licensing disposition.
- If a file cannot be cleared, remove it from the distributable package only after impact analysis and an authorized scope decision, or replace it with independently sourced material whose license is verified. Do not silently replace canonical project content.

## 4. Maintainer/contact verification and outreach

The repository owner/account shown by GitHub is `Plomillo` at [github.com/Plomillo](https://github.com/Plomillo). Git commits contain `diegonorambuenamiranda2@gmail.com`, but this address is only commit metadata: the review has not verified deliverability, mailbox control, legal identity, or designation as the Debian/upstream maintainer. It must not be promoted to a verified maintainer contact.

The package currently retains `Louksna Project <maintainers@louksna.invalid>` in `debian/control` and the changelog as an explicit non-operational HOLD marker. Preserve it until an actual contact is confirmed.

The reviewed file histories expose the bot identity and the `Plomillo` commit identity, but no other named individual or organization that can responsibly be contacted as a third-party rights holder. Consequently, no external rights holder has been contacted: there is no evidence-grounded recipient to contact yet. Sending a message to the repository owner/account would not resolve unknown third-party ownership. The repository's issue/PR tracker is a public, auditable channel, but opening an issue there would only solicit information; it would not verify an answer or create rights.

To close this point, identify any external origin from a code match, notice, dependency, commit reference, or contributor record, then contact that identified party through an independently verified official channel. Keep the request, response, URL, timestamp, and evidence in the provenance register. For the project maintainer field, verify a real maintained mailbox or other stable, unambiguous upstream contact and confirm that person accepts the role.

## 5. Debian copyright file, build checks, and independent closure

Debian Policy requires the distribution license(s) to accompany every package in `/usr/share/doc/PACKAGE/copyright`; the source package should include `debian/copyright`. The machine-readable DEP-5 format is suitable once file coverage and exact license text are evidenced.

**Not done (blocked by missing legal evidence):** creating `debian/copyright`, running a new package build with a complete legal metadata file, obtaining a passing Lintian result for the current HEAD, and independent legal/provenance validation. These must not be represented as passed.

Closure sequence:
1. Finish source comparison and provenance review for every packaged file; record a result even when the result is “origin unknown”.
2. Obtain applicable existing license/assignment/permission evidence from each identified rights holder, or establish that the file can be redistributed under an independently verified existing license.
3. Verify the actual maintainer contact and document the confirmation.
4. Generate DEP-5 `debian/copyright` from evidenced facts only, preserving required license text and notices verbatim.
5. Build the exact candidate source package; run Lintian and package tests; retain logs, package hashes, and the complete file-to-license map.
6. Have a reviewer independent of the authoring process verify every file group and the resulting license obligations.
7. Lift HOLD only after all required gates pass. A passing build or test suite alone does not grant redistribution rights.

## Evidence and references

- Reviewed branch tree: [HEAD `d1adea8`](https://github.com/Plomillo/luna-linux-bridge/tree/work/louksna-zd-v04-03-mtls-provisioning-20261008).
- Current candidate PR: [#48](https://github.com/Plomillo/luna-linux-bridge/pull/48).
- Existing source provenance register: [`docs/SOURCE_PROVENANCE_REGISTER.md`](https://github.com/Plomillo/luna-linux-bridge/blob/work/louksna-zd-v04-03-mtls-provisioning-20261008/docs/SOURCE_PROVENANCE_REGISTER.md).
- Existing legal metadata audit: [`docs/LEGAL_METADATA_AUDIT_0.4.0-3.md`](https://github.com/Plomillo/luna-linux-bridge/blob/work/louksna-zd-v04-03-mtls-provisioning-20261008/docs/LEGAL_METADATA_AUDIT_0.4.0-3.md).
- GitHub guidance on licenses: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
- Debian Policy, copyright: https://www.debian.org/doc/debian-policy/ch-source.html
- DEP-5 format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
- Chilean Department of Intellectual Rights FAQ: https://www.propiedadintelectual.gob.cl/faq

## Final gate

`SOURCE_PROVENANCE=PARTIAL`  
`THIRD_PARTY_CLEARANCE=INCOMPLETE`  
`RIGHTS_HOLDER=UNKNOWN`  
`REDISTRIBUTION_LICENSE=NOT_ESTABLISHED`  
`MAINTAINER_CONTACT=UNVERIFIED`  
`DEBIAN_COPYRIGHT=BLOCKED`  
`BUILD_AND_LINTIAN_CURRENT_HEAD=NOT_RUN_FOR_LEGAL_CLOSURE`  
`INDEPENDENT_REVIEW=PENDING`  
`RELEASE=HOLD`


## 6. Supplemental public-web legal and provenance investigation (2026-10-09)

This addendum records an additional bounded public-web search after the file/history review above. It does not replace the report's evidence limitations or constitute a legal opinion.

### Public source results

- GitHub's official licensing guidance states that a public repository without a license remains subject to default copyright rules; public visibility alone does not grant permission to reproduce, distribute, or create derivative works: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
- Chile's Departamento de Derechos Intelectuales explains that copyright authorship and ownership/entitlement to exploit a work are distinct; its software-registration guidance asks for source code, operating manual, third-party software licenses, and identification of natural-person creators when author and owner differ: https://www.propiedadintelectual.gob.cl/faq and https://www.propiedadintelectual.gob.cl/node/1234
- The same Chilean authority describes the general rule that public use of a privately owned work requires express authorization, subject to statutory exceptions, and says an authorization should specify the granted rights and limits: https://www.propiedadintelectual.gob.cl/node/554
- Chilean Law 17.336 expressly includes computer programs and preparatory documentation within protected works; its Article 8 contains particular rules for programs created by employees or commissioned, subject to contrary written stipulation. Those rules cannot be applied to this repository without knowing the actual working/commissioning arrangements: https://www.bcn.cl/leychile/navegar?idNorma=28933
- Debian Policy requires the package's distribution license(s) to be included in `/usr/share/doc/PACKAGE/copyright` and a corresponding `debian/copyright` in the source package. It also describes upstream source location and contact information: https://www.debian.org/doc/debian-policy/ch-source.html and https://www.debian.org/doc/debian-policy/ch-docs.html
- DEP-5 provides the standard machine-readable format for the Debian copyright file: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/

### Search outcome and limits

Exact-string public web searches for `maintainers@louksna.invalid`, `LRB_MTLS_READONLY_GATEWAY/0.3`, `LRB_APP`, `custosz-v7-runtime-bot`, and the repository's project name did not surface an independently verifiable third-party rights holder or upstream source. GitHub code search for these distinctive strings returned no indexed matches. These are negative search results only: search engines and code indexes are incomplete, and no match does not establish original authorship or absence of third-party content.

The reviewed repository metadata identifies the repository as public and the repository license field as absent/null. The PR branch's legal report is a documentation-only change; no license, rights-holder declaration, or contact confirmation was discovered by this supplemental search. No external party was contacted because no specific third-party rights holder could be identified responsibly from the evidence. No guessed address or legal declaration has been sent.

### Legal closure determination

The public sources clarify the applicable process but do not themselves grant rights to this project's files. Remaining project-specific facts cannot be established by web research alone: who authored each file; whether any source was copied, generated from, or adapted from third-party material; whether any employment/commission/assignment agreement applies; and which person/entity can grant the required permissions. These require file-level provenance evidence and/or declarations and agreements from the relevant people/entities.

Therefore, the gate remains:

`PUBLIC_WEB_LEGAL_RESEARCH=COMPLETED_BOUNDED`
`EXTERNAL_RIGHTS_HOLDER_IDENTIFIED=NO`
`THIRD_PARTY_CLEARANCE=INCOMPLETE`
`RIGHTS_HOLDER=UNKNOWN`
`REDISTRIBUTION_LICENSE=NOT_ESTABLISHED`
`DEBIAN_COPYRIGHT=BLOCKED_PENDING_EVIDENCE`
`RELEASE=HOLD`

This does not mean infringement has been found. It means redistribution permission has not yet been established. The next evidence-bearing step is a file-by-file source-origin comparison and a documented creator/rights declaration for the material whose origin remains unknown; only then can any necessary specific contact be made.


## 7. CI distribution artifact gate — 2026-10-09 UTC

A fail-closed CI gate was added after diagnostic build/test/evidence generation and before artifact staging. It requires both a DEP-5 `debian/copyright` file and `docs/DISTRIBUTION_CLEARANCE.json` tied to the exact checked-out commit and the SHA-256 of the copyright file. The record must declare `status=CLEARED`, include evidence references and reviewer/timestamp fields, and assert completion of file coverage, third-party clearance, redistribution authorization, maintainer verification, and independent review. The release-policy regression test now checks that this gate precedes artifact staging.

The gate is a workflow control, not a substitute for underlying evidence or legal review. A JSON declaration cannot make an unsupported assertion true. No clearance JSON or `debian/copyright` was fabricated. With both absent, the expected behavior is to stop the workflow before the .deb is staged/uploaded as an artifact. Diagnostic build/test steps may still execute first.

Commits implementing the control:
- `de7af3d943d10200465bedbe8491070064fb4a36` — workflow gate before artifact staging.
- `7b11fb6218652c47b1a4ff51b5c4cfaea788878b` — regression test for gate ordering and required record.

Verification status at report update: source files were fetched back from the PR branch and the gate's presence/order was confirmed. The GitHub connector returned no workflow runs or commit status for `7b11fb6218652c47b1a4ff51b5c4cfaea788878b`; execution of the updated workflow and tests is therefore **NOT VERIFIED**. Do not claim CI pass.

Updated gate:
`CI_ARTIFACT_UPLOAD_GATE=IMPLEMENTED`
`CI_EXECUTION=NOT_VERIFIED`
`DEBIAN_COPYRIGHT=BLOCKED`
`DISTRIBUTION_CLEARANCE=NOT_ESTABLISHED`
`RELEASE=HOLD`
