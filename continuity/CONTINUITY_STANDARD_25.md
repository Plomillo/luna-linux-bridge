# LOUKSNA V0.4 — CONTINUITY STANDARD 25

Scope: Rama 1 / Directiva only.
Authority: Louksna.md. Supporting assurance: PUAC2.md.
No cross-branch authority or state is permitted.

1 CONTINUATION_STATE durable
2 generic Worker FSM
3 persistent reconciler
4 metacognitive supervisor
5 second-order meta-supervisor
6 heartbeat
7 progress
8 stall detection
9 checkpoint
10 mandatory .txt checkpoint report
11 idempotency key
12 lease
13 recovery from verified checkpoint
14 explicit dispatch
15 redundant dispatch path
16 schedule only as fallback
17 external watchdog contract
18 UNKNOWN state
19 fail-closed
20 G23/G24 separation
21 causal diagnosis
22 real-time uncertainty resolution
23 evidence-first external research with reusable solution registry
24 dependency identity
25 observability integrity

Operational rule: SAFE_WORK_PENDING + NOT_TERMINAL + NOT_BLOCKED + NO_VALID_WORKER_ACTIVE => DISPATCH_REQUIRED.
No state named QUIET is terminal. UNKNOWN/CONFLICT/missing evidence deny the unsafe transition.
