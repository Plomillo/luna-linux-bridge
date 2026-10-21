{-# OPTIONS --safe --without-K #-}
module TaskAndStateModelV2 where

open import Agda.Builtin.String using (String)
open import Agda.Builtin.Nat using (Nat)
open import Agda.Builtin.Bool using (Bool; true; false)

record TaskState : Set where
  constructor taskState
  field
    taskId : String
    revision : Nat
    preconditionsSatisfied : Bool
    forbiddenAction : Bool
open TaskState

data Decision : Set where
  executeNextAction : Decision
  holdForEvidence : Decision
  denyForbiddenAction : Decision

decide : TaskState -> Decision
decide (taskState _ _ _ true) = denyForbiddenAction
decide (taskState _ _ true false) = executeNextAction
decide (taskState _ _ false false) = holdForEvidence
