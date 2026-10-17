{-# OPTIONS --safe #-}
module TaskAndStateModel where
open import Agda.Builtin.String using (String)
open import Agda.Builtin.Nat using (Nat)
open import Agda.Builtin.Bool using (Bool)
record TaskState : Set where
  constructor taskState
  field taskId : String
        revision : Nat
        preconditionsSatisfied : Bool
data Decision : Set where
  executeNextAction : Decision
  holdForEvidence : Decision
  denyUnsafeAction : Decision
decide : TaskState -> Decision
decide (taskState _ _ true) = executeNextAction
decide (taskState _ _ false) = holdForEvidence
