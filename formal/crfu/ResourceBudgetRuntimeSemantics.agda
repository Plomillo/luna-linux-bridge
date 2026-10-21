{-# OPTIONS --safe #-}
module ResourceBudgetRuntimeSemantics where

-- Candidate correction: Python evaluate_budget now uses the same strict
-- natural-number bounds as ResourceBudgetModel. Equality is rejected.
open import Agda.Builtin.Nat using (Nat; _-_; _+_; _<_)
open import Agda.Builtin.Bool using (Bool)
open import ResourceBudgetModel using (ResourceNeed)

usableRam : ResourceNeed -> Nat
usableRam r = ResourceNeed.availableRam r - ResourceNeed.reservedRam r

-- Exact guard is required + reserved < available; it rejects over-reservation,
-- including zero demand, because reserved >= available cannot satisfy the guard.
ramSufficientRuntimeSemantics : ResourceNeed -> Bool
ramSufficientRuntimeSemantics r =
  ResourceNeed.requiredRam r + ResourceNeed.reservedRam r < ResourceNeed.availableRam r

diskSufficientRuntimeSemantics : ResourceNeed -> Bool
diskSufficientRuntimeSemantics r =
  ResourceNeed.requiredDisk r < ResourceNeed.availableDisk r
