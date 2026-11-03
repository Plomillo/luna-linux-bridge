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


## Addendum — 2026-11-02 repository-state correction

The pinned Greek and Latin source archives are now materialized in
`research/LOUKSNAPG2_DYNAMIC_LEXICON_SOURCE/` at the repository's current
`louksnapg2/puac2-alternative-20261029` candidate state. The measured archive
SHA-256 values are:

- Greek: `e9b4f2ff9ab62c5b4b838b74fab78dff3b28fa8381889931f1885792683dd3b8`
- Latin: `f7d0b0ce41c5b7ec75c4d83e5018371b4a366b27f2f8f169abfdbe8af21e42ac`

The inspected source schema uses
`lexicalentry/form/poscontainer/senses/sensecontainer/sense`, with sense-level
`count`, `prob` and `loglikelihood` fields. The previous alignment extractor
looked for `syntaxcontainer/collocation` and consequently produced zero records
from these archives. The replacement research extractor reads the observed sense
schema and binds itself to the archive SHA-256 values above.

A shared normalized English sense plus the same part of speech is only a
correspondence hypothesis. These automatically induced lexicons may contain noise,
homonymy, polysemy, corpus imbalance and incorrect glosses. The output preserves
source-member and sense-level provenance, bounds many-to-many groups, and requires
held-out philological validation. It does not assert translation equivalence and
does not write any FST, modify the runtime manifest, or authorize automatic
promotion. Existing Latin-English and Greek-English resource coverage remains
partial and unchanged.
