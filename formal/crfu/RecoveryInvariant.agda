{-# OPTIONS --safe #-}
module RecoveryInvariant where
open import Agda.Builtin.Bool using (Bool; true; false)
record RestoreEvidence : Set where
  constructor restoreEvidence
  field bytesMatch identityMatches dependenciesMatch invariantsPass journalPass : Bool
open RestoreEvidence

restorationProven : RestoreEvidence -> Bool
restorationProven r with bytesMatch r
... | false = false
... | true with identityMatches r
...   | false = false
...   | true with dependenciesMatch r
...     | false = false
...     | true with invariantsPass r
...       | false = false
...       | true = journalPass r
