# CUSTOSZ V9 — Lunita recovery bridge

This branch contains the scoped CUSTOSZ V9 bridge and the derived Lunita beta-v1.6 launcher contract.

## Persistent artifacts

- \`custoszv9_lunita_bridge.py\` — bounded adapter. Audits the local mission and operator contract, uses one checkpointed continuation tick per invocation, records hash-linked receipts, and does not grant certification.
- \`lunita_beta_v1_6.py\` — exact copy of the derived candidate launcher. SHA-256: \`d5ba3f2ce9e113e76f4674c69608ddb7b9877b9a1fc7701cc0d9941c87559004\`.
- \`BETA_PROVENANCE_v1_6.json\` — provenance and explicit post-patch validation status.
- \`test_custoszv9_lunita_bridge.py\` — bridge contract tests.
- \`test_lunita_beta_v1_6.py\` — structural tests for v1.6 pins, fail-closed sandbox behavior, writable Brújula test HOME, bounded Qwen invocation, and source provenance.
- \`test_continuation_antiparalysis.py\` and \`patches/custosz_mision1_continuation_v1.antiparalysis.patch\` — check that blocked work does not advance mission state.

## Local invocation

From the CUSTOSZ operator project, where the V9 package and local mission contract reside:

\`\`\`bash
python3 integrations/lunita-custoszv9/custoszv9_lunita_bridge.py --audit
python3 integrations/lunita-custoszv9/custoszv9_lunita_bridge.py --self-test
python3 integrations/lunita-custoszv9/custoszv9_lunita_bridge.py --run-one-step
\`\`\`

\`--audit\` is read-only. \`--self-test\` uses synthetic tasks. \`--run-one-step\` is the only mutating mode and is limited to one checkpointed continuation tick and append-only receipts. Inspect the operator contract and current continuation state before a mutating invocation.

The authoritative local candidate remains \`G06_REBUILD_CANDIDATE_R1\` under \`state/g06_rebuild_candidates\`. The v1.6 source is a derived candidate, **not** the frozen G06 original. Its original launcher input \`lunita.py.pre-G05\` still matches SHA-256 \`dc7d673b16a578c5cc94999856ed4b70d0b039702155779660a1083e2da54066\`; the expected frozen launcher SHA is \`502f28c2398ee3129f7d4df42bf5117797c19cf59d27cbff218b36bbd271c319\` and has not been recovered at the recorded frozen-source path.

## Validation boundary

The GitHub Actions workflow runs Python compilation and unit tests on changes in this recovery directory. A green CI validates the repository contract, **not** the live Flatpak applications, rootfs inventory, frozen G06, G08, or canonical Louksna certification.

Current beta-v1.6 evidence:
- PASS: launcher start, R 4.6.1 arithmetic probe, Brújula smoke test with a scoped writable temporary HOME/XDG profile.
- PASS: Qwen load/inference from existing hash-bound evidence; the core \`qwen()\` function and model are unchanged in v1.6, so Qwen was not needlessly rerun.
- PASS: 11/11 fault-injection tests and exact local Flathub commit pins for Jamovi and JASP.
- BLOCKED: Jamovi and JASP app sandbox launches in the nested, non-booted candidate rootfs; \`bwrap\` reports it cannot create/mount its inner namespace (\`Operation not permitted\`). The sandbox is not disabled or bypassed.
- BLOCKED: canonical frozen G06 rootfs and its certification manifest are not available at the recorded path. The supplied Dropbox URL is a navigation URL and the connected Dropbox account returns \`SHARED_LINK_NOT_FOUND\` / \`FILE_NOT_FOUND\` for that target; nothing was downloaded or duplicated.

Therefore S31 remains \`BLOCKED_RUNTIME_TESTS\`; S32 independent validation and any beta operational receipt remain blocked. Canonical G06/G08 certification stays \`NOT_GRANTED\`. No automatic certification propagation, canonical promotion, main-branch write, merge, force-push, or workflow dispatch is authorized.
