{-# OPTIONS --safe #-}
module ResourceBudgetModel where
open import Agda.Builtin.Nat using (Nat; _+_; _<_ )
open import Agda.Builtin.Bool using (Bool; true; false)
record ResourceNeed : Set where
  constructor resourceNeed
  field requiredRam reservedRam availableRam requiredDisk availableDisk : Nat
ramSufficient : ResourceNeed -> Bool
ramSufficient r = requiredRam r + reservedRam r < availableRam r
diskSufficient : ResourceNeed -> Bool
diskSufficient r = requiredDisk r < availableDisk r
