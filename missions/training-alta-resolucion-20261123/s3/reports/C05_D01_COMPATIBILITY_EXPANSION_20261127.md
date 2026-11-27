# D01 source-grounded compatibility expansion — 2026-11-27

Status: implementation and plan readiness only. This report does not claim restricted-container execution or C05 certification.

- Governing source: `PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt`
- Source Git blob: `c259b6bca37fdfc9711ffda07b3e388e3b9774ff`
- Added source-bound normal plans: MGL5-INF-0033, 0034, 0035, 0039, 0040, 0049.
- Completed missing negative and boundary controls: MGL5-INF-0013, 0014, 0015.
- New registered capabilities: yaml_types, yaml_ambiguous, protobuf_compat, schema_migrate, unknown_field, mixed_roundtrip.
- Independent oracles: fixed typed YAML vectors, explicit YAML 1.2 scalar semantics, independent protobuf wire parsing, schema invariant comparison, unknown-field preservation checks, and a fixed MessagePack byte encoder.
- Additional dependencies: PyYAML and msgpack, bounded to major versions below the next breaking major.
- Expected plan census after CI compilation: 88 complete plans / 912 NOT_RUN. This is readiness, not execution.
- Required next gate: run all 88 plans in the pinned restricted Docker image (440 separate operations), inspect persisted evidence, then independently validate all 88 dossiers.
- Remaining 912 cases remain NOT_RUN. C05 remains NOT_PASSED.
