# Continuous automation — Louksna Document Workbench

Status: CANDIDATE_AUTOMATION_CONFIGURED_NOT_CERTIFIED

## Automated triggers

The candidate workflow at .github/workflows/louksna-document-workbench-continuous.yml defines:
- validation automatically on relevant pushes to this candidate branch;
- validation on pull requests touching this component;
- a workflow_dispatch trigger declaration; manual dispatch is not usable until this workflow exists on the default branch;
- a six-hour schedule declaration (13 */6 * * * UTC); the schedule is not active while this workflow exists only on the candidate branch;
- a read-only GitHub permission set and a non-cancelling concurrency group.

## What each run does

1. Creates an isolated Python virtual environment.
2. Installs this project and its unit-test dependency.
3. Checks dependency consistency and compiles all Python source, tests and CI scripts.
4. Audits the runtime package for Python syntax errors, accidental Document Factory imports, unsafe subprocess.run(..., shell=True) usage and literal HTTP(S) endpoints.
5. Runs unit tests.
6. Builds a temporary three-page synthetic PDF and tests inspection, audited page reordering, text-only reflow, and invariance of the input SHA-256.
7. Checks out the identified PDF from main in read-only mode and computes an evidence-backed folio/chapter order analysis.
8. Applies a complete page permutation only when printed folios prove a unique, contiguous sequence; otherwise it preserves the exact source bytes and records the need for manual review.
9. Adds chapter/part navigation bookmarks and verifies the output against the page sequence selected by the order stage.
10. Builds a separate academic reading edition with a cover, table of contents, readable typography, PDF bookmarks and a source-page marker for every input page.
11. Packages both reading outputs, provenance reports and SHA-256 checksums as a time-limited Actions artifact.
7. Records the commit ID, Python version and dependency inventory.
8. Uploads non-secret evidence for 14 days.

The smoke fixture remains synthetic. A separate, scoped workflow step reads the identified PDF already present on main, runs the printed-folio analysis, conditionally reorders only on strong evidence, creates a bookmarked PDF and creates a separate typographically reflowed reading edition. It does not change main or the source PDF; output is committed only to the explicitly named candidate branch on successful push runs. OCR and translation are not exercised unless system OCR dependencies or local language models are separately provisioned. Machine-translation accuracy and visual fidelity are not certified by these checks.

## Schedule activation constraint

GitHub Actions requires both schedule and workflow_dispatch workflows to exist on the repository's default branch. This candidate must not be described as running every six hours or manually dispatchable while the workflow exists only on this branch. Relevant push events in this candidate are configured for event-driven automation, and pull-request validation is declared; the recurring and manual triggers remain DECLARED_NOT_ACTIVE until the governed release process authorizes promotion of the workflow to the default branch.

No attempt is made to bypass this boundary through an unregistered token, external scheduler, existing Kestra flow, or mutation of main. A separate persistent Kestra runtime could later become an approved scheduler, but runtime import, execution isolation, credential scope and observed run evidence must be validated independently before claiming continuous scheduled operation.

## Failure and recovery

Any failed command stops the job. On a successful push-triggered run for this candidate branch, the workflow commits the organized ZIP plus its organization report, source inventory and package report under louksna-document-workbench/output/. That output path is excluded from the push filter to prevent recursive CI runs. This write is confined to the candidate branch; main, Document Factory and the source PDF are not modified. The ZIP and assurance evidence are also uploaded as time-limited Actions artifacts. The run ID and failing stage identify the failure; retries are explicit rather than blind.

## Release gates

This configuration is not G23 independent validation, G24 certification, non-regression proof, rollback verification, or production activation. Those gates must be completed independently against an exact reviewed commit before release.
