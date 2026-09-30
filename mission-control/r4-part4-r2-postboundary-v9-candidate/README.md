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
