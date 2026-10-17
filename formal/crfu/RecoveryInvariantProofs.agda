{-# OPTIONS --safe --without-K #-}
module RecoveryInvariantProofs where

open import Agda.Builtin.Bool using (true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import FalseElimination using (false-not-true; void-elim)
open import RecoveryInvariant

restore-bytes-necessary :
  (r : RestoreEvidence) ->
  restorationProven r ≡ true ->
  RestoreEvidence.bytesMatch r ≡ true
restore-bytes-necessary (restoreEvidence false i d v j) pass =
  void-elim (false-not-true pass)
restore-bytes-necessary (restoreEvidence true i d v j) pass = refl

restore-identity-necessary :
  (r : RestoreEvidence) ->
  restorationProven r ≡ true ->
  RestoreEvidence.identityMatches r ≡ true
restore-identity-necessary (restoreEvidence false i d v j) pass =
  void-elim (false-not-true pass)
restore-identity-necessary (restoreEvidence true false d v j) pass =
  void-elim (false-not-true pass)
restore-identity-necessary (restoreEvidence true true d v j) pass = refl

restore-dependencies-necessary :
  (r : RestoreEvidence) ->
  restorationProven r ≡ true ->
  RestoreEvidence.dependenciesMatch r ≡ true
restore-dependencies-necessary (restoreEvidence false i d v j) pass =
  void-elim (false-not-true pass)
restore-dependencies-necessary (restoreEvidence true false d v j) pass =
  void-elim (false-not-true pass)
restore-dependencies-necessary (restoreEvidence true true false v j) pass =
  void-elim (false-not-true pass)
restore-dependencies-necessary (restoreEvidence true true true v j) pass = refl

restore-invariants-necessary :
  (r : RestoreEvidence) ->
  restorationProven r ≡ true ->
  RestoreEvidence.invariantsPass r ≡ true
restore-invariants-necessary (restoreEvidence false i d v j) pass =
  void-elim (false-not-true pass)
restore-invariants-necessary (restoreEvidence true false d v j) pass =
  void-elim (false-not-true pass)
restore-invariants-necessary (restoreEvidence true true false v j) pass =
  void-elim (false-not-true pass)
restore-invariants-necessary (restoreEvidence true true true false j) pass =
  void-elim (false-not-true pass)
restore-invariants-necessary (restoreEvidence true true true true j) pass = refl

restore-journal-necessary :
  (r : RestoreEvidence) ->
  restorationProven r ≡ true ->
  RestoreEvidence.journalPass r ≡ true
restore-journal-necessary (restoreEvidence false i d v j) pass =
  void-elim (false-not-true pass)
restore-journal-necessary (restoreEvidence true false d v j) pass =
  void-elim (false-not-true pass)
restore-journal-necessary (restoreEvidence true true false v j) pass =
  void-elim (false-not-true pass)
restore-journal-necessary (restoreEvidence true true true false j) pass =
  void-elim (false-not-true pass)
restore-journal-necessary (restoreEvidence true true true true false) pass =
  void-elim (false-not-true pass)
restore-journal-necessary (restoreEvidence true true true true true) pass = refl
