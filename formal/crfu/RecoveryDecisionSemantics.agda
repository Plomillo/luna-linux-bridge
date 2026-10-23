{-# OPTIONS --safe --without-K #-}
module RecoveryDecisionSemantics where

open import Agda.Builtin.Bool using (Bool; true; false)
open import Agda.Builtin.Equality using (_≡_; refl)

-- Normalized control predicate of verify_restoration in recovery.py.
-- True means that the exact runtime guard for that condition was satisfied.
record RestoreInput : Set where
  constructor restoreInput
  field
    payloadBytesMatch : Bool
    stateIdentityMatches : Bool
    dependencyFingerprintMatches : Bool
    invariantsAreProven : Bool
    evidenceJournalIsValid : Bool
open RestoreInput

data RestorationDecision : Set where
  restorationPass restorationBlocked : RestorationDecision

restorationDecision : RestoreInput -> RestorationDecision
restorationDecision r with payloadBytesMatch r
... | false = restorationBlocked
... | true with stateIdentityMatches r
...   | false = restorationBlocked
...   | true with dependencyFingerprintMatches r
...     | false = restorationBlocked
...     | true with invariantsAreProven r
...       | false = restorationBlocked
...       | true with evidenceJournalIsValid r
...         | false = restorationBlocked
...         | true = restorationPass

-- Converse and necessary-condition theorems for the normalized guards.
all-restoration-guards-imply-pass :
  (r : RestoreInput) ->
  payloadBytesMatch r ≡ true ->
  stateIdentityMatches r ≡ true ->
  dependencyFingerprintMatches r ≡ true ->
  invariantsAreProven r ≡ true ->
  evidenceJournalIsValid r ≡ true ->
  restorationDecision r ≡ restorationPass
all-restoration-guards-imply-pass
  (restoreInput true true true true true) refl refl refl refl refl = refl

pass-requires-payload-bytes :
  (r : RestoreInput) -> restorationDecision r ≡ restorationPass ->
  payloadBytesMatch r ≡ true
pass-requires-payload-bytes (restoreInput false i d v j) ()
pass-requires-payload-bytes (restoreInput true i d v j) p = refl

pass-requires-state-identity :
  (r : RestoreInput) -> restorationDecision r ≡ restorationPass ->
  stateIdentityMatches r ≡ true
pass-requires-state-identity (restoreInput false i d v j) ()
pass-requires-state-identity (restoreInput true false d v j) ()
pass-requires-state-identity (restoreInput true true d v j) p = refl

pass-requires-dependency-fingerprint :
  (r : RestoreInput) -> restorationDecision r ≡ restorationPass ->
  dependencyFingerprintMatches r ≡ true
pass-requires-dependency-fingerprint (restoreInput false i d v j) ()
pass-requires-dependency-fingerprint (restoreInput true false d v j) ()
pass-requires-dependency-fingerprint (restoreInput true true false v j) ()
pass-requires-dependency-fingerprint (restoreInput true true true v j) p = refl

pass-requires-proven-invariants :
  (r : RestoreInput) -> restorationDecision r ≡ restorationPass ->
  invariantsAreProven r ≡ true
pass-requires-proven-invariants (restoreInput false i d v j) ()
pass-requires-proven-invariants (restoreInput true false d v j) ()
pass-requires-proven-invariants (restoreInput true true false v j) ()
pass-requires-proven-invariants (restoreInput true true true false j) ()
pass-requires-proven-invariants (restoreInput true true true true j) p = refl

pass-requires-valid-journal :
  (r : RestoreInput) -> restorationDecision r ≡ restorationPass ->
  evidenceJournalIsValid r ≡ true
pass-requires-valid-journal (restoreInput false i d v j) ()
pass-requires-valid-journal (restoreInput true false d v j) ()
pass-requires-valid-journal (restoreInput true true false v j) ()
pass-requires-valid-journal (restoreInput true true true false j) ()
pass-requires-valid-journal (restoreInput true true true true false) ()
pass-requires-valid-journal (restoreInput true true true true true) p = refl
