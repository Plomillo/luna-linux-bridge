# LOUKSNA Remote Bridge — single-use signed scope checkpoint

State: CANDIDATE / NOT CERTIFIED / NO ROOT EXECUTOR. Additive module `bridge/one_time_scope.py` reuses the **existing** elastic mission state, existing external cryptographic G23/G24/G23_2/G24_2 verifier, and the existing evidence ledger. It does not reimplement signature verification or invent a second scheduler. This closes the *local reservation* part of the current root-broker gap, not deployment.

## Exact contract

Preconditions: the admitted owner mission is paused at its exact GATED_OPERATION, with current scope, objective SHA256 and original mission SHA256. Owner's signed request binds exact machine, boot ID, live `bridge/live_link.py` content SHA256 **and** `bridge/one_time_scope.py` SHA256 (`reservation_module_sha256`), capability and deadline. Five independently provisioned public trust roots and genuine externally signed owner/G23/G24/G23_2/G24_2 documents must be accessible to the existing `ExternalGateVerifier`. G23/G24 signatures from the historic APC installation do not apply.

Process: hold a private interprocess `flock` and the original mission lock. Verify the original evidence chain, mission identity and current gated step; refuse any scope ID, exact request hash or mission ID that already appears in the ledger as reserved; invoke the existing strong external verifier; reject malformed or self-authorizing claims; append and `fsync` one `STRONG_SCOPE_RESERVED` entry **before** returning a checkpoint receipt. If the process dies after the append, the same scope is unusable rather than silently retried.

Outputs: `RESERVED_ONCE_AWAITING_INDEPENDENT_EXECUTOR` with the exact immutable receipt hash. Explicit `root_operation_executed=false`, `certified=false`, `issuer_operator_independence_certified=false`.

Security boundary: this module **never** shells out, never calls `sudo`, never signs gates, never trusts synthetic test keys for production and never gives the LLM an execution token. The script accepts signed external inputs but not a remote arbitrary command. Positive unit tests use a clearly synthetic injected verifier to check state transitions; `bridge/tests/test_external_gates.py` is the separate cryptographic test suite.

**Important known residual risk:** this is one-shot only *within the canonical owner-private ledger*. A separately reviewed, centrally enforced root-broker replay register must prevent reuse across alternate state directories, restarts, and host deployments. The material executor must recheck signer independence, time, source, host, boot, owner consent and entire signature chain **immediately before** consuming any authority. Production release remains HOLD until that component, actual five independent signer custody, CUSTOSZ V7 review, G23/G24 decisions, second-order review and Maestro acceptance are proven. No disk or boot mutation is authorized.

## Deployment readiness

CLI: `python3 -B bridge/one_time_scope.py --state-dir /verified/private/lrb --mission-id M --request /verified/request.json --owner-signature /verified/owner.sig --g23 /verified/g23.json --g23-signature /verified/g23.sig --g24 /verified/g24.json --g24-signature /verified/g24.sig --g23-2 /verified/g23_2.json --g23-2-signature /verified/g23_2.sig --g24-2 /verified/g24_2.json --g24-2-signature /verified/g24_2.sig`.

The signed request includes the new `reservation_module_sha256` field; do not reuse any signed request lacking the exact current module SHA. No private signer keys may ever be committed to GitHub.
