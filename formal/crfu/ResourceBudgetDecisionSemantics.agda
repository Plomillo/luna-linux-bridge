{-# OPTIONS --safe --without-K #-}
module ResourceBudgetDecisionSemantics where

open import Agda.Builtin.Bool using (Bool; true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import Agda.Builtin.Nat using (Nat; _-_; _+_; _<_)
open import FalseElimination using (Void; false-not-true; void-elim)

notBool : Bool -> Bool
notBool false = true
notBool true = false

_andB_ : Bool -> Bool -> Bool
false andB _ = false
true andB b = b

andB-left : (a b : Bool) -> (a andB b) ≡ true -> a ≡ true
andB-left false b p = void-elim (false-not-true p)
andB-left true b p = refl

andB-right : (a b : Bool) -> (a andB b) ≡ true -> b ≡ true
andB-right false b p = void-elim (false-not-true p)
andB-right true b p = p

record BudgetInput : Set where
  constructor budgetInput
  field
    budgetFieldsValid : Bool
    ramKnown diskKnown cpuKnown confidenceMeasured : Bool
    ramRequired ramReserved ramAvailable : Nat
    diskRequired diskAvailable : Nat
    cpuCount requestedConcurrency : Nat
open BudgetInput

-- Available RAM after the reported reserve, retained for diagnostics.
-- Admission itself uses the strict source-level predicate below, so over-reservation
-- cannot pass merely because truncated subtraction yields zero.
usableRam : BudgetInput -> Nat
usableRam b = ramAvailable b - ramReserved b

maxOne : Nat -> Nat
maxOne n with 0 < n
... | false = 1
... | true = n

measurementComplete : BudgetInput -> Bool
measurementComplete b =
  ramKnown b andB (diskKnown b andB (cpuKnown b andB confidenceMeasured b))

ramWithinBudget : BudgetInput -> Bool
ramWithinBudget b = ramRequired b + ramReserved b < ramAvailable b

diskWithinBudget : BudgetInput -> Bool
diskWithinBudget b = diskRequired b < diskAvailable b

concurrencyWithinBudget : BudgetInput -> Bool
concurrencyWithinBudget b =
  notBool (requestedConcurrency b < 1) andB
  notBool (maxOne (cpuCount b) < requestedConcurrency b)

data BudgetDecision : Set where
  budgetFail budgetHold budgetPass : BudgetDecision

-- Decision priority matches the runtime: malformed budgets FAIL before
-- measurement checks; unknown/untrusted measurements HOLD; measured limit
-- violations FAIL; otherwise PASS.
budgetDecision : BudgetInput -> BudgetDecision
budgetDecision b with budgetFieldsValid b
... | false = budgetFail
... | true with measurementComplete b
...   | false = budgetHold
...   | true with ramWithinBudget b
...     | false = budgetFail
...     | true with diskWithinBudget b
...       | false = budgetFail
...       | true with concurrencyWithinBudget b
...         | false = budgetFail
...         | true = budgetPass

budgetFail-not-pass : budgetFail ≡ budgetPass -> Void
budgetFail-not-pass ()

budgetHold-not-pass : budgetHold ≡ budgetPass -> Void
budgetHold-not-pass ()

budget-pass-requires-valid-budget :
  (b : BudgetInput) -> budgetDecision b ≡ budgetPass -> budgetFieldsValid b ≡ true
budget-pass-requires-valid-budget b p with budgetFieldsValid b
... | false = void-elim (budgetFail-not-pass p)
... | true = refl

budget-pass-requires-complete-measurements :
  (b : BudgetInput) -> budgetDecision b ≡ budgetPass -> measurementComplete b ≡ true
budget-pass-requires-complete-measurements b p with budgetFieldsValid b
... | false = void-elim (budgetFail-not-pass p)
... | true with measurementComplete b
...   | false = void-elim (budgetHold-not-pass p)
...   | true = refl

budget-pass-requires-ram-within-limit :
  (b : BudgetInput) -> budgetDecision b ≡ budgetPass -> ramWithinBudget b ≡ true
budget-pass-requires-ram-within-limit b p with budgetFieldsValid b
... | false = void-elim (budgetFail-not-pass p)
... | true with measurementComplete b
...   | false = void-elim (budgetHold-not-pass p)
...   | true with ramWithinBudget b
...     | false = void-elim (budgetFail-not-pass p)
...     | true = refl

budget-pass-requires-disk-within-limit :
  (b : BudgetInput) -> budgetDecision b ≡ budgetPass -> diskWithinBudget b ≡ true
budget-pass-requires-disk-within-limit b p with budgetFieldsValid b
... | false = void-elim (budgetFail-not-pass p)
... | true with measurementComplete b
...   | false = void-elim (budgetHold-not-pass p)
...   | true with ramWithinBudget b
...     | false = void-elim (budgetFail-not-pass p)
...     | true with diskWithinBudget b
...       | false = void-elim (budgetFail-not-pass p)
...       | true = refl

budget-pass-requires-valid-concurrency :
  (b : BudgetInput) -> budgetDecision b ≡ budgetPass -> concurrencyWithinBudget b ≡ true
budget-pass-requires-valid-concurrency b p with budgetFieldsValid b
... | false = void-elim (budgetFail-not-pass p)
... | true with measurementComplete b
...   | false = void-elim (budgetHold-not-pass p)
...   | true with ramWithinBudget b
...     | false = void-elim (budgetFail-not-pass p)
...     | true with diskWithinBudget b
...       | false = void-elim (budgetFail-not-pass p)
...       | true with concurrencyWithinBudget b
...         | false = void-elim (budgetFail-not-pass p)
...         | true = refl

measurement-complete-implies-ram-known :
  (b : BudgetInput) -> measurementComplete b ≡ true -> ramKnown b ≡ true
measurement-complete-implies-ram-known b = andB-left (ramKnown b) _

measurement-complete-implies-disk-known :
  (b : BudgetInput) -> measurementComplete b ≡ true -> diskKnown b ≡ true
measurement-complete-implies-disk-known b p =
  andB-left (diskKnown b) _ (andB-right (ramKnown b) _ p)

measurement-complete-implies-cpu-known :
  (b : BudgetInput) -> measurementComplete b ≡ true -> cpuKnown b ≡ true
measurement-complete-implies-cpu-known b p =
  andB-left (cpuKnown b) _
    (andB-right (diskKnown b) _ (andB-right (ramKnown b) _ p))

measurement-complete-implies-confidence-measured :
  (b : BudgetInput) -> measurementComplete b ≡ true -> confidenceMeasured b ≡ true
measurement-complete-implies-confidence-measured b p =
  andB-right (cpuKnown b) _
    (andB-right (diskKnown b) _ (andB-right (ramKnown b) _ p))

-- Constructive converse: satisfying every guard yields PASS, not HOLD.
guards-imply-budget-pass :
  (b : BudgetInput) ->
  budgetFieldsValid b ≡ true ->
  measurementComplete b ≡ true ->
  ramWithinBudget b ≡ true ->
  diskWithinBudget b ≡ true ->
  concurrencyWithinBudget b ≡ true ->
  budgetDecision b ≡ budgetPass
guards-imply-budget-pass b valid measured ram disk concurrency
  rewrite valid | measured | ram | disk | concurrency = refl
