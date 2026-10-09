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

## Change made

- Set `debian/control` Maintainer to `Plomillo <diegonorambuenamiranda2@gmail.com>`.
- Updated only the current 0.4.0-3 changelog trailer to match. Historical 0.4.0-2 and 0.4.0-1 entries were preserved.

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

Workflow run [37871381167](https://github.com/Plomillo/luna-linux-bridge/actions/runs/37871381167) checked out commit `d3bfdf39331680bc6bc7ad515d544221e8a9fede`. The package build failed in `bridge.tests.test_release_policy.ReleasePolicyTests.test_release_stays_blocked_without_authoritative_legal_and_contact_metadata`, because the regression test hard-coded the former synthetic `maintainers@louksna.invalid` address after `debian/control` was changed to the repository-attributed contact. The test was corrected in commit `02bff3c42bb7e87ef0f0df52365bdfcd8195e3df` to check that the contact remains unverified, legal metadata remains absent, and the release hold remains in place. That correction is not itself evidence of a passing test; a new workflow result must confirm it.

The same failed run did not reach Lintian evidence collection or later integration tests. The release remains blocked until the next run establishes build/test results and legal provenance is resolved. The known `no-copyright-file` Lintian finding from earlier runs remains applicable until verified otherwise.

### Evidence still required

The public repository data located so far does not determine (a) the legal person/entity owning the bridge copyright, (b) the intended license grant, (c) whether all packaged code was authored by that rights holder, or (d) whether any copied/adapted code or bundled assets require third-party notices. These are not facts that Git author metadata or a project architecture document can establish. Do not create a guessed license or represent the package as redistributable without a rights-holder decision or an applicable existing license record.
