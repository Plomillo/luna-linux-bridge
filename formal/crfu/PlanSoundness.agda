{-# OPTIONS --safe #-}
module PlanSoundness where
open import Agda.Builtin.Bool using (Bool; true; false)
record PlanEvidence : Set where
  constructor planEvidence
  field dependenciesResolved capabilitiesAdmissible effectsAdmissible resourceBudgetPassed authorizationPassed : Bool
planAdmissible : PlanEvidence -> Bool
planAdmissible p with dependenciesResolved p
... | false = false
... | true with capabilitiesAdmissible p
...   | false = false
...   | true with effectsAdmissible p
...     | false = false
...     | true with resourceBudgetPassed p
...       | false = false
...       | true = authorizationPassed p
