{-# OPTIONS --safe --without-K #-}
module GlobalGateCertificationV2 where

open import Agda.Builtin.Bool using (Bool; true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import Agda.Builtin.List using (List; []; _∷_)

-- Canonical gate identity space. G24 is the terminal decision, not one of
-- its own prerequisites; therefore the input ledger contains exactly G01-G23.
data GateId : Set where
  G01 G02 G03 G04 G05 G06 G07 G08 G09 G10 G11 G12
  G13 G14 G15 G16 G17 G18 G19 G20 G21 G22 G23 G24 : GateId

data GateStatus : Set where
  passStatus failStatus holdStatus : GateStatus

record GateEntry (id : GateId) : Set where
  constructor gateEntry
  field statusOf : GateStatus
open GateEntry

data GateLedger : List GateId -> Set where
  emptyLedger : GateLedger []
  ledgerCons : {id : GateId} {ids : List GateId} ->
    GateEntry id -> GateLedger ids -> GateLedger (id ∷ ids)

CanonicalPrerequisiteIds : List GateId
CanonicalPrerequisiteIds =
  G01 ∷ G02 ∷ G03 ∷ G04 ∷ G05 ∷ G06 ∷ G07 ∷ G08 ∷
  G09 ∷ G10 ∷ G11 ∷ G12 ∷ G13 ∷ G14 ∷ G15 ∷ G16 ∷
  G17 ∷ G18 ∷ G19 ∷ G20 ∷ G21 ∷ G22 ∷ G23 ∷ []

PrerequisiteLedger : Set
PrerequisiteLedger = GateLedger CanonicalPrerequisiteIds

data EveryPrerequisitePassed : {ids : List GateId} -> GateLedger ids -> Set where
  everyPassedEmpty : EveryPrerequisitePassed emptyLedger
  everyPassedCons : {id : GateId} {ids : List GateId}
    {head : GateEntry id} {tail : GateLedger ids} ->
    statusOf head ≡ passStatus ->
    EveryPrerequisitePassed tail ->
    EveryPrerequisitePassed (ledgerCons head tail)

containsFailure : {ids : List GateId} -> GateLedger ids -> Bool
containsFailure emptyLedger = false
containsFailure (ledgerCons (gateEntry failStatus) rest) = true
containsFailure (ledgerCons (gateEntry passStatus) rest) = containsFailure rest
containsFailure (ledgerCons (gateEntry holdStatus) rest) = containsFailure rest

containsHold : {ids : List GateId} -> GateLedger ids -> Bool
containsHold emptyLedger = false
containsHold (ledgerCons (gateEntry holdStatus) rest) = true
containsHold (ledgerCons (gateEntry passStatus) rest) = containsHold rest
containsHold (ledgerCons (gateEntry failStatus) rest) = containsHold rest

allPrerequisitesPassed : {ids : List GateId} -> GateLedger ids -> Bool
allPrerequisitesPassed emptyLedger = true
allPrerequisitesPassed (ledgerCons (gateEntry passStatus) rest) = allPrerequisitesPassed rest
allPrerequisitesPassed (ledgerCons (gateEntry failStatus) rest) = false
allPrerequisitesPassed (ledgerCons (gateEntry holdStatus) rest) = false

all-pass-sound : {ids : List GateId} (ledger : GateLedger ids) ->
  allPrerequisitesPassed ledger ≡ true -> EveryPrerequisitePassed ledger
all-pass-sound emptyLedger p = everyPassedEmpty
all-pass-sound (ledgerCons (gateEntry passStatus) rest) p =
  everyPassedCons refl (all-pass-sound rest p)
all-pass-sound (ledgerCons (gateEntry failStatus) rest) ()
all-pass-sound (ledgerCons (gateEntry holdStatus) rest) ()

all-pass-complete : {ids : List GateId} (ledger : GateLedger ids) ->
  EveryPrerequisitePassed ledger -> allPrerequisitesPassed ledger ≡ true
all-pass-complete emptyLedger everyPassedEmpty = refl
all-pass-complete (ledgerCons (gateEntry passStatus) rest)
  (everyPassedCons refl tailProof) = all-pass-complete rest tailProof

record G24Evidence : Set where
  constructor g24Evidence
  field
    sourceAndPackageBound : Bool
    independentValidationPassed : Bool
    g23AttestationVerified : Bool
    sourceManifestsConsistent : Bool
    runtimeCertificateAndAttestationVerified : Bool
    priorCertificatesPreserved : Bool
    canonicalAuthorityPreserved : Bool
    scopeAndLimitationsDeclared : Bool
open G24Evidence

_andB_ : Bool -> Bool -> Bool
false andB _ = false
true andB b = b

evidenceComplete : G24Evidence -> Bool
evidenceComplete e =
  sourceAndPackageBound e andB
  (independentValidationPassed e andB
  (g23AttestationVerified e andB
  (sourceManifestsConsistent e andB
  (runtimeCertificateAndAttestationVerified e andB
  (priorCertificatesPreserved e andB
  (canonicalAuthorityPreserved e andB scopeAndLimitationsDeclared e))))))

data G24Decision : Set where
  issueG24Certificate denyG24Certificate holdG24ForEvidence : G24Decision

-- G24 decision order is fail-closed: any known failed prerequisite denies;
-- otherwise any HOLD or incomplete G24 evidence holds; only a complete
-- exact G01-G23 ledger plus complete, bound G24 evidence can issue a cert.
decideG24 : PrerequisiteLedger -> G24Evidence -> G24Decision
decideG24 ledger evidence with containsFailure ledger
... | true = denyG24Certificate
... | false with containsHold ledger
...   | true = holdG24ForEvidence
...   | false with evidenceComplete evidence
...     | true = issueG24Certificate
...     | false = holdG24ForEvidence

g24-pass-requires-every-prerequisite-pass :
  (ledger : PrerequisiteLedger) -> (evidence : G24Evidence) ->
  decideG24 ledger evidence ≡ issueG24Certificate ->
  EveryPrerequisitePassed ledger
g24-pass-requires-every-prerequisite-pass emptyLedger evidence p = everyPassedEmpty
g24-pass-requires-every-prerequisite-pass
  (ledgerCons (gateEntry passStatus) rest) evidence p
  with containsFailure rest | containsHold rest | evidenceComplete evidence
... | true | _ | _ = all-pass-sound (ledgerCons (gateEntry passStatus) rest) p
... | false | true | _ = all-pass-sound (ledgerCons (gateEntry passStatus) rest) p
... | false | false | true =
  everyPassedCons refl
    (g24-pass-requires-every-prerequisite-pass rest evidence refl)

all-prerequisites-and-evidence-issue-g24 :
  (ledger : PrerequisiteLedger) -> EveryPrerequisitePassed ledger ->
  (evidence : G24Evidence) -> evidenceComplete evidence ≡ true ->
  decideG24 ledger evidence ≡ issueG24Certificate
all-prerequisites-and-evidence-issue-g24 emptyLedger everyPassedEmpty evidence complete = refl
all-prerequisites-and-evidence-issue-g24
  (ledgerCons (gateEntry passStatus) rest) (everyPassedCons refl restPassed)
  evidence complete with containsFailure rest | containsHold rest
... | false | false = all-prerequisites-and-evidence-issue-g24 rest restPassed evidence complete

fail-closed-known-failure-denies :
  (ledger : PrerequisiteLedger) (evidence : G24Evidence) ->
  containsFailure ledger ≡ true -> decideG24 ledger evidence ≡ denyG24Certificate
fail-closed-known-failure-denies ledger evidence failed with containsFailure ledger
... | true = refl

missing-or-held-prerequisite-blocks-issue :
  (ledger : PrerequisiteLedger) (evidence : G24Evidence) ->
  containsFailure ledger ≡ false -> containsHold ledger ≡ true ->
  decideG24 ledger evidence ≡ holdG24ForEvidence
missing-or-held-prerequisite-blocks-issue ledger evidence noFailure held
  with containsFailure ledger | containsHold ledger
... | false | true = refl
