{-# OPTIONS --safe --without-K #-}
module GlobalGateCertificationV2 where

open import Agda.Builtin.Bool using (Bool; true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import Agda.Builtin.List using (List; []; _∷_)
open import FalseElimination using (Void; void-elim)

-- Canonical gate identity space. G24 is the terminal decision, not one of
-- its own prerequisites; therefore the input ledger contains exactly G01-G23.
data GateId : Set where
  G01 : GateId
  G02 : GateId
  G03 : GateId
  G04 : GateId
  G05 : GateId
  G06 : GateId
  G07 : GateId
  G08 : GateId
  G09 : GateId
  G10 : GateId
  G11 : GateId
  G12 : GateId
  G13 : GateId
  G14 : GateId
  G15 : GateId
  G16 : GateId
  G17 : GateId
  G18 : GateId
  G19 : GateId
  G20 : GateId
  G21 : GateId
  G22 : GateId
  G23 : GateId
  G24 : GateId

data GateStatus : Set where
  passStatus : GateStatus
  failStatus : GateStatus
  holdStatus : GateStatus

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
  issueG24Certificate : G24Decision
  denyG24Certificate : G24Decision
  holdG24ForEvidence : G24Decision

-- G24 decision order: a complete all-PASS prerequisite ledger plus complete
-- G24 evidence issues the certificate; known failures deny; all other cases HOLD.
decideG24 : {ids : List GateId} -> GateLedger ids -> G24Evidence -> G24Decision
decideG24 ledger evidence with allPrerequisitesPassed ledger | evidenceComplete evidence
... | true | true = issueG24Certificate
... | true | false = holdG24ForEvidence
... | false | _ with containsFailure ledger
...   | true = denyG24Certificate
...   | false = holdG24ForEvidence

deny-not-issue : denyG24Certificate ≡ issueG24Certificate -> Void
deny-not-issue ()

hold-not-issue : holdG24ForEvidence ≡ issueG24Certificate -> Void
hold-not-issue ()

g24-pass-requires-every-prerequisite-pass :
  (ledger : PrerequisiteLedger) -> (evidence : G24Evidence) ->
  decideG24 ledger evidence ≡ issueG24Certificate ->
  EveryPrerequisitePassed ledger
g24-pass-requires-every-prerequisite-pass ledger evidence proof
  with allPrerequisitesPassed ledger | evidenceComplete evidence
... | true | true = all-pass-sound ledger refl
... | true | false = void-elim (hold-not-issue proof)
... | false | _ with containsFailure ledger
...   | true = void-elim (deny-not-issue proof)
...   | false = void-elim (hold-not-issue proof)

g24-pass-requires-complete-evidence :
  (ledger : PrerequisiteLedger) -> (evidence : G24Evidence) ->
  decideG24 ledger evidence ≡ issueG24Certificate ->
  evidenceComplete evidence ≡ true
g24-pass-requires-complete-evidence ledger evidence proof
  with allPrerequisitesPassed ledger | evidenceComplete evidence
... | true | true = refl
... | true | false = void-elim (hold-not-issue proof)
... | false | _ with containsFailure ledger
...   | true = void-elim (deny-not-issue proof)
...   | false = void-elim (hold-not-issue proof)

all-prerequisites-and-evidence-issue-g24 :
  (ledger : PrerequisiteLedger) -> EveryPrerequisitePassed ledger ->
  (evidence : G24Evidence) -> evidenceComplete evidence ≡ true ->
  decideG24 ledger evidence ≡ issueG24Certificate
all-prerequisites-and-evidence-issue-g24 ledger allPassed evidence complete
  rewrite all-pass-complete ledger allPassed | complete = refl
