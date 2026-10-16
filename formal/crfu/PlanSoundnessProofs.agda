{-# OPTIONS --safe --without-K #-}
module PlanSoundnessProofs where

open import Agda.Builtin.Bool using (true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import FalseElimination using (false-not-true; void-elim)
open import PlanSoundness
open PlanEvidence

plan-dependencies-necessary :
  (p : PlanEvidence) ->
  planAdmissible p ≡ true ->
  dependenciesResolved p ≡ true
plan-dependencies-necessary p pass with dependenciesResolved p
... | false = void-elim (false-not-true pass)
... | true = refl

plan-capabilities-necessary :
  (p : PlanEvidence) ->
  planAdmissible p ≡ true ->
  capabilitiesAdmissible p ≡ true
plan-capabilities-necessary p pass
  with dependenciesResolved p | capabilitiesAdmissible p
... | false | _ = void-elim (false-not-true pass)
... | true | false = void-elim (false-not-true pass)
... | true | true = refl

plan-effects-necessary :
  (p : PlanEvidence) ->
  planAdmissible p ≡ true ->
  effectsAdmissible p ≡ true
plan-effects-necessary p pass
  with dependenciesResolved p | capabilitiesAdmissible p | effectsAdmissible p
... | false | _ | _ = void-elim (false-not-true pass)
... | true | false | _ = void-elim (false-not-true pass)
... | true | true | false = void-elim (false-not-true pass)
... | true | true | true = refl

plan-resources-necessary :
  (p : PlanEvidence) ->
  planAdmissible p ≡ true ->
  resourceBudgetPassed p ≡ true
plan-resources-necessary p pass
  with dependenciesResolved p | capabilitiesAdmissible p
     | effectsAdmissible p | resourceBudgetPassed p
... | false | _ | _ | _ = void-elim (false-not-true pass)
... | true | false | _ | _ = void-elim (false-not-true pass)
... | true | true | false | _ = void-elim (false-not-true pass)
... | true | true | true | false = void-elim (false-not-true pass)
... | true | true | true | true = refl

plan-authorization-necessary :
  (p : PlanEvidence) ->
  planAdmissible p ≡ true ->
  authorizationPassed p ≡ true
plan-authorization-necessary p pass
  with dependenciesResolved p | capabilitiesAdmissible p
     | effectsAdmissible p | resourceBudgetPassed p | authorizationPassed p
... | false | _ | _ | _ | _ = void-elim (false-not-true pass)
... | true | false | _ | _ | _ = void-elim (false-not-true pass)
... | true | true | false | _ | _ = void-elim (false-not-true pass)
... | true | true | true | false | _ = void-elim (false-not-true pass)
... | true | true | true | true | false = void-elim (false-not-true pass)
... | true | true | true | true | true = refl
