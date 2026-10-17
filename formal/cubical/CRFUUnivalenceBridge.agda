{-# OPTIONS --cubical --safe --guardedness #-}
module CRFUUnivalenceBridge where

open import Cubical.Foundations.Prelude using (Level; Type; _≡_; refl; transport)
open import Cubical.Foundations.Equiv using (_≃_; idEquiv; equivFun)
open import Cubical.Foundations.Univalence using
  ( ua
  ; uaIdEquiv
  ; pathToEquiv
  ; univalence
  ; ua-pathToEquiv
  ; pathToEquiv-ua
  ; uaβ
  )

private
  variable
    ℓ : Level

-- A path between types induces an equivalence by transport.
type-path-to-equivalence :
  {A B : Type ℓ} -> A ≡ B -> A ≃ B
type-path-to-equivalence = pathToEquiv

-- An equivalence induces a path between types via univalence.
equivalence-to-type-path :
  {A B : Type ℓ} -> A ≃ B -> A ≡ B
equivalence-to-type-path = ua

-- Full univalence equivalence: paths between types and equivalences between
-- those types are equivalent types, not merely a one-way ua interface.
crfu-univalence-equivalence :
  {A B : Type ℓ} -> (A ≡ B) ≃ (A ≃ B)
crfu-univalence-equivalence = univalence

-- The two inverse laws are checked by Cubical Agda's univalence theorem.
univalence-path-roundtrip :
  {A B : Type ℓ} -> (p : A ≡ B) -> ua (pathToEquiv p) ≡ p
univalence-path-roundtrip = ua-pathToEquiv

univalence-equivalence-roundtrip :
  {A B : Type ℓ} -> (e : A ≃ B) -> pathToEquiv (ua e) ≡ e
univalence-equivalence-roundtrip = pathToEquiv-ua

-- Computation rule: transport along the univalent path acts as the
-- equivalence's forward map. This connects the path to its computational
-- action, while deliberately making no unproved claim about Python semantics.
univalence-computation-rule :
  {A B : Type ℓ} (e : A ≃ B) (x : A) ->
  transport (ua e) x ≡ equivFun e x
univalence-computation-rule = uaβ

identity-equivalence-path :
  {A : Type ℓ} -> A ≡ A
identity-equivalence-path {A = A} = ua (idEquiv A)

identity-equivalence-path-is-refl :
  {A : Type ℓ} -> ua (idEquiv A) ≡ refl
identity-equivalence-path-is-refl = uaIdEquiv
