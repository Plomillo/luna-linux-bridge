# Auditoría de defecto del certificador — run #224

STATUS=CORRECTIVE_PATCH_PROPOSED
ROOT_CAUSE=UNGUARDED_NULL_EVIDENCE_PATH
CERTIFICATION=NOT_GRANTED

## Identificación

- Repository: `Plomillo/luna-linux-bridge`
- Operational branch at run: `fix/lunita-v18-rootfs-bound-checkpoint-20261109`
- Commit: `ce973ee7e5b7c2854fc0ae6ff37a3b568d78b093`
- Workflow run: `43350661978` (#224)
- Target/independent job: `131641413956`
- Candidate: `G06_REBUILD_CANDIDATE_R1`, version `1.8.0`

## Evidencia directa del defecto

El step 21, `Run the existing v1.8 independent rootfs and JASP certification lane`, terminó failure. El traceback registra:

```
update_independent_report()
  -> jasp_case_accepted()
  -> evidence_path = pathlib.Path(row.get("evidence_path", ""))
TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'NoneType'
```

La causa inmediata es que el caso JASP contiene explícitamente `evidence_path=null`; `dict.get(key, default)` devuelve `None` cuando la clave existe con valor null, por lo que el default vacío no protege la construcción de `Path`.

El efecto observado fue aborto no controlado de la generación del informe independiente. Esto no equivale a un PASS ni a un rechazo del contenido de la imagen: significa que el certificador no terminó de evaluar los controles y no produjo evidencia S32.

## Controles del mismo run

- Direct target runtime acceptance y pruebas de motores E01–E15: PASS.
- Aplicaciones heredadas: PASS.
- Build y round-trip de `LUNITA.squashfs`: PASS.
- Carga del artefacto candidato: PASS (artifact ID `14004786933`; ZIP SHA-256 `e4e21ee7c3759d505db7e97c113ab22fb698888a03d3ea8f4ef0df38531495b0`; es hash del ZIP, no de la imagen interna).
- Step 21: FAILURE por TypeError del certificador.
- Step 22 (S32): SKIPPED.
- Certificado funcional y bundle certificado: NOT ISSUED.
- Recolección de evidencia y limpieza de mounts: PASS.

## Corrección propuesta

El predicado de aceptación ahora requiere que el registro sea un dict y que `evidence_path` sea un string no vacío. La resolución, existencia, no-symlink y hash del archivo se validan dentro de un bloque controlado; errores de ruta o E/S retornan False. Esto hace que la evidencia inválida permanezca BLOCKED y permite que el informe independiente se genere con el subgate fallido, en vez de abortar la fase.

Se añade prueba de regresión con los cuatro casos JASP presentes y `flatpak_launch.evidence_path=null`. La expectativa es que el informe se emita y que `jasp_packaged_fixture_nonregression=BLOCKED`, `all_case_evidence_hashes_current=false`, sin mission completion claim.

## Límite de la corrección

Esta corrección solo repara el tratamiento de referencias de evidencia inválidas. No cambia el fixture Death Penalty, no modifica el resultado estadístico, no cambia los return codes, no ajusta tolerancias, no marca el caso JASP como aprobado y no otorga certificación. El mismatch entre resultados históricos y JASP 0.98.8 sigue siendo un bloqueo independiente. La corrección requiere CI contractual y una nueva ejecución funcional completa sobre el commit que la incorpore.

## AX-LUN-028

El requisito de referencia de evidencia ausente/nula/malformada fail-closed y sin excepción no controlada se incorpora de forma append-only al documento de axiomas. La evidencia histórica de run #224 queda preservada.
