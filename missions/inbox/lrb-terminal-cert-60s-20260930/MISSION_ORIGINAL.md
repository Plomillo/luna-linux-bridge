MISSION_ID = LRB-TERMINAL-CERT-60S-20260930
MISSION_CLASS = LRB_SOURCE_SECURITY_REVIEW
WORKER = CUSTOSZ_V7
RUNTIME = CUSTOSZ_RUNTIME_V1
AUTHORITY = Louksna.md
TARGET_SOURCE_COMMIT = c961a198f524a128dba6374290e2abe73dfaece6
SCOPE = LOUKSNA_REMOTE_BRIDGE_NON_MODEL_ONLY
WALLCLOCK_SECONDS = 60
FAILURE_POSTURE = FAIL_CLOSED
DOCTRINE = EXTEND_DO_NOT_REPLACE
NO_SILENT_OPERATIONS = ABSOLUTE
CERTIFICATION_PROPAGATION = FORBIDDEN
ROUTING = CUSTOSZ_RUNTIME;SELF-HOSTED;GITHUB;ROLLBACK

OBJECTIVE = Independently review the exact non-model LOUKSNA Remote Bridge source and produce primary evidence for terminal certification.

REQUIRED = Verify exact candidate identity, CUSTOSZ V7 status/selftest, Python syntax, full Bridge test suite, security invariants, local transport bounds, mTLS loopback-only bounds, external-gate no-self-issuance, one-use reservation, global replay fixture, resource-capped service templates, provenance, rollback, and absence of model/virtual-brain benchmark additions after the frozen non-model checkpoint.

FORBIDDEN = Canonical mutation; model/Qwen/virtual-brain work; unsupported PASS; self-certification; silent executor substitution; sudoers/disk/partition/fstab/boot mutation.

OUTPUT = PASS or HOLD with exact evidence and unresolved blockers.
