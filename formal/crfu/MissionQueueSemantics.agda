{-# OPTIONS --safe --without-K #-}
module MissionQueueSemantics where

open import FalseElimination using (Void)

-- This relation reproduces the ALLOWED transition table in
-- custoszv9/crfu/event_queue.py. It is a specification of permitted state
-- transitions, not an assertion that SQLite itself has been mechanically
-- verified.
data MissionState : Set where
  RECEIVED PREFLIGHT BLOCKED DENIED READY WAITING_FOR_EVENT RUNNING : MissionState
  CHECKPOINTED VALIDATING COMPLETED FAILED RECOVERING : MissionState

infix 4 _↝_
data _↝_ : MissionState -> MissionState -> Set where
  received-preflight : RECEIVED ↝ PREFLIGHT
  received-blocked : RECEIVED ↝ BLOCKED
  received-denied : RECEIVED ↝ DENIED
  preflight-ready : PREFLIGHT ↝ READY
  preflight-blocked : PREFLIGHT ↝ BLOCKED
  preflight-waiting : PREFLIGHT ↝ WAITING_FOR_EVENT
  preflight-denied : PREFLIGHT ↝ DENIED
  ready-running : READY ↝ RUNNING
  ready-blocked : READY ↝ BLOCKED
  running-waiting : RUNNING ↝ WAITING_FOR_EVENT
  running-checkpointed : RUNNING ↝ CHECKPOINTED
  running-validating : RUNNING ↝ VALIDATING
  running-completed : RUNNING ↝ COMPLETED
  running-failed : RUNNING ↝ FAILED
  running-blocked : RUNNING ↝ BLOCKED
  waiting-ready : WAITING_FOR_EVENT ↝ READY
  waiting-blocked : WAITING_FOR_EVENT ↝ BLOCKED
  waiting-failed : WAITING_FOR_EVENT ↝ FAILED
  checkpointed-running : CHECKPOINTED ↝ RUNNING
  checkpointed-validating : CHECKPOINTED ↝ VALIDATING
  checkpointed-recovering : CHECKPOINTED ↝ RECOVERING
  checkpointed-blocked : CHECKPOINTED ↝ BLOCKED
  validating-running : VALIDATING ↝ RUNNING
  validating-completed : VALIDATING ↝ COMPLETED
  validating-recovering : VALIDATING ↝ RECOVERING
  validating-failed : VALIDATING ↝ FAILED
  validating-blocked : VALIDATING ↝ BLOCKED
  recovering-running : RECOVERING ↝ RUNNING
  recovering-blocked : RECOVERING ↝ BLOCKED
  recovering-failed : RECOVERING ↝ FAILED

-- Terminal-state invariants are theorem-level exclusions, not test labels.
completed-has-no-outgoing-transition :
  {next : MissionState} -> COMPLETED ↝ next -> Void
completed-has-no-outgoing-transition ()

failed-has-no-outgoing-transition :
  {next : MissionState} -> FAILED ↝ next -> Void
failed-has-no-outgoing-transition ()

blocked-has-no-outgoing-transition :
  {next : MissionState} -> BLOCKED ↝ next -> Void
blocked-has-no-outgoing-transition ()

denied-has-no-outgoing-transition :
  {next : MissionState} -> DENIED ↝ next -> Void
denied-has-no-outgoing-transition ()
