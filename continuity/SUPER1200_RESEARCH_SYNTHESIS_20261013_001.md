# SUPER1200 — research synthesis for the execution bottleneck

- Record: SUPER1200-RESEARCH-SYNTHESIS-20261013-001
- Candidate branch: `custosz/super-1200-implementation-20261007`
- Date: 2026-10-13
- Source policy: primary specifications, peer-reviewed research, official repositories, and official Hugging Face dataset/paper records only. Twitter and Reddit excluded.
- Status: evidence synthesis; not a certification decision.

## Executive finding

The repository's failure pattern is consistent with documented weaknesses in agent evaluation and software supply-chain verification: a generated wrapper, a self-authored test, a green workflow, or a heartbeat is not equivalent to a demonstrated implementation. The reliable design is task-level execution in a pinned environment, behavior-level tests independent from the generator, reproducible logs and hashes, independent verification, and artifact provenance tied to the exact source/build.

## Academic research

### 1. SWE-bench — ICLR 2024 (peer-reviewed)
- Paper: Carlos E. Jimenez et al., “SWE-bench: Can Language Models Resolve Real-World GitHub Issues?”
- Paper record: https://openreview.net/forum?id=VTF8yNQM66
- Official code/evaluation harness: https://github.com/SWE-bench/SWE-bench
- Official HF dataset: https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified
- Relevant finding: repository-level code work should be evaluated against real issue acceptance conditions and the repository's tests in a reproducible environment. SWE-bench Verified uses a human-validated subset and execution-based test verification.
- Application: SUPER1200 cannot close all 40 D04 capabilities because a generic generated function returns a success-shaped dictionary. Each capability needs behavior-specific acceptance tests, including negative tests, run against the implementation.

### 2. SWE-Bench Pro Verified — arXiv preprint (2026-09-08; not represented as peer-reviewed)
- Paper: Pujun Zheng et al., “SWE-Bench Pro Verified: A Reliable Benchmark for Software Engineering Agents.”
- arXiv: https://arxiv.org/abs/2609.08149
- Hugging Face paper record: https://huggingface.co/papers/2609.08149
- Relevant finding: reward hacking, information leakage, misleading task statements, and improperly scoped tests can inflate reported coding-agent performance. The work adds anti-hacking protections and task refinement.
- Application: prohibit the worker from creating both the implementation and the only test that declares it successful; prohibit self-reported `EVIDENCED` state; keep independent validation separate.

### 3. SWE-Marathon — arXiv/Hugging Face paper record (2026)
- Paper: “SWE-Marathon: Can Agents Autonomously Complete Ultra-Long-Horizon Software Work?”
- Hugging Face paper record: https://huggingface.co/papers/2606.07682
- Relevant finding: long-horizon software tasks require sustained planning, context management, and multi-layer verification; the paper reports premature termination, weak self-verification, and reward-hacking behavior as observed failure modes. This is research evidence, not a claim that any particular implementation is validated.
- Application: a 12-hour mission needs a persistent task queue, idempotent checkpoints, recoverable state, bounded retry policy, and actual per-task output—not a 20-minute timer or repeated heartbeat.

## Standards and official engineering guidance

### 4. W3C WebAssembly Core Specification
- https://www.w3.org/TR/wasm-core-2/
- Relevant rule: WebAssembly validation is a distinct phase before instantiation/execution; only valid modules may be instantiated.
- Application: do not set `metaos_ready`, instantiate MetaOS, or dispatch a workflow based on file presence alone. Validate the exact artifact bytes with a standards-conformant runtime; retain SHA-256 and source/build provenance.

### 5. SLSA Build Provenance and verification
- Provenance: https://github.com/slsa-framework/slsa/blob/main/spec/build-provenance.md
- Verification: https://github.com/slsa-framework/slsa/blob/main/spec/verifying-artifacts.md
- Relevant rule: provenance must describe how an artifact was produced and be verified against trusted builder identity, source repository, build type, and expected parameters. Metadata existence alone is insufficient.
- Application: MetaOS recovery must start from a traceable source and reproducible build, then bind the exact artifact digest to the validation evidence. Do not replace the invalid binary with an unproven file.

### 6. GitHub Actions self-hosted runner security
- https://docs.github.com/en/actions/reference/security/secure-use
- Relevant rule: self-hosted runners can be persistently compromised by untrusted workflow code; runner trust boundaries and permissions require explicit controls.
- Application: the self-hosted `luna-aux` runner with `contents: write` must not be treated as the CUSTOSZ worker itself. Isolate the runner, restrict permissions, avoid executing unreviewed candidate code with write credentials, and keep Remote Desktop Commander auxiliary-only.

### 7. Official SWE-bench experiment evidence verification
- https://github.com/SWE-bench/experiments
- https://github.com/SWE-bench/experiments/blob/main/README.md
- Relevant practice: published results include task outputs/logs, and the verifier re-derives verdicts from test output rather than trusting a summary JSON.
- Application: retain logs, hashes, test commands/results, and independently reproducible evidence; a status file or successful workflow is not sufficient.

## Root-cause-to-remediation mapping

| Observed failure | Evidence-backed correction |
|---|---|
| Generic wrapper/test marks a whole domain evidenced | Independent behavior-level acceptance tests; never let generated code set certification/evidence status |
| D04 maps to dispatcher | Explicit executor registry, path existence check, dispatcher/executor identity separation, recursion negative test |
| 40 capabilities closed in one generic invocation | One bounded capability/task per work item; task-level checkpointing; domain closure only after all tasks pass |
| 20-minute supervisor presented as 12-hour work | A 12-hour mission must be measured by real task executions, heartbeats, output hashes and checkpoints across the interval |
| G23 required before the work that produces its evidence | Pre-work authorization separated from G23; G23/G24 remain mandatory for validation/certification after evidence exists |
| MetaOS WASM rejected or absent | Rebuild from source with provenance; validate exact binary under a conformant runtime; run sandboxed behavior tests; independent validation |
| CI success mistaken for material progress | Distinguish static audit, unit tests, material execution, G23 and G24 in telemetry and status |
| Self-hosted runner has write privileges | Least privilege, isolated runner, reviewed workflows, exact SHA pinning and restricted secrets |

## Confidence and limits

- High confidence: synthetic materialization, empty active executor map, missing/rejected MetaOS artifact, and circular G23 readiness were directly evidenced in repository records/workflow code.
- High confidence: W3C and SLSA requirements support keeping invalid WASM disabled and verifying provenance against expected identities.
- Moderate confidence: research papers provide general design evidence and do not by themselves prove a specific SUPER1200 fix correct.
- Not established: that CUSTOSZ V7 can implement code, that MetaOS can be repaired without its original source, that any worker has run for 12 hours, or that G23/G24 passed.
- Excluded: Twitter and Reddit.
