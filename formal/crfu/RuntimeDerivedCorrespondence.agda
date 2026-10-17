{-# OPTIONS --safe --without-K #-}
module RuntimeDerivedCorrespondence where

open import Agda.Builtin.Equality using (_≡_; refl)
open import RuntimeDerivedQueueModel using
  (runtimeQueueTransitions; runtimeRequiredTaskFields)
open import PythonQueueTransitionsGenerated using
  (pythonQueueTransitions; pythonRequiredTaskFields)

-- The producer extracts both right-hand sides from the exact protected
-- Python files and G22 binds those source bytes to the separately certified
-- runtime package. A change in any edge fails this definitional equality.
sqlite-queue-transition-table-refines-exact-python-runtime :
  runtimeQueueTransitions ≡ pythonQueueTransitions
sqlite-queue-transition-table-refines-exact-python-runtime = refl

-- A change, omission, duplication or reordering in the required task fields
-- fails this equality. This is a source-derived schema correspondence theorem.
python-task-required-fields-refine-exact-python-runtime :
  runtimeRequiredTaskFields ≡ pythonRequiredTaskFields
python-task-required-fields-refine-exact-python-runtime = refl
