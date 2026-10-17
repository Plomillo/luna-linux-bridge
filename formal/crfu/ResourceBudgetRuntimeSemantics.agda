{-# OPTIONS --safe #-}
module ResourceBudgetRuntimeSemantics where

-- Additive, versioned specification of the current Python evaluate_budget
-- RAM/disk boundary semantics. The previously certified ResourceBudgetModel
-- module remains byte-identical; this module records its strict-boundary
-- discrepancy rather than silently rewriting a historically bound source.
open import Agda.Builtin.Nat using (Nat; _-_; _<_)
open import Agda.Builtin.Bool using (Bool; true; false)
open import ResourceBudgetModel using
  ( ResourceNeed
  ; requiredRam
  ; reservedRam
  ; availableRam
  ; requiredDisk
  ; availableDisk
  )

notBool : Bool -> Bool
notBool false = true
notBool true = false

-- Agda natural subtraction truncates at zero, matching Python max(0, a - b).
usableRam : ResourceNeed -> Nat
usableRam r = availableRam r - reservedRam r

-- The runtime accepts equality: rejection occurs only when required > usable.
ramSufficientRuntimeSemantics : ResourceNeed -> Bool
ramSufficientRuntimeSemantics r = notBool (usableRam r < requiredRam r)

diskSufficientRuntimeSemantics : ResourceNeed -> Bool
diskSufficientRuntimeSemantics r = notBool (availableDisk r < requiredDisk r)
