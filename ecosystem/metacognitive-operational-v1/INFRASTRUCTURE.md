# INFRASTRUCTURE — MINIMUM STABLE TOPOLOGY

## Control plane
- GitHub repository: manifests, contracts, policy, small evidence and READMEs.
- GitHub Actions: ephemeral build/test/analysis workers.
- SHA-pinned Actions; least-privilege workflow permissions.
- PR/check boundary before admission.

## Compute plane
- GitHub-hosted Linux for general compute and Debian 13/Trixie containers.
- GitHub-hosted Linux direct host lane for Android API 36/37 emulator workloads where nested-container acceleration is unsuitable.
- GitHub-hosted Windows lane for Windows-specific builds/tests.
- Worker scheduler scales only from measured demand; 64 is a ceiling candidate, not a default.
- CUSTOSZ mission routing may touch the authorized auxiliary runner only for bounded ingress/routing; heavy work remains cloud-hosted.

## Remote data plane
Install/standardize only when demanded by an admitted mission:
- `rclone` for governed remote transfer.
- `duckdb`, `pyarrow`, `polars`, `huggingface_hub`, `datasets`, `fsspec` for remote corpus streaming/query.
- PostgreSQL + pgvector **or equivalent admitted store** for durable indexed state; do not provision automatically.
- S3-compatible/object-store or Hugging Face storage adapter for large content-addressed objects.
- OpenTelemetry SDK/Collector for traces/metrics/logs.
- Durable workflow adapter such as Temporal only if long-running missions prove GitHub Actions alone insufficient.
- Event-stream adapter such as NATS JetStream/Redpanda/Kafka only for true continuous/low-latency streams.

## Security/provenance tool candidates
- cosign
- syft
- trivy or grype
- opa/conftest
- oras

These are candidates, not silently installed dependencies. Each requires version pin, official source, provenance, license, functional test, rollback and admission evidence.

## Storage rule
Git stores hashes/manifests/READMEs, not bulk corpus bytes. Large durable payloads live in the data plane and are referenced by immutable digest.
