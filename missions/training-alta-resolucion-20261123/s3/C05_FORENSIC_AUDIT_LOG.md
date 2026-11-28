# C05 forensic audit log — 2026-11-27

## Audit entry: PR #199 hosted run

- Inspected commit: `139b52a71f053bc81e9c9b6a9032bba0e4cc3b02`
- PR: #199 (open; not merged)
- Unit/adversarial validation run: `46020543585` — SUCCESS
- Hosted restricted-container run: `46020543843` — SUCCESS
- Hosted evidence artifact: `15208003564`, SHA-256 `d098e44388efd4adbad1ea4a40fa590dcaeacf51e2036364c0d935424f34da92`
- Coverage artifact: `15207908062`, SHA-256 `83dd2ce49603841c245c143c998c36c809a6ff36e1757dda44f3774a11d5a45f`
- Source-plan backlog artifact: `15208112766`, SHA-256 `e7b8b970ff3606600754c616830060770df19d5e17db4eacfaf30eb486e7e8c2`

## Evidence inspection

Downloaded and unpacked the hosted evidence archive; independently checked its layout and SHA-256 manifests:

- 95 distinct case directories.
- 5 repetitions per case: 475 distinct run UUIDs.
- 6,175 checksum entries verified against extracted bytes.
- 0 checksum mismatches / missing referenced files.
- Hosted population report: 95 PASS operations, 95 contractual PASS, 95 authentic results; 905 NOT_RUN; no blocked/failed/inconclusive rows.
- Population report explicitly says `c05_passed=false`, `c05_status=NOT_PASSED`; 1,000 cases are required.
- Backlog summary is a separate source-bound 1,000-case dossier population and explicitly reports `planned=0`, `not_run=1000`, `plan_fields_null_by_design=true`. Do not conflate that planning population with the 95 executed-plan evidence.

## Forensic conclusion

CI and hosted seed execution are green for the implemented subset; the evidence archive is byte-integrity-valid under the independently run manifest check. This is **not C05 certification**. Functional coverage remains 95/1,000 and 905 cases remain NOT_RUN/unimplemented. No merge or certification action was taken.

## Next work

Expand the executable-plan backlog with the next source-bound case(s), including implementation, negative/boundary controls, independent oracle, per-case evidence, tests and coverage/population count updates. Keep the append-only audit log updated with each subsequent inspection.


## Audit entry: 2026-11-28 12:40:49 -03:00 — INF-0633/0634 source/control reconciliation

- Main inspected: `b53ea644c21264360fa2b648e4a545a0db36c137`.
- PR #199: closed and **already merged**; head `93b323fe496a81cdc9f5675884d3ea6c1827d9c6`, merge commit `a8ed0b3df175a4792eb36b5e02324f6512af9161`. The requested branch still exists, but it no longer has an open PR. No new PR was created.
- Active C05 work inspected: PR #204 branch `work/c05-archive-forensics-20261127`, head `68b6ce9bf7f143d92c3f14f64124e4ea18bd664e`; PR #205 branch `work/c05-animal-inf0065-apk-inventory-20261128`, head `9ac8becb3c31284882c82d2e20c64ef241f72eed`.
- PR #204 failures: unit workflow `46101101376` failed Ruff `I001` import ordering; hosted workflow `46101101322` failed the authored/compiled plan equality. Compiler report: 164 authored normal specs, 163 compiled, `MGL5-INF-0633` skipped for missing controls, 837 NOT_RUN.
- PR #205 hosted restricted execution `46160117218` and independent validation `46160117209` succeeded for its head; evidence artifact `15269795531`, 15,751,655 bytes, digest `sha256:41f2ce2535e6f1dd18d40582ed75261b1d0af72060a6344bc9cffc9b3fc75180`. Its branch reports 164 plans / 836 NOT_RUN; this is a separate open PR, not merged or added to PR #204's count.
- Forensic source mismatch: INF-0633 is ACF and already had a normal spec in batch4; its controls were accidentally moved to INF-0634. INF-0634's source criterion is linear-trend stationarity analysis, but its plan used ACF lag-0, a false-positive operation mapping. This left INF-0633 uncompileable and inflated the missing-plan count.
- Applied repair on the existing PR #204 branch (no duplicate PR): INF-0633 negative/boundary controls restored; INF-0634 changed to a deterministic linear-trend diagnostic with a fixed-vector independent oracle, a no-trend negative control and a two-point power-boundary control; added tests for stable output, exact slope/R² reference values, primary/independent adjudication and source mapping; corrected coverage assertions to 164 ready / 836 blocked.
- Code commits in this repair sequence: `0104620f11fddda2031466d65b5f6dff965e0627`, `9a4430d245661c29d8467419efe8746a05bb84d2`, `84c3b1bff1b0234e3f1a92ae8cfc812fdf8c7ebf`, `1e155a07b16275d852cea41f6575f1f58744aa07`, `a9b90de4ae92438a82c8b41f1f5df4b96be757c0`, `be266bf01854d5bc1dab1fba38741baf5bb1da71`, `abd2b7ef2aeadf4b6334110f444d35b1376614a1`, `f4fb7096e73465747d5e8e4a8587f8ade3a0b78e`, `c48b016eea4ebc22c5170f2cd03832a8029ae6c2`, `3a2fa2d4b42eda24dcc7cfc542d0723a4f462f68`, `fa8413b3329d1e5914c90bd5b23ca1b90fbbdfd1`.
- CI and hosted restricted population for the repaired head: **PENDING** at this entry. No PASS/certification and no merge.
