# Foma translation resources

This directory contains hash-bound lexical resources, not a complete general-purpose
Latin/Greek MT system.

## Available transducers

- `lat->eng`: 154 lexical lemma pairs derived from the pinned Apertium Latin-English
  dictionary, plus one separately classified curated phrase override
  (`alea iacta est` -> `the die is cast`). This does not establish general Latin
  morphology or sentence translation.
- `grc->eng`: one independently sourced curated phrase
  (`πάντα ῥεῖ` -> `everything flows`). This does not establish general Ancient Greek
  translation.
- `lat->spa`, `grc->spa`, and `grc->lat`: not registered in the active manifest.

The runtime rejects traversal, symlinks, missing files, hash mismatches and no-analysis
results. The Foma compiler smoke test proves toolkit build and execution only.
Independent linguistic known-answer tests are required for every registered data scope;
G23/G24 remain separate certification gates.

## Dynamic Lexicon research input (not yet packaged)

The Perseus Digital Library's Dynamic Lexicon publishes separate Greek and Latin XML
lexicon archives, with automatically aligned Greek-English and Latin-English lexical
evidence. Its data description states CC BY-SA licensing and warns that automatically
induced entries can contain noise. A Greek-Latin bridge must therefore be derived as
ranked candidate correspondences from shared English senses and/or aligned parallel
texts; it must preserve ambiguity, provenance, morphology, sense and corpus evidence.
It must not treat every shared English gloss as an interchangeable translation.

Pinned upstream repository:
- `PerseusDL/dynamic-lexicon`
- commit `945b03db7ff358217a18540a7d7efef9d7339b66`
- `data/dynamic-lex-entries/greeklexicon.tar.gz`
- `data/dynamic-lex-entries/latinlexicon.tar.gz`
- archive SHA-256 is not asserted here because the Git object ID is SHA-1 and the
  archive payload has not been materialized and independently hashed in this build.

The separate `OpenGreekAndLatin/GRC-LAT-Dynamic-lexicon` application repository
contains application code and research description; it does not contain the production
XML data archives. It must not be mistaken for a packaged dictionary.

Dynamic Lexicon source data is not currently embedded in this repository or registered
as a runtime transducer. Promotion requires archive materialization, XML schema
inspection, cryptographic hashing, a reproducible Greek-Latin extraction pipeline,
held-out philological evaluation and resource-specific provenance.
