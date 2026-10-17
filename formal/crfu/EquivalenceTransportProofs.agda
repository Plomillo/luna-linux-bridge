{-# OPTIONS --safe --without-K #-}
module EquivalenceTransportProofs where

open import Agda.Builtin.Bool using (true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import FalseElimination using (false-not-true; void-elim)
open import EquivalenceTransport

equivalence-source-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  EquivalenceClaim.sourceIdentityBound e ≡ true
equivalence-source-necessary (equivalenceClaim false t p s) pass =
  void-elim (false-not-true pass)
equivalence-source-necessary (equivalenceClaim true t p s) pass = refl

equivalence-target-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  EquivalenceClaim.targetIdentityBound e ≡ true
equivalence-target-necessary (equivalenceClaim false t p s) pass =
  void-elim (false-not-true pass)
equivalence-target-necessary (equivalenceClaim true false p s) pass =
  void-elim (false-not-true pass)
equivalence-target-necessary (equivalenceClaim true true p s) pass = refl

equivalence-proof-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  EquivalenceClaim.proofIndependentlyVerified e ≡ true
equivalence-proof-necessary (equivalenceClaim false t p s) pass =
  void-elim (false-not-true pass)
equivalence-proof-necessary (equivalenceClaim true false p s) pass =
  void-elim (false-not-true pass)
equivalence-proof-necessary (equivalenceClaim true true false s) pass =
  void-elim (false-not-true pass)
equivalence-proof-necessary (equivalenceClaim true true true s) pass = refl

equivalence-scope-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  EquivalenceClaim.scopeEnumerated e ≡ true
equivalence-scope-necessary (equivalenceClaim false t p s) pass =
  void-elim (false-not-true pass)
equivalence-scope-necessary (equivalenceClaim true false p s) pass =
  void-elim (false-not-true pass)
equivalence-scope-necessary (equivalenceClaim true true false s) pass =
  void-elim (false-not-true pass)
equivalence-scope-necessary (equivalenceClaim true true true false) pass =
  void-elim (false-not-true pass)
equivalence-scope-necessary (equivalenceClaim true true true true) pass = refl
