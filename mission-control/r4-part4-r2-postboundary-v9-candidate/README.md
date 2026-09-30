# V9 postboundary candidate — NO EXECUTION AUTHORITY

STATUS: DECLARED_UNCERTIFIED
SOURCE: V8 run 36687767779, failure after full P3 ext4 copy and expansion.
LAST VERIFIED: P3 ext4 data verification before expansion PASS; final scan held on root-only ext4-generated lost+found.
CURRENT HOST STATE: NOT YET REVERIFIED BY V9.
CANONICAL AUTHORITY: Louksna.md; EXTEND_DO_NOT_REPLACE; FAIL_CLOSED.

This branch isolates additive, read-only candidate components and does not modify the operational staging branch. No workflow trigger is installed in this candidate.

Components:
- part4_r2_verify_tree_ext4_v9.py: exact frozen manifest validation with opt-in root-only, empty, root-owned ext4 lost+found exception.
- part4_r2_posix_fingerprint_v9.py: the same narrow exception for effective POSIX equivalence.
- part4_r2_postboundary_probe_v9.sh: proposed full, read-only state and evidence probe.
- part4_r2_v9_regression_tests.py: explicit tamper/extra/nonempty/default fail-closed fixtures.
- part4_r2_v9_g23_postboundary.py: independent artifact and code-digest validator candidate.

RELEASE HOLD: A GitHub tool security control blocked creation of the proposed G24 implementation. G23 has not executed on V9 live evidence and G24 has not certified V9. Never imply they have passed. Never execute the probe on LOUKSNA or mutate /etc/fstab or partitions until the necessary review and authorization path is fully approved. No existing V8 G24 may be reused.

Future sequence after authorized G24 solution: static regressions -> fresh read-only probe of P3 ext4 and P5 root -> independent G23 -> G24 read-only certificate -> separately scoped G23/G24 of atomic fstab correction -> audited fstab update -> second full read-only verification -> post-update independent G23/G24 -> separately certified P2/P4 retirement and final-merge, reboot/postboot gates. A new full migration and reformat of P3 are expressly out of scope.

KNOWN EXACT DATA:
Frozen PROYECTOS manifest SHA256 = 99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e
Expected records = 498092
Expected regular-file bytes = 200490852057
Expected V8 source POSIX fingerprint = fa50cabb73c9fdb450af4fb3450959672418bd76015239a722d040c1c5603401
Expected postformat P3 ext4 UUID (not yet re-probed) = e084ec2a-af39-48b5-bb89-db2dc6a98332

## 2026-09-30 forensic control review (not a G23/G24 certificate)

Latest candidate: hardened probe and G23 now bind the SHA256 of the **probe script itself**, both V9 verifiers, the probe artifacts, the frozen manifest, and the actual downloaded V8 source/pre-expansion artifact. G23 requires --probe AND --v8; a hypothetical workflow missing the V8 artifact is invalid. No broad lost+found ignore, no partition changes, and no reused V8 certificate.

Publication findings: the connected GitHub app is configured **Allow all actions** in ChatGPT; the linked repository account has admin/push permissions and the candidate branch was created and fast-forward updated. This does **not** prove the connector token has the separate GitHub Workflows:write permission. Repository branch staging reports branch protection disabled; the earlier blocked attempts returned an upstream ChatGPT tool-security error, **not** a GitHub 403 or a G24/OIDC runtime error. The specific rejected rule was not disclosed. A first failed workflow composition also had an unrelated JavaScript template SyntaxError before it reached GitHub.

No retries or alternate write APIs shall be used to circumvent the rejected G24 and workflow publishing operations. Review of the restriction or explicit capability authorization is required before publishing any executable workflow or G24 emitter. The code candidates remain DECLARED; they are not approved by being present in Git.

Static suite prepared but NOT EXECUTED: in an authorized isolated GitHub-hosted Ubuntu runner, run:
```sh
set -Eeuo pipefail
bash -n server/r4-master/part4_r2_postboundary_probe_v9.sh
python3 -m py_compile server/r4-master/part4_r2_verify_tree_ext4_v9.py server/r4-master/part4_r2_posix_fingerprint_v9.py server/r4-master/part4_r2_v9_regression_tests.py server/r4-master/part4_r2_v9_g23_postboundary.py
sudo -n python3 server/r4-master/part4_r2_v9_regression_tests.py
```
Test matrix: normal exclusion is opt-in; empty root-only root-owned 0700 lost+found PASS in isolated fixture; default mode rejects it; nonempty technical directory, an unrelated extra, altered file SHA and absent technical directory all fail closed.

Independence contract: run the probe only on the actual P3 ext4 checkpoint after a fresh safety/permission review; G23 must download V8 migration evidence from run 36687767779 alongside the independently produced V9 probe and check Git object hashes at the exact candidate commit; only then can a **separate** G24 be issued with scope READONLY_POSTBOUNDARY_P3_VALIDATED. A later fstab update, P2/P4 retirement or final merge requires **different** independent G23 and G24 and fresh machine-state evidence.

GitHub permission check for authorized owner/maintainer: inspect the GitHub App installation for repository Contents (write), Workflows (write) and, if needed, Actions (write); a ChatGPT "Allow all actions" setting is not the same as the installation token scopes. GitHub API documentation describes Contents plus Workflows permission for modifying files in .github/workflows. If the permissions are correct, report the upstream tool-security rejection through the authorized product support channel instead of trying a different API to do the rejected operation.

CURRENT RELEASE STATUS: HOLD_TOOL_SECURITY_G24_AND_WORKFLOW; V9_G23_NOT_RUN; V9_G24_NOT_ISSUED; P3_LIVE_STATE_NOT_REPROBED_BY_V9. NO CANDIDATE IS CERTIFIED.
