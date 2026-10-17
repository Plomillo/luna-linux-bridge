{-# OPTIONS --safe --without-K #-}
module RuntimeDerivedQueueModel where

open import Agda.Builtin.List using (List; []; _∷_)
open import Agda.Builtin.String using (String)
open import Agda.Builtin.Nat using (Nat)

-- Additive model slice derived from the protected CUSTOSZV9 runtime source.
-- Existing certified Agda modules remain byte-for-byte unchanged.
data QueueState : Set where
  received : QueueState
  preflight : QueueState
  ready : QueueState
  running : QueueState
  waitingForEvent : QueueState
  checkpointed : QueueState
  validating : QueueState
  recovering : QueueState
  completed : QueueState
  failed : QueueState
  blocked : QueueState
  denied : QueueState

record QueueEdge : Set where
  constructor queueEdge
  field
    edgeFrom : QueueState
    edgeTo : QueueState
open QueueEdge

-- Canonical reference relation. CI extracts the Python ALLOWED table and
-- Agda's definitional equality rejects any difference in order, state, or edge.
runtimeQueueTransitions : List QueueEdge
runtimeQueueTransitions =
  queueEdge received preflight ∷
  queueEdge received blocked ∷
  queueEdge received denied ∷
  queueEdge preflight ready ∷
  queueEdge preflight blocked ∷
  queueEdge preflight waitingForEvent ∷
  queueEdge preflight denied ∷
  queueEdge ready running ∷
  queueEdge ready blocked ∷
  queueEdge running waitingForEvent ∷
  queueEdge running checkpointed ∷
  queueEdge running validating ∷
  queueEdge running completed ∷
  queueEdge running failed ∷
  queueEdge running blocked ∷
  queueEdge waitingForEvent ready ∷
  queueEdge waitingForEvent blocked ∷
  queueEdge waitingForEvent failed ∷
  queueEdge checkpointed running ∷
  queueEdge checkpointed validating ∷
  queueEdge checkpointed recovering ∷
  queueEdge checkpointed blocked ∷
  queueEdge validating running ∷
  queueEdge validating completed ∷
  queueEdge validating recovering ∷
  queueEdge validating failed ∷
  queueEdge validating blocked ∷
  queueEdge recovering running ∷
  queueEdge recovering blocked ∷
  queueEdge recovering failed ∷
  []

runtimeQueueStateCount : Nat
runtimeQueueStateCount = 12

-- Exact task-contract field list from the protected Python REQUIRED tuple.
runtimeRequiredTaskFields : List String
runtimeRequiredTaskFields =
  "task_id" ∷
  "mission_id" ∷
  "project_id" ∷
  "source_identity" ∷
  "target_identity" ∷
  "source_state_hash" ∷
  "dependency_set" ∷
  "authorized_scope" ∷
  "required_capabilities" ∷
  "inputs" ∷
  "preconditions" ∷
  "permitted_effects" ∷
  "resource_budget" ∷
  "execution_deadline" ∷
  "maximum_planning_budget" ∷
  "maximum_retry_budget" ∷
  "acceptance_criteria" ∷
  "expected_outputs" ∷
  "validation_strategy" ∷
  "evidence_requirements" ∷
  "checkpoint_reference" ∷
  "rollback_strategy" ∷
  "completion_condition" ∷
  "escalation_condition" ∷
  []
