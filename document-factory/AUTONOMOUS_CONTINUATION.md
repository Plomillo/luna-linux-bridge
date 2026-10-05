# GitHub-native autonomous continuation — Document Factory

MISSION_ID=DOCUMENT_FACTORY_AUTONOMOUS_CONTINUATION_V1
AUTHORITY=Louksna.md
ASSURANCE=PUAC2.md
BASE_BRANCH=candidate/document-factory-v1-20261005
MAIN_MUTATION=FORBIDDEN
TRUST_ROOT_MUTATION=FORBIDDEN
LOUKSNA_MUTATION=FORBIDDEN
PUAC2_MUTATION=FORBIDDEN
AUTO_MERGE=FORBIDDEN
CERTIFICATION_PROPAGATION=FORBIDDEN
FAILURE_POSTURE=FAIL_CLOSED

## Starting checkpoint

The current operational chain has already produced a successful exact-head run with:
- candidate producer PASS;
- independent producer PASS;
- G23 PASS;
- G24 PASS;
- pinned immutable reusable trust-root.

Continue from the existing Document Factory. Do not rebuild it from scratch.

## Worker

GitHub Copilot coding agent is the intended GitHub-native worker for this mission.
Create a new working branch from `candidate/document-factory-v1-20261005`.
Open a pull request back to that candidate branch.
Do not merge the PR yourself.

## Mission

Finish the technical skeleton as a generic, source-first, Git-native, multiformat document factory. Work sequentially and preserve all existing evidence, claims and negative tests.

1. Remove remaining task-specific coupling from the engine and workflows. The UNIACC neuroplasticity profile must remain a profile/fixture, never engine logic.
2. Harden generic profile ingestion and validation for future rubrics/instructions without semantic inference.
3. Implement a typed rubric compiler: requirement -> claim -> validator obligation -> evidence row -> rubric result. Machine-checkable and human/G23 criteria must remain distinct.
4. Harden the source ledger and citation pipeline. Add CSL/Pandoc citation support and APA-compatible validation where supported. Never fabricate DOI, author, page, URL or bibliographic metadata.
5. Admit an audiovisual validation provider. Resolve and pin FFmpeg/ffprobe provenance/version/hash where an authoritative reproducible source supports it; otherwise record the unresolved property and keep that claim excluded. Add profile-driven duration/orientation/stream metadata validation.
6. Add profile-driven image constraints (declared DPI and pixel dimensions) without treating DPI and pixel dimensions as equivalent concepts.
7. Strengthen DOCX/PPTX/PDF/XLSX structural validation and evidence generation. Keep source Markdown/JSON/CSL authoritative.
8. Preserve writer-provider separation: a writer may produce candidate text but can never issue G23/G24.
9. Extend claims, risk register, traceability, monitoring, test plan and negative tests for every newly implemented capability. No new capability may be silently covered by an old certificate.
10. Add reproducible build documentation and a clean end-to-end demonstration using synthetic content only. Do not generate or submit the student's actual assignment as part of infrastructure certification.
11. Run all local tests available in the GitHub runner. Preserve failures. Do not weaken tests or assurance rules to obtain green status.
12. Finish by opening one PR to `candidate/document-factory-v1-20261005` with an exact inventory of implemented items, unresolved items, tests, provenance and scope exclusions.

## Absolute boundaries

Do not modify:
- `main`;
- `Louksna.md`;
- `PUAC2.md`;
- `recovery/**`;
- `scripts/assurance/**`;
- `trust-root/document-factory-v1-20261005`;
- canonical IDs, agents, commands, engines, CFEs, axioms or frozen documents.

Allowed work:
- `document-factory/**`;
- candidate-specific tests/docs;
- a candidate workflow change only when strictly necessary and without weakening the immutable trust-root call.

If evidence is missing, use UNKNOWN/HOLD. Do not infer a PASS.
If an upstream artifact cannot be pinned or verified, keep the capability excluded and continue with independent tasks.
