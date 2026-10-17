"""Runtime enforcement for two-step Hoare-style contract composition.

This module checks the executable obligations at runtime. It does not pretend
that Python callbacks are machine-checked proof terms; the Agda source proves
the abstract composition theorem, while this module rejects a run unless the
intermediate postcondition and next precondition are both witnessed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RuntimeContract:
    contract_id: str
    precondition: Callable[[Any], object]
    transition: Callable[[Any], Any]
    postcondition: Callable[[Any, Any], object]


def _well_formed(contract: object) -> bool:
    return (
        isinstance(contract, RuntimeContract)
        and isinstance(contract.contract_id, str)
        and bool(contract.contract_id.strip())
        and callable(contract.precondition)
        and callable(contract.transition)
        and callable(contract.postcondition)
    )


def run_composed_contracts(
    first: RuntimeContract,
    second: RuntimeContract,
    bridge_check: Callable[[Any, Any], object],
    initial_state: Any,
) -> dict[str, Any]:
    """Execute two contracts only when the intermediate obligation is checked.

    A missing/false bridge or precondition is HOLD. A failed postcondition is
    FAIL. No result grants execution authorization, certification, or authority.
    """
    if not _well_formed(first) or not _well_formed(second):
        return {
            "status": "HOLD",
            "reason": "CONTRACT_DEFINITION_INVALID",
            "execution_authorized": False,
            "certification_propagation": False,
            "authority_transfer": False,
        }
    if first.contract_id == second.contract_id:
        return {
            "status": "HOLD",
            "reason": "CONTRACT_IDENTITIES_NOT_DISTINCT",
            "execution_authorized": False,
            "certification_propagation": False,
            "authority_transfer": False,
        }
    if not callable(bridge_check):
        return {
            "status": "HOLD",
            "reason": "POST_PRE_BRIDGE_MISSING",
            "execution_authorized": False,
            "certification_propagation": False,
            "authority_transfer": False,
        }

    try:
        if first.precondition(initial_state) is not True:
            return {
                "status": "HOLD",
                "reason": "FIRST_PRECONDITION_NOT_SATISFIED",
                "execution_authorized": False,
                "certification_propagation": False,
                "authority_transfer": False,
            }

        intermediate = first.transition(initial_state)
        if first.postcondition(initial_state, intermediate) is not True:
            return {
                "status": "FAIL",
                "reason": "FIRST_POSTCONDITION_FAILED",
                "execution_authorized": False,
                "certification_propagation": False,
                "authority_transfer": False,
            }

        if bridge_check(initial_state, intermediate) is not True:
            return {
                "status": "HOLD",
                "reason": "POST_PRE_BRIDGE_NOT_ESTABLISHED",
                "execution_authorized": False,
                "certification_propagation": False,
                "authority_transfer": False,
            }
        if second.precondition(intermediate) is not True:
            return {
                "status": "HOLD",
                "reason": "SECOND_PRECONDITION_NOT_SATISFIED",
                "execution_authorized": False,
                "certification_propagation": False,
                "authority_transfer": False,
            }

        final_state = second.transition(intermediate)
        if second.postcondition(intermediate, final_state) is not True:
            return {
                "status": "FAIL",
                "reason": "SECOND_POSTCONDITION_FAILED",
                "execution_authorized": False,
                "certification_propagation": False,
                "authority_transfer": False,
            }
        return {
            "status": "PASS_FOR_DECLARED_CONTRACTS",
            "reason": None,
            "first_contract_id": first.contract_id,
            "second_contract_id": second.contract_id,
            "initial_state": initial_state,
            "intermediate_state": intermediate,
            "final_state": final_state,
            "bridge_checked": True,
            "execution_authorized": False,
            "certification_propagation": False,
            "authority_transfer": False,
        }
    except Exception as exc:
        # Do not leak arbitrary callback details or reinterpret an exception as PASS.
        return {
            "status": "HOLD",
            "reason": "CONTRACT_CALLBACK_EXCEPTION:" + type(exc).__name__,
            "execution_authorized": False,
            "certification_propagation": False,
            "authority_transfer": False,
        }
