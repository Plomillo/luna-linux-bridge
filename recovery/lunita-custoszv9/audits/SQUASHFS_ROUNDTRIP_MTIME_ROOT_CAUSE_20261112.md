# Auditoría de causa raíz — SquashFS round-trip y precisión temporal

**Auditoría:** `SQUASHFS_ROUNDTRIP_MTIME_ROOT_CAUSE_20261112`  
**Repositorio:** `Plomillo/luna-linux-bridge`  
**Rama de origen:** `fix/lunita-v18-rootfs-bound-checkpoint-20261109`  
**HEAD que falló:** `68f3c7be05e9599813aaa02a428ca72e3efbf3c3`  
**Workflow:** `43322862456`  
**Job:** `131548521156` — Lunita v1.8 real target and independent acceptance  
**Step:** 19 — Build and round-trip verify LUNITA.squashfs  
**Fecha del fallo:** 2026-11-12 23:00:32 UTC  
**Objeto:** `scripts/lunita/package_candidate_squashfs_v1.py`

## 1. Evidencia primaria

El log de GitHub Actions devolvió:

```json
{
  "status": "BLOCKED",
  "error": {
    "error": "SquashFS extraction does not reproduce the candidate rootfs manifest",
    "source_entries": 465628,
    "extracted_entries": 465628,
    "missing_paths": [],
    "extra_paths": [],
    "changed": [
      {
        "path": "opt/lunita/engines/runtime_engines_v1/vendor/python3.12/site-packages/charset_normalizer/__pycache__/constant.cpython-312.pyc",
        "fields": {
          "mtime_seconds": [1794523804, 1794523803]
        }
      }
    ]
  },
  "certification": "NOT_GRANTED"
}
```

La evidencia establece que el empaquetado y la extracción contuvieron el mismo número de entradas, sin rutas ausentes ni adicionales. El único delta reportado fue la marca temporal entera de un archivo. No es evidencia de corrupción de contenido, pero sí es un incumplimiento del contrato de metadatos exactos. El paquete quedó bloqueado correctamente.

## 2. Análisis de causa raíz

El manifiesto calculaba las marcas temporales con `int(stat_result.st_mtime)`. `st_mtime` es un valor de punto flotante. Una marca situada extremadamente cerca del límite del segundo siguiente puede representarse como el siguiente segundo por redondeo binario antes de aplicar `int()`.

Ejemplo determinista del límite:

- marca nanosegundo exacta: `1794523803999999999`;
- segundo representable por el inode SquashFS: `1794523803`;
- conversión flotante susceptible de redondear a `1794523804.0`;
- manifiesto anterior: `1794523804`;
- inode extraído: `1794523803`.

La evidencia histórica no conservó el `st_mtime_ns` original del archivo afectado; por ello la atribución del caso concreto a ese redondeo es una hipótesis de causa raíz de alta correspondencia, no una afirmación de medición retrospectiva de aquellos nanosegundos. La hipótesis es falsable mediante el test de frontera añadido.

## 3. Corrección mínima implementada

Commit:

`3aac9f57efadf19194c9e411088095f173911b0b`

Cambios en `tree_manifest`:

```python
"mtime_seconds": directory_stat.st_mtime_ns // 1_000_000_000
"mtime_seconds": before.st_mtime_ns // 1_000_000_000
```

Se aplica tanto a directorios como a entradas. La resolución queda explicitada mediante división entera, sin float. No se eliminan metadatos, no se introduce tolerancia de ±1 segundo, no se cambia el contenido, no se omiten rutas y no se debilita la comparación del manifiesto.

## 4. Prueba de regresión añadida

El `self_test()` del empaquetador crea `etc/mtime-boundary.bin`, asigna `st_mtime_ns=1794523803999999999`, y exige:

`mtime_seconds == st_mtime_ns // 1_000_000_000`

La misma fixture participa en dos empaquetados completos, extracciones y comparaciones de manifiesto ya existentes. Así, el test verifica tanto la conversión del manifiesto como el comportamiento real de `mksquashfs/unsquashfs`.

El workflow contractual ejecuta explícitamente:

`python scripts/lunita/package_candidate_squashfs_v1.py --self-test`

## 5. Estado epistemológico y autorización

`PRIMARY_FAILURE_EVIDENCE = PASS`  
`ROOT_CAUSE = FLOAT_TIMESTAMP_ROUNDING_AT_INTEGER_SECOND_BOUNDARY (PROBABLE; BOUNDARY_TEST_ADDED)`  
`MINIMAL_CORRECTION = IMPLEMENTED`  
`REGRESSION_TEST = ADDED_NOT_YET_EXECUTED_ON_OPERATIONAL_HEAD`  
`FULL_REVALIDATION = PENDING`  
`CERTIFICATION = NOT_GRANTED`

PR de corrección: [#171](https://github.com/Plomillo/luna-linux-bridge/pull/171).

El workflow #43326401590 estaba activo en el paso de reconstrucción del rootfs contra el HEAD anterior a esta corrección. No se modificó esa rama ni se canceló la ejecución. La corrección solo puede considerarse validada después de integrar el cambio, pasar el self-test contractual, reconstruir el rootfs, volver a generar `LUNITA.squashfs`, pasar el round-trip exacto, completar la aceptación independiente JASP/rootfs, S32, stable release y certificar el mismo SHA-256 de imagen.

**Regla de cierre:** el defecto solo se cierra si el nuevo round-trip conserva exactamente el manifiesto entero representable. Una repetición sin el caso de frontera no demuestra que el defecto específico esté corregido.
