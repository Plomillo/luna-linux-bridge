# REMOTE CORPUS + EXTREME TRANSLATION CONTRACT

## Massive corpus

"Without downloading" means **without full local materialization**. Reading remotely still transfers requested bytes.

Required strategy:
```text
SOURCE_IDENTITY
 -> RIGHTS/POLICY CHECK
 -> REMOTE METADATA/TOC
 -> SHARD/RANGE PLAN
 -> STREAM/QUERY
 -> EPHEMERAL PROCESSING
 -> DERIVED INDEX/EVIDENCE
 -> DISCARD EPHEMERAL BYTES
```

Required evidence per source:
`SOURCE_ID, URI/PROVIDER, REVISION, LICENSE/RIGHTS_STATE, CONTENT_HASH_IF_AVAILABLE, READ_RANGES_OR_SHARDS, BYTES_READ, COVERAGE, EXTRACTION_LIMITS, DERIVED_OUTPUT_HASHES`.

No FULL_READ claim when only partial streaming occurred.

## 100,000-page-class translation

The translation plane SHALL use stable segment identity, preferably XLIFF-compatible:
```text
BOOK -> VOLUME -> CHAPTER -> SECTION -> SEGMENT_ID
```

Each segment records:
`SOURCE_HASH, SOURCE_TEXT_POINTER, CONTEXT_POINTERS, TERMINOLOGY_VERSION, TARGET_CANDIDATE, MODEL/ENGINE_ID, QA_STATE, TARGET_HASH`.

Parallel workers may translate independent shards, but global terminology, entity, quotation, numeric, note, cross-reference and structural invariants are validated before reassembly.

Terminal translation PASS requires:
- every expected segment accounted for;
- no silent dropped/duplicated/reordered segment;
- terminology checks;
- named entity and numeric fidelity checks;
- syntax/semantic QA;
- structure/footnote/reference preservation;
- independent sampled and risk-based review;
- reproducible reassembly manifest.

Large translated bodies remain outside Git; Git stores manifests, QA summaries, hashes and final README.
