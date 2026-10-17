{-# OPTIONS --safe --without-K #-}
module ResourceBudgetRuntimeSemanticsProofs where

open import Agda.Builtin.Bool using (true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import ResourceBudgetModel using (resourceNeed)
open import ResourceBudgetRuntimeSemantics
open import ResourceBudgetModel as Legacy using (ramSufficient; diskSufficient)

-- Positive and negative boundary facts are definitional proofs, not sampled
-- observations. These states correspond to evaluate_budget's integer guards.
ram-equality-at-usable-capacity-is-accepted :
  ramSufficientRuntimeSemantics (resourceNeed 900 100 1000 0 2000) ≡ true
ram-equality-at-usable-capacity-is-accepted = refl

ram-one-byte-over-usable-capacity-is-rejected :
  ramSufficientRuntimeSemantics (resourceNeed 901 100 1000 0 2000) ≡ false
ram-one-byte-over-usable-capacity-is-rejected = refl

ram-zero-demand-with-reservation-above-availability-matches-runtime :
  ramSufficientRuntimeSemantics (resourceNeed 0 101 100 0 2000) ≡ true
ram-zero-demand-with-reservation-above-availability-matches-runtime = refl

disk-equality-at-available-capacity-is-accepted :
  diskSufficientRuntimeSemantics (resourceNeed 0 0 1000 2000 2000) ≡ true
disk-equality-at-available-capacity-is-accepted = refl

disk-one-byte-over-available-capacity-is-rejected :
  diskSufficientRuntimeSemantics (resourceNeed 0 0 1000 2001 2000) ≡ false
disk-one-byte-over-available-capacity-is-rejected = refl

-- Explicitly retain proof of the historical mismatch. The old strict model
-- is not silently overwritten or claimed equivalent at an equality boundary.
legacy-strict-ram-model-rejects-equality :
  Legacy.ramSufficient (resourceNeed 900 100 1000 0 2000) ≡ false
legacy-strict-ram-model-rejects-equality = refl

legacy-strict-disk-model-rejects-equality :
  Legacy.diskSufficient (resourceNeed 0 0 1000 2000 2000) ≡ false
legacy-strict-disk-model-rejects-equality = refl
