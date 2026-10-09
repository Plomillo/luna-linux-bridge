# Distribution clearance gate — 0.4.0-3

**Current status: HOLD.** This gate prevents the CI workflow from staging or uploading a Debian package until the repository contains evidence-backed clearance. It does not itself grant rights, certify authorship, or replace independent review.

## Required evidence before distribution

The workflow requires both:

- `debian/copyright`: valid DEP-5 metadata covering every file shipped in the source/binary package, with copyright statements and license texts based on evidence, not assumptions.
- `docs/DISTRIBUTION_CLEARANCE.json`: a reviewed clearance record whose `status` is exactly `CLEARED` and which confirms all of the following with evidence references:
  - exact packaged file coverage and source-provenance review complete;
  - third-party content and applicable notices/licenses resolved;
  - redistribution permission established for every shipped file;
  - maintainer contact verified;
  - independent review completed by an identified reviewer;
  - the clearance record refers to the exact candidate commit and the DEP-5 file.

The clearance JSON must include non-empty fields `candidate_commit`, `debian_copyright_sha256`, `evidence_refs`, `reviewer`, and `reviewed_at_utc`; booleans `file_coverage_complete`, `third_party_clearance_complete`, `redistribution_authorized`, `maintainer_contact_verified`, and `independent_review_passed` must all be `true`. These are assertions to be backed by attached evidence; merely filling the fields is not proof.

## Fail-closed behavior

Until the required evidence exists and validates, CI may still run diagnostic build and test steps, but it must not stage or upload the `.deb` as an artifact. The CI run is not a release, and a successful compile/test does not imply redistribution authorization.

No guessed license, copyright holder, year, email address, or third-party permission may be inserted to satisfy this gate. If a component remains uncleared, exclude it only through a reviewed, documented packaging change or obtain the necessary evidence before distribution.

## Current unresolved facts

At the time this gate was added, the candidate had no `debian/copyright` and no independently evidenced clearance record. Therefore the expected current result is `DISTRIBUTION_GATE=HOLD`, with package artifact upload blocked.
