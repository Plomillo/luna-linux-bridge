{-# OPTIONS --safe --without-K #-}
module RecoveryInvariantProofs where

open import Agda.Builtin.Bool using (true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import FalseElimination using (false-not-true; void-elim)
open import RecoveryInvariant
open RestoreEvidence

restore-bytes-necessary :
  (r : RestoreEvidence) ->
  restorationProven r ≡ true ->
  bytesMatch r ≡ true
restore-bytes-necessary r pass with bytesMatch r
... | false = void-elim (false-not-true pass)
... | true = refl

restore-identity-necessary :
  (r : RestoreEvidence) ->
  restorationProven r ≡ true ->
  identityMatches r ≡ true
restore-identity-necessary r pass with bytesMatch r | identityMatches r
... | false | _ = void-elim (false-not-true pass)
... | true | false = void-elim (false-not-true pass)
... | true | true = refl

restore-dependencies-necessary :
  (r : RestoreEvidence) ->
  restorationProven r ≡ true ->
  dependenciesMatch r ≡ true
restore-dependencies-necessary r pass
  with bytesMatch r | identityMatches r | dependenciesMatch r
... | false | _ | _ = void-elim (false-not-true pass)
... | true | false | _ = void-elim (false-not-true pass)
... | true | true | false = void-elim (false-not-true pass)
... | true | true | true = refl

restore-invariants-necessary :
  (r : RestoreEvidence) ->
  restorationProven r ≡ true ->
  invariantsPass r ≡ true
restore-invariants-necessary r pass
  with bytesMatch r | identityMatches r | dependenciesMatch r | invariantsPass r
... | false | _ | _ | _ = void-elim (false-not-true pass)
... | true | false | _ | _ = void-elim (false-not-true pass)
... | true | true | false | _ = void-elim (false-not-true pass)
... | true | true | true | false = void-elim (false-not-true pass)
... | true | true | true | true = refl

restore-journal-necessary :
  (r : RestoreEvidence) ->
  restorationProven r ≡ true ->
  journalPass r ≡ true
restore-journal-necessary r pass
  with bytesMatch r | identityMatches r | dependenciesMatch r
     | invariantsPass r | journalPass r
... | false | _ | _ | _ | _ = void-elim (false-not-true pass)
... | true | false | _ | _ | _ = void-elim (false-not-true pass)
... | true | true | false | _ | _ = void-elim (false-not-true pass)
... | true | true | true | false | _ = void-elim (false-not-true pass)
... | true | true | true | true | false = void-elim (false-not-true pass)
... | true | true | true | true | true = refl
