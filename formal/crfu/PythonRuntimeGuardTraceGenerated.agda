{-# OPTIONS --safe --without-K #-}
module PythonRuntimeGuardTraceGenerated where
open import Agda.Builtin.List using (List; []; _∷_)
open import Agda.Builtin.String using (String)

pythonRuntimeGuardTrace : List String
pythonRuntimeGuardTrace =
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
  "custoszv9/crfu/gates.py|evaluate_gate_evidence|END_FUNCTION|94:161|" ∷ []
