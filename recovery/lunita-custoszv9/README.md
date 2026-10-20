# CUSTOSZ V9 — Lunita scoped bridge

This directory contains the source for a locally tested, narrowly scoped adapter between the CUSTOSZ V9 CRFU coordinator and the existing Lunita/Cajita continuation state machine.

## Execution model

- The existing branch is \`recovery/lunita-custoszv9-operational-20261020\`.
- The live host script is installed at \`5. CUSTOSZ/0. CUSTOSZ  - OPERADOR/CUSTOSZ_CONTINUITY_V1/integrations/lunita-custoszv9/custoszv9_lunita_bridge.py\`.
- The bridge verifies the CUSTOSZ V9 package hash before importing its CRFU modules, uses the existing local mission hash and operator contract, enforces a concurrency lock, creates an auditable bounded task, and dispatches at most one continuation tick per invocation.
- The V9 persistent queue and a separate hash-linked event journal record adapter-task lifecycle. A receipt is written for the operation and a separate closeout receipt records post-validation.
- If a continuation step is blocked, the bridge verifies that the step index, completed-step count and progress timestamp remain unchanged. If a step passes, it verifies a one-step index advance and the exact hash-bound result receipt.
- The adapter does not alter frozen G06/G08 artifacts, grant certification authority, certify the canonical root filesystem or automatically propagate certification.

## Local commands

Run these from the original CUSTOSZ operator project, where \`CUSTOSZV9.pyz\`, the mission contract and continuation state are present:

\`\`\`bash
python3 integrations/lunita-custoszv9/custoszv9_lunita_bridge.py --audit
python3 integrations/lunita-custoszv9/custoszv9_lunita_bridge.py --self-test
python3 integrations/lunita-custoszv9/custoszv9_lunita_bridge.py --run-one-step
\`\`\`

\`--audit\` is read-only. \`--self-test\` uses synthetic tasks and performs no mission-side effects. \`--run-one-step\` is the only mutating mode and is limited to one checkpointed continuation tick and append-only local receipts. Review the local contract, checkpoint and current continuation state before each invocation.

## Validation

The GitHub Actions workflow \`.github/workflows/lunita-custoszv9-recovery-contract.yml\` runs unit tests on changes under this recovery directory. These tests establish local adapter contract behavior only. CI passing does not certify the live runtime, Lunita, frozen G06, G08, or any canonical Louksna gate.

## Explicit remaining blockers

- The frozen original G06 root filesystem source and its original launcher hash remain unresolved. This adapter operates against a versioned derived candidate; that candidate must never be represented as the frozen original.
- The live candidate requires runtime functional tests and independent validation before a candidate-beta operational receipt may be emitted.
- The bridge's local authorization record expressly confines repository mutations to the three named paths on the branch above; no main-branch writes, merges, force-pushes, workflow dispatches, repository-setting changes, or secret access are permitted.

Certification remains \`NOT_GRANTED\` unless a separate, evidence-backed and independently validated release gate authorizes an exactly scoped candidate-beta receipt. No automatic promotion is performed.
