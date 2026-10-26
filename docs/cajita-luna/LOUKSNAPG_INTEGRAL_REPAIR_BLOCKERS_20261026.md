# LOUKSNAPG model repair — observed functional blocker report

Audit record: [GitHub Actions run 40284216661](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40284216661)  
Source commit: `d09f79a088781d26fc5b1c3e830db9abfb42c147`  
Candidate: `LOUKSNAPG.md`, 371,947,716 bytes  
Candidate SHA-256: `febfd2ca07f5238b3ab69e526158532a116c429a608397df86b0136f468f5f84`  
Decision: **`HOLD_NOT_CERTIFIED`**

This is historical, commit-bound evidence from the cited run. It is not evidence for subsequent branch commits or a new candidate.

## Observed outcome

The package identity validator passed and the six source-bound engine smoke checks passed within their limited scope. The runtime smoke harness itself returned `0`, but the model-task harness returned `3`; the integral functional gate returned `2`; G24 remained `NOT_GRANTED`. All five model processes returned successfully at the execution layer, yet **all five task-quality assertions failed**.

| Target | Quality check | Observed output excerpt | Quality-output SHA-256 | Compact candidate weights SHA-256 |
|---|---|---|---|---|
| `D01_CEREBRO_ROOT` | Repository-storage answer | `ron amongronronron among amongron amongssronron` | `9308bc822ed96f27b929493bd15837d4c54852d27ee851e6e004e57533ebfa7d` | `e2516453d09285581bd6f3bf45a4c3a9fa6431bdc3dff56e7249d30e4e294ae0` |
| `D03_TRANSCRIPCION_ROOT` | Known-speech “hello world” | `daughterziest manuscript ele` | `c2dcf834728a60f2b53b3f8668969b7b98c926d2b77a97905e5f8e3031720a6d` | `67ee70beb2fb3529270a8169fbb6bd0f538912a064a6a303bec238647b4a5f5f` |
| `D04_TRADUCCION_GENERAL` | English-to-Spanish greeting | `te te te apres te te te te who te te` | `10e494e1adfd2b16103009d2d5fe97aba97e7fb88f7447d3405e519d3159836a` | `630aad9958f9c78603852c29c382b0fe9d63e64772e21dc6367875a91dc6a28f` |
| `D05_DOCLING` | Invoice total 133.45 | `onationonationonation underrated underrated underrated shitty underrated` | `acee8e9dded82726b2f0cf977b4980e042c050a5d1adcc8ef40d4dd453dcd25d` | `4a13b916b63b682a28c8fe89fc608b90d3bf5a8a77cb0988e1e19131c64ebc88` |
| `D06_ANALISIS_AVANZADO` | Arithmetic: 2 + 2 | `irts airways` | `b1a75ce6640d3d5f39e985ad1e0d4d54e76861b8294f6d997fba2f5e66743a67` | `01eba827b9dd001a2352f0fd28a0bea229d3a5b3a78a41f3ea3e7c6c21995f56` |

The exact machine-readable evidence, including model-output hashes, source commit, safety state and blockers, is recorded in `LOUKSNAPG_INTEGRAL_REPAIR_BLOCKERS_20261026.json`.

## Provenance and compression evidence

The repository's compression metadata reports GPT-OSS rank-1 randomized SVD with aggregate relative Frobenius error `0.9983363410727844`. Qwen3 rank-12 reports residual `0.9964067735222465` before factor INT8 quantization and aggregate relative Frobenius error `0.9964088220513415` after it. Whisper and Seamless candidates are low-rank INT8-factor representations at ranks 29 and 4 respectively. The Docling candidate uses a custom NanoQuant-family low-rank binary factorization with 2.5% embedding rank fraction and 2% text rank fraction.

Those metrics and the observed outputs establish that successful model loading/forward execution must not be interpreted as recovered task behavior. The compact factors do not carry the discarded higher-rank components needed to reconstruct the original weight matrices. The current workflow did not download heavy original checkpoints, consistent with the prohibition.

## Worker and certification state

CUSTOSZ V9 completed a bounded package-build/evidence action; that does not establish a model-repair mission. The Kestra job at [run 40284216700](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40284216700) failed closed because `KESTRA_URL` and `KESTRA_API_TOKEN` were absent. No Kestra execution ID was produced. No signed product-functional G23 attestation or separate signed G24 grant exists.

The six source-bound target-engine smoke checks are limited engine checks; task coverage for all 21 registered targets remains `NOT_ESTABLISHED`. Contract integrity, package integrity, finite logits, non-empty outputs, and startup smoke tests do not override these failures.

## Governed conclusion

**Current disposition: `HOLD_NOT_CERTIFIED`.** The evidence does not support an integral model-repair or certification claim. With heavy checkpoint downloads prohibited and model identity substitution unauthorized, recovery of the discarded model information is not evidenced by the present repository. Any future candidate must show material repair of each model's weights, task-level quality passes, all 21 target results, persistent artifact-bound telemetry, a real Kestra execution receipt, independent signed G23, separate signed G24, non-regression, host coverage and rollback verification before release eligibility can be considered.
