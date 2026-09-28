# README — conclusiones verificables del despacho CUSTOSZ V7

El presente informe registra solamente comprobaciones realmente realizadas. No constituye G23/G24 ni autoriza instalaciones.

## Identidad y plazo

- Misión: SYMPHYLAX_R1_LUNA_R4_FINAL_COMPLETION_RESEARCH
- Inicio UTC: 2026-09-28T03:44:08.349144+00:00
- Fin UTC: 2026-09-28T03:44:10.547403+00:00
- Duración real: 2.198 segundos.
- Plazo máximo: 1200 segundos; WITHIN_20_MINUTES
- Acuse nativo CUSTOSZ: NOT_VERIFIED
- Acuse runtime: SELFTEST_AND_READONLY_JOURNAL_PASS
- GitHub Actions run ID: 36374864210
- Commit examinado: 0550bd1e3fc77b09eaa8acb5d34e8e5e3b934b3c

## Pruebas reales

| Prueba | Estado | Evidencia |
|---|---|---|
| A0 | PASS | bytes=11536067, sha256=5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9 |
| PUAC2 | PASS | bytes=62950, sha256=c872ab8d31e0e301de93ab06047294424d309d947f225e62148cee8265b15869 |
| CUSTOSZ | PASS | bytes=49379, sha256=dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2 |
| RUNTIME | PASS | bytes=10376, sha256=a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67 |
| METAOS | PASS | bytes=2442, sha256=5d8f1239e3a0b452be722078760b000afc22af0a64f93ffb0a1f74024f15aed0 |
| MISSION | PASS | bytes=17596, sha256=f4811c8c5b6ab6186f70b69620972ae49c3e2718a956d6cfae72df07c19ac5da |
| Runtime API selftest and mission journal | SELFTEST_AND_READONLY_JOURNAL_PASS | anatomy=['GovernanceKernel', 'MissionController', 'CognitivePlane', 'MetacognitivePlane', 'ExecutorRegistry', 'ProcessSupervisor', 'TimeBudgetController', 'CheckpointStore', 'EvidenceJournal', 'TelemetryFabric', 'SourceRegistry', 'ResumeManager', 'Fa |
| CUSTOSZ v07-status | PASS | exit_code=0, reported_status=None, version=7.0.0-candidate |
| CUSTOSZ v07-selftest | PASS | exit_code=0, reported_status=PASS, version=None |
| CUSTOSZ native mission-start | FAIL_CLOSED | exit_code=2, detail=WORKSPACE_AMBIGUOUS_OR_MISSING:[] |
| A1 original bytes | PASS | sha256=2114188988126aa7a9650c131526c9d7c54ad351db315635569a317114f4eb51, bytes=11542631, ref=origin/staging/architecture-louksnamejorada-20260927, path=LOUKSNAMEJORADA.md |
| R4 Skeleton original bytes | PASS | sha256=fb9fad37994e684ad54b1ffc2762660eebcb8e41bd9c4ba685ffac55217d5b0f, bytes=24964, ref=origin/staging/luna-r4-context-recovery-20260927, path=docs/luna-r4/source/SKELETON_CANONICO_REFERENCIA.txt |
| CAS source manifest | PASS | expected=252, github_uploaded=4, github_pending=248 |
| Installation authorization contract | PREPARATION_INERT | user_authorized=False, automation_armed=False |

## Conclusiones

- The original CUSTOSZ executable was invoked. Its mission-start controls a supervisory clock; it is not an autonomous researcher without an authorized executor binding.
- The original runtime API accepted a read-only GitHub research mission in an isolated runner temporary evidence journal.
- Firefox is already uninstalled according to the owner; this research did not repeat removal.

## Contradicciones

- Staged runtime hash a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67 differs from runtime hash 4e9bf0e799487ea0fd6a6d32359176bdce996010e33ed151ce0f186155d11df0 stated in the R4 Skeleton; variant and provenance require reconciliation.

## Bloqueos

- Native CUSTOSZ requires a real resolved LUNA_PROJECT workspace; never manufacture one to fake receipt.

## No realizado

- No se instaló ningún componente en el host ni se activó un runtime de producción.
- No se tocó Windows, EFI, GPT, particiones ni PROYECTOS.
- No se obtuvieron dictámenes independientes G23/G24.
- No se realizó investigación externa fuera del repositorio y sus artefactos.
- Un selftest de PYZ no equivale a una misión de ingeniería completa.

## Siguiente hito
Resolver los bloqueos documentados; evaluar adaptador de ejecución autenticado y pruebas independientes. F3-DISK exige autorización separada H2/H4.

[Misión íntegra](MISION_MAESTRA_DEFINITIVA.md) · [Orden GitHub #5](https://github.com/Plomillo/luna-linux-bridge/issues/5) · [Evidencia](RESEARCH_EVIDENCE.json)


## Despacho material CUSTOSZ + Runtime run 36376615311

Evidencia de ejecución: https://github.com/Plomillo/luna-linux-bridge/actions/runs/36376615311

El trabajo pesado de esta etapa se ejecutó en GitHub-hosted; no constituye activación de producción en LOUKSNA ni autorización F3-DISK.

~~~json
{
  "ended_utc": null,
  "g23": null,
  "g24": null,
  "host_disk_mutation": null,
  "host_installation": null,
  "mission_id": null,
  "research_result": null,
  "runtime_dispatch": null,
  "started_utc": null,
  "status": "RUNTIME_DISPATCH_NO_RESULT",
  "user_host_ram_heavy_research": null
}
~~~


## Despacho material CUSTOSZ + Runtime run 36376796627

Evidencia de ejecución: https://github.com/Plomillo/luna-linux-bridge/actions/runs/36376796627

El trabajo pesado de esta etapa se ejecutó en GitHub-hosted; no constituye activación de producción en LOUKSNA ni autorización F3-DISK.

~~~json
{
  "ended_utc": "2026-09-28T04:13:48.202602+00:00",
  "g23": "HOLD",
  "g24": "HOLD",
  "host_disk_mutation": false,
  "host_installation": false,
  "mission_id": "MIS-6d75cad1fb234f099a4d",
  "research_result": {
    "cas": {
      "content_validation_pending": true,
      "expected": 252,
      "pending": 248,
      "uploaded": 4
    },
    "conclusions": [
      "A0, A1, PUAC2, Skeleton and mission identities were verified on GitHub-hosted compute.",
      "The native CUSTOSZ continuation is registered on the real LUNA_PROJECT workspace; this material research is bound to the same mission_id without consuming user-host RAM.",
      "The staging runtime is selected by its staging manifest but its SHA-256 differs from the generic Skeleton runtime pin; host activation remains blocked until provenance/variant reconciliation.",
      "PUAC2 remains a 2.0.0 candidate with G23/G24 not granted; it may govern assurance requirements but cannot self-certify.",
      "CAS transfer completion and semantic runtime validation remain separate; the GitHub branch still records pending CAS objects.",
      "No installation, Windows/EFI/GPT/PROYECTOS mutation or reboot was performed."
    ],
    "mission_id": "MIS-6d75cad1fb234f099a4d",
    "next_authorized_research": [
      "Reconcile selected runtime variant against the Skeleton pin and original provenance.",
      "Complete A0-A1 semantic/admission evidence without mutating canonical sources.",
      "Complete CAS Git LFS transport from an isolated clean checkout and validate destination hashes.",
      "Prepare the differential R4 component matrix and sandbox installation lots.",
      "Independently test the consent/executor bridge before any host installation."
    ],
    "puac2": {
      "candidate_2_0_present": true,
      "d01_d10_markers": 10,
      "g23_not_granted": true,
      "g24_not_granted": true
    },
    "r4": {
      "installation_performed_false": true,
      "runtime_pin_declared": "4e9bf0e799487ea0fd6a6d32359176bdce996010e33ed151ce0f186155d11df0",
      "target_os_debian13": true
    },
    "scope": "READONLY_RESEARCH",
    "status": "MATERIAL_RESEARCH_COMPLETED",
    "verified": {
      "a0_sha256": "5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9",
      "a1_sha256": "2114188988126aa7a9650c131526c9d7c54ad351db315635569a317114f4eb51",
      "mission_sha256": "f4811c8c5b6ab6186f70b69620972ae49c3e2718a956d6cfae72df07c19ac5da",
      "puac2_sha256": "c872ab8d31e0e301de93ab06047294424d309d947f225e62148cee8265b15869",
      "skeleton_sha256": "fb9fad37994e684ad54b1ffc2762660eebcb8e41bd9c4ba685ffac55217d5b0f"
    }
  },
  "runtime_dispatch": {
    "evidence_chain_head": "7c478e39b3b047835f7298d476a8a1832512296b361935c394fe7e2e70c84ebb",
    "global_step_gate": 1,
    "material_execution_proven": true,
    "result": "PASS"
  },
  "started_utc": "2026-09-28T04:13:46.506128+00:00",
  "status": "CUSTOSZ_AND_RUNTIME_MATERIAL_RESEARCH_PASS",
  "user_host_ram_heavy_research": false
}
~~~
