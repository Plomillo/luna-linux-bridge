# Louksnapg2 Foma and lexicon repair — 2026-11-02

## Change envelope

- Repository: \`Plomillo/luna-linux-bridge\`
- Source branch: \`louksnapg2/puac2-alternative-20261029\`
- Source commit: \`e89d5cee0ab4b2e519253d50ca37f12de2c8ccd3\`
- Repair branch: \`repair/louksnapg2-foma-sense-xml-20261102\`
- Change doctrine: additive, source-pinned, fail-closed.
- No model weights, Foma source files, canonical IDs, runtime manifest, or canonical release files are modified by this patch.

## Evidence-based defects

1. The current functional-evaluation containers did not install \`make\`, \`cc\`,
   \`flex\`, \`bison\`, \`libreadline-dev\` and \`zlib1g-dev\`. The Foma runtime
   correctly builds a disposable copy of its source at first use, but therefore
   failed before the two ancient-language cases could execute:
   \`FOMA_COMMAND_LAUNCH_FAILED:make\`.
2. The research extractor expected \`syntaxcontainer/collocation\`; the pinned
   Perseus XML inspected in GitHub Actions uses \`poscontainer/senses/sensecontainer/sense\`.
   The previous extractor returned zero source records and zero candidate pairs
   while exiting as a candidate-extraction success.
3. The XML inventory confirmed 10,279 Greek XML members (6,945,634 uncompressed
   bytes) and 7,672 Latin XML members (6,198,588 uncompressed bytes).

## Changes

- Foma preflight now lists each required compiler executable and its missing set.
  Runtime compilation fails early with a deterministic toolchain error.
- Both real-model evaluation workflows install the Foma build toolchain in their
  isolated containers; source weights remain untouched.
- The Dynamic Lexicon parser follows the observed sense schema, verifies the exact
  pinned archive SHA-256 values, preserves gloss/POS/count/probability/source-member
  evidence and bounds high-ambiguity Cartesian groups.
- A zero-record or zero-candidate extraction is now an explicit failure status.
  A successful extraction is still research-only and cannot promote an FST.
- Unit tests cover source-schema parsing, POS separation, empty alignment,
  ambiguity bounds, traversal rejection and compiler-toolchain preflight.

## Required validation

This commit is a repair candidate, not a certification. The branch's GitHub Actions
runs must pass the added tests and demonstrate non-zero parsed sense records before
any further linguistic evaluation. Neural-model semantic repair, G23 independent
validation and G24 certification are separate gates and are not inferred from this
change.
