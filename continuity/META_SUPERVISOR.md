# SECOND-ORDER META-SUPERVISOR — RAMA 1

The meta-supervisor monitors the supervisor, not the mission authority.
It may detect stale supervisor state, missing reports, contradictory states, failed dispatch, or blocked transitions.
It may request redispatch or raise BLOCKED/ALERT; it may not certify, activate, mutate Louksna.md, or override G23/G24.
Independent watchdog remains external to this repository workflow.

Invariant: supervisor_failure OR stale_supervisor OR contradictory_state => META_ESCALATE.
