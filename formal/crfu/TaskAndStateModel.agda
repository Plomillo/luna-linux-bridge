{-# OPTIONS --safe --without-K #-}
module TaskAndStateModel where

open import Agda.Builtin.String using (String)
open import Agda.Builtin.Nat using (Nat)
open import Agda.Builtin.Bool using (Bool)
open import Agda.Builtin.List using (List; []; _∷_)
open import Agda.Builtin.Equality using (_≡_; refl)

record TaskState : Set where
  constructor taskState
  field
    taskId : String
    revision : Nat
    preconditionsSatisfied : Bool

data Decision : Set where
  executeNextAction : Decision
  holdForEvidence : Decision
  denyUnsafeAction : Decision

decide : TaskState -> Decision
decide (taskState _ _ true) = executeNextAction
decide (taskState _ _ false) = holdForEvidence

-- Exact REQUIRED field order from TaskContract in custoszv9/crfu/model.py.
requiredTaskFields : List String
requiredTaskFields =
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
  "escalation_condition" ∷ []

-- The complete finite state alphabet used by PersistentMissionQueue in
-- custoszv9/crfu/event_queue.py. Constructor names map one-to-one to the
-- exact state strings in the runtime source.
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

-- A directed state edge. The order of the table matches the order in which
-- the runtime source declares each state and its allowed targets.
record QueueEdge : Set where
  constructor queueEdge
  field
    edgeFrom : QueueState
    edgeTo : QueueState
open QueueEdge

sqliteQueueTransitions : List QueueEdge
sqliteQueueTransitions =
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

queueStateCount : Nat
queueStateCount = 12

-- The Python source extractor checks the finite state set, duplicates,
-- literal transition guard, direct SQL state updates, and BEGIN IMMEDIATE
-- transaction boundaries. The generated PythonQueueTransitionsGenerated
-- module is then compared by definitional equality in
-- ModelImplementationCorrespondence.agda.
