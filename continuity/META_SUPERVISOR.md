# SECOND-ORDER META-SUPERVISOR — RAMA 2

The meta-supervisor monitors the continuity supervisor, not capability authority.
It detects stale state, missing .txt reports, contradictory domain claims, dispatch failure, or worker/supervisor silence.
It cannot mark capabilities EVIDENCED, G23, G24, CERTIFIED or ACTIVE. It can only escalate, redispatch, or fail closed.

Invariant: supervisor_failure OR stale_supervisor OR contradictory_state => META_ESCALATE.
