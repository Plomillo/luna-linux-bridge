{-# OPTIONS --safe --without-K #-}
module PlannerDecisionSemantics where

open import Agda.Builtin.Bool using (Bool; true; false)
open import Agda.Builtin.Equality using (_≡_; refl)

-- Normalized guard order from build_plan in planner.py.
record PlannerInput : Set where
  constructor plannerInput
  field
    planningBudgetValid : Bool
    withinAlternativeBudget : Bool
    actionIdentifiersUnique : Bool
    dependenciesResolved : Bool
    actionsAdmissible : Bool
    dependencyGraphAcyclic : Bool
open PlannerInput

data PlannerDecision : Set where
  planValidated planHeld planDenied : PlannerDecision

plannerDecision : PlannerInput -> PlannerDecision
plannerDecision p with planningBudgetValid p
... | false = planDenied
... | true with withinAlternativeBudget p
...   | false = planHeld
...   | true with actionIdentifiersUnique p
...     | false = planDenied
...     | true with dependenciesResolved p
...       | false = planHeld
...       | true with actionsAdmissible p
...         | false = planDenied
...         | true with dependencyGraphAcyclic p
...           | false = planDenied
...           | true = planValidated

-- A validated plan remains a proposal, not an execution authorization.
executionAuthorized : PlannerInput -> Bool
executionAuthorized _ = false

validated-plan-never-authorizes-execution :
  (p : PlannerInput) -> plannerDecision p ≡ planValidated ->
  executionAuthorized p ≡ false
validated-plan-never-authorizes-execution p q = refl

all-planner-guards-imply-validation :
  (p : PlannerInput) ->
  planningBudgetValid p ≡ true ->
  withinAlternativeBudget p ≡ true ->
  actionIdentifiersUnique p ≡ true ->
  dependenciesResolved p ≡ true ->
  actionsAdmissible p ≡ true ->
  dependencyGraphAcyclic p ≡ true ->
  plannerDecision p ≡ planValidated
all-planner-guards-imply-validation
  (plannerInput true true true true true true) refl refl refl refl refl refl = refl

validation-requires-valid-budget :
  (p : PlannerInput) -> plannerDecision p ≡ planValidated ->
  planningBudgetValid p ≡ true
validation-requires-valid-budget (plannerInput false b u d a c) ()
validation-requires-valid-budget (plannerInput true b u d a c) q = refl

validation-requires-alternative-bound :
  (p : PlannerInput) -> plannerDecision p ≡ planValidated ->
  withinAlternativeBudget p ≡ true
validation-requires-alternative-bound (plannerInput false b u d a c) ()
validation-requires-alternative-bound (plannerInput true false u d a c) ()
validation-requires-alternative-bound (plannerInput true true u d a c) q = refl

validation-requires-unique-identifiers :
  (p : PlannerInput) -> plannerDecision p ≡ planValidated ->
  actionIdentifiersUnique p ≡ true
validation-requires-unique-identifiers (plannerInput false b u d a c) ()
validation-requires-unique-identifiers (plannerInput true false u d a c) ()
validation-requires-unique-identifiers (plannerInput true true false d a c) ()
validation-requires-unique-identifiers (plannerInput true true true d a c) q = refl

validation-requires-resolved-dependencies :
  (p : PlannerInput) -> plannerDecision p ≡ planValidated ->
  dependenciesResolved p ≡ true
validation-requires-resolved-dependencies (plannerInput false b u d a c) ()
validation-requires-resolved-dependencies (plannerInput true false u d a c) ()
validation-requires-resolved-dependencies (plannerInput true true false d a c) ()
validation-requires-resolved-dependencies (plannerInput true true true false a c) ()
validation-requires-resolved-dependencies (plannerInput true true true true a c) q = refl

validation-requires-admissible-actions :
  (p : PlannerInput) -> plannerDecision p ≡ planValidated ->
  actionsAdmissible p ≡ true
validation-requires-admissible-actions (plannerInput false b u d a c) ()
validation-requires-admissible-actions (plannerInput true false u d a c) ()
validation-requires-admissible-actions (plannerInput true true false d a c) ()
validation-requires-admissible-actions (plannerInput true true true false a c) ()
validation-requires-admissible-actions (plannerInput true true true true false c) ()
validation-requires-admissible-actions (plannerInput true true true true true c) q = refl

validation-requires-acyclic-graph :
  (p : PlannerInput) -> plannerDecision p ≡ planValidated ->
  dependencyGraphAcyclic p ≡ true
validation-requires-acyclic-graph (plannerInput false b u d a c) ()
validation-requires-acyclic-graph (plannerInput true false u d a c) ()
validation-requires-acyclic-graph (plannerInput true true false d a c) ()
validation-requires-acyclic-graph (plannerInput true true true false a c) ()
validation-requires-acyclic-graph (plannerInput true true true true false c) ()
validation-requires-acyclic-graph (plannerInput true true true true true false) ()
validation-requires-acyclic-graph (plannerInput true true true true true true) q = refl
