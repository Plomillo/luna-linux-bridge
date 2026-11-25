"""Small dependency graph. Cycles are rejected, not ignored."""
from __future__ import annotations

from pydantic import BaseModel, Field

from metagente_luna_s3.registry import REGISTRY


class CycleError(ValueError):
    pass


class Step(BaseModel):
    step_id: str
    capability_id: str
    depends_on: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    plan_id: str
    steps: list[Step]
    status: str


def order(steps: list[Step]) -> list[str]:
    pending = {step.step_id: set(step.depends_on) for step in steps}
    known = set(pending)
    for deps in pending.values():
        missing = deps - known
        if missing:
            raise ValueError(f"unknown dependency: {sorted(missing)}")
    done: list[str] = []
    while pending:
        ready = sorted(step for step, deps in pending.items() if not deps)
        if not ready:
            raise CycleError("circular dependency")
        current = ready[0]
        done.append(current)
        pending.pop(current)
        for deps in pending.values():
            deps.discard(current)
    return done


def plan_for(plan_id: str, capability_id: str | None) -> Plan:
    if capability_id is None or capability_id not in REGISTRY:
        return Plan(plan_id=plan_id, steps=[], status="NOT_EXECUTABLE")
    return Plan(
        plan_id=plan_id,
        steps=[Step(step_id="execute", capability_id=capability_id)],
        status="READY",
    )
