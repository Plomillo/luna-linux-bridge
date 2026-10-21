{-# OPTIONS --safe --without-K #-}
module GlobalGateTerminalModel where

open import Agda.Builtin.Bool using (Bool; true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import Agda.Builtin.Nat using (Nat; zero; suc)

-- A terminal ledger has exactly 24 ordered positions corresponding to
-- canonical G01..G24. Its evidence loader must bind those positions to the
-- canonical gate IDs and reject duplicate/missing IDs before constructing it.
data GateResult : Set where
  gatePass gateFail gateHold : GateResult

data Vec (A : Set) : Nat -> Set where
  vnil : Vec A zero
  vcons : {n : Nat} -> A -> Vec A n -> Vec A (suc n)

data AllPassing : {n : Nat} -> Vec GateResult n -> Set where
  allPassingNil : AllPassing vnil
  allPassingCons : {n : Nat} {tail : Vec GateResult n} ->
    AllPassing tail -> AllPassing (vcons gatePass tail)

allGatesPass : {n : Nat} -> Vec GateResult n -> Bool
allGatesPass vnil = true
allGatesPass (vcons gatePass rest) = allGatesPass rest
allGatesPass (vcons gateFail rest) = false
allGatesPass (vcons gateHold rest) = false

allGatesPass-sound :
  {n : Nat} (ledger : Vec GateResult n) ->
  allGatesPass ledger ≡ true -> AllPassing ledger
allGatesPass-sound vnil p = allPassingNil
allGatesPass-sound (vcons gatePass rest) p =
  allPassingCons (allGatesPass-sound rest p)
allGatesPass-sound (vcons gateFail rest) ()
allGatesPass-sound (vcons gateHold rest) ()

allGatesPass-complete :
  {n : Nat} (ledger : Vec GateResult n) ->
  AllPassing ledger -> allGatesPass ledger ≡ true
allGatesPass-complete vnil allPassingNil = refl
allGatesPass-complete (vcons gatePass rest) (allPassingCons proof) =
  allGatesPass-complete rest proof

-- Nat indexing enforces exactly 24 gate slots; the slot order is the
-- canonical sequence G01 through G24, with no shorter ledger type accepted.
GlobalGateLedger : Set
GlobalGateLedger = Vec GateResult 24

terminalCertifiable : GlobalGateLedger -> Bool
terminalCertifiable = allGatesPass

-- G24 cannot become PASS unless every slot in the exact 24-element ledger
-- is PASS. FAIL and HOLD both block terminal certification.
terminal-pass-implies-all-24-passing :
  (ledger : GlobalGateLedger) ->
  terminalCertifiable ledger ≡ true -> AllPassing ledger
terminal-pass-implies-all-24-passing ledger proof =
  allGatesPass-sound ledger proof

all-24-passing-implies-terminal-pass :
  (ledger : GlobalGateLedger) ->
  AllPassing ledger -> terminalCertifiable ledger ≡ true
all-24-passing-implies-terminal-pass ledger proof =
  allGatesPass-complete ledger proof

failed-gate-blocks-terminal-certification :
  (rest : Vec GateResult 23) ->
  terminalCertifiable (vcons gateFail rest) ≡ false
failed-gate-blocks-terminal-certification rest = refl

held-gate-blocks-terminal-certification :
  (rest : Vec GateResult 23) ->
  terminalCertifiable (vcons gateHold rest) ≡ false
held-gate-blocks-terminal-certification rest = refl
