# KNOWN SOLUTIONS REGISTRY — RAMA 1

Purpose: prevent redundant Internet research. Reuse this registry first; research again only when the recorded remedy fails, is inapplicable, or a new derivative failure is evidenced.

## SOL-001 — Silent workflow termination
Problem: checkpoint exposes next_point but no dispatcher consumes it.
Evidence: Rama 1 P02 reached CHECKPOINT_02 with next_point=P03 and ended.
Remedy: durable continuation state + explicit dispatcher + worker FSM + supervisor + meta-supervisor + fail-closed BLOCKED state.
Primary evidence: Louksna sections 42.6/43/44; PUAC2 separation of evidence/validation/G23/G24.
External evidence: runtime verification supports continuous trace monitoring and explicit UNKNOWN; SRE recommends real-time metrics plus structured logs; workflow research supports checkpointed recovery and separation of execution/recovery. Sources reviewed: Springer runtime verification 2026; Google SRE monitoring/checkpointing; OSDI/USENIX ExoFlow/Unum.
Reuse condition: same causal pattern.
Reopen research condition: remedy fails in the actual branch, or a new causal mechanism is observed.

## SOL-002 — Research-source escalation
Order: canonical branch evidence -> local solution registry -> peer-reviewed/academic evidence -> senior/SRE practice -> GitHub -> Hugging Face. Internet material is evidence, never canonical authority.
