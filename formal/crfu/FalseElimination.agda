{-# OPTIONS --safe --without-K #-}
module FalseElimination where

open import Agda.Builtin.Bool using (false; true)
open import Agda.Builtin.Equality using (_≡_)

data Void : Set where

false-not-true : false ≡ true -> Void
false-not-true ()

void-elim : {A : Set} -> Void -> A
void-elim ()
