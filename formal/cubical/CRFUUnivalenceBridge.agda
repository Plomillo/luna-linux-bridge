{-# OPTIONS --cubical --safe #-}
module CRFUUnivalenceBridge where

open import Cubical.Foundations.Prelude using (Level; Type; _≡_)
open import Cubical.Foundations.Equiv using (_≃_; idEquiv)
open import Cubical.Foundations.Univalence using (ua)

-- Typechecked interface to the Cubical Agda univalence construction.
-- This proves only the stated representation-level path construction.
-- It does not assert correspondence with the Python implementation.
equivalence-to-type-path :
  {ℓ : Level} {A B : Type ℓ} ->
  A ≃ B ->
  A ≡ B
equivalence-to-type-path = ua

identity-equivalence-path :
  {ℓ : Level} {A : Type ℓ} ->
  A ≡ A
identity-equivalence-path {A = A} = ua (idEquiv A)
