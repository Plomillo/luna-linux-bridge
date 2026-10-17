{-# OPTIONS --safe #-}
module MigrationCoherence where
open import Agda.Builtin.Bool using (Bool; true; false)
record MigrationEvidence : Set where
  constructor migrationEvidence
  field sourceBound targetBound invariantsPreserved rollbackAvailable : Bool
open MigrationEvidence

migrationCoherent : MigrationEvidence -> Bool
migrationCoherent m with sourceBound m
... | false = false
... | true with targetBound m
...   | false = false
...   | true with invariantsPreserved m
...     | false = false
...     | true = rollbackAvailable m
