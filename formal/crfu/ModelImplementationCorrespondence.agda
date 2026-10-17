{-# OPTIONS --safe --without-K #-}
module ModelImplementationCorrespondence where

open import Agda.Builtin.Bool using (Bool; true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import TaskAndStateModel using (sqliteQueueTransitions; requiredTaskFields)
open import PythonQueueTransitionsGenerated using (pythonQueueTransitions; pythonRequiredTaskFields)

record CorrespondenceEvidence : Set where
  constructor correspondenceEvidence
  field
    modelIdentityBound implementationIdentityBound obligationsEnumerated checkerIndependentlyVerified : Bool
open CorrespondenceEvidence

correspondenceAdmissible : CorrespondenceEvidence -> Bool
correspondenceAdmissible e with modelIdentityBound e
... | false = false
... | true with implementationIdentityBound e
...   | false = false
...   | true with obligationsEnumerated e
...     | false = false
...     | true = checkerIndependentlyVerified e

-- The runtime transition table is generated in CI by parsing the exact
-- PersistentMissionQueue.ALLOWED literal from custoszv9/crfu/event_queue.py.
-- CI also checks the actual transition() guard, all static SQL state updates,
-- and the BEGIN IMMEDIATE transaction boundaries before this module is checked.
-- refl therefore rejects any mismatch in the full finite allowed-edge list.
sqlite-queue-transition-table-refines-exact-python-runtime :
  sqliteQueueTransitions ≡ pythonQueueTransitions
sqlite-queue-transition-table-refines-exact-python-runtime = refl

-- The Python source extractor reads the literal REQUIRED tuple in
-- TaskContract's model.py and generates this ordered list. Equality is
-- checked for every field and its position, not just set membership.
python-task-required-fields-refine-exact-python-runtime :
  requiredTaskFields ≡ pythonRequiredTaskFields
python-task-required-fields-refine-exact-python-runtime = refl
