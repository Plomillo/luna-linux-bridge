# Legal metadata audit — louksna-linux-bridge 0.4.0-3

Date: 2026-10-09 UTC
Scope: repository tree at branch `work/louksna-zd-v04-03-mtls-provisioning-20261008`, commit observed before this audit: `fdb3ad7356af07a346401e56ca9e5c77bc36f39a`.

## Findings supported by repository evidence

1. The recursive Git tree contained 171 entries. No root or nested `LICENSE`, `COPYING`, `NOTICE`, `AUTHORS`, `CONTRIBUTORS`, or `debian/copyright` file was present.
2. GitHub repository metadata reported `license: null`.
3. Root `README.md` contains the project heading and Romans 11:36, but no license grant, copyright notice, or rights-holder declaration.
4. `bridge/README.md` describes the bridge as a draft/uncertified candidate and establishes architectural governance; it does not grant a software license.
5. `PUAC2.md` concerns architectural governance and expressly says the proposal is pending formal admission; it does not establish a license for this bridge's source code.
6. The current `debian/control` previously used `Louksna Project <maintainers@louksna.invalid>`. The repository's recent commits repeatedly record the Git author/committer as `Plomillo <diegonorambuenamiranda2@gmail.com>`. This supports attribution of that address to repository commits, but does not independently prove mailbox deliverability, legal identity, copyright ownership, or authorization to license all source files.

## Packaging contact disposition

A provisional change briefly set `debian/control` and the 0.4.0-3 changelog trailer to `Plomillo <diegonorambuenamiranda2@gmail.com>`, because that address appears in commit metadata. Further inspection of `docs/PACKAGE_COMPONENT_INVENTORY.md` showed an explicit requirement that the real authorized maintenance contact must not be replaced by an inferred address. The provisional assignment was therefore reversed in subsequent additive commits. Current `debian/control` and the current changelog trailer retain `Louksna Project <maintainers@louksna.invalid>` as an explicit HOLD marker until the authorized maintainer supplies a real contact. Historical changelog entries remain preserved.

The commit-attributed email is a lead to confirm with the responsible human, not an authorized maintainer identity. It must not be represented as validated or operational.

## Unresolved — release-blocking

No repository evidence found in this audit establishes:
- the copyright holder(s) and applicable year(s) for the bridge code;
- the license under which the project code may be redistributed;
- licenses and attribution obligations for any third-party code included in the package.

Therefore `debian/copyright` has deliberately **not** been fabricated and the license blocker remains open. Do not infer MIT, Apache, GPL, public domain, or any other license from project name, repository visibility, commit authorship, or the license of a separate voice asset.

## Verification limits

The maintainer email is sourced from public commit metadata but has not been tested for delivery or independently confirmed as the designated package-maintainer contact. This change is a repository-evidence-based provisional correction, not legal verification or certification.

## Required next evidence

Locate an existing, applicable license/authorization and copyright provenance in source history or upstream origin, or obtain an explicit rights-holder decision. Then create `debian/copyright` in Debian copyright-format 1.0, with accurate file coverage, copyright statements, license text, and third-party notices. Run the package build and fail-closed Lintian checks again. Do not release while the license and copyright evidence remain unknown.

## Expanded search and CI findings — 2026-10-09 UTC

### Additional repository refs checked

The exact paths `LICENSE`, `COPYING`, `NOTICE`, and `debian/copyright` were also queried on `main`, `candidate/louksna-remote-bridge-v0-unreleased`, and `candidate/lrb-apc-trust-readonly-preflight-20260930`. All 12 path/ref checks returned not found. This is additional negative evidence for those refs, not a claim that every historical Git object or every branch has been exhaustively inspected.

### Search queries

Repository-scoped GitHub code searches for `license copyright SPDX`, `Copyright Plomillo`, `SPDX-License-Identifier`, `third-party license dependency notice`, `COPYING`, and `author rights ownership` returned no matching files on the default-branch search surface. Public web searches for the exact repository and its license/copyright terms produced no authoritative license or upstream-origin record. Unrelated repositories named “Luna” are not evidence for this project and were excluded.

### CI failure diagnosis and correction

Workflow run [37871381167](https://github.com/Plomillo/luna-linux-bridge/actions/runs/37871381167) checked out commit `d3bfdf39331680bc6bc7ad515d544221e8a9fede`. The package build failed in `bridge.tests.test_release_policy.ReleasePolicyTests.test_release_stays_blocked_without_authoritative_legal_and_contact_metadata`, because the regression test expected the synthetic `maintainers@louksna.invalid` marker after the provisional contact assignment. Commit `02bff3c42bb7e87ef0f0df52365bdfcd8195e3df` temporarily changed the test expectation; subsequent review found that this would conflict with the component inventory's explicit rule against substituting an inferred email. The control field and current changelog trailer were restored to the HOLD marker, and the regression test was restored to enforce that hold in commits `f56542a02b2662f6b3387fae6e4973b964a6926f`, `8a8aabf40e3a0b47c42e0c064619344eb27a1bfb`, and `3ddad80f44bd3c09dce17b9117395969c8b9add5`.

The same failed run did not reach Lintian evidence collection or later integration tests. A new workflow result must confirm the corrected test state. The known `no-copyright-file` Lintian finding from earlier runs remains applicable until verified otherwise.

### Evidence still required

The public repository data located so far does not determine (a) the legal person/entity owning the bridge copyright, (b) the intended license grant, (c) whether all packaged code was authored by that rights holder, or (d) whether any copied/adapted code or bundled assets require third-party notices. These are not facts that Git author metadata or a project architecture document can establish. Do not create a guessed license or represent the package as redistributable without a rights-holder decision or an applicable existing license record.

## Execution of the three closure workstreams — 2026-10-09 UTC

Two actionable repository artifacts have now been committed to this candidate branch:

- `docs/RIGHTS_HOLDER_ATTESTATION_TEMPLATE.md`: structured declaration for rights holder/authorized signer, copyright years and covered paths, explicit license grant, third-party exclusions, and operational maintainer contact. It is deliberately blank where human authority/evidence is required; it is not a license.
- `docs/SOURCE_PROVENANCE_REGISTER.md`: maps each file group copied by `debian/rules` to its package destination, records what packaging files establish, marks unresolved copyright/license/provenance questions, distinguishes system dependencies from bundled code, and defines the per-file history/content review needed before DEP-5 generation.

### Workstream 1 — rights-holder declaration
Repository and public web searches did not reveal an applicable rights-holder instrument. The declaration template is ready, but the actual legal name, authority, covered files, copyright years, and explicit redistribution grant cannot be filled from repository commit metadata. No legal declaration was fabricated.

### Workstream 2 — per-file source and third-party provenance
The register maps the installed file groups from `debian/rules` and `docs/PACKAGE_COMPONENT_INVENTORY.md`. It explicitly records that the packaging rules do not identify a bundled voice/TTS asset and do not copy Debian dependency binaries, while also withholding an unsupported claim that every source file is original or free of copied snippets. Full per-file history/blame and packaged-output comparison remain required; the current connector evidence did not provide a complete file-by-file blame/export suitable to close those questions.

### Workstream 3 — maintainer confirmation
The public GitHub profile has no public email field, and the commit-attributed email is not proof of a designated package-maintainer contact. No authenticated confirmation from the rights holder/maintainer was found. The template specifies the evidence required. `Louksna Project <maintainers@louksna.invalid>` remains an explicit HOLD marker, not a usable contact.

### Result
The three workstreams have been advanced as far as repository/web evidence permits and their remaining human-evidence requirements are explicit. This is not legal closure: `debian/copyright` is not generated, and merge/release/redistribution remain blocked. CI must be checked against the latest branch HEAD before any test status is claimed.


## Authorization scope recorded — 2026-10-09 UTC

The project user explicitly authorized continuation of the technical and documentary investigation for the three closure workstreams in the active conversation. This authorization permits further repository/source-history inspection, provenance documentation, and preparation of evidence templates within the existing candidate branch and project governance constraints. It is **not** itself a rights-holder attestation, a license grant, proof of authority over third-party materials, maintainer-contact confirmation, or authorization to merge, publish, release, or redistribute the package. Those gates remain closed until the corresponding evidence is supplied and independently checked.
