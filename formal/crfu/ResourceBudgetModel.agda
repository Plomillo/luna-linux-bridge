{-# OPTIONS --safe #-}
module ResourceBudgetModel where
open import Agda.Builtin.Nat using (Nat; _+_; _<_)

record ResourceNeed : Set where
  constructor resourceNeed
  field
    requiredRam reservedRam availableRam : Nat
    requiredDisk availableDisk : Nat
open ResourceNeed

-- Logical propositions, not runtime Bool values: builtin Nat strict inequality
-- has propositional type Set. The original draft incorrectly annotated these
-- results as Bool. This correction exists only on the formal-assurance branch.
ramSufficient : ResourceNeed -> Set
ramSufficient r = requiredRam r + reservedRam r < availableRam r

diskSufficient : ResourceNeed -> Set
diskSufficient r = requiredDisk r < availableDisk r
