{-# OPTIONS --safe --without-K #-}
module JournalChainSemantics where

open import Agda.Builtin.Bool using (Bool; true; false)
open import Agda.Builtin.Equality using (_≡_; refl)

-- Normalized row checks from verify_event_chain in event_queue.py.
-- The trusted Python verifier computes previous_hash_matches by comparing
-- previous_event_hash to the prior event digest, and digest_matches by
-- recomputing SHA-256 over the canonicalized event material.
record EventCheck : Set where
  constructor eventCheck
  field
    previousHashMatches : Bool
    canonicalEventDigestMatches : Bool
open EventCheck

data Journal : Set where
  emptyJournal : Journal
  journalCons : EventCheck -> Journal -> Journal

_andB_ : Bool -> Bool -> Bool
false andB _ = false
true andB b = b

journalValid : Journal -> Bool
journalValid emptyJournal = true
journalValid (journalCons e rest) =
  previousHashMatches e andB
  (canonicalEventDigestMatches e andB journalValid rest)

allPreviousLinksMatch : Journal -> Bool
allPreviousLinksMatch emptyJournal = true
allPreviousLinksMatch (journalCons e rest) =
  previousHashMatches e andB allPreviousLinksMatch rest

allCanonicalDigestsMatch : Journal -> Bool
allCanonicalDigestsMatch emptyJournal = true
allCanonicalDigestsMatch (journalCons e rest) =
  canonicalEventDigestMatches e andB allCanonicalDigestsMatch rest

-- Fundamental soundness: accepting the journal implies that every previous
-- hash link and every canonical event digest check is true.
journal-pass-implies-all-links-match :
  (j : Journal) -> journalValid j ≡ true -> allPreviousLinksMatch j ≡ true
journal-pass-implies-all-links-match emptyJournal p = refl
journal-pass-implies-all-links-match
  (journalCons (eventCheck false d) rest) ()
journal-pass-implies-all-links-match
  (journalCons (eventCheck true false) rest) ()
journal-pass-implies-all-links-match
  (journalCons (eventCheck true true) rest) p =
  journal-pass-implies-all-links-match rest p

journal-pass-implies-all-digests-match :
  (j : Journal) -> journalValid j ≡ true -> allCanonicalDigestsMatch j ≡ true
journal-pass-implies-all-digests-match emptyJournal p = refl
journal-pass-implies-all-digests-match
  (journalCons (eventCheck false d) rest) ()
journal-pass-implies-all-digests-match
  (journalCons (eventCheck true false) rest) ()
journal-pass-implies-all-digests-match
  (journalCons (eventCheck true true) rest) p =
  journal-pass-implies-all-digests-match rest p

-- Completeness for the normalized decision predicate: if every row's link
-- and digest check passes, the complete finite journal is accepted.
all-row-checks-imply-journal-pass :
  (j : Journal) ->
  allPreviousLinksMatch j ≡ true ->
  allCanonicalDigestsMatch j ≡ true ->
  journalValid j ≡ true
all-row-checks-imply-journal-pass emptyJournal links digests = refl
all-row-checks-imply-journal-pass
  (journalCons (eventCheck false d) rest) () digests
all-row-checks-imply-journal-pass
  (journalCons (eventCheck true false) rest) links ()
all-row-checks-imply-journal-pass
  (journalCons (eventCheck true true) rest) links digests =
  all-row-checks-imply-journal-pass rest links digests

-- Fail-closed tampering lemmas: a mismatched previous link or a mismatched
-- canonical event digest makes the chain predicate false immediately.
wrong-previous-link-blocks-journal :
  (d : Bool) (rest : Journal) ->
  journalValid (journalCons (eventCheck false d) rest) ≡ false
wrong-previous-link-blocks-journal d rest = refl

wrong-event-digest-blocks-journal :
  (rest : Journal) ->
  journalValid (journalCons (eventCheck true false) rest) ≡ false
wrong-event-digest-blocks-journal rest = refl
