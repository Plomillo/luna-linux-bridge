# MISIÓN — CUSTOSZ V7 / DOCUMENT FACTORY CONTINUATION

MISSION_ID = MIS-DOCUMENT-FACTORY-CUSTOSZ-V7-20261005
MISSION_CLASS = DOCUMENT_FACTORY_GOVERNED_CONTINUATION_V1
AUTHORITY = Louksna.md
ASSURANCE = PUAC2.md
WORKER = CUSTOSZ_V7
RUNTIME = CUSTOSZ_RUNTIME_V1
SUPERVISOR = SYMPHYLAX_R1
GOVERNOR = MetaOS
EXECUTION_MODE = CONTINUOUS_GOVERNED_CONTINUATION
FAILURE_POSTURE = FAIL_CLOSED
DESKTOP_COMMANDER = FORBIDDEN
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
ROLLBACK = REQUIRED
NON_REGRESSION = REQUIRED
NO_SILENT_OPERATIONS = ABSOLUTE
AUTO_CERTIFICATION = FORBIDDEN
CERTIFICATION_PROPAGATION = FORBIDDEN

REPOSITORY = Plomillo/luna-linux-bridge
CERTIFIED_CHECKPOINT_SHA = 067e1be0b13d9400c2c78d6174138c10ce980dd7
CERTIFIED_CHECKPOINT_RUN = 37318811748
TARGET_BRANCH = candidate/document-factory-v1-20261005
WORK_BRANCH = custosz/document-factory-runtime-20261005
MAIN_BRANCH = main
MAIN_ROLE = DEPENDENCY_AND_DOWNLOAD_DISPATCH_SOURCE
MAIN_READ_FETCH_FOR_DEPENDENCIES = AUTHORIZED
MAIN_DEPENDENCY_DOWNLOAD_DISPATCH = AUTHORIZED
MAIN_CANONICAL_MUTATION = FORBIDDEN
TARGET_MUTATION = AUTHORIZED_ONLY_THROUGH_WORK_BRANCH
AUTO_MERGE = FORBIDDEN

OBJECTIVE:
Continue the existing source-first Git-native multiformat Document Factory from the exact certified checkpoint.
Do not restart completed work and do not replace the existing skeleton.
Use document-factory/AUTONOMOUS_CONTINUATION.md as the immediate continuation specification after reconciling it with the certified checkpoint.

CUSTOSZ_CAPABILITY_POLICY:
Use all nine CUSTOSZ V7 families as pertinent:
F01_IO_KNOWLEDGE
F02_EXECUTION_RESOURCES
F03_SECURITY_TRUST
F04_INTELLIGENCE_SYNTHESIS
F05_ASSURANCE_EPISTEMIC
F06_CONTINUITY_INTEROP
F07_MEMORY_DOCUMENTATION
F08_FORMAL_CORE
F09_CAPABILITY_GAPS_EVOLUTION

Require family_count=9, capability_count=72 and unique_capability_count=72 before material work.
Family 9 governs capability-gap/evolution review. No family may manufacture certification.

START_STATE:
The GitHub Copilot/Codex PR route is not an active worker path.
The last accepted Document Factory checkpoint is the certified SHA above.
Before mutation: verify checkpoint; reconcile target; create isolated work branch; checkpoint; run existing tests; verify CUSTOSZ status/selftest; verify Runtime selftest; verify the nine-family census.

MAIN DEPENDENCY COORDINATION:
For each required dependency/download:
CHECK_WORKTREE -> CHECK_MAIN -> CHECK_EXISTING_HASH_VALID_ARTIFACT -> REUSE_IF_VALID
-> otherwise resolve official source/version/hash -> download once -> record provenance/hash/license.
No silent dependency substitution. main is authorized as the dependency/download dispatch source, not as a place to rewrite canonical authority.

MATERIAL WORK:
Continue the generic backlog, prioritizing:
1. generic profile/rubric compiler;
2. source-ledger and citation/CSL pipeline;
3. FFmpeg/ffprobe provider admission when provenance is verifiable;
4. separate image DPI and pixel-dimension checks;
5. stronger DOCX/PPTX/PDF/XLSX validation;
6. writer-provider separation;
7. claims/risk/traceability/monitoring/tests for each new capability;
8. reproducible synthetic end-to-end demonstration.

For each change:
OBSERVE -> RECONCILE -> ANTI_DUPLICATION -> PROVENANCE -> CHECKPOINT
-> MINIMUM_ADDITIVE_DELTA -> TEST -> NEGATIVE_TEST -> NON_REGRESSION -> EVIDENCE -> CONTINUE.

Do not generate or submit the student's actual assignment.
Do not use Desktop Commander.
Do not mutate Louksna.md, PUAC2.md, recovery/**, scripts/assurance/** or trust-root branches.
No merge to target or main is authorized.

TERMINAL:
Leave changes on WORK_BRANCH for review toward TARGET_BRANCH.
Every changed candidate requires fresh producer -> independent validation -> G23 -> G24.
On blocker: preserve exact evidence and HOLD; no blind retry.
