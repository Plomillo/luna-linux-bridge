# LUNA R4 — MISIÓN MAESTRA OPERACIONAL PART 1 → PART 9

MISSION_CLASS = LUNA_R4_MASTER_PART1_PART9
AUTHORITY = Louksna.md
DOCTRINE = EXTEND_DO_NOT_REPLACE
FAILURE_POSTURE = FAIL_CLOSED
GOVERNOR = MetaOS
WORKER = CUSTOSZ V7
RUNTIME = CUSTOSZ_RUNTIME_V1
SUPERVISOR = SYMPHYLAX R1
VALIDATOR = G23
CERTIFIER = G24

START_FROM = PART_1
RESUME_MODE = DIFFERENTIAL
CHECKPOINT = /home/diegoignacionorambuenamiranda/LOUKSNA_MAESTRO_20260925/MISSION3_OPERATIVE/R4_PART1_DESKTOP_V1/runs/20260926T034746Z-38579

DO_NOT_REPEAT = PART_0;PART_1_FULL_REINSTALL;SERVER_READY_G08_G09_G23_G24

SERVER_READY_CERTIFIED_RUN = 36503769931
APC48_V2_POSTINSTALL_G23_G24_RUN = 36519487206
APC48_V2_CANDIDATE_DIGEST = ed3c4267f94b3c53f1fec64b331f72dc657ebcc5e2c62a9314321c67c89684b7

OBJECTIVE:
Resume LUNA R4 from the existing PART 1 checkpoint, close that checkpoint by
fresh evidence and independent validation without reinstalling it, and then
advance strictly in order through PART 2, PART 3, PART 4, PART 5, PART 6,
PART 7, PART 8 and PART 9.

ORDER IS IMMUTABLE:
PART_1 -> PART_2 -> PART_3 -> PART_4 -> PART_5 -> PART_6 -> PART_7 -> PART_8 -> PART_9

PART_1:
Verify the existing KDE/Desktop implementation against the frozen checkpoint
and approved UI references. Apply only a missing delta if the evidence proves
one exists. No full reinstall. Exit only with PART1_POST_VALIDATION_PASS after
EVIDENCE -> VALIDATION -> G23 -> G24.

PART_2 — ENGINEERING:
Close the differential engineering foundation required by the R4 Skeleton:
Node.js/npm/npx, Python/venv/pip/pipx, Git, Linux 7-Zip, OpenJDK, Mojo,
C++23/GCC/G++, CMake, Ninja, GDB and pkg-config. Reuse correct installed
components. Research only unresolved exact versions/sources. Every mutable
operation requires checkpoint, functional test, non-regression and rollback.

PART_3 — CORE ORCHESTRATION AND PROJECTS:
Verify and integrate CUSTOSZ V7, CUSTOSZ_RUNTIME_V1, MetaOS, SYMPHYLAX,
the semantic container, Projects Center, architecture/version management and
the locally governed project workspace. Preserve Louksna authority and frozen
identities.

PART_4 — PROJECTS PROTECTION AND WINDOWS RETIREMENT — R2:
Operational amendment PART4-R2-20260929 is authoritative for PART_4 execution
under Louksna.md without canonical mutation or authority transfer. The certified
PROYECTOS cryptographic freeze (manifest SHA-256
99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e) replaces
the former requirement for two complete pre-destruction backups and pre-delete
restore proof. H2 and H4 remain human gates. Every destructive transition still
requires exact-scope evidence, step-specific independent G23 and G24, rollback
or HOLD semantics, traceability, provenance, auditability and non-regression.

PART_4 R2 ORDER:
1. Preserve the G23/G24-certified freeze of exact PROYECTOS.
2. Prevalidate and independently certify the exact purge scope.
3. Delete every direct child of /dev/nvme0n1p3's Windows mount except exact
   PROYECTOS; do not touch p1/p2/p4/p5 in this purge.
4. Post-validate PROYECTOS integrity against the certified manifest.
5. Unmount and shrink NTFS only after geometry/filesystem prevalidation.
6. Shrink the p3 boundary, create new Linux ext4 space, and validate it.
7. Migrate PROYECTOS transactionally NTFS -> ext4; no source object may be
   retired until its destination object validates.
8. Require complete source/destination tree/hash equivalence.
9. Retire remaining NTFS and Windows recovery/residual storage only after the
   migration equivalence gate passes.
10. Reassign reclaimed capacity to a validated Linux-only storage layout.
11. After the NTFS->ext4 project migration is independently certified, apply
    PART4-R2-FINAL-MERGE-20260929: migrate the valid Debian root into the
    verified ext4 Linux partition, preserve EFI, prove the new root boot,
    retire the old Debian root only after post-boot G23/G24, and expand the
    new root to the final usable boundary.
12. Final target layout: required EFI + one main Linux ext4 root containing
    Debian and PROYECTOS; normal alignment gaps are permitted.
13. Close PART_4 only after the final merged layout, PROYECTOS integrity,
    boot-chain non-regression, G23 and G24 all PASS.
PART_5 through PART_9 are unchanged by this amendment.

PART_5 — LABORATORY:
Close QEMU/KVM/libvirt/virt-manager and the authorized lab images and
virtualization functions. Quarantined or hash-mismatched media must never be
promoted.

PART_6 — GAMING:
Close Wine, Steam, Proton, Bottles, Lutris, Prism and Waydroid from verified
sources/materialized artifacts, with functional tests and rollback.

PART_7 — STUDY AND DEVOTIONAL:
Close the study surface and LUNA_DEVOTIONAL with source immutability,
provenance, indexing, document classification and the Louksna hermeneutic
controls. UNKNOWN consequential document classes remain fail-closed.

PART_8 — SYSTEM:
Close system status/resources/updates/backup/recovery/storage/hygiene,
architecture/version management and governed resource controls. Hygiene must
never blindly delete protected sources, checkpoints, evidence or project data.

PART_9 — FINAL INTEGRATION:
Execute the complete post-install matrix, global non-regression, recovery
proof, final G23, final G24 and only then the authorized final reboot and
post-reboot verification. GLOBAL_MISSION_STATUS may become COMPLETE only from
material evidence.

EVIDENCE CONTRACT:
Every consequential operation records mission/operation/requirement IDs,
actor, authority binding, timestamp, source/version, input/output SHA-256,
dependencies, parameters, expected/observed results, validation,
non-regression, checkpoint, rollback pointer, incident reference, G23 reference,
G24 reference and status.

EXECUTION RULES:
- use current correct state instead of repeating work;
- one mutable domain batch at a time;
- use sudo -n /usr/local/sbin/louksna-apc for the currently authorized
  privileged interface;
- an unexpected password prompt is HOLD;
- no silent overwrite, replacement, reclassification or authority transfer;
- no fake PASS;
- a failed gate stops the dependent transition, preserves evidence and exposes
  the exact blocker;
- independent domains may continue only when doing so cannot bypass the
  chronological certification gate.

SUCCESS:
PART 1 through PART 9 each have material evidence, independent validation and
certification for their actual scope; final post-reboot tests pass; protected
data are intact; rollback/evidence survive; GLOBAL_MISSION_STATUS=COMPLETE.

PART_4 — POST-P5 HARDENED P3 GROWTH CONTINUATION:
MANDATORY_ADDENDUM = PART4_P3_GROWTH_HARDENED_ANTI_PARALYSIS.json
CONTRACT_ID = PART4-P3-GROWTH-HARDENED-ANTI-PARALYSIS-20261001
RESUME_FROM = LAST_VALID_POST_P5_CHECKPOINT
REMOTE_DESKTOP_COMMANDER = PROHIBITED
DESKTOP_COMMANDER = PROHIBITED
LIVE_OBSERVATION = LOUKSNA_REMOTE_BRIDGE
ANTI_PARALYSIS = MANDATORY
HOLD_SEMANTICS = BLOCK_ONLY_UNSAFE_DEPENDENT_TRANSITION
NO_INDEFINITE_HOLD = TRUE
NO_BLIND_DESTRUCTIVE_RETRY = TRUE
NO_FULL_PIPELINE_REPLAY_WHEN_DIFFERENTIAL_RECOVERY_EXISTS = TRUE
SAFE_OBSERVATION_DIAGNOSIS_AND_MINIMAL_REMEDIATION_WHILE_HOLD = REQUIRED
AUTO_ADVANCE_AFTER_EXACT_GATES_PASS = REQUIRED

The twelve hardened stages in the mandatory addendum govern the remaining
POST-P5 PART_4 work. No partition or filesystem mutation is authorized merely
by this mission text or by the addendum. Every destructive commit requires its
own fresh exact-scope evidence, G23 independent validation and digest-bound G24.

