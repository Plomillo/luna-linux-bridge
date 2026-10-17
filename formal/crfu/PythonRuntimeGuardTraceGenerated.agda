{-# OPTIONS --safe --without-K #-}
module PythonRuntimeGuardTraceGenerated where
open import Agda.Builtin.List using (List; []; _∷_)
open import Agda.Builtin.String using (String)

pythonRuntimeGuardTrace : List String
pythonRuntimeGuardTrace =
  "custoszv9/cli.py|emit|FUNCTION|7:0|" ∷
  "custoszv9/cli.py|emit|END_FUNCTION|7:79|" ∷
  "custoszv9/cli.py|crfu|FUNCTION|8:0|" ∷
  "custoszv9/cli.py|crfu|IF|13:1|a.command == 'status'" ∷
  "custoszv9/cli.py|crfu|RETURN|14:401|0" ∷
  "custoszv9/cli.py|crfu|END_IF|13:1|" ∷
  "custoszv9/cli.py|crfu|IF|15:1|a.command == 'selftest'" ∷
  "custoszv9/cli.py|crfu|RETURN|16:31|0 if out['status'] == 'PASS' else 1" ∷
  "custoszv9/cli.py|crfu|END_IF|15:1|" ∷
  "custoszv9/cli.py|crfu|IF|17:1|a.command == 'journal-verify'" ∷
  "custoszv9/cli.py|crfu|RETURN|18:39|0 if out['status'] == 'PASS' else 1" ∷
  "custoszv9/cli.py|crfu|END_IF|17:1|" ∷
  "custoszv9/cli.py|crfu|RETURN|19:1|2" ∷
  "custoszv9/cli.py|crfu|END_FUNCTION|19:9|" ∷
  "custoszv9/cli.py|main|FUNCTION|20:0|" ∷
  "custoszv9/cli.py|main|IF|22:1|args == ['--version']" ∷
  "custoszv9/cli.py|main|RETURN|22:62|0" ∷
  "custoszv9/cli.py|main|END_IF|22:1|" ∷
  "custoszv9/cli.py|main|IF|23:1|args and args[0] == 'crfu'" ∷
  "custoszv9/cli.py|main|RETURN|23:29|crfu(args[1:])" ∷
  "custoszv9/cli.py|main|END_IF|23:1|" ∷
  "custoszv9/cli.py|main|RETURN|27:1|int(result) if isinstance(result, int) else 0" ∷
  "custoszv9/cli.py|main|END_FUNCTION|27:52|" ∷
  "custoszv9/crfu/anti_paralysis.py|state_fingerprint|FUNCTION|4:0|" ∷
  "custoszv9/crfu/anti_paralysis.py|state_fingerprint|RETURN|4:41|hashlib.sha256(canonical_json(state).encode('utf-8')).hexdigest()" ∷
  "custoszv9/crfu/anti_paralysis.py|state_fingerprint|END_FUNCTION|4:113|" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|FUNCTION|5:0|" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|IF|6:1|planning_budget_remaining <= 0" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|RETURN|6:33|{'decision': 'BLOCKED', 'reason': 'PLANNING_BUDGET_EXHAUSTED', 'next_action': None}" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|END_IF|6:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|IF|7:1|not action_id or not strategy_id or len(state_hash) != 64" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|RETURN|7:60|{'decision': 'BLOCKED', 'reason': 'ACTION_STRATEGY_OR_STATE_IDENTITY_INVALID', 'next_action': None}" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|END_IF|7:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|IF|9:1|repeated and (not new_evidence)" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|RETURN|9:34|{'decision': 'BLOCKED', 'reason': 'REPEATED_STRATEGY_WITHOUT_NEW_EVIDENCE', 'next_action': None}" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|END_IF|9:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|IF|10:1|wait_condition is not None" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|IF|11:2|not wait_condition.strip() or not wait_deadline_utc" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|RETURN|11:57|{'decision': 'BLOCKED', 'reason': 'UNBOUNDED_WAIT_FORBIDDEN', 'next_action': None}" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|END_IF|11:2|" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|RETURN|12:2|{'decision': 'WAIT_CONDITIONALLY', 'wait_condition': wait_condition, 'wait_deadline_utc': wait_deadline_utc, 'next_action': 'RESUME_ON_CONDITION_OR_DEADLINE'}" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|END_IF|10:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|IF|13:1|retry_budget_remaining < 0" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|RETURN|13:29|{'decision': 'BLOCKED', 'reason': 'RETRY_BUDGET_INVALID', 'next_action': None}" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|END_IF|13:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|RETURN|14:1|{'decision': 'EXECUTE_NEXT_ACTION', 'reason': 'BOUNDED_PLAN_ADMISSIBLE', 'next_action': action_id, 'strategy_id': strategy_id}" ∷
  "custoszv9/crfu/anti_paralysis.py|decide_next_action|END_FUNCTION|14:127|" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|FUNCTION|15:0|" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|IF|19:1|idempotency_class not in {'READ_ONLY', 'IDEMPOTENT', 'NON_IDEMPOTENT', 'UNKNOWN'}" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|RETURN|20:2|{'decision': 'DENY_RETRY', 'reason': 'IDEMPOTENCY_CLASS_INVALID'}" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|END_IF|19:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|IF|21:1|any((isinstance(v, bool) or not isinstance(v, int) for v in (retries_used, max_retries, wait_seconds))) or retries_used < 0 or max_retries < 0 or (wait_seconds < 0)" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|RETURN|22:2|{'decision': 'DENY_RETRY', 'reason': 'RETRY_BUDGET_INVALID'}" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|END_IF|21:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|IF|23:1|not transient_failure" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|RETURN|23:26|{'decision': 'DENY_RETRY', 'reason': 'FAILURE_NOT_CLASSIFIED_TRANSIENT'}" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|END_IF|23:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|IF|24:1|retries_used >= max_retries" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|RETURN|24:30|{'decision': 'DENY_RETRY', 'reason': 'RETRY_BUDGET_EXHAUSTED'}" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|END_IF|24:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|IF|25:1|authorization_valid is not True" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|RETURN|25:36|{'decision': 'DENY_RETRY', 'reason': 'AUTHORIZATION_NOT_VALID'}" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|END_IF|25:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|IF|26:1|idempotency_class == 'UNKNOWN'" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|RETURN|26:33|{'decision': 'DENY_RETRY', 'reason': 'UNKNOWN_IDEMPOTENCY_CLASS'}" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|END_IF|26:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|IF|27:1|idempotency_class == 'NON_IDEMPOTENT' and (not effects_reconciled or not idempotency_key)" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|RETURN|28:2|{'decision': 'DENY_RETRY', 'reason': 'NON_IDEMPOTENT_EFFECTS_NOT_RECONCILED'}" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|END_IF|27:1|" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|RETURN|29:1|{'decision': 'WAIT_CONDITIONALLY' if wait_seconds else 'RETRY_ADMISSIBLE', 'reason': 'BOUNDED_TRANSIENT_RETRY', 'wait_seconds': wait_seconds, 'retries_remaining': max_retries - retries_used - 1, 'authorization_reused_only_within_same_valid_scope': True}" ∷
  "custoszv9/crfu/anti_paralysis.py|retry_decision|END_FUNCTION|31:66|" ∷
  "custoszv9/crfu/contracts.py|_well_formed|FUNCTION|22:0|" ∷
  "custoszv9/crfu/contracts.py|_well_formed|RETURN|23:4|isinstance(contract, RuntimeContract) and isinstance(contract.contract_id, str) and bool(contract.contract_id.strip()) and callable(contract.precondition) and callable(contract.transition) and callable(contract.postcondition)" ∷
  "custoszv9/crfu/contracts.py|_well_formed|END_FUNCTION|30:5|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|FUNCTION|33:0|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|IF|44:4|not _well_formed(first) or not _well_formed(second)" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|RETURN|45:8|{'status': 'HOLD', 'reason': 'CONTRACT_DEFINITION_INVALID', 'execution_authorized': False, 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|END_IF|44:4|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|IF|52:4|first.contract_id == second.contract_id" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|RETURN|53:8|{'status': 'HOLD', 'reason': 'CONTRACT_IDENTITIES_NOT_DISTINCT', 'execution_authorized': False, 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|END_IF|52:4|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|IF|60:4|not callable(bridge_check)" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|RETURN|61:8|{'status': 'HOLD', 'reason': 'POST_PRE_BRIDGE_MISSING', 'execution_authorized': False, 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|END_IF|60:4|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|TRY|69:4|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|IF|70:8|first.precondition(initial_state) is not True" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|RETURN|71:12|{'status': 'HOLD', 'reason': 'FIRST_PRECONDITION_NOT_SATISFIED', 'execution_authorized': False, 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|END_IF|70:8|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|IF|80:8|first.postcondition(initial_state, intermediate) is not True" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|RETURN|81:12|{'status': 'FAIL', 'reason': 'FIRST_POSTCONDITION_FAILED', 'execution_authorized': False, 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|END_IF|80:8|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|IF|89:8|bridge_check(initial_state, intermediate) is not True" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|RETURN|90:12|{'status': 'HOLD', 'reason': 'POST_PRE_BRIDGE_NOT_ESTABLISHED', 'execution_authorized': False, 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|END_IF|89:8|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|IF|97:8|second.precondition(intermediate) is not True" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|RETURN|98:12|{'status': 'HOLD', 'reason': 'SECOND_PRECONDITION_NOT_SATISFIED', 'execution_authorized': False, 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|END_IF|97:8|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|IF|107:8|second.postcondition(intermediate, final_state) is not True" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|RETURN|108:12|{'status': 'FAIL', 'reason': 'SECOND_POSTCONDITION_FAILED', 'execution_authorized': False, 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|END_IF|107:8|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|RETURN|115:8|{'status': 'PASS_FOR_DECLARED_CONTRACTS', 'reason': None, 'first_contract_id': first.contract_id, 'second_contract_id': second.contract_id, 'initial_state': initial_state, 'intermediate_state': intermediate, 'final_state': final_state, 'bridge_checked': True, 'execution_authorized': False, 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|EXCEPT|128:4|Exception" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|RETURN|130:8|{'status': 'HOLD', 'reason': 'CONTRACT_CALLBACK_EXCEPTION:' + type(exc).__name__, 'execution_authorized': False, 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|END_TRY|69:4|" ∷
  "custoszv9/crfu/contracts.py|run_composed_contracts|END_FUNCTION|136:9|" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|FUNCTION|7:0|" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|IF|9:1|issues or task is None" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|RETURN|9:27|{'status': 'DENIED', 'stage': 'TASK_VALIDATION', 'reasons': issues, 'next_action': 'CORRECT_TASK_CONTRACT'}" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|END_IF|9:1|" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|IF|10:1|authorization_verifier is None" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|RETURN|10:35|{'status': 'HOLD', 'stage': 'AUTHORIZATION', 'reasons': ['TRUSTED_AUTHORIZATION_VERIFIER_UNAVAILABLE'], 'next_action': 'CONFIGURE_TRUSTED_AUTHORIZATION_ADAPTER'}" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|END_IF|10:1|" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|IF|12:1|not isinstance(auth, dict) or auth.get('status') != 'PASS' or auth.get('task_id') != task.task_id" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|RETURN|12:97|{'status': 'DENIED', 'stage': 'AUTHORIZATION', 'reasons': ['AUTHORIZATION_NOT_VALIDLY_BOUND'], 'next_action': 'OBTAIN_VALID_SCOPE_BOUND_AUTHORIZATION'}" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|END_IF|12:1|" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|IF|15:1|resource['status'] != 'PASS'" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|RETURN|15:31|{'status': 'HOLD', 'stage': 'RESOURCE_PREFLIGHT', 'resource': resource, 'next_action': 'WAIT_FOR_RESOURCE_CONDITION_OR_REPLAN'}" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|END_IF|15:1|" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|IF|17:1|plan['status'] != 'PLAN_VALIDATED'" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|RETURN|17:37|{'status': 'HOLD', 'stage': 'PLANNING', 'plan': plan, 'next_action': 'REPLAN_OR_RECORD_BLOCKER'}" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|END_IF|17:1|" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|IF|18:1|action_runner is None" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|RETURN|18:26|{'status': 'HOLD', 'stage': 'EXECUTION', 'plan': plan, 'next_action': 'CONFIGURE_GOVERNED_ACTION_ADAPTER'}" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|END_IF|18:1|" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|FOR|20:1|step in plan['actions'][:max(0, min(maximum_steps, planning_budget))]" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|IF|23:2|decision['decision'] != 'EXECUTE_NEXT_ACTION'" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|RETURN|23:49|{'status': 'BLOCKED', 'completed': completed, 'decision': decision}" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|END_IF|23:2|" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|IF|25:2|not isinstance(outcome, dict) or outcome.get('status') != 'PASS'" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|RETURN|25:67|{'status': 'BLOCKED', 'completed': completed, 'failed_action': step['action_id'], 'failure': outcome, 'next_action': 'PRESERVE_CHECKPOINT_AND_REVALIDATE'}" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|END_IF|25:2|" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|END_FOR|20:1|" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|RETURN|28:1|{'status': status, 'completed_actions': completed, 'plan': plan, 'completion_claim': status == 'COMPLETED', 'certification': 'NOT_GRANTED', 'canonical_promotion': 'NOT_AUTHORIZED'}" ∷
  "custoszv9/crfu/coordinator.py|run_bounded_mission|END_FUNCTION|28:175|" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|FUNCTION|5:0|" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|IF|6:1|not isinstance(record, dict)" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|RETURN|6:32|{'status': 'UNPROVEN', 'issues': ['EQUIVALENCE_RECORD_NOT_OBJECT'], 'property_transport': 'DENIED'}" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|END_IF|6:1|" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|IF|8:1|not is_sha256(record.get('source_sha256')) or not is_sha256(record.get('target_sha256'))" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|END_IF|8:1|" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|IF|9:1|not record.get('equivalence_specification_id') or not is_sha256(record.get('specification_sha256'))" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|END_IF|9:1|" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|IF|10:1|record.get('proof_status') != 'VERIFIED' or record.get('proof_verified_by') in (None, '', record.get('producer_identity'))" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|END_IF|10:1|" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|IF|12:1|not isinstance(props, list) or not props" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|END_IF|12:1|" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|IF|14:1|forbidden" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|END_IF|14:1|" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|IF|15:1|issues" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|RETURN|15:11|{'status': 'UNPROVEN', 'issues': issues, 'property_transport': 'DENIED'}" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|END_IF|15:1|" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|RETURN|16:1|{'status': 'ADMISSIBLE_FOR_DECLARED_SCOPE', 'issues': [], 'property_transport': sorted(set(props)), 'authority_transfer': False, 'certification_transfer': False}" ∷
  "custoszv9/crfu/equivalence.py|validate_equivalence|END_FUNCTION|16:160|" ∷
  "custoszv9/crfu/event_queue.py|utc_now|FUNCTION|25:0|" ∷
  "custoszv9/crfu/event_queue.py|utc_now|RETURN|25:19|datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')" ∷
  "custoszv9/crfu/event_queue.py|utc_now|END_FUNCTION|25:109|" ∷
  "custoszv9/crfu/event_queue.py|_hash_event|FUNCTION|26:0|" ∷
  "custoszv9/crfu/event_queue.py|_hash_event|RETURN|27:1|hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()" ∷
  "custoszv9/crfu/event_queue.py|_hash_event|END_FUNCTION|27:73|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.__init__|FUNCTION|33:1|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.__init__|WITH|35:2|closing(self._connect())" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.__init__|END_WITH|35:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.__init__|END_FUNCTION|37:306|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue._connect|FUNCTION|38:1|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue._connect|RETURN|43:2|db" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue._connect|END_FUNCTION|43:11|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue._append|FUNCTION|44:1|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue._append|END_FUNCTION|52:86|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|FUNCTION|53:1|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|IF|55:2|issues or task is None" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|RAISE|55:28|ValueError('TASK_CONTRACT_INVALID:' + ','.join(issues))" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|END_IF|55:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|TRY|58:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|IF|61:3|old" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|IF|62:4|old['task_json'] != raw" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|RAISE|63:19|QueueConflict('MISSION_ID_REUSED_WITH_DIFFERENT_TASK')" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|END_IF|62:4|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|RETURN|64:16|{'mission_id': mission, 'state': old['state'], 'idempotent_duplicate': True}" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|END_IF|61:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|RETURN|68:15|{'mission_id': mission, 'state': 'RECEIVED', 'idempotent_duplicate': False}" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|EXCEPT|69:2|Exception" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|IF|70:3|db.in_transaction" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|END_IF|70:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|RAISE|71:3|re-raise" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|FINALLY|72:10|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|END_TRY|58:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.submit|END_FUNCTION|72:20|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|FUNCTION|73:1|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|IF|74:2|new_state not in ALLOWED.get(expected_state, set())" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|RAISE|74:56|InvalidTransition(f'TRANSITION_FORBIDDEN:{expected_state}->{new_state}')" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|END_IF|74:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|IF|76:2|set(fields) - allowed_fields" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|RAISE|76:32|ValueError('UNRECOGNIZED_STATE_FIELDS')" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|END_IF|76:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|IF|77:2|new_state == 'WAITING_FOR_EVENT'" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|IF|79:3|not isinstance(condition, str) or not condition.strip() or (not isinstance(deadline, str)) or (not deadline.strip())" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|RAISE|80:4|ValueError('WAIT_CONDITION_AND_DEADLINE_REQUIRED')" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|END_IF|79:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|TRY|81:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|EXCEPT|82:3|ValueError" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|RAISE|82:21|ValueError('WAIT_DEADLINE_INVALID')" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|END_TRY|81:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|IF|83:3|parsed.tzinfo is None" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|RAISE|83:28|ValueError('WAIT_DEADLINE_MUST_BE_TIMEZONE_AWARE')" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|END_IF|83:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|END_IF|77:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|TRY|85:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|IF|88:3|not row" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|RAISE|88:14|KeyError('MISSION_NOT_FOUND')" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|END_IF|88:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|IF|89:3|row['state'] != expected_state" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|RAISE|89:35|QueueConflict('MISSION_STATE_CHANGED:' + str(row['state']))" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|END_IF|89:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|RETURN|96:3|self.get(mission_id)" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|EXCEPT|97:2|Exception" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|IF|98:3|db.in_transaction" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|END_IF|98:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|RAISE|99:3|re-raise" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|FINALLY|100:10|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|END_TRY|85:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.transition|END_FUNCTION|100:20|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|FUNCTION|101:1|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|TRY|104:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|IF|107:3|not row" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|RETURN|107:26|None" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|END_IF|107:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|RETURN|111:15|self.get(mission)" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|EXCEPT|112:2|Exception" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|IF|113:3|db.in_transaction" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|END_IF|113:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|RAISE|114:3|re-raise" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|FINALLY|115:10|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|END_TRY|104:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.claim_next_ready|END_FUNCTION|115:20|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|FUNCTION|116:1|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|IF|118:2|not isinstance(signal_key, str) or not signal_key.strip()" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|RAISE|118:62|ValueError('SIGNAL_KEY_REQUIRED')" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|END_IF|118:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|TRY|121:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|FOR|124:3|row in rows" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|TRY|126:4|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|EXCEPT|127:4|ValueError" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|END_TRY|126:4|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|IF|129:4|due is None or due <= now" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|ELSE|133:4|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|IF|133:4|row['wait_condition'] == signal_key" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|END_IF|133:4|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|END_IF|129:4|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|END_FOR|124:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|RETURN|138:3|{'signal_key': signal_key, 'resumed': resumed, 'expired': expired}" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|EXCEPT|139:2|Exception" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|IF|140:3|db.in_transaction" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|END_IF|140:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|RAISE|141:3|re-raise" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|FINALLY|142:10|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|END_TRY|121:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.emit_signal|END_FUNCTION|142:20|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.get|FUNCTION|143:1|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.get|WITH|144:2|closing(self._connect())" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.get|END_WITH|144:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.get|IF|146:2|not row" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.get|RAISE|146:13|KeyError('MISSION_NOT_FOUND')" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.get|END_IF|146:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.get|RETURN|147:70|result" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.get|END_FUNCTION|147:83|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|FUNCTION|148:1|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|WITH|150:2|closing(self._connect())" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|END_WITH|150:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|FOR|152:2|(no, row) in enumerate(rows, 1)" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|IF|153:3|row['previous_event_hash'] != previous" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|RETURN|153:43|{'status': 'FAIL', 'reason': 'PREVIOUS_EVENT_HASH_MISMATCH', 'event_number': no}" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|END_IF|153:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|IF|156:3|_hash_event(material) != row['event_hash']" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|RETURN|156:47|{'status': 'FAIL', 'reason': 'EVENT_HASH_MISMATCH', 'event_number': no}" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|END_IF|156:3|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|END_FOR|152:2|" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|RETURN|158:2|{'status': 'PASS', 'event_count': count, 'last_hash': previous}" ∷
  "custoszv9/crfu/event_queue.py|PersistentMissionQueue.verify_event_chain|END_FUNCTION|158:67|" ∷
  "custoszv9/crfu/evidence.py|_lock|FUNCTION|9:0|" ∷
  "custoszv9/crfu/evidence.py|_lock|IF|10:1|os.name == 'nt'" ∷
  "custoszv9/crfu/evidence.py|_lock|TRY|13:2|" ∷
  "custoszv9/crfu/evidence.py|_lock|EXCEPT|14:2|OSError" ∷
  "custoszv9/crfu/evidence.py|_lock|END_TRY|13:2|" ∷
  "custoszv9/crfu/evidence.py|_lock|ELSE|16:2|" ∷
  "custoszv9/crfu/evidence.py|_lock|END_IF|10:1|" ∷
  "custoszv9/crfu/evidence.py|_lock|END_FUNCTION|17:31|" ∷
  "custoszv9/crfu/evidence.py|_unlock|FUNCTION|18:0|" ∷
  "custoszv9/crfu/evidence.py|_unlock|IF|19:1|os.name == 'nt'" ∷
  "custoszv9/crfu/evidence.py|_unlock|ELSE|23:2|" ∷
  "custoszv9/crfu/evidence.py|_unlock|END_IF|19:1|" ∷
  "custoszv9/crfu/evidence.py|_unlock|END_FUNCTION|24:31|" ∷
  "custoszv9/crfu/evidence.py|_hash|FUNCTION|25:0|" ∷
  "custoszv9/crfu/evidence.py|_hash|RETURN|27:1|sha256_bytes(canonical_json(value).encode('utf-8'))" ∷
  "custoszv9/crfu/evidence.py|_hash|END_FUNCTION|27:59|" ∷
  "custoszv9/crfu/evidence.py|append_event|FUNCTION|28:0|" ∷
  "custoszv9/crfu/evidence.py|append_event|IF|30:1|missing" ∷
  "custoszv9/crfu/evidence.py|append_event|RAISE|30:12|ValueError('EVIDENCE_FIELDS_MISSING:' + ','.join(missing))" ∷
  "custoszv9/crfu/evidence.py|append_event|END_IF|30:1|" ∷
  "custoszv9/crfu/evidence.py|append_event|WITH|32:1|_LOCK" ∷
  "custoszv9/crfu/evidence.py|append_event|TRY|34:2|" ∷
  "custoszv9/crfu/evidence.py|append_event|IF|36:3|checked['status'] != 'PASS'" ∷
  "custoszv9/crfu/evidence.py|append_event|RAISE|36:32|ValueError('JOURNAL_PREEXISTING_INTEGRITY_FAILURE')" ∷
  "custoszv9/crfu/evidence.py|append_event|END_IF|36:3|" ∷
  "custoszv9/crfu/evidence.py|append_event|TRY|39:3|" ∷
  "custoszv9/crfu/evidence.py|append_event|IF|40:4|os.write(out, line) != len(line)" ∷
  "custoszv9/crfu/evidence.py|append_event|RAISE|40:37|OSError('SHORT_EVIDENCE_WRITE')" ∷
  "custoszv9/crfu/evidence.py|append_event|END_IF|40:4|" ∷
  "custoszv9/crfu/evidence.py|append_event|FINALLY|42:11|" ∷
  "custoszv9/crfu/evidence.py|append_event|END_TRY|39:3|" ∷
  "custoszv9/crfu/evidence.py|append_event|RETURN|43:3|row" ∷
  "custoszv9/crfu/evidence.py|append_event|FINALLY|44:10|" ∷
  "custoszv9/crfu/evidence.py|append_event|END_TRY|34:2|" ∷
  "custoszv9/crfu/evidence.py|append_event|END_WITH|32:1|" ∷
  "custoszv9/crfu/evidence.py|append_event|END_FUNCTION|44:34|" ∷
  "custoszv9/crfu/evidence.py|verify_journal|FUNCTION|45:0|" ∷
  "custoszv9/crfu/evidence.py|verify_journal|IF|47:1|not p.exists()" ∷
  "custoszv9/crfu/evidence.py|verify_journal|RETURN|47:19|{'status': 'PASS', 'event_count': 0, 'last_hash': '0' * 64}" ∷
  "custoszv9/crfu/evidence.py|verify_journal|END_IF|47:1|" ∷
  "custoszv9/crfu/evidence.py|verify_journal|TRY|49:1|" ∷
  "custoszv9/crfu/evidence.py|verify_journal|WITH|50:2|p.open('r', encoding='utf-8')" ∷
  "custoszv9/crfu/evidence.py|verify_journal|FOR|51:3|(no, line) in enumerate(stream, 1)" ∷
  "custoszv9/crfu/evidence.py|verify_journal|IF|52:4|not line.endswith('\\n')" ∷
  "custoszv9/crfu/evidence.py|verify_journal|RETURN|52:31|{'status': 'FAIL', 'reason': 'UNTERMINATED_EVENT', 'line': no}" ∷
  "custoszv9/crfu/evidence.py|verify_journal|END_IF|52:4|" ∷
  "custoszv9/crfu/evidence.py|verify_journal|IF|54:4|not isinstance(row, dict)" ∷
  "custoszv9/crfu/evidence.py|verify_journal|RAISE|54:32|ValueError('EVENT_NOT_OBJECT')" ∷
  "custoszv9/crfu/evidence.py|verify_journal|END_IF|54:4|" ∷
  "custoszv9/crfu/evidence.py|verify_journal|IF|55:4|row.get('previous_event_hash') != previous" ∷
  "custoszv9/crfu/evidence.py|verify_journal|RETURN|55:48|{'status': 'FAIL', 'reason': 'PREVIOUS_HASH_MISMATCH', 'line': no}" ∷
  "custoszv9/crfu/evidence.py|verify_journal|END_IF|55:4|" ∷
  "custoszv9/crfu/evidence.py|verify_journal|IF|57:4|current != _hash(row)" ∷
  "custoszv9/crfu/evidence.py|verify_journal|RETURN|57:27|{'status': 'FAIL', 'reason': 'CURRENT_HASH_MISMATCH', 'line': no}" ∷
  "custoszv9/crfu/evidence.py|verify_journal|END_IF|57:4|" ∷
  "custoszv9/crfu/evidence.py|verify_journal|END_FOR|51:3|" ∷
  "custoszv9/crfu/evidence.py|verify_journal|END_WITH|50:2|" ∷
  "custoszv9/crfu/evidence.py|verify_journal|EXCEPT|59:1|(OSError, UnicodeError, json.JSONDecodeError, ValueError)" ∷
  "custoszv9/crfu/evidence.py|verify_journal|RETURN|59:70|{'status': 'FAIL', 'reason': 'JOURNAL_UNREADABLE_OR_MALFORMED', 'detail': str(exc)}" ∷
  "custoszv9/crfu/evidence.py|verify_journal|END_TRY|49:1|" ∷
  "custoszv9/crfu/evidence.py|verify_journal|RETURN|60:1|{'status': 'PASS', 'event_count': count, 'last_hash': previous}" ∷
  "custoszv9/crfu/evidence.py|verify_journal|END_FUNCTION|60:66|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|FUNCTION|4:0|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|IF|5:1|not isinstance(bundle, dict)" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|RETURN|5:32|{'status': 'HOLD', 'reasons': ['PROOF_BUNDLE_NOT_OBJECT'], 'proof_transport': 'DENIED'}" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|END_IF|5:1|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|IF|7:1|not is_sha256(target_sha256)" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|END_IF|7:1|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|IF|8:1|bundle.get('target_sha256') != target_sha256" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|END_IF|8:1|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|IF|9:1|bundle.get('scope') != required_scope" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|END_IF|9:1|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|IF|10:1|not is_sha256(bundle.get('specification_sha256'))" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|END_IF|10:1|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|IF|12:1|not isinstance(tool, dict) or not tool.get('name') or (not tool.get('version'))" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|END_IF|12:1|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|IF|13:1|not isinstance(bundle.get('assumptions'), list) or not isinstance(bundle.get('limitations'), list)" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|END_IF|13:1|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|IF|14:1|bundle.get('status') not in {'PASS', 'PASS_WITH_LIMITATIONS'}" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|END_IF|14:1|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|IF|15:1|bundle.get('evidence_verified') is not True" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|END_IF|15:1|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|IF|16:1|issues" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|RETURN|16:11|{'status': 'HOLD', 'reasons': issues, 'proof_transport': 'DENIED', 'claim': 'NO_FORMAL_CORRECTNESS_CLAIM'}" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|END_IF|16:1|" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|RETURN|17:1|{'status': 'PASS_FOR_DECLARED_SCOPE', 'reasons': [], 'proof_transport': 'ONLY_EXPLICITLY_LISTED_PROPERTIES', 'transportable_properties': bundle.get('transportable_properties', []), 'not_transported': ['binary_identity', 'authorization', 'signatures', 'certification', 'canonical_authority', 'empirical_model_quality']}" ∷
  "custoszv9/crfu/formal.py|validate_proof_bundle|END_FUNCTION|17:311|" ∷
  "custoszv9/crfu/gates.py|is_git_commit|FUNCTION|10:0|" ∷
  "custoszv9/crfu/gates.py|is_git_commit|RETURN|11:1|isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value) is not None" ∷
  "custoszv9/crfu/gates.py|is_git_commit|END_FUNCTION|11:81|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|FUNCTION|13:0|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|18:1|not is_git_commit(candidate_commit_sha) or not is_sha256(package_sha256) or (not is_git_commit(trusted_workflow_sha))" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|RETURN|19:2|{'status': 'HOLD', 'reason': 'CANDIDATE_OR_TRUST_ROOT_IDENTITY_INVALID', 'release_eligible': False}" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|18:1|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|20:1|not isinstance(producer_identity, str) or not producer_identity.strip()" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|RETURN|21:2|{'status': 'HOLD', 'reason': 'PRODUCER_IDENTITY_MISSING', 'release_eligible': False}" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|20:1|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|22:1|not isinstance(records, list)" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|RETURN|23:2|{'status': 'HOLD', 'reason': 'GATE_EVIDENCE_ROOT_NOT_LIST', 'release_eligible': False}" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|22:1|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|FOR|26:1|(position, row) in enumerate(records)" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|27:2|not isinstance(row, dict) or not isinstance(row.get('gate_id'), str) or (not row['gate_id'].strip())" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|RETURN|28:3|{'status': 'FAIL', 'reason': 'MALFORMED_GATE_RECORD:' + str(position), 'release_eligible': False}" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|27:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|30:2|gate_id not in registered" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|RETURN|31:3|{'status': 'FAIL', 'reason': 'UNREGISTERED_GATE_IDENTIFIER:' + gate_id, 'release_eligible': False}" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|30:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|32:2|gate_id in index" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|RETURN|33:3|{'status': 'FAIL', 'reason': 'DUPLICATE_GATE_RECORD:' + gate_id, 'release_eligible': False}" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|32:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_FOR|26:1|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|FOR|36:1|gate in list(CANONICAL_GATES) + list(LOCAL_PUAC_CONTROLS)" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|40:2|row is None" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|40:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|43:2|row.get('candidate_commit_sha') != candidate_commit_sha" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|43:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|44:2|row.get('package_sha256') != package_sha256" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|44:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|45:2|row.get('trusted_workflow_sha') != trusted_workflow_sha" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|45:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|46:2|row.get('producer_identity') != producer_identity" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|46:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|47:2|not row.get('evaluator_identity')" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|ELSE|48:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|48:2|row.get('evaluator_identity') == row.get('producer_identity')" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|48:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|47:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|49:2|not is_sha256(row.get('evidence_sha256'))" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|49:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|51:2|gate_state == 'FAIL'" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|ELSE|52:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|52:2|gate_state != 'PASS'" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|52:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|51:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|53:2|trusted_signature_verifier is None" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|ELSE|56:3|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|TRY|56:3|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|58:4|not isinstance(result, dict) or result.get('status') != 'PASS'" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|58:4|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|EXCEPT|59:3|Exception" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_TRY|56:3|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|53:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|60:2|local" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|TRY|61:3|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|65:4|checked.get('status') == 'HOLD'" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|ELSE|67:4|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|67:4|checked.get('status') != 'PASS_FOR_LOCAL_CONTROL_SCOPE'" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|67:4|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|65:4|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|EXCEPT|69:3|Exception" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_TRY|61:3|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|60:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|70:2|hard" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|ELSE|71:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|71:2|pending" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|ELSE|72:7|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|71:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|70:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_FOR|36:1|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|73:1|applicability_verifier is None" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|ELSE|76:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|TRY|76:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|78:3|not isinstance(application, dict) or application.get('status') != 'PASS'" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|ELSE|81:4|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|82:4|not isinstance(allowed, list) or set(allowed) != set(CANONICAL_GATES)" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|82:4|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|78:3|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|EXCEPT|84:2|Exception" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_TRY|76:2|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|73:1|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|85:1|cf or lf" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|ELSE|86:1|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|IF|86:1|len(cp) == 24 and len(lp) == 8 and (not ch) and (not lh)" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|ELSE|87:6|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|86:1|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_IF|85:1|" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|RETURN|88:1|{'schema': 'CUSTOSZV9_GATE_EVIDENCE_BINDING/1.1', 'status': status, 'canonical_gate_count': 24, 'canonical_gates_passed': cp, 'canonical_gates_held': ch, 'canonical_gates_failed': cf, 'local_puac_control_count': 8, 'local_controls_passed': lp, 'local_controls_held': lh, 'local_controls_failed': lf, 'signature_verification_results': signature_results, 'release_eligible': False, 'certification': 'NOT_GRANTED_BY_CRFU', 'puac2_canonical_admission': 'NOT_GRANTED', 'canonical_promotion': 'NOT_AUTHORIZED', 'note': 'Unavailable or incomplete assurance prerequisites yield HOLD. Contradictions yield FAIL. A field claiming VERIFIED is never itself a signature check.'}" ∷
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_FUNCTION|94:161|" ∷
  "custoszv9/crfu/migration.py|MigrationWitness.to_dict|FUNCTION|30:4|" ∷
  "custoszv9/crfu/migration.py|MigrationWitness.to_dict|RETURN|31:8|asdict(self)" ∷
  "custoszv9/crfu/migration.py|MigrationWitness.to_dict|END_FUNCTION|31:27|" ∷
  "custoszv9/crfu/migration.py|_digest_is_valid|FUNCTION|34:0|" ∷
  "custoszv9/crfu/migration.py|_digest_is_valid|RETURN|35:4|isinstance(value, str) and _SHA256.fullmatch(value) is not None" ∷
  "custoszv9/crfu/migration.py|_digest_is_valid|END_FUNCTION|35:74|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|FUNCTION|38:0|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|52:4|not isinstance(witness, MigrationWitness)" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|53:8|{'status': 'HOLD', 'reason': 'MIGRATION_WITNESS_INVALID', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|52:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|65:4|not all((_digest_is_valid(item) for item in fields))" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|66:8|{'status': 'HOLD', 'reason': 'MIGRATION_DIGEST_INVALID', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|65:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|72:4|not isinstance(witness.source_version, str) or not witness.source_version.strip()" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|73:8|{'status': 'HOLD', 'reason': 'MIGRATION_SOURCE_VERSION_MISSING', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|72:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|75:4|not isinstance(witness.target_version, str) or not witness.target_version.strip()" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|76:8|{'status': 'HOLD', 'reason': 'MIGRATION_TARGET_VERSION_MISSING', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|75:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|78:4|witness.source_version == witness.target_version" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|79:8|{'status': 'FAIL', 'reason': 'MIGRATION_VERSIONS_NOT_DISTINCT', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|78:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|81:4|not isinstance(witness.invariant_id, str) or not witness.invariant_id.strip()" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|82:8|{'status': 'HOLD', 'reason': 'MIGRATION_INVARIANT_UNBOUND', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|81:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|84:4|witness.proof_status != 'VERIFIED'" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|85:8|{'status': 'HOLD', 'reason': 'MIGRATION_PROOF_NOT_VERIFIED', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|84:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|87:4|not isinstance(witness.producer_identity, str) or not witness.producer_identity.strip() or (not isinstance(witness.verifier_identity, str)) or (not witness.verifier_identity.strip()) or (witness.producer_identity == witness.verifier_identity)" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|94:8|{'status': 'HOLD', 'reason': 'MIGRATION_REQUIRES_INDEPENDENT_VERIFIER', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|87:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|96:4|hashlib.sha256(source_artifact).hexdigest() != witness.source_artifact_sha256" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|97:8|{'status': 'FAIL', 'reason': 'MIGRATION_SOURCE_ARTIFACT_MISMATCH', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|96:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|99:4|hashlib.sha256(target_artifact).hexdigest() != witness.target_artifact_sha256" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|100:8|{'status': 'FAIL', 'reason': 'MIGRATION_TARGET_ARTIFACT_MISMATCH', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|99:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|102:4|source_invariant_holds is not True" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|103:8|{'status': 'HOLD', 'reason': 'MIGRATION_SOURCE_INVARIANT_NOT_ESTABLISHED', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|102:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|IF|105:4|target_invariant_holds is not True" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|106:8|{'status': 'FAIL', 'reason': 'MIGRATION_TARGET_INVARIANT_FAILED', 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_IF|105:4|" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|RETURN|109:4|{'status': 'PASS_FOR_DECLARED_INVARIANT', 'reason': None, 'source_version': witness.source_version, 'target_version': witness.target_version, 'source_artifact_sha256': witness.source_artifact_sha256, 'target_artifact_sha256': witness.target_artifact_sha256, 'invariant_id': witness.invariant_id, 'invariant_proof_sha256': witness.invariant_proof_sha256, 'rollback_artifact_sha256': witness.rollback_artifact_sha256, 'invariant_witness_validated': True, 'universal_migration_refinement_proven': False, 'certification_propagation': False, 'authority_transfer': False}" ∷
  "custoszv9/crfu/migration.py|validate_migration_witness|END_FUNCTION|123:5|" ∷
  "custoszv9/crfu/model.py|canonical_json|FUNCTION|9:0|" ∷
  "custoszv9/crfu/model.py|canonical_json|RETURN|9:35|json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))" ∷
  "custoszv9/crfu/model.py|canonical_json|END_FUNCTION|9:114|" ∷
  "custoszv9/crfu/model.py|sha256_bytes|FUNCTION|10:0|" ∷
  "custoszv9/crfu/model.py|sha256_bytes|RETURN|10:34|hashlib.sha256(data).hexdigest()" ∷
  "custoszv9/crfu/model.py|sha256_bytes|END_FUNCTION|10:73|" ∷
  "custoszv9/crfu/model.py|is_sha256|FUNCTION|11:0|" ∷
  "custoszv9/crfu/model.py|is_sha256|RETURN|11:31|isinstance(value, str) and SHA256_RE.fullmatch(value) is not None" ∷
  "custoszv9/crfu/model.py|is_sha256|END_FUNCTION|11:102|" ∷
  "custoszv9/crfu/model.py|valid_utc|FUNCTION|12:0|" ∷
  "custoszv9/crfu/model.py|valid_utc|IF|13:1|not isinstance(value, str) or not value.strip()" ∷
  "custoszv9/crfu/model.py|valid_utc|RETURN|13:51|False" ∷
  "custoszv9/crfu/model.py|valid_utc|END_IF|13:1|" ∷
  "custoszv9/crfu/model.py|valid_utc|TRY|14:1|" ∷
  "custoszv9/crfu/model.py|valid_utc|RETURN|14:5|datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None" ∷
  "custoszv9/crfu/model.py|valid_utc|EXCEPT|15:1|ValueError" ∷
  "custoszv9/crfu/model.py|valid_utc|RETURN|15:19|False" ∷
  "custoszv9/crfu/model.py|valid_utc|END_TRY|14:1|" ∷
  "custoszv9/crfu/model.py|valid_utc|END_FUNCTION|15:31|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|FUNCTION|20:1|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|IF|21:2|not isinstance(value, dict)" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|RETURN|21:32|(None, ['TASK_CONTRACT_NOT_OBJECT'])" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_IF|21:2|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|FOR|23:2|k in ('task_id', 'mission_id', 'project_id', 'source_identity', 'target_identity', 'authorized_scope', 'validation_strategy', 'rollback_strategy', 'completion_condition', 'escalation_condition')" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|IF|24:3|not isinstance(value.get(k), str) or not value[k].strip()" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_IF|24:3|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_FOR|23:2|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|IF|25:2|not is_sha256(value.get('source_state_hash'))" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_IF|25:2|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|FOR|26:2|k in ('dependency_set', 'required_capabilities', 'inputs', 'preconditions', 'permitted_effects', 'acceptance_criteria', 'expected_outputs', 'evidence_requirements')" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|IF|27:3|not isinstance(value.get(k), (list, dict))" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_IF|27:3|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_FOR|26:2|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|FOR|28:2|(k, m) in (('maximum_planning_budget', 1), ('maximum_retry_budget', 0))" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|IF|30:3|isinstance(n, bool) or not isinstance(n, int) or n < m" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_IF|30:3|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_FOR|28:2|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|IF|32:2|not isinstance(b, dict)" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|ELSE|33:2|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|IF|33:2|any((isinstance(b.get(k), bool) or not isinstance(b.get(k), int) or b[k] < 0 for k in ('ram_required_bytes', 'ram_reserved_bytes', 'disk_required_bytes', 'max_concurrency')))" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_IF|33:2|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_IF|32:2|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|IF|34:2|not valid_utc(value.get('execution_deadline'))" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_IF|34:2|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|IF|35:2|issues" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|RETURN|35:12|(None, issues)" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_IF|35:2|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|IF|37:2|not value.get('authorization_evidence_reference')" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_IF|37:2|" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|RETURN|38:2|(cls(dict(value)), issues)" ∷
  "custoszv9/crfu/model.py|TaskContract.validate|END_FUNCTION|38:32|" ∷
  "custoszv9/crfu/model.py|TaskContract.task_id|FUNCTION|40:1|" ∷
  "custoszv9/crfu/model.py|TaskContract.task_id|RETURN|40:24|str(self.value['task_id'])" ∷
  "custoszv9/crfu/model.py|TaskContract.task_id|END_FUNCTION|40:57|" ∷
  "custoszv9/crfu/model.py|TaskContract.source_state_hash|FUNCTION|42:1|" ∷
  "custoszv9/crfu/model.py|TaskContract.source_state_hash|RETURN|44:2|str(self.value['source_state_hash'])" ∷
  "custoszv9/crfu/model.py|TaskContract.source_state_hash|END_FUNCTION|44:45|" ∷
  "custoszv9/crfu/planner.py|ActionSpec.from_dict|FUNCTION|12:1|" ∷
  "custoszv9/crfu/planner.py|ActionSpec.from_dict|IF|13:2|not isinstance(v, dict) or not isinstance(v.get('action_id'), str) or (not v['action_id'].strip())" ∷
  "custoszv9/crfu/planner.py|ActionSpec.from_dict|RAISE|13:100|ValueError('ACTION_ID_REQUIRED')" ∷
  "custoszv9/crfu/planner.py|ActionSpec.from_dict|END_IF|13:2|" ∷
  "custoszv9/crfu/planner.py|ActionSpec.from_dict|IF|15:2|idem not in {'READ_ONLY', 'IDEMPOTENT', 'NON_IDEMPOTENT', 'UNKNOWN'}" ∷
  "custoszv9/crfu/planner.py|ActionSpec.from_dict|RAISE|15:71|ValueError('IDEMPOTENCY_CLASS_INVALID')" ∷
  "custoszv9/crfu/planner.py|ActionSpec.from_dict|END_IF|15:2|" ∷
  "custoszv9/crfu/planner.py|ActionSpec.from_dict|RETURN|16:2|cls(v['action_id'], tuple(v.get('dependencies', ())), tuple(v.get('required_capabilities', ())), tuple(v.get('permitted_effects', ())), idem)" ∷
  "custoszv9/crfu/planner.py|ActionSpec.from_dict|END_FUNCTION|16:143|" ∷
  "custoszv9/crfu/planner.py|build_plan|FUNCTION|17:0|" ∷
  "custoszv9/crfu/planner.py|build_plan|IF|18:1|isinstance(max_alternatives, bool) or max_alternatives < 1" ∷
  "custoszv9/crfu/planner.py|build_plan|RETURN|18:60|{'status': 'DENIED', 'reason': 'PLANNING_BUDGET_INVALID', 'ordered_actions': []}" ∷
  "custoszv9/crfu/planner.py|build_plan|END_IF|18:1|" ∷
  "custoszv9/crfu/planner.py|build_plan|IF|20:1|len(rows) > max_alternatives" ∷
  "custoszv9/crfu/planner.py|build_plan|RETURN|20:31|{'status': 'HOLD', 'reason': 'ALTERNATIVE_BUDGET_EXCEEDED', 'ordered_actions': [], 'actions_seen': len(rows), 'max_alternatives': max_alternatives}" ∷
  "custoszv9/crfu/planner.py|build_plan|END_IF|20:1|" ∷
  "custoszv9/crfu/planner.py|build_plan|FOR|22:1|row in rows" ∷
  "custoszv9/crfu/planner.py|build_plan|IF|23:2|row.action_id in by" ∷
  "custoszv9/crfu/planner.py|build_plan|RETURN|23:25|{'status': 'DENIED', 'reason': 'DUPLICATE_ACTION_ID:' + row.action_id, 'ordered_actions': []}" ∷
  "custoszv9/crfu/planner.py|build_plan|END_IF|23:2|" ∷
  "custoszv9/crfu/planner.py|build_plan|END_FOR|22:1|" ∷
  "custoszv9/crfu/planner.py|build_plan|IF|26:1|missing" ∷
  "custoszv9/crfu/planner.py|build_plan|RETURN|26:12|{'status': 'HOLD', 'reason': 'DEPENDENCY_UNRESOLVED', 'missing_dependencies': missing, 'ordered_actions': []}" ∷
  "custoszv9/crfu/planner.py|build_plan|END_IF|26:1|" ∷
  "custoszv9/crfu/planner.py|build_plan|FOR|27:1|row in rows" ∷
  "custoszv9/crfu/planner.py|build_plan|IF|29:2|caps or effects" ∷
  "custoszv9/crfu/planner.py|build_plan|RETURN|29:21|{'status': 'DENIED', 'reason': 'ACTION_NOT_ADMISSIBLE', 'action_id': row.action_id, 'missing_capabilities': caps, 'forbidden_effects': effects, 'ordered_actions': []}" ∷
  "custoszv9/crfu/planner.py|build_plan|END_IF|29:2|" ∷
  "custoszv9/crfu/planner.py|build_plan|END_FOR|27:1|" ∷
  "custoszv9/crfu/planner.py|build_plan|WHILE|31:1|ready" ∷
  "custoszv9/crfu/planner.py|build_plan|FOR|33:2|key in sorted(incoming)" ∷
  "custoszv9/crfu/planner.py|build_plan|IF|34:3|cur in incoming[key]" ∷
  "custoszv9/crfu/planner.py|build_plan|IF|36:4|not incoming[key] and key not in ordered and (key not in ready)" ∷
  "custoszv9/crfu/planner.py|build_plan|END_IF|36:4|" ∷
  "custoszv9/crfu/planner.py|build_plan|END_IF|34:3|" ∷
  "custoszv9/crfu/planner.py|build_plan|END_FOR|33:2|" ∷
  "custoszv9/crfu/planner.py|build_plan|END_WHILE|31:1|" ∷
  "custoszv9/crfu/planner.py|build_plan|IF|38:1|len(ordered) != len(rows)" ∷
  "custoszv9/crfu/planner.py|build_plan|RETURN|38:28|{'status': 'DENIED', 'reason': 'DEPENDENCY_CYCLE', 'ordered_actions': [], 'cyclic_actions': sorted((k for k, d in incoming.items() if d))}" ∷
  "custoszv9/crfu/planner.py|build_plan|END_IF|38:1|" ∷
  "custoszv9/crfu/planner.py|build_plan|RETURN|39:1|{'status': 'PLAN_VALIDATED', 'ordered_actions': ordered, 'actions': [asdict(by[k]) for k in ordered], 'execution_authorized': False, 'global_optimum_claimed': False}" ∷
  "custoszv9/crfu/planner.py|build_plan|END_FUNCTION|39:164|" ∷
  "custoszv9/crfu/puac2.py|_time|FUNCTION|13:0|" ∷
  "custoszv9/crfu/puac2.py|_time|IF|14:1|not isinstance(value, str) or not value.strip()" ∷
  "custoszv9/crfu/puac2.py|_time|RETURN|14:51|None" ∷
  "custoszv9/crfu/puac2.py|_time|END_IF|14:1|" ∷
  "custoszv9/crfu/puac2.py|_time|TRY|15:1|" ∷
  "custoszv9/crfu/puac2.py|_time|RETURN|17:2|dt if dt.tzinfo is not None else None" ∷
  "custoszv9/crfu/puac2.py|_time|EXCEPT|18:1|ValueError" ∷
  "custoszv9/crfu/puac2.py|_time|RETURN|18:19|None" ∷
  "custoszv9/crfu/puac2.py|_time|END_TRY|15:1|" ∷
  "custoszv9/crfu/puac2.py|_time|END_FUNCTION|18:30|" ∷
  "custoszv9/crfu/puac2.py|_interval|FUNCTION|19:0|" ∷
  "custoszv9/crfu/puac2.py|_interval|IF|21:1|not isinstance(value, dict)" ∷
  "custoszv9/crfu/puac2.py|_interval|RETURN|21:31|['VALIDITY_INTERVAL_NOT_TYPED_OBJECT']" ∷
  "custoszv9/crfu/puac2.py|_interval|END_IF|21:1|" ∷
  "custoszv9/crfu/puac2.py|_interval|IF|23:1|start is None" ∷
  "custoszv9/crfu/puac2.py|_interval|END_IF|23:1|" ∷
  "custoszv9/crfu/puac2.py|_interval|IF|24:1|end is None" ∷
  "custoszv9/crfu/puac2.py|_interval|END_IF|24:1|" ∷
  "custoszv9/crfu/puac2.py|_interval|IF|25:1|start and end and (start >= end)" ∷
  "custoszv9/crfu/puac2.py|_interval|END_IF|25:1|" ∷
  "custoszv9/crfu/puac2.py|_interval|IF|27:1|start and now < start" ∷
  "custoszv9/crfu/puac2.py|_interval|END_IF|27:1|" ∷
  "custoszv9/crfu/puac2.py|_interval|IF|28:1|end and now >= end" ∷
  "custoszv9/crfu/puac2.py|_interval|END_IF|28:1|" ∷
  "custoszv9/crfu/puac2.py|_interval|RETURN|29:1|errors" ∷
  "custoszv9/crfu/puac2.py|_interval|END_FUNCTION|29:14|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|FUNCTION|31:0|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|32:1|not isinstance(claim, dict)" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|32:31|{'status': 'DENY', 'reasons': ['CLAIM_NOT_OBJECT']}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|32:1|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|FOR|35:1|field in ('claim_id', 'subject_id', 'property_id', 'scope_id', 'context_id', 'version')" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|36:2|field in claim and (not isinstance(claim[field], str) or not claim[field].strip())" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|36:2|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_FOR|35:1|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|38:1|missing" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|38:12|{'status': 'HOLD', 'reasons': ['CLAIM_FIELDS_MISSING:' + ','.join(missing)]}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|38:1|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|41:1|isinstance(unit, dict)" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|42:2|not unit.get('unit_id') or not unit.get('dimension') or (not unit.get('version'))" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|42:2|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|43:2|unit.get('dimension') == 'dimensionless' and (not unit.get('dimensionless_declared', False))" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|43:2|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|ELSE|44:1|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|44:1|unit == 'dimensionless'" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|ELSE|46:6|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|44:1|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|41:1|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|48:1|interval_errors" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|48:20|{'status': 'HOLD', 'reasons': interval_errors, 'semantic_key': key}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|48:1|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|49:1|unit_errors" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|49:16|{'status': 'HOLD', 'reasons': unit_errors, 'semantic_key': key}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|49:1|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|50:1|claim.get('evidence_state') not in EVIDENCE_STATES" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|51:2|{'status': 'HOLD', 'reasons': ['CLAIM_EVIDENCE_STATE_INVALID_OR_MISSING'], 'semantic_key': key}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|50:1|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|52:1|claim.get('not_applicable') is True and (not str(claim.get('not_applicable_basis', '')).strip())" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|53:2|{'status': 'HOLD', 'reasons': ['NOT_APPLICABLE_REQUIRES_BASIS'], 'semantic_key': key}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|52:1|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|55:1|conversion is not None" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|58:2|absent" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|58:12|{'status': 'HOLD', 'reasons': ['CONVERSION_EVIDENCE_MISSING:' + ','.join(absent)], 'semantic_key': key}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|58:2|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|60:2|not isinstance(source_unit, dict) or not isinstance(target_unit, dict)" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|61:3|{'status': 'HOLD', 'reasons': ['CONVERSION_UNITS_NOT_TYPED'], 'semantic_key': key}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|60:2|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|FOR|62:2|(label, unit_record) in (('SOURCE', source_unit), ('TARGET', target_unit))" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|63:3|not all((isinstance(unit_record.get(field), str) and unit_record[field].strip() for field in ('unit_id', 'dimension', 'version')))" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|64:4|{'status': 'HOLD', 'reasons': [f'CONVERSION_{label}_UNIT_ID_DIMENSION_VERSION_REQUIRED'], 'semantic_key': key}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|63:3|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_FOR|62:2|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|65:2|source_unit.get('dimension') != target_unit.get('dimension')" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|66:3|{'status': 'DENY', 'reasons': ['CONVERSION_DIMENSION_MISMATCH'], 'semantic_key': key}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|65:2|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|IF|67:2|'original_value' in claim and conversion.get('original_value') != claim.get('original_value')" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|68:3|{'status': 'DENY', 'reasons': ['CONVERSION_DID_NOT_PRESERVE_ORIGINAL_VALUE'], 'semantic_key': key}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|67:2|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_IF|55:1|" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|RETURN|69:1|{'status': 'PASS_SCHEMA_ONLY', 'reasons': [], 'claim_id': claim['claim_id'], 'semantic_key': key, 'evidence_state': claim['evidence_state'], 'claim_truth_asserted': False, 'claim_id_is_record_identity_not_semantic_key': True, 'unit_of_measure': unit}" ∷
  "custoszv9/crfu/puac2.py|validate_claim_v2|END_FUNCTION|71:84|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|FUNCTION|72:0|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|IF|73:1|not isinstance(claims, list) or not claims" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|RETURN|74:2|{'status': 'HOLD', 'errors': ['CLAIM_SET_EMPTY_OR_INVALID'], 'conflicts': [], 'claims_checked': 0, 'claim_truth_asserted': False, 'direct_contradiction_requires_same_semantic_key': True}" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_IF|73:1|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|FOR|77:1|claim in claims" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|IF|79:2|result['status'] != 'PASS_SCHEMA_ONLY'" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_IF|79:2|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|IF|81:2|claim_id in by_id" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_IF|81:2|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|IF|84:2|state == 'UNKNOWN'" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|ELSE|85:2|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|IF|85:2|state == 'REFUTED'" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|ELSE|86:2|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|IF|86:2|state == 'CONFLICT'" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_IF|86:2|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_IF|85:2|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_IF|84:2|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|IF|88:2|previous is not None and (previous.get('value') != claim.get('value') or previous.get('evidence_state') != state)" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|ELSE|90:7|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_IF|88:2|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_FOR|77:1|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|IF|91:1|errors" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|ELSE|92:1|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|IF|92:1|conflicts or declared_conflicts" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|ELSE|93:1|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|IF|93:1|unknown" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|ELSE|94:1|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|IF|94:1|refuted" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|ELSE|95:6|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_IF|94:1|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_IF|93:1|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_IF|92:1|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_IF|91:1|" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|RETURN|96:1|{'status': status, 'errors': errors, 'conflicts': conflicts, 'unknown_claim_ids': unknown, 'refuted_claim_ids': refuted, 'declared_conflict_claim_ids': declared_conflicts, 'claims_checked': len(claims), 'claim_truth_asserted': False, 'direct_contradiction_requires_same_semantic_key': True}" ∷
  "custoszv9/crfu/puac2.py|classify_claim_conflicts|END_FUNCTION|99:64|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|FUNCTION|101:0|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|102:1|not isinstance(events, list) or not events" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|RETURN|102:46|{'status': 'HOLD', 'reasons': ['EVENT_RECORD_SET_EMPTY_OR_INVALID']}" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|102:1|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|FOR|105:1|e in events" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|106:2|not isinstance(e, dict)" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|106:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|108:2|missing" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|108:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|110:2|not isinstance(eid, str) or not eid.strip()" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|110:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|111:2|eid in index" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|111:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|FOR|113:2|k in ('event_time_utc', 'observed_at_utc', 'recorded_at_utc')" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|114:3|_time(e.get(k)) is None" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|114:3|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_FOR|113:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|116:2|isinstance(n, bool) or not isinstance(n, int) or n < 1" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|ELSE|117:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|117:2|n in seqs" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|ELSE|118:7|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|117:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|116:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|119:2|not isinstance(e.get('causal_parents'), list)" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|ELSE|120:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|120:2|any((not isinstance(p, str) or not p.strip() for p in e['causal_parents']))" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|120:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|119:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_FOR|105:1|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|121:1|holds or errors" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|RETURN|121:20|{'status': 'HOLD' if holds and (not errors) else 'FAIL', 'reasons': holds + errors, 'event_count': len(index)}" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|121:1|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|FOR|122:1|(eid, e) in index.items()" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|FOR|123:2|parent in e['causal_parents']" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|124:3|parent not in index" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|124:3|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|125:3|parent == eid" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|125:3|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_FOR|123:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_FOR|122:1|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|FOR|134:1|eid in graph" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|135:2|not visit(eid)" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|135:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_FOR|134:1|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|136:1|errors" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|RETURN|136:11|{'status': 'FAIL', 'reasons': sorted(set(errors)), 'event_count': len(index)}" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|136:1|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|IF|137:1|holds" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|RETURN|137:10|{'status': 'HOLD', 'reasons': sorted(set(holds)), 'event_count': len(index)}" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_IF|137:1|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|RETURN|138:1|{'status': 'PASS', 'reasons': [], 'event_count': len(index), 'causal_graph_acyclic': True, 'event_time_observed_time_recorded_time_distinguished': True, 'time_order_alone_not_used_as_causality': True}" ∷
  "custoszv9/crfu/puac2.py|validate_event_records|END_FUNCTION|140:55|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|FUNCTION|127:1|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|IF|128:2|eid in visiting" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|RETURN|128:21|False" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|END_IF|128:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|IF|129:2|eid in visited" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|RETURN|129:20|True" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|END_IF|129:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|FOR|131:2|parent in graph[eid]" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|IF|132:3|parent in graph and (not visit(parent))" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|RETURN|132:44|False" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|END_IF|132:3|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|END_FOR|131:2|" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|RETURN|133:40|True" ∷
  "custoszv9/crfu/puac2.py|validate_event_records.visit|END_FUNCTION|133:51|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|FUNCTION|144:0|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|IF|147:1|not isinstance(binding, dict)" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|RETURN|147:33|{'status': 'DENY', 'reason': 'AUTHORITY_BINDING_NOT_OBJECT'}" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|END_IF|147:1|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|IF|149:1|missing" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|RETURN|149:12|{'status': 'DENY', 'reason': 'AUTHORITY_BINDING_FIELDS_MISSING', 'fields': missing}" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|END_IF|149:1|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|IF|150:1|binding.get('action') != action or binding.get('object_id') != object_id or binding.get('scope_id') != scope_id" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|RETURN|151:2|{'status': 'DENY', 'reason': 'ACTION_OBJECT_OR_SCOPE_MISMATCH'}" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|END_IF|150:1|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|IF|152:1|not isinstance(binding.get('delegation_chain'), list)" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|RETURN|152:57|{'status': 'DENY', 'reason': 'DELEGATION_CHAIN_INVALID'}" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|END_IF|152:1|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|IF|153:1|binding.get('revocation_state') != 'NOT_REVOKED'" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|RETURN|153:51|{'status': 'DENY', 'reason': 'AUTHORITY_REVOKED_OR_UNKNOWN'}" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|END_IF|153:1|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|IF|155:1|interval" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|RETURN|155:13|{'status': 'DENY', 'reason': 'AUTHORITY_VALIDITY_NOT_PROVEN', 'details': interval}" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|END_IF|155:1|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|IF|156:1|binding.get('signature_required') is True and (not binding.get('signature_if_required'))" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|RETURN|157:2|{'status': 'DENY', 'reason': 'REQUIRED_SIGNATURE_MISSING'}" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|END_IF|156:1|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|IF|158:1|trust_verifier is None" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|RETURN|158:27|{'status': 'DENY', 'reason': 'TRUSTED_IDENTITY_AND_DELEGATION_VERIFIER_UNAVAILABLE'}" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|END_IF|158:1|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|IF|160:1|not isinstance(verified, dict) or verified.get('status') != 'PASS' or verified.get('binding_id') != binding['binding_id']" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|RETURN|161:2|{'status': 'DENY', 'reason': 'IDENTITY_DELEGATION_OR_ISSUER_PROOF_NOT_VERIFIED'}" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|END_IF|160:1|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|IF|165:1|missing_attestations" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|RETURN|165:25|{'status': 'DENY', 'reason': 'AUTHORITY_VERIFICATION_ATTESTATIONS_INCOMPLETE', 'missing_attestations': missing_attestations}" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|END_IF|165:1|" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|RETURN|167:1|{'status': 'PASS', 'binding_id': binding['binding_id'], 'action': action, 'object_id': object_id, 'scope_id': scope_id, 'actor_id': binding['actor_id'], 'authorization_grant': True, 'provenance_id': binding['provenance_id']}" ∷
  "custoszv9/crfu/puac2.py|validate_authority_binding|END_FUNCTION|168:108|" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|FUNCTION|172:0|" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|IF|173:1|not isinstance(plan, dict)" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|RETURN|173:30|{'status': 'HOLD', 'reasons': ['RECOVERY_PLAN_NOT_OBJECT']}" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|END_IF|173:1|" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|IF|176:1|not is_sha256(plan.get('checkpoint_hash'))" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|END_IF|176:1|" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|FOR|177:1|k in ('dependency_hashes', 'restoration_oracles', 'irreversible_side_effects')" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|IF|178:2|not isinstance(plan.get(k), list)" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|ELSE|179:2|" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|IF|179:2|k == 'dependency_hashes' and any((not is_sha256(h) for h in plan[k]))" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|END_IF|179:2|" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|END_IF|178:2|" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|END_FOR|177:1|" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|FOR|180:1|k in ('incident_id', 'authorized_actor', 'checkpoint_id', 'target_environment', 'nonregression_plan', 'rollback_scope', 'authority_ref')" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|IF|181:2|not isinstance(plan.get(k), str) or not plan[k].strip()" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|END_IF|181:2|" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|END_FOR|180:1|" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|RETURN|182:1|{'status': 'HOLD' if missing else 'FAIL' if errors else 'PASS_SCHEMA_ONLY', 'reasons': (['RECOVERY_FIELDS_MISSING:' + ','.join(missing)] if missing else []) + errors, 'reversibility_proven': False, 'execution_or_restoration_not_inferred_from_plan': True}" ∷
  "custoszv9/crfu/puac2.py|validate_recovery_plan|END_FUNCTION|184:93|" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|FUNCTION|185:0|" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|IF|188:1|not isinstance(evidence, dict)" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|RETURN|188:34|{'status': 'HOLD', 'reasons': ['INCIDENT_EVIDENCE_NOT_OBJECT'], 'incident_closed': False, 'activation_authorized': False}" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|END_IF|188:1|" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|IF|191:1|missing" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|RETURN|191:12|{'status': 'HOLD', 'reasons': ['INCIDENT_CLOSURE_EVIDENCE_MISSING:' + ','.join(missing)], 'incident_closed': False, 'activation_authorized': False, 'reactivation_requires_separate_authorization_controller': True}" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|END_IF|191:1|" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|FOR|195:1|key in ('diagnosis_verified', 'correction_authorized', 'correction_executed', 'restoration_verified', 'nonregression_verified', 'traceability_complete')" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|IF|197:2|evidence.get(key) is not True" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|END_IF|197:2|" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|END_FOR|195:1|" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|IF|198:1|not isinstance(evidence.get('g23_g24_required'), bool) or not isinstance(evidence.get('g23_g24_pass'), bool)" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|ELSE|200:1|" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|IF|200:1|evidence.get('g23_g24_required') is True and evidence.get('g23_g24_pass') is not True" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|END_IF|200:1|" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|END_IF|198:1|" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|RETURN|203:1|{'status': 'PASS' if closed else 'BLOCKED', 'reasons': failures, 'incident_closed': closed, 'activation_authorized': False, 'reactivation_authorization_evidence_present': evidence.get('new_operational_authorization') is True, 'reactivation_requires_separate_authorization_controller': True, 'certification_propagation': False}" ∷
  "custoszv9/crfu/puac2.py|evaluate_incident_closure|END_FUNCTION|206:106|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|FUNCTION|208:0|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|211:1|not is_sha256(target_sha256)" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|212:2|{'status': 'HOLD', 'reason': 'EXACT_TARGET_ARTIFACT_SHA256_REQUIRED', **base}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|211:1|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|213:1|required_test_classes != 28 or required_invariants != 16" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|214:2|{'status': 'HOLD', 'reason': 'CANONICAL_COVERAGE_CARDINALITY_OVERRIDE_FORBIDDEN', 'required_test_classes': 28, 'required_invariants': 16, **base}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|213:1|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|216:1|not isinstance(requirements, list) or not requirements" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|217:2|{'status': 'HOLD', 'reason': 'CRITICAL_REQUIREMENT_SET_EMPTY_OR_UNKNOWN', **base}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|216:1|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|FOR|219:1|row in requirements" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|220:2|not isinstance(row, dict) or not isinstance(row.get('requirement_id'), str) or (not row['requirement_id'].strip())" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|221:3|{'status': 'HOLD', 'reason': 'REQUIREMENT_ID_INVALID', **base}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|220:2|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_FOR|219:1|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|223:1|len(set(ids)) != len(ids)" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|224:2|{'status': 'FAIL', 'reason': 'DUPLICATE_REQUIREMENT_ID', 'duplicate_ids': sorted({x for x in ids if ids.count(x) > 1}), **base}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|223:1|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|226:1|not isinstance(documented_requirement_ids, (list, set, tuple))" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|227:2|{'status': 'HOLD', 'reason': 'DOCUMENTED_REQUIREMENT_IDS_INVALID', **base}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|226:1|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|229:1|any((not isinstance(x, str) or not x.strip() for x in documented_raw))" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|230:2|{'status': 'HOLD', 'reason': 'DOCUMENTED_REQUIREMENT_ID_INVALID', **base}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|229:1|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|232:1|not isinstance(operational_evidence, list)" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|233:2|{'status': 'HOLD', 'reason': 'OPERATIONAL_EVIDENCE_NOT_LIST', **base}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|232:1|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|FOR|236:1|(index, evidence) in enumerate(operational_evidence)" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|237:2|not isinstance(evidence, dict)" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|238:3|{'status': 'FAIL', 'reason': 'MALFORMED_OPERATIONAL_EVIDENCE_RECORD', 'record_index': index, **base}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|237:2|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|239:2|evidence.get('status') != 'PASS'" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|239:2|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|240:2|evidence.get('reference_only') is True" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|240:2|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|242:2|evidence.get('target_sha256') != target_sha256" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|242:2|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|247:2|isinstance(rid, str) and rid in required_ids" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|247:2|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|250:2|record_type == 'TEST_CLASS'" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|251:3|not isinstance(ident, str) or ident not in {f'T{i:02d}' for i in range(1, 29)}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|ELSE|253:8|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|251:3|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|250:2|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|255:2|record_type == 'INVARIANT'" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|256:3|not isinstance(ident, str) or ident not in {f'INV-{i:02d}' for i in range(1, 17)}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|ELSE|258:8|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|256:3|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|255:2|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_FOR|236:1|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|259:1|unknown_tests or unknown_invariants" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|260:2|{'status': 'FAIL', 'reason': 'UNREGISTERED_TEST_OR_INVARIANT_ID', 'unregistered_test_class_ids': sorted(set(unknown_tests)), 'unregistered_invariant_ids': sorted(set(unknown_invariants)), **base}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|259:1|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|IF|275:1|stale" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|276:2|{'status': 'HOLD', 'reason': 'STALE_OR_UNBOUND_OPERATIONAL_EVIDENCE', **metrics}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_IF|275:1|" ∷
  "custoszv9/crfu/puac2.py|coverage_report|RETURN|277:1|{'status': 'MEASURED', **metrics}" ∷
  "custoszv9/crfu/puac2.py|coverage_report|END_FUNCTION|277:39|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|FUNCTION|309:0|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|313:1|not isinstance(binding, dict)" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|RETURN|313:33|{'status': 'HOLD', 'reasons': ['CONTROL_EVIDENCE_BINDING_MISSING']}" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|313:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|317:1|missing" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|RETURN|317:12|{'status': 'HOLD', 'reasons': ['CONTROL_EVIDENCE_BINDING_FIELDS_MISSING:' + ','.join(missing)]}" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|317:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|319:1|binding.get('schema') != 'PUAC2_CONTROL_EVIDENCE_BINDING/1.0'" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|319:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|320:1|binding.get('control_id') != control_id" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|320:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|321:1|not is_sha256(binding.get('candidate_sha256'))" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|ELSE|322:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|322:1|candidate_sha256 and binding.get('candidate_sha256') != candidate_sha256" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|322:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|321:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|323:1|not isinstance(binding.get('candidate_commit_sha'), str) or re.fullmatch('[0-9a-f]{40}', binding['candidate_commit_sha']) is None" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|ELSE|325:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|325:1|candidate_commit_sha is None or binding.get('candidate_commit_sha') != candidate_commit_sha" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|325:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|323:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|327:1|not is_sha256(binding.get('payload_sha256'))" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|ELSE|329:2|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|331:2|observed != binding.get('payload_sha256')" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|331:2|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|327:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|332:1|not isinstance(binding.get('producer_identity'), str) or not binding['producer_identity'].strip()" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|ELSE|334:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|334:1|producer_identity is not None and binding['producer_identity'] != producer_identity" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|334:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|332:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|336:1|not isinstance(binding.get('evaluator_identity'), str) or not binding['evaluator_identity'].strip()" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|ELSE|338:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|338:1|binding['evaluator_identity'] == binding.get('producer_identity')" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|ELSE|340:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|340:1|evaluator_identity is not None and binding['evaluator_identity'] != evaluator_identity" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|340:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|338:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|336:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|342:1|_time(binding.get('generated_at_utc')) is None" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|342:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|343:1|not isinstance(binding.get('scope'), str) or not binding['scope'].strip()" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|343:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|345:1|not isinstance(refs, list) or not refs" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|ELSE|346:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|IF|346:1|any((not isinstance(item, dict) or not isinstance(item.get('sha256'), str) or (not is_sha256(item.get('sha256'))) or (not item.get('uri')) for item in refs))" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|346:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_IF|345:1|" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|RETURN|348:1|{'status': 'FAIL' if errors else 'PASS', 'reasons': sorted(set(errors)), 'candidate_sha256': binding.get('candidate_sha256'), 'candidate_commit_sha': binding.get('candidate_commit_sha'), 'payload_sha256': binding.get('payload_sha256')}" ∷
  "custoszv9/crfu/puac2.py|_validate_control_evidence_binding|END_FUNCTION|350:56|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|FUNCTION|352:0|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|353:1|control_id not in PUAC_CONTROL_OUTPUTS" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|RETURN|353:43|{'status': 'HOLD', 'reasons': ['CONTROL_ID_NOT_REGISTERED_LOCALLY']}" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|353:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|354:1|not isinstance(payload, dict)" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|RETURN|354:33|{'status': 'HOLD', 'reasons': ['CONTROL_EVIDENCE_PAYLOAD_MISSING']}" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|354:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|355:1|not is_sha256(candidate_sha256)" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|RETURN|356:2|{'status': 'HOLD', 'reasons': ['EXACT_CANDIDATE_DIGEST_REQUIRED'], 'control_id': control_id, 'canonical_admission': 'NOT_GRANTED'}" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|355:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|357:1|not isinstance(candidate_commit_sha, str) or re.fullmatch('[0-9a-f]{40}', candidate_commit_sha) is None" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|RETURN|358:2|{'status': 'HOLD', 'reasons': ['EXACT_CANDIDATE_COMMIT_REQUIRED'], 'control_id': control_id, 'canonical_admission': 'NOT_GRANTED'}" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|357:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|361:1|bound['status'] == 'HOLD'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|RETURN|361:28|{'status': 'HOLD', 'reasons': bound['reasons'], 'control_id': control_id, 'canonical_admission': 'NOT_GRANTED'}" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|361:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|362:1|bound['status'] != 'PASS'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|RETURN|362:28|{'status': 'FAIL', 'reasons': bound['reasons'], 'control_id': control_id, 'canonical_admission': 'NOT_GRANTED'}" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|362:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|FOR|365:1|flag in PUAC_CONTROL_TRUE_FLAGS[control_id]" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|366:2|flag not in payload" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|ELSE|367:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|367:2|payload[flag] is not True" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|367:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|366:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_FOR|365:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|FOR|368:1|flag in PUAC_CONTROL_FALSE_FLAGS[control_id]" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|369:2|flag not in payload" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|ELSE|370:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|370:2|payload[flag] is not False" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|370:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|369:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_FOR|368:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|371:1|control_id == 'PUAC.C26' and isinstance(payload.get('unresolved_claims'), list) and payload['unresolved_claims']" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|371:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|373:1|control_id == 'PUAC.C27'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|375:2|not evaluator or not producer or evaluator == producer" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|375:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|373:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|376:1|control_id == 'PUAC.C25'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|377:2|not isinstance(payload.get('claim_registry'), (list, dict))" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|377:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|378:2|not isinstance(payload.get('acceptance_criteria'), (list, dict))" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|378:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|380:2|not isinstance(scope_evidence, dict)" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|ELSE|381:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|381:2|candidate_sha256 and scope_evidence.get('package_sha256') != candidate_sha256" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|381:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|380:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|376:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|382:1|control_id == 'PUAC.C26'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|383:2|not isinstance(payload.get('unresolved_claims'), list)" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|ELSE|384:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|384:2|payload['unresolved_claims']" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|384:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|383:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|385:2|not payload.get('assurance_case')" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|385:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|386:2|not payload.get('argumentation_record')" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|386:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|382:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|387:1|control_id == 'PUAC.C27'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|388:2|not isinstance(payload.get('allowed_evaluators'), list) or not payload['allowed_evaluators']" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|388:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|389:2|not payload.get('separation_evidence')" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|389:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|391:2|not evaluator or not producer or evaluator == producer" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|391:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|387:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|392:1|control_id == 'PUAC.C28'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|393:2|not payload.get('threat_model') or not payload.get('risk_criteria')" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|393:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|394:2|not payload.get('residual_risk_record')" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|394:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|392:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|395:1|control_id == 'PUAC.C29'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|397:2|not isinstance(reproduction, dict) or reproduction.get('status') != 'PASS'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|397:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|399:2|not isinstance(identity, dict) or not is_sha256(identity.get('sha256'))" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|ELSE|400:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|400:2|candidate_sha256 and identity.get('sha256') != candidate_sha256" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|400:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|399:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|401:2|not payload.get('dependency_lock') or not payload.get('build_recipe') or (not payload.get('execution_environment'))" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|401:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|402:2|not payload.get('provenance_attestation') or not payload.get('supply_chain_evidence')" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|402:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|395:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|403:1|control_id == 'PUAC.C30'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|404:2|not isinstance(payload.get('dependency_graph'), dict) or not isinstance(payload.get('impact_graph'), dict)" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|404:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|406:2|not isinstance(build, dict)" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|ELSE|407:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|407:2|candidate_sha256 and build.get('package_sha256') != candidate_sha256" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|407:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|406:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|408:2|not isinstance(payload.get('revalidation_plan'), (dict, list))" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|408:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|403:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|409:1|control_id == 'PUAC.C31'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|411:2|not isinstance(restoration, dict) or restoration.get('restoration_proven') is not True" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|411:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|413:2|not isinstance(checkpoint, dict) or not is_sha256(checkpoint.get('sha256'))" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|ELSE|414:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|414:2|isinstance(restoration, dict) and restoration.get('checkpoint_sha256') != checkpoint.get('sha256')" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|414:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|413:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|416:2|not isinstance(rollback, dict) or rollback.get('status') != 'PASS'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|416:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|409:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|417:1|control_id == 'PUAC.C32'" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|419:2|not isinstance(profile, dict) or not profile" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|ELSE|420:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|420:2|not profile.get('responsible_roles')" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|420:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|419:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|421:2|not isinstance(payload.get('observations'), list) or not isinstance(payload.get('change_events'), list)" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|421:2|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|417:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|422:1|missing" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|RETURN|422:12|{'status': 'HOLD', 'reasons': sorted(set(errors + ['CONTROL_EVIDENCE_FIELDS_MISSING:' + ','.join(sorted(set(missing)))])), 'control_id': control_id, 'canonical_admission': 'NOT_GRANTED'}" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|422:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|IF|423:1|errors" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|RETURN|423:11|{'status': 'FAIL', 'reasons': sorted(set(errors)), 'control_id': control_id, 'canonical_admission': 'NOT_GRANTED'}" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_IF|423:1|" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|RETURN|424:1|{'status': 'PASS_FOR_LOCAL_CONTROL_SCOPE', 'reasons': [], 'control_id': control_id, 'canonical_admission': 'NOT_GRANTED', 'does_not_replace_G23_G24': True}" ∷
  "custoszv9/crfu/puac2.py|validate_puac_control|END_FUNCTION|425:41|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|FUNCTION|427:0|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|IF|429:1|not isinstance(dependency_graph, dict) or not isinstance(changed_nodes, (list, set, tuple)) or (not changed_nodes)" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|RETURN|430:2|{'status': 'HOLD', 'reason': 'DEPENDENCY_GRAPH_OR_CHANGED_SET_INVALID', 'impacted_nodes': []}" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_IF|429:1|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|FOR|432:1|(node, deps) in dependency_graph.items()" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|IF|433:2|not isinstance(node, str) or not node.strip() or (not isinstance(deps, list)) or any((not isinstance(d, str) or not d.strip() for d in deps))" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|RETURN|434:3|{'status': 'HOLD', 'reason': 'DEPENDENCY_EDGE_INVALID', 'node': str(node), 'impacted_nodes': []}" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_IF|433:2|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_FOR|432:1|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|IF|438:1|not changed.issubset(set(graph))" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|RETURN|439:2|{'status': 'HOLD', 'reason': 'CHANGED_NODE_UNREGISTERED', 'unknown_changed_nodes': sorted(changed - set(graph)), 'impacted_nodes': []}" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_IF|438:1|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|IF|440:1|unknown" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|RETURN|440:12|{'status': 'HOLD', 'reason': 'DEPENDENCY_NODE_UNRESOLVED', 'unknown_dependencies': unknown, 'impacted_nodes': []}" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_IF|440:1|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|FOR|449:1|node in graph" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|IF|450:2|not visit(node)" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|RETURN|450:21|{'status': 'FAIL', 'reason': 'DEPENDENCY_CYCLE', 'cycle_nodes': sorted(set(cycle)), 'impacted_nodes': []}" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_IF|450:2|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_FOR|449:1|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|FOR|452:1|(node, deps) in graph.items()" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|FOR|453:2|dep in deps" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_FOR|453:2|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_FOR|452:1|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|WHILE|455:1|frontier" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|FOR|457:2|dependent in reverse[current]" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|IF|458:3|dependent not in changed and dependent not in impacted" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_IF|458:3|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_FOR|457:2|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_WHILE|455:1|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|RETURN|460:1|{'status': 'PASS', 'changed_nodes': sorted(changed), 'impacted_nodes': sorted(impacted), 'dependency_graph_complete': True, 'transitive_closure': True}" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact|END_FUNCTION|461:68|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|FUNCTION|442:1|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|IF|443:2|node in visiting" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|RETURN|443:41|False" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|END_IF|443:2|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|IF|444:2|node in visited" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|RETURN|444:21|True" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|END_IF|444:2|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|FOR|446:2|dep in graph[node]" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|IF|447:3|not visit(dep)" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|RETURN|447:21|False" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|END_IF|447:3|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|END_FOR|446:2|" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|RETURN|448:42|True" ∷
  "custoszv9/crfu/puac2.py|transitive_dependency_impact.visit|END_FUNCTION|448:53|" ∷
  "custoszv9/crfu/recovery.py|checkpoint_record|FUNCTION|5:0|" ∷
  "custoszv9/crfu/recovery.py|checkpoint_record|IF|6:1|not checkpoint_id or not state_identity or (not is_sha256(dependency_fingerprint))" ∷
  "custoszv9/crfu/recovery.py|checkpoint_record|RAISE|6:85|ValueError('CHECKPOINT_IDENTITY_INVALID')" ∷
  "custoszv9/crfu/recovery.py|checkpoint_record|END_IF|6:1|" ∷
  "custoszv9/crfu/recovery.py|checkpoint_record|RETURN|7:1|{'checkpoint_id': checkpoint_id, 'state_identity': state_identity, 'dependency_fingerprint': dependency_fingerprint, 'payload_sha256': hashlib.sha256(payload).hexdigest(), 'payload_size_bytes': len(payload), 'restoration_proven': False, 'status': 'CHECKPOINT_CAPTURED_NOT_RESTORED'}" ∷
  "custoszv9/crfu/recovery.py|checkpoint_record|END_FUNCTION|7:277|" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|FUNCTION|8:0|" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|IF|10:1|hashlib.sha256(restored_payload).hexdigest() != record.get('payload_sha256') or len(restored_payload) != record.get('payload_size_bytes')" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|END_IF|10:1|" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|IF|11:1|expected_state_identity != record.get('state_identity')" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|END_IF|11:1|" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|IF|12:1|expected_dependency_fingerprint != record.get('dependency_fingerprint')" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|END_IF|12:1|" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|IF|13:1|invariants_pass is not True" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|END_IF|13:1|" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|IF|14:1|journal_valid is not True" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|END_IF|14:1|" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|RETURN|15:1|{'status': 'PASS' if not fail else 'BLOCKED', 'failures': fail, 'restoration_proven': not fail, 'certification_propagation': False}" ∷
  "custoszv9/crfu/recovery.py|verify_restoration|END_FUNCTION|15:132|" ∷
  "custoszv9/crfu/resources.py|ResourceSnapshot.to_dict|FUNCTION|19:4|" ∷
  "custoszv9/crfu/resources.py|ResourceSnapshot.to_dict|RETURN|20:8|asdict(self)" ∷
  "custoszv9/crfu/resources.py|ResourceSnapshot.to_dict|END_FUNCTION|20:27|" ∷
  "custoszv9/crfu/resources.py|_nonnegative_int|FUNCTION|31:0|" ∷
  "custoszv9/crfu/resources.py|_nonnegative_int|RETURN|32:4|isinstance(value, int) and (not isinstance(value, bool)) and (value >= 0)" ∷
  "custoszv9/crfu/resources.py|_nonnegative_int|END_FUNCTION|32:80|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|FUNCTION|35:0|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|IF|39:4|os.name == 'posix'" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|TRY|40:8|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|IF|43:12|pages >= 0 and page_size > 0" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_IF|43:12|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|EXCEPT|46:8|(OSError, ValueError, KeyError)" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_TRY|40:8|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_IF|39:4|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|IF|48:4|available_ram is None and os.name == 'nt'" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|TRY|49:8|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|IF|67:12|ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_IF|67:12|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|EXCEPT|70:8|(AttributeError, OSError, TypeError)" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_TRY|49:8|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_IF|48:4|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|IF|72:4|available_ram is None" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|TRY|73:8|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|FOR|74:12|line in Path('/proc/meminfo').read_text(encoding='ascii').splitlines()" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|IF|75:16|line.startswith('MemAvailable:')" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_IF|75:16|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_FOR|74:12|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|EXCEPT|79:8|(OSError, ValueError, IndexError)" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_TRY|73:8|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_IF|72:4|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|TRY|81:4|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|EXCEPT|83:4|(OSError, ValueError)" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_TRY|81:4|" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|RETURN|91:4|ResourceSnapshot(available_ram, disk_free, cpu, datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'), source, confidence)" ∷
  "custoszv9/crfu/resources.py|probe_host_resources|END_FUNCTION|98:5|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|FUNCTION|101:0|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|FOR|104:4|(name, value) in (('ram_required_bytes', budget.ram_required_bytes), ('ram_reserved_bytes', budget.ram_reserved_bytes), ('disk_required_bytes', budget.disk_required_bytes), ('max_concurrency', budget.max_concurrency))" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|IF|110:8|not _nonnegative_int(value)" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_IF|110:8|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_FOR|104:4|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|IF|112:4|invalid" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|RETURN|113:8|{'status': 'FAIL', 'reasons': invalid, 'snapshot': snapshot.to_dict()}" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_IF|112:4|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|FOR|121:4|(name, value) in values" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|IF|122:8|value is None" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|ELSE|124:8|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|IF|124:8|not _nonnegative_int(value)" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_IF|124:8|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_IF|122:8|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_FOR|121:4|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|IF|126:4|snapshot.confidence != 'MEASURED'" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_IF|126:4|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|IF|128:4|missing" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|RETURN|129:8|{'status': 'HOLD', 'reasons': missing, 'snapshot': snapshot.to_dict()}" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_IF|128:4|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|ASSERT|131:4|snapshot.ram_available_bytes is not None" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|ASSERT|132:4|snapshot.disk_available_bytes is not None" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|ASSERT|133:4|snapshot.cpu_count is not None" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|IF|138:4|budget.ram_required_bytes + budget.ram_reserved_bytes >= snapshot.ram_available_bytes" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_IF|138:4|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|IF|141:4|budget.disk_required_bytes >= snapshot.disk_available_bytes" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_IF|141:4|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|IF|143:4|budget.max_concurrency < 1 or budget.max_concurrency > max(1, snapshot.cpu_count)" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_IF|143:4|" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|RETURN|145:4|{'status': 'FAIL' if fail else 'PASS', 'reasons': fail, 'ram_usable_bytes': usable, 'disk_available_bytes': snapshot.disk_available_bytes, 'cpu_count': snapshot.cpu_count, 'measured_at_utc': snapshot.measured_at_utc, 'source': snapshot.source}" ∷
  "custoszv9/crfu/resources.py|evaluate_budget|END_FUNCTION|153:5|" ∷
  "custoszv9/crfu/selftest.py|_task|FUNCTION|20:0|" ∷
  "custoszv9/crfu/selftest.py|_task|RETURN|22:4|{'task_id': f'selftest-{index:04d}', 'mission_id': f'selftest-{index:04d}', 'project_id': 'crfu-offline-selftest', 'source_identity': 'selftest-source', 'target_identity': 'selftest-target', 'source_state_hash': sha256_bytes(b'selftest-source-state'), 'dependency_set': [], 'authorized_scope': 'LOCAL_TEST_ONLY', 'required_capabilities': [], 'inputs': {}, 'preconditions': [], 'permitted_effects': [], 'resource_budget': {'ram_required_bytes': 0, 'ram_reserved_bytes': 0, 'disk_required_bytes': 0, 'max_concurrency': 1}, 'execution_deadline': (now + timedelta(minutes=5)).isoformat(), 'maximum_planning_budget': 1, 'maximum_retry_budget': 0, 'acceptance_criteria': [], 'expected_outputs': [], 'validation_strategy': 'offline-selftest', 'evidence_requirements': [], 'checkpoint_reference': None, 'rollback_strategy': 'temporary-file-checkpoint-restore', 'completion_condition': 'selftest complete', 'escalation_condition': 'deny on failed invariant', 'authorization_evidence_reference': 'TEST_FIXTURE_NOT_AUTHORIZATION'}" ∷
  "custoszv9/crfu/selftest.py|_task|END_FUNCTION|53:5|" ∷
  "custoszv9/crfu/selftest.py|run_selftest|FUNCTION|56:0|" ∷
  "custoszv9/crfu/selftest.py|run_selftest|WITH|113:4|tempfile.TemporaryDirectory(prefix='custoszv9-selftest-')" ∷
  "custoszv9/crfu/selftest.py|run_selftest|TRY|177:8|" ∷
  "custoszv9/crfu/selftest.py|run_selftest|FOR|178:12|i in range(32)" ∷
  "custoszv9/crfu/selftest.py|run_selftest|IF|180:16|accepted.get('state') != 'RECEIVED'" ∷
  "custoszv9/crfu/selftest.py|run_selftest|END_IF|180:16|" ∷
  "custoszv9/crfu/selftest.py|run_selftest|END_FOR|178:12|" ∷
  "custoszv9/crfu/selftest.py|run_selftest|FOR|182:12|mission in sorted(expected_missions)" ∷
  "custoszv9/crfu/selftest.py|run_selftest|END_FOR|182:12|" ∷
  "custoszv9/crfu/selftest.py|run_selftest|WHILE|190:12|True" ∷
  "custoszv9/crfu/selftest.py|run_selftest|IF|192:16|item is None" ∷
  "custoszv9/crfu/selftest.py|run_selftest|END_IF|192:16|" ∷
  "custoszv9/crfu/selftest.py|run_selftest|END_WHILE|190:12|" ∷
  "custoszv9/crfu/selftest.py|run_selftest|EXCEPT|203:8|Exception" ∷
  "custoszv9/crfu/selftest.py|run_selftest|END_TRY|177:8|" ∷
  "custoszv9/crfu/selftest.py|run_selftest|END_WITH|113:4|" ∷
  "custoszv9/crfu/selftest.py|run_selftest|RETURN|248:4|{'schema': 'CUSTOSZV9_CRFU_SELFTEST/2.0', 'status': 'PASS' if not failed else 'FAIL', 'checks': checks, 'check_count': len(checks), 'failed_checks': failed, 'external_host_operations': False, 'authorization_granted': False, 'certification': 'NOT_GRANTED_BY_SELFTEST'}" ∷
  "custoszv9/crfu/selftest.py|run_selftest|END_FUNCTION|257:5|" ∷ []
