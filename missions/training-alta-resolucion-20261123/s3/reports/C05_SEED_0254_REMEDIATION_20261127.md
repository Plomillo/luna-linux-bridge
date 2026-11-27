# C05 seed 0254 remediation record — 2026-11-27

## Scope

This record documents the source-bound hosted execution of MGL5-INF-0254. It does not close C05 or promote historical evidence.

## Defects found and corrected

1. The hosted workflow initially installed only base dependencies. The runner imports `jsonschema`; installation was changed to `pip install -e ".[dev]"`.
2. The source excerpt line-range calculation included a trailing blank line. The exact range calculation was corrected and verified against the UTF-8 source bytes.
3. The seed harness expected lifecycle labels that the runner does not emit as final result labels. Assertions now use the persisted `result_status` contract.
4. Invalid CIDR prefix `/33` raised an exception in the executor, which the runner correctly classified as inconclusive. The executor now returns a structured rejection without producing subnet bounds; the independent `ipaddress` oracle verifies rejection.
5. The first structured-rejection change added an `accepted=true` field to valid outputs and caused three existing regression failures. That schema drift was removed; valid CIDR outputs retain their canonical `network` and `broadcast` fields. Two regression tests were added for invalid prefix and invalid IPv4 octet rejection.

## Hosted execution evidence

- Workflow: C05 hosted authentic seed execution
- Run ID: 45935695749
- Commit: 820754d9a16c788ea94fa1c083e025607c087ad5
- Job: seed-0254 — success
- Artifact ID: 15170601285
- Artifact SHA-256: 84ca85db786f8f82af5e31c9474d4923ed2253a6b727b23cd667779f1e77e82c
- Artifact URL: https://github.com/Plomillo/luna-linux-bridge/actions/runs/45935695749/artifacts/15170601285
- Three NORMAL repetitions: PASS / PASS / PASS
- NEGATIVE `192.0.2.130/33`: PASS; explicit rejection independently confirmed
- BOUNDARY `192.0.2.130/32`: PASS; network and broadcast equal the host address
- Evidence upload: 71 files, successful

The hosted job ran the existing fresh-process temporary-workspace runner. Its own metadata explicitly says `sandbox=false`, `LOCAL_SUBPROCESS_TEST_ONLY`, and no network isolation. This is authentic execution evidence from a GitHub-hosted runner, but it is not proof of a security sandbox and is not eligible for a C05 certification claim under the stricter isolation gate.

## Regression discovered

The change that introduced an `accepted=true` field into successful results caused 3 failures and 57 passes in the S3 pilot suite. The canonical valid-result shape was restored, and explicit invalid-input regression tests were added. The follow-up CI runs are associated with commits 3988061884ad7842e5c51bfce81f2943e1c2f908, 11054a22119615f76dddf29ea6343b4e5ea2819d, and 6239cb3256ab73b80781b152522ccefeefd944a6. Their conclusions must be read from GitHub Actions before treating the regression repair as verified.

## C05 population gate

The controlling population remains 1,000 INF cases plus the separately specified TEO cases and full per-case evidence chain. Existing repository forensic records document 1,000 historical dossiers as NOT_RUN/INCOMPLETE, 106 auxiliary helper records (103 criterion-met, 3 blocked), 74 unique control-summary cases with zero PASS, and 926 NOT_RUN in that auxiliary summary. These populations are not interchangeable.

The current seed is one case with five source-bound runs. It does not satisfy the 1,000-case population requirement. The source-plan backlog still contains no complete executable plans for the remaining cases. Unsupported capability mappings, fixtures, negative controls, and boundary controls must remain NOT_RUN until authored from the source and independently checked; no fabricated parameters or status promotion is permitted.

## Verdict

`MGL5-INF-0254` has a successful hosted seed run with five independently checked outcomes and uploaded raw evidence. C05 remains `NOT_PASSED`. The next blocking work is secure sandbox execution and source-grounded, independently validated plans and evidence for the full population.


## Follow-up implementation — restricted container and TEO dossier compiler

### Restricted-container execution

- Workflow: [C05 hosted restricted-container seed execution](https://github.com/Plomillo/luna-linux-bridge/actions/runs/45936964550)
- Run ID: 45936964550
- Candidate commit: a0738c67a3b42d322a35079366e244fb3db40b34
- Conclusion: success
- Job: seed-0254-container — success
- Artifact ID: 15170693617
- Artifact SHA-256: ed3aa693932ce3342aed4eba82534303f692d3a2859485bfe254f4d8923fb788
- Immutable Python base image: python@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b
- Worker image ID: sha256:b3a75ec8792b135dfc47e520150eb7e66137750d77bb9bb5831c28ab6555ce0c
- Five source-bound runs: 3 NORMAL, 1 NEGATIVE, 1 BOUNDARY; all five returned PASS with independent oracle agreement.
- Container assertions passed for all five runs: network disabled, read-only root filesystem, all Linux capabilities dropped, non-root UID 65534, 64-process limit, 256 MiB memory limit and 1 CPU limit.
- The first container attempt failed because Docker was not attached to stdin. The failure was preserved; adding `docker run -i` fixed it and the subsequent run passed.

This is restricted-container evidence, not VM isolation: the container shares the host kernel. The record intentionally retains `sandbox=false` and `SHARED_HOST_KERNEL_NOT_VM`. No stronger security claim is made.

### TEO dossier compiler

- Added `scripts/build_c05_teo_dossiers.py`.
- Added the dossier compiler and artifact archival to `c05-automated-validation.yml`.
- Workflow: [C05 automated independent validation](https://github.com/Plomillo/luna-linux-bridge/actions/runs/45936959606)
- Run ID: 45936959606 — success.
- Artifact ID: 15170907691.
- Artifact SHA-256: db13a0f3ac873035938272505b8b6f526bc5605bc31b1089bafede6649917b8d.
- The compiler checks the exact 50 ordered TEO IDs, source blob, file hash, excerpt hashes and line ranges; it emits one dossier per case.
- Dossiers preserve operation, criterion, control protocol, hermeneutic stages and anti-error controls.
- All 50 remain BLOCKED / NOT_RUN / NOT_CERTIFIED until the primary passage, edition, reference, pericope and contextual sources are supplied and reviewed by a competent human reviewer. This is dossier creation, not TEO validation.

### INF planning census

A source-corpus audit found 1,000 ordered INF records across D01–D20, each with operation, PASS criterion and oracle requirement. The fixture declaration contains explicit literals in 141 records and says `ninguno explícito` in 859 records. This count does not prove that those 859 lack all usable semantic parameters; each still needs case-level fixture analysis. The source-bound backlog generator continues to emit no executable plan rather than inventing a capability or fixture.

### Current gate

C05 remains NOT_PASSED. The restricted-container seed and TEO dossier compilation are validated implementation increments only. The 999 remaining INF plans, all 50 TEO source-specific validations, stronger-than-shared-kernel isolation, the full 1,000-case execution population, Q5 controls and final independent closure remain outstanding.
