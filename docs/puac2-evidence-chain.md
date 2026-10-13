# PUAC-2 evidence-chain contract and remediation record

Status: implementation proposal on the PR branch; operational certification remains **HOLD** until the protected target-host workflow and both independent signatures are verified.

## Defect repaired

The former `.github/workflows/puac2-e2e.yml` mixed pull-request preflight and privileged release certification. Its manual-release preflight required `evidence/mtls-certification.json` before host validation, G23, and G24 ran; those later jobs then checked out the repository again and expected the same manifest without an artifact handoff. That was a broken evidence dependency and could not be a reliable release path.

The workflow is now explicitly PR-only and non-certifying. It runs source/regression checks, emits a candidate-bound preflight report, and says in the Actions summary that host mTLS, operational tests, rollback, G23, and G24 were not performed. The privileged chain remains in `.github/workflows/puac2-autonomous.yml`, whose host/G23/G24 jobs remain excluded from `pull_request` events. This boundary must not be weakened to make PR checks green.

## Evidence production and transfer contract

The autonomous workflow is the only configured workflow that attempts the complete operational chain:

1. **Source validation:** compile and execute the regression suite; produce `tests.txt`, `tests.json`, and the `puac2-source-evidence` artifact. A test run with zero tests, failures, or no passed tests is not PASS.
2. **Host validation:** run only on the dedicated `self-hosted, linux, louksna-mtls-host` runner; verify root-owned, non-symlinked host configuration, active service, and a certificate-verified mTLS handshake. Never upload keys, credentials, or the mTLS configuration.
3. **Host test and rollback reports:** both reports must be JSON, bound to the exact candidate SHA, and explicitly pass:
   - Host report: `schema=PUAC2_HOST_TEST_REPORT/1.0`, `status=PASS`, `candidate_commit=<exact GITHUB_SHA>`, integer `tests_passed >= 1`, and `tests_failed=0`.
   - Rollback report: `schema=PUAC2_ROLLBACK_REPORT/1.0`, `status=PASS`, `candidate_commit=<exact GITHUB_SHA>`, and `rollback_verified=true`.
   The workflow copies the reports into the host evidence artifact and records SHA-256 hashes.
4. **G23:** download source and host artifacts; independently validate the test report, host report, rollback report, candidate binding, and the recorded SHA-256 values; then sign the evidence bundle with the G23 Ed25519 key. G23 must not share an identity or signing key with G24.
5. **G24:** independently verify the G23 signature and bundle, check the distinct G24 identity/key, create the certification manifest, and run `scripts/puac2_mtls_gate.py` with trusted public keys.
6. **Final evidence:** retain the G23 attestation and G24 certification/manifest/decision artifacts. A workflow-level success is not sufficient unless the required jobs ran and the final gate returned `CERTIFICATION_CHAIN_VERIFIED`.

The host report schema is intentionally strict. Existing host report producers must be adapted to this contract before the protected run can pass. A missing report, malformed JSON, stale candidate SHA, non-PASS status, hash mismatch, absent signing identity, or failed signature must stop the chain.

## Operational prerequisites not provable from a pull request

The code cannot provision or attest for the real host on its own. Before certification, repository administrators/operators must verify the dedicated runner is authorized and isolated; the protected host environment and service are configured; the required environment variables and secrets are provisioned; G23 and G24 identities are independently controlled; and their public keys match the signing keys. Do not expose secrets in logs or artifacts. Do not dispatch the privileged workflow merely to test whether credentials exist.

The schedule in `.github/workflows/puac2-autonomous.yml` runs on the default branch. Changes on a PR branch are not part of the scheduled production chain until the PR is reviewed and merged. This remediation does not merge the PR, change repository permissions, change branch protection, provision credentials, or claim operational certification.

## Academic and primary technical basis

These sources are used for design principles, not as proof that this repository has passed:

1. Torres-Arias et al., **“in-toto: Providing farm-to-table guarantees for bits and bytes,”** USENIX Security Symposium 2019, pp. 1393–1410. The paper motivates verifiable, ordered supply-chain steps and integrity across actors and artifacts. [USENIX paper page](https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias).
2. Samuel, Mathewson, Cappos, and Dingledine, **“Survivable Key Compromise in Software Update Systems,”** ACM CCS 2010, DOI [10.1145/1866307.1866315](https://doi.org/10.1145/1866307.1866315). It motivates key separation, trust boundaries, revocation, and resilience to signing-key compromise.
3. Thariq and Ekanayake, **“ARGO-SLSA: Software Supply Chain Security in Argo Workflows,”** arXiv:2503.20079 (2025). It studies cryptographic signing and provenance attestations in multi-step workflow systems. [arXiv record](https://arxiv.org/abs/2503.20079).
4. **in-toto Specification 1.0.0** (primary technical specification, 2023): requires verifiable steps, authorized actors, and integrity of materials across the supply chain. [Specification source](https://github.com/in-toto/specification/blob/master/in-toto-spec.md).
5. **SLSA Build Provenance and Distribution specifications** (primary technical specifications): provenance must identify how artifacts were produced and must be distributed in a form consumers can verify. [Build provenance](https://github.com/slsa-framework/slsa/blob/main/spec/build-provenance.md), [distribution](https://github.com/slsa-framework/slsa/blob/main/spec/distributing-provenance.md).
6. GitHub's official **Secure use reference** warns against running untrusted pull-request code on self-hosted runners and against mixing privileged contexts with untrusted checkout. [GitHub Actions security guidance](https://docs.github.com/en/actions/reference/security/secure-use).

No Twitter/X, Wikipedia, or Reddit sources were used.

## Acceptance criteria

- PR workflow tests only the candidate and labels itself non-certifying.
- No privileged runner or release dispatch is reachable from `pull_request`.
- Every evidence object is bound to the same 40-character candidate commit.
- Host/rollback reports have explicit PASS semantics and independently verified SHA-256 hashes.
- G23 and G24 have distinct identities and Ed25519 keys; signatures and bundle hashes verify.
- The final gate returns `CERTIFICATION_CHAIN_VERIFIED`.
- Evidence artifacts and workflow logs are retained for review.
- Any missing prerequisite yields HOLD/failure, never inferred certification.
