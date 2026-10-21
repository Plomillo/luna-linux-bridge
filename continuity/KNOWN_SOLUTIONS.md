# KNOWN SOLUTIONS REGISTRY — RAMA 2

## SOL-001 — D02 completion without D03 dispatch
Observed causal pattern: D02 worker can persist its own implementation while the continuation workflow is keyed to D02 and the commit does not itself establish a durable generic next-domain dispatcher.
Remedy: durable continuation state + generic first-pending-domain reconciler + explicit workflow_dispatch + fail-closed executor registry + .txt checkpoint report + second-order supervision.
Reuse: exact same causal pattern.
Reopen Internet research only if this remedy fails or a distinct failure mechanism is evidenced.

## SOL-002 — External research hierarchy
1 branch evidence and canonical governance; 2 local solution registry; 3 academic/paper evidence; 4 senior/SRE practice; 5 GitHub; 6 Hugging Face. External sources never grant certification or authority.
