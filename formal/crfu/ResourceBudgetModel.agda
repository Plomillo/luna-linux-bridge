{-# OPTIONS --safe #-}
module ResourceBudgetModel where
open import Agda.Builtin.Nat using (Nat; _+_; _<_)
open import Agda.Builtin.Bool using (Bool)

record ResourceNeed : Set where
  constructor resourceNeed
  field
    requiredRam reservedRam availableRam : Nat
    requiredDisk availableDisk : Nat
open ResourceNeed

-- Agda.Builtin.Nat defines strict natural-number comparison as Bool.
-- This declaration preserves that exact built-in interface.
ramSufficient : ResourceNeed -> Bool
ramSufficient r = requiredRam r + reservedRam r < availableRam r

diskSufficient : ResourceNeed -> Bool
diskSufficient r = requiredDisk r < availableDisk r
