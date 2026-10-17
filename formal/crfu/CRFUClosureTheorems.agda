{-# OPTIONS --safe --without-K #-}
module CRFUClosureTheorems where

open import Agda.Builtin.Bool using (true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import Agda.Builtin.Nat using (Nat)
open import Agda.Builtin.String using (String)
open import FalseElimination using (Void; false-not-true; void-elim)
open import PlanSoundness using (PlanEvidence; planEvidence; planAdmissible)
open import ContractComposition using
  ( ContractEvidence; contractEvidence; contractComposable )
open import MigrationCoherence using
  ( MigrationEvidence; migrationEvidence; migrationCoherent )
open import RecoveryInvariant using
  ( RestoreEvidence; restoreEvidence; restorationProven )
open import EquivalenceTransport using
  ( EquivalenceClaim; equivalenceClaim; equivalenceAdmissible )
open import TaskAndStateModel using
  ( taskState; executeNextAction; holdForEvidence; decide )

-- Sufficiency theorems complement the existing necessity lemmas. Together
-- they characterize acceptance of each Boolean guard, rather than merely
-- type-checking the fields that happen to be present in a record.
plan-all-guards-true-imply-admissible :
  (p : PlanEvidence) ->
  PlanEvidence.dependenciesResolved p ≡ true ->
  PlanEvidence.capabilitiesAdmissible p ≡ true ->
  PlanEvidence.effectsAdmissible p ≡ true ->
  PlanEvidence.resourceBudgetPassed p ≡ true ->
  PlanEvidence.authorizationPassed p ≡ true ->
  planAdmissible p ≡ true
plan-all-guards-true-imply-admissible
  (planEvidence true true true true true) refl refl refl refl refl = refl

contract-all-guards-true-imply-composable :
  (c : ContractEvidence) ->
  ContractEvidence.inputsValid c ≡ true ->
  ContractEvidence.preconditionsPass c ≡ true ->
  ContractEvidence.effectsWithinScope c ≡ true ->
  ContractEvidence.outputsValidated c ≡ true ->
  contractComposable c ≡ true
contract-all-guards-true-imply-composable
  (contractEvidence true true true true) refl refl refl refl = refl

contract-inputs-necessary :
  (c : ContractEvidence) -> contractComposable c ≡ true ->
  ContractEvidence.inputsValid c ≡ true
contract-inputs-necessary (contractEvidence false p e o) pass =
  void-elim (false-not-true pass)
contract-inputs-necessary (contractEvidence true p e o) pass = refl

contract-preconditions-necessary :
  (c : ContractEvidence) -> contractComposable c ≡ true ->
  ContractEvidence.preconditionsPass c ≡ true
contract-preconditions-necessary (contractEvidence false p e o) pass =
  void-elim (false-not-true pass)
contract-preconditions-necessary (contractEvidence true false e o) pass =
  void-elim (false-not-true pass)
contract-preconditions-necessary (contractEvidence true true e o) pass = refl

contract-effects-necessary :
  (c : ContractEvidence) -> contractComposable c ≡ true ->
  ContractEvidence.effectsWithinScope c ≡ true
contract-effects-necessary (contractEvidence false p e o) pass =
  void-elim (false-not-true pass)
contract-effects-necessary (contractEvidence true false e o) pass =
  void-elim (false-not-true pass)
contract-effects-necessary (contractEvidence true true false o) pass =
  void-elim (false-not-true pass)
contract-effects-necessary (contractEvidence true true true o) pass = refl

contract-outputs-necessary :
  (c : ContractEvidence) -> contractComposable c ≡ true ->
  ContractEvidence.outputsValidated c ≡ true
contract-outputs-necessary (contractEvidence false p e o) pass =
  void-elim (false-not-true pass)
contract-outputs-necessary (contractEvidence true false e o) pass =
  void-elim (false-not-true pass)
contract-outputs-necessary (contractEvidence true true false o) pass =
  void-elim (false-not-true pass)
contract-outputs-necessary (contractEvidence true true true false) pass =
  void-elim (false-not-true pass)
contract-outputs-necessary (contractEvidence true true true true) pass = refl

migration-all-guards-true-imply-coherent :
  (m : MigrationEvidence) ->
  MigrationEvidence.sourceBound m ≡ true ->
  MigrationEvidence.targetBound m ≡ true ->
  MigrationEvidence.invariantsPreserved m ≡ true ->
  MigrationEvidence.rollbackAvailable m ≡ true ->
  migrationCoherent m ≡ true
migration-all-guards-true-imply-coherent
  (migrationEvidence true true true true) refl refl refl refl = refl

migration-source-necessary :
  (m : MigrationEvidence) -> migrationCoherent m ≡ true ->
  MigrationEvidence.sourceBound m ≡ true
migration-source-necessary (migrationEvidence false t i r) pass =
  void-elim (false-not-true pass)
migration-source-necessary (migrationEvidence true t i r) pass = refl

migration-target-necessary :
  (m : MigrationEvidence) -> migrationCoherent m ≡ true ->
  MigrationEvidence.targetBound m ≡ true
migration-target-necessary (migrationEvidence false t i r) pass =
  void-elim (false-not-true pass)
migration-target-necessary (migrationEvidence true false i r) pass =
  void-elim (false-not-true pass)
migration-target-necessary (migrationEvidence true true i r) pass = refl

migration-invariants-necessary :
  (m : MigrationEvidence) -> migrationCoherent m ≡ true ->
  MigrationEvidence.invariantsPreserved m ≡ true
migration-invariants-necessary (migrationEvidence false t i r) pass =
  void-elim (false-not-true pass)
migration-invariants-necessary (migrationEvidence true false i r) pass =
  void-elim (false-not-true pass)
migration-invariants-necessary (migrationEvidence true true false r) pass =
  void-elim (false-not-true pass)
migration-invariants-necessary (migrationEvidence true true true r) pass = refl

migration-rollback-necessary :
  (m : MigrationEvidence) -> migrationCoherent m ≡ true ->
  MigrationEvidence.rollbackAvailable m ≡ true
migration-rollback-necessary (migrationEvidence false t i r) pass =
  void-elim (false-not-true pass)
migration-rollback-necessary (migrationEvidence true false i r) pass =
  void-elim (false-not-true pass)
migration-rollback-necessary (migrationEvidence true true false r) pass =
  void-elim (false-not-true pass)
migration-rollback-necessary (migrationEvidence true true true false) pass =
  void-elim (false-not-true pass)
migration-rollback-necessary (migrationEvidence true true true true) pass = refl

-- The existing necessity lemmas remain in RecoveryInvariantProofs and
-- EquivalenceTransportProofs; these provide the complementary directions.
restoration-all-guards-true-imply-proven :
  (r : RestoreEvidence) ->
  RestoreEvidence.bytesMatch r ≡ true ->
  RestoreEvidence.identityMatches r ≡ true ->
  RestoreEvidence.dependenciesMatch r ≡ true ->
  RestoreEvidence.invariantsPass r ≡ true ->
  RestoreEvidence.journalPass r ≡ true ->
  restorationProven r ≡ true
restoration-all-guards-true-imply-proven
  (restoreEvidence true true true true true) refl refl refl refl refl = refl

equivalence-all-guards-true-imply-admissible :
  (e : EquivalenceClaim) ->
  EquivalenceClaim.sourceIdentityBound e ≡ true ->
  EquivalenceClaim.targetIdentityBound e ≡ true ->
  EquivalenceClaim.proofIndependentlyVerified e ≡ true ->
  EquivalenceClaim.scopeEnumerated e ≡ true ->
  equivalenceAdmissible e ≡ true
equivalence-all-guards-true-imply-admissible
  (equivalenceClaim true true true true) refl refl refl refl = refl

-- The current two-branch decision function has exact, checked equations.
execute-when-preconditions-are-satisfied :
  (taskId : String) -> (revision : Nat) ->
  decide (taskState taskId revision true) ≡ executeNextAction
execute-when-preconditions-are-satisfied _ _ = refl

hold-when-preconditions-are-missing :
  (taskId : String) -> (revision : Nat) ->
  decide (taskState taskId revision false) ≡ holdForEvidence
hold-when-preconditions-are-missing _ _ = refl

-- Explicit lifecycle relation for the intended transition contract. Terminal
-- states cannot transition onward; unsafe transitions are absent by design.
data TaskPhase : Set where
  received validated authorized running waitingForEvidence completed failed rolledBack : TaskPhase

infix 4 _↦_
data _↦_ : TaskPhase -> TaskPhase -> Set where
  received-to-validated : received ↦ validated
  validated-to-authorized : validated ↦ authorized
  authorized-to-running : authorized ↦ running
  running-to-completed : running ↦ completed
  running-to-waiting : running ↦ waitingForEvidence
  waiting-to-running : waitingForEvidence ↦ running
  running-to-failed : running ↦ failed
  failed-to-rolled-back : failed ↦ rolledBack

completed-has-no-outgoing-transition :
  {next : TaskPhase} -> completed ↦ next -> Void
completed-has-no-outgoing-transition ()

rolled-back-has-no-outgoing-transition :
  {next : TaskPhase} -> rolledBack ↦ next -> ⊥
rolled-back-has-no-outgoing-transition ()
