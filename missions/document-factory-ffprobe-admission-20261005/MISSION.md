# MISSION — CUSTOSZ V7 / FFPROBE PROVIDER ADMISSION

MISSION_ID = MIS-DOCUMENT-FACTORY-FFPROBE-ADMISSION-20261005
AUTHORITY = Louksna.md
WORKER = CUSTOSZ_V7
RUNTIME = CUSTOSZ_RUNTIME_V1
GOVERNOR = MetaOS
SUPERVISOR = SYMPHYLAX_R1
FAILURE_POSTURE = FAIL_CLOSED
TRACEABILITY = REQUIRED
AUDITABILITY = REQUIRED
PROVENANCE = REQUIRED
ROLLBACK = REQUIRED
NON_REGRESSION = REQUIRED
DESKTOP_COMMANDER = FORBIDDEN
CERTIFICATION_PROPAGATION = FORBIDDEN
AUTO_CERTIFICATION = FORBIDDEN

REPOSITORY = Plomillo/luna-linux-bridge
MAIN_BRANCH = main
MAIN_ROLE = AUTHORITY_LEDGER_AND_DEPENDENCY_DISPATCH
ACTIVE_CANDIDATE_SHA = 43a82aa30607b8775c998fa39b2bc08bfc2a263f
ACTIVE_CANDIDATE_DIGEST_SHA256 = b0c59f37c70e58ca42f7fd215fad890e9a24b255d369110665e7141f26f57404
ACTIVE_SCOPE = DOCUMENT_FACTORY_FRAMEWORK_CORE_V0.1
ACTIVE_CERTIFICATION_MUST_REMAIN_UNCHANGED = TRUE
WORK_BRANCH = custosz/document-factory-ffprobe-admission-20261005

UPSTREAM = FFmpeg
UPSTREAM_VERSION = 9.0.2
UPSTREAM_SOURCE = https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz
UPSTREAM_SIGNATURE = https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz.asc
UPSTREAM_SIGNING_KEY = https://ffmpeg.org/ffmpeg-devel.asc
UPSTREAM_SIGNING_KEY_FINGERPRINT = FCF986EA15E6E293A5644F10B4322F04D67658D8

OBJECTIVE:
Admit FFprobe as an auditable, governed, traceable runtime provider for Document Factory audiovisual validation without mutating or invalidating the currently ACTIVE exact certified digest.

MANDATORY FLOW:
VERIFY_ACTIVE_LEDGER
-> VERIFY_CUSTOSZ_AND_RUNTIME
-> FETCH_OFFICIAL_SOURCE_SIGNATURE_KEY
-> VERIFY_KEY_FINGERPRINT
-> VERIFY_PGP_SIGNATURE
-> COMPUTE_SOURCE_SHA256
-> BUILD_FFPROBE_ISOLATED
-> COMPUTE_BINARY_SHA256
-> FUNCTIONAL_TEST_SYNTHETIC_MEDIA
-> BASELINE_NON_REGRESSION
-> UPDATE_TOOLCHAIN_LOCK_AND_PROVIDER_EVIDENCE
-> CHECKPOINT_WORK_BRANCH
-> STOP_BEFORE_CERTIFICATION

BOUNDARIES:
- Never rewrite the existing operational authorization record.
- Never claim that the new FFprobe capability is covered by the existing G24.
- Never mutate Louksna.md, PUAC2.md, recovery/** or trust-root branches.
- Never merge to main or candidate.
- The new provider remains CANDIDATE_PENDING_FRESH_G23_G24 until a new independent certification chain passes.
- Preserve the current ACTIVE candidate SHA and digest as the rollback anchor.
- Use official FFmpeg release provenance and verify the release signature before build.
- If signature verification, fingerprint verification, build, functional test or non-regression fails: HOLD/FAIL_CLOSED, preserve evidence, do not weaken controls.

POST-MATERIAL NEXT STATE:
FFPROBE_PROVIDER_CANDIDATE_READY_FOR_FRESH_PRODUCER_VALIDATION
-> INDEPENDENT_VALIDATION
-> G23
-> G24
-> NEW_OPERATIONAL_AUTHORIZATION
