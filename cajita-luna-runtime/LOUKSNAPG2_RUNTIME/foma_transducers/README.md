# Foma translation resources

The Foma engine source is present in Cajita and is compiled/tested by the CUSTOSZ V9
repair worker. This directory deliberately contains no linguistic data: the repository
currently has no approved Latin or Ancient Greek translation FST.

To register a source-to-target transducer, place the binary Foma transducer in this
directory and add an entry to `manifest.json` keyed as `lat->eng`, `lat->spa`,
`grc->eng` or `grc->spa`. Each entry must contain a relative `path`, exact
`bytes` and SHA-256. The runtime rejects traversal, symlinks, missing files, hash
mismatches and no-analysis results.

The compiler smoke test (including synthetic cat→dog lookup) proves toolkit build
and execution only. It does NOT establish Latin/Greek translation quality; independent
linguistic known-answer tests and G24 remain mandatory.
