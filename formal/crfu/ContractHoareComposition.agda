{-# OPTIONS --safe --without-K #-}
module ContractHoareComposition where

-- A contract is a state transformer equipped with pre/postconditions and a
-- proof that the transformer preserves its declared contract.
record HoareContract (State : Set) : Set₁ where
  constructor hoareContract
  field
    Precondition : State -> Set
    Postcondition : State -> Set
    execute : State -> State
    correctness : (state : State) -> Precondition state ->
      Postcondition (execute state)
open HoareContract

-- The caller must prove that the first contract's postcondition establishes
-- the second contract's precondition at the intermediate state.
composeContracts :
  {State : Set} ->
  (first second : HoareContract State) ->
  ((state : State) ->
    Postcondition first (execute first state) ->
    Precondition second (execute first state)) ->
  HoareContract State
composeContracts first second bridge =
  hoareContract
    (Precondition first)
    (Postcondition second)
    (\state -> execute second (execute first state))
    (\state pre ->
      correctness second (execute first state)
        (bridge state (correctness first state pre)))

-- Explicit composition theorem. This requires no Boolean "coherent=true"
-- flag: the proof term itself must establish the intermediate contract.
composition-preserves-postcondition :
  {State : Set} ->
  (first second : HoareContract State) ->
  (bridge : (state : State) ->
    Postcondition first (execute first state) ->
    Precondition second (execute first state)) ->
  (state : State) -> Precondition first state ->
  Postcondition second (execute second (execute first state))
composition-preserves-postcondition first second bridge state pre =
  correctness second (execute first state)
    (bridge state (correctness first state pre))
