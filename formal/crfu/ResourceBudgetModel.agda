{-# OPTIONS --safe #-}
module ResourceBudgetModel where
open import Agda.Builtin.Nat using (Nat; _+_; _<_)

record ResourceNeed : Set where
  constructor resourceNeed
  field
    requiredRam reservedRam availableRam : Nat
    requiredDisk availableDisk : Nat

-- These are logical propositions (Set), not runtime Bool values.
-- The previous candidate annotated them as Bool even though builtin Nat
-- strict inequality has propositional type. This corrected file is isolated
-- to the formal-assurance branch; the previous commit remains unchanged.
ramSufficient : ResourceNeed -> Set
ramSufficient r = requiredRam r + reservedRam r < availableRam r

diskSufficient : ResourceNeed -> Set
diskSufficient r = requiredDisk r < availableDisk r
