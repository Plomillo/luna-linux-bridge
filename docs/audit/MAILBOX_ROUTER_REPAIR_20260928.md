# MAILBOX ROUTER REPAIR — 2026-09-28

STATUS = REPAIR_VALIDATED_FAIL_CLOSED
AUTHORITY = Louksna.md
DOCTRINE = EXTEND_DO_NOT_REPLACE
NO_SILENT_OPERATIONS = TRUE

## Scope

Repair the CUSTOSZ mission mailbox executor/adapter circular dependency without mutating the immutable final SERVER_READY mission.

## Preserved mission identity

MAIL_ID = MAIL-8191840DEBD98F8775E5
SOURCE_SHA256 = 8191840debd98f8775e530a37d3d23770f148693af64689f8e0d187be037cb21
MISSION_CLASS = FINAL_SERVER_READY_CLOSURE
MISSION_SOURCE_MUTATED = FALSE

## Repair commit

REPAIR_COMMIT = 316adb4b117c4a83bc63872243eb43fa192d436a

Changes:
- adapters may provide executor binding without requiring a prebound executor;
- adapter selection no longer equates provider selection with EXECUTOR_BINDING=PASS;
- source SHA-256 is enforced;
- mission class is enforced;
- adapter status is enforced;
- execution location is enforced;
- scope must be declared;
- adapters unable to provide binding remain rejected when executor is unbound;
- exact rejection reasons are preserved;
- route execution location is explicitly SELF_HOSTED_LUNA_AUX;
- router policy selftest added.

## Non-regression

SELFTEST = MAILBOX_ROUTER_POLICY_SELFTEST=PASS
STATIC_VALIDATION = PASS

The test proves:
1. an exact binding-providing adapter can be selected from an unbound state;
2. location mismatch fails closed;
3. the old SERVER_READY_TEST_ONLY adapter is rejected for the final mission;
4. an adapter that cannot provide binding cannot execute from an unbound state.

## Verification rerun

RUN_ID = 36399270000
RUN_URL = https://github.com/Plomillo/luna-linux-bridge/actions/runs/36399270000
WORKFLOW_TECHNICAL_STATUS = PASS
COMPILE = PASS
ROUTE = PASS

NEW_CUSTOSZ_MISSION_ID = MIS-40921769aee14a1cba9e
MISSION_TERMINAL_STATUS = HOLD
CURRENT_GATE = RUNTIME_ADAPTER
ROOT_CAUSE = NO_UNIQUE_PINNED_RUNTIME_ADAPTER

OBSERVED_STATE = executor_bound=False; matching_adapters=0; rejected_adapters=1

Rejected adapter:
ADAPTER_ID = SERVER_READY_CANDIDATE_V1
REASONS =
- EXECUTION_LOCATION_MISMATCH
- MISSION_CLASS_MISMATCH
- SOURCE_SHA256_MISMATCH

This rejection is expected and correct. The prior adapter is TEST_ONLY, pinned to the previous SERVER_READY source, and declared GITHUB_HOSTED_ONLY. It MUST NOT be silently reused for FINAL_SERVER_READY_CLOSURE.

## Runtime state

RUNTIME_SELFTEST = PASS
RUNTIME_SHA256 = a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67
CUSTOSZ_SHA256 = dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2
METAOS_SHA256 = 5d8f1239e3a0b452be722078760b000afc22af0a64f93ffb0a1f74024f15aed0
AUTHORITY_SHA256 = 5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9

## Evidence artifacts

custosz-mailbox-compiled
SHA256 = 0812143c41c366aaf9c20a5edbe0fafa940256e6e6cb7becaf83efe7f79cbb35
SIZE_BYTES = 9486

custosz-mailbox-results
SHA256 = f820f2e4abc5972b2d67eb9cbd3228c30fcf600d11464ad19eb9991494afe2d8
SIZE_BYTES = 13120

## Current authorized transition

NEXT_GATE = RUNTIME_ADAPTER

Exact remediation:
Create and independently review exactly one SHA-256-pinned adapter dedicated to:
- SOURCE_SHA256 8191840debd98f8775e530a37d3d23770f148693af64689f8e0d187be037cb21
- MISSION_CLASS FINAL_SERVER_READY_CLOSURE
- execution location SELF_HOSTED_LUNA_AUX
- real SERVER_READY deployment/persistence/recovery scope
- provides_executor_binding=true if binding is established by that adapter

The adapter must not reuse SERVER_READY_TEST_ONLY semantics and must not claim deployment, G23 or G24 without material evidence.

## Terminal assessment

EXECUTOR_ADAPTER_CYCLE = RESOLVED
ADAPTER_POLICY_HARDENING = PASS
MISSION_HASH_PRESERVATION = PASS
NON_REGRESSION_SELFTEST = PASS
MISSION_RERUN = PASS_AT_TRANSPORT_AND_ROUTING
MATERIAL_FINAL_MISSION_EXECUTION = NOT_STARTED
SERVER_DEPLOYED = FALSE
G23 = NOT_RUN
G24 = NOT_RUN
SERVER_CERTIFIED = FALSE

COORDINATION_DECISION = HOLD
SINGLE_ROOT_BLOCKER = NO_UNIQUE_PINNED_RUNTIME_ADAPTER
