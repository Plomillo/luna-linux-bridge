{-# OPTIONS --safe --without-K #-}
module ResourceBudgetRuntimeSemanticsProofs where

open import Agda.Builtin.Bool using (true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import Agda.Builtin.Nat using (_+_)
open import ResourceBudgetModel using (ResourceNeed; resourceNeed)
open import ResourceBudgetRuntimeSemantics
open import ResourceBudgetModel as Legacy using (ramSufficient; diskSufficient)

-- Machine-checked strict-boundary facts for the normalized runtime contract.
ram-one-byte-inside-strict-boundary-is-accepted :
  ramSufficientRuntimeSemantics (resourceNeed 899 100 1000 10 2000) ≡ true
ram-one-byte-inside-strict-boundary-is-accepted = refl

ram-equality-at-usable-capacity-is-rejected :
  ramSufficientRuntimeSemantics (resourceNeed 900 100 1000 10 2000) ≡ false
ram-equality-at-usable-capacity-is-rejected = refl

ram-one-byte-over-usable-capacity-is-rejected :
  ramSufficientRuntimeSemantics (resourceNeed 901 100 1000 10 2000) ≡ false
ram-one-byte-over-usable-capacity-is-rejected = refl

ram-reservation-at-or-above-availability-is-rejected :
  ramSufficientRuntimeSemantics (resourceNeed 0 101 100 10 2000) ≡ false
ram-reservation-at-or-above-availability-is-rejected = refl

disk-one-byte-inside-strict-boundary-is-accepted :
  diskSufficientRuntimeSemantics (resourceNeed 0 0 1000 1999 2000) ≡ true
disk-one-byte-inside-strict-boundary-is-accepted = refl

disk-equality-at-available-capacity-is-rejected :
  diskSufficientRuntimeSemantics (resourceNeed 0 0 1000 2000 2000) ≡ false
disk-equality-at-available-capacity-is-rejected = refl

disk-one-byte-over-available-capacity-is-rejected :
  diskSufficientRuntimeSemantics (resourceNeed 0 0 1000 2001 2000) ≡ false
disk-one-byte-over-available-capacity-is-rejected = refl

-- The legacy strict declarations and corrected runtime semantics now agree
-- on all demonstrated boundary cases.
legacy-strict-ram-model-agrees-at-equality :
  Legacy.ramSufficient (resourceNeed 900 100 1000 10 2000) ≡
  ramSufficientRuntimeSemantics (resourceNeed 900 100 1000 10 2000)
legacy-strict-ram-model-agrees-at-equality = refl

legacy-strict-disk-model-agrees-at-equality :
  Legacy.diskSufficient (resourceNeed 0 0 1000 2000 2000) ≡
  diskSufficientRuntimeSemantics (resourceNeed 0 0 1000 2000 2000)
legacy-strict-disk-model-agrees-at-equality = refl


-- Universal definitional refinement between the shared formal RAM guard and
-- the runtime-semantics predicate for every natural-number resource vector.
strict-ram-guard-refines-formal-model-for-all-inputs :
  (r : ResourceNeed) ->
  Legacy.ramSufficient r ≡ ramSufficientRuntimeSemantics r
strict-ram-guard-refines-formal-model-for-all-inputs r = refl

-- Universal definitional refinement between the shared formal disk guard and
-- the runtime-semantics predicate for every natural-number resource vector.
strict-disk-guard-refines-formal-model-for-all-inputs :
  (r : ResourceNeed) ->
  Legacy.diskSufficient r ≡ diskSufficientRuntimeSemantics r
strict-disk-guard-refines-formal-model-for-all-inputs r = refl
