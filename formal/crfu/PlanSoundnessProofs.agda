{-# OPTIONS --safe --without-K #-}
module PlanSoundnessProofs where

open import Agda.Builtin.Bool using (true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import FalseElimination using (false-not-true; void-elim)
open import PlanSoundness

plan-dependencies-necessary :
  (p : PlanEvidence) ->
  planAdmissible p ≡ true ->
  PlanEvidence.dependenciesResolved p ≡ true
plan-dependencies-necessary (planEvidence false c e r a) pass =
  void-elim (false-not-true pass)
plan-dependencies-necessary (planEvidence true c e r a) pass = refl

plan-capabilities-necessary :
  (p : PlanEvidence) ->
  planAdmissible p ≡ true ->
  PlanEvidence.capabilitiesAdmissible p ≡ true
plan-capabilities-necessary (planEvidence false c e r a) pass =
  void-elim (false-not-true pass)
plan-capabilities-necessary (planEvidence true false e r a) pass =
  void-elim (false-not-true pass)
plan-capabilities-necessary (planEvidence true true e r a) pass = refl

plan-effects-necessary :
  (p : PlanEvidence) ->
  planAdmissible p ≡ true ->
  PlanEvidence.effectsAdmissible p ≡ true
plan-effects-necessary (planEvidence false c e r a) pass =
  void-elim (false-not-true pass)
plan-effects-necessary (planEvidence true false e r a) pass =
  void-elim (false-not-true pass)
plan-effects-necessary (planEvidence true true false r a) pass =
  void-elim (false-not-true pass)
plan-effects-necessary (planEvidence true true true r a) pass = refl

plan-resources-necessary :
  (p : PlanEvidence) ->
  planAdmissible p ≡ true ->
  PlanEvidence.resourceBudgetPassed p ≡ true
plan-resources-necessary (planEvidence false c e r a) pass =
  void-elim (false-not-true pass)
plan-resources-necessary (planEvidence true false e r a) pass =
  void-elim (false-not-true pass)
plan-resources-necessary (planEvidence true true false r a) pass =
  void-elim (false-not-true pass)
plan-resources-necessary (planEvidence true true true false a) pass =
  void-elim (false-not-true pass)
plan-resources-necessary (planEvidence true true true true a) pass = refl

plan-authorization-necessary :
  (p : PlanEvidence) ->
  planAdmissible p ≡ true ->
  PlanEvidence.authorizationPassed p ≡ true
plan-authorization-necessary (planEvidence false c e r a) pass =
  void-elim (false-not-true pass)
plan-authorization-necessary (planEvidence true false e r a) pass =
  void-elim (false-not-true pass)
plan-authorization-necessary (planEvidence true true false r a) pass =
  void-elim (false-not-true pass)
plan-authorization-necessary (planEvidence true true true false a) pass =
  void-elim (false-not-true pass)
plan-authorization-necessary (planEvidence true true true true false) pass =
  void-elim (false-not-true pass)
plan-authorization-necessary (planEvidence true true true true true) pass = refl
