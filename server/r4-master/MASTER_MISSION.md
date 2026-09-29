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

PART_4 — PROJECTS PROTECTION AND WINDOWS RETIREMENT:
PROYECTOS must remain intact and restorable. Two independent verified backups,
restore proof and exact disk/EFI map are mandatory. H2 and H4 remain human
gates. Windows/EFI/GPT/partition operations are forbidden until the specific
destructive-scope evidence, G23 and G24 all PASS. Generic master authorization
does not silently satisfy H2/H4.

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
