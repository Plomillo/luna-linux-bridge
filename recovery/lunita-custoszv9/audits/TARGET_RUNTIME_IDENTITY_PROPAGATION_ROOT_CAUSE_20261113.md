# Lunita v1.8 — Auditoría de procedencia y propagación de identidad del runtime

**Fecha:** 2026-11-13  
**Run observado:** 43337415331 (#211)  
**HEAD observado:** 7cea08fd33e36f894f98103af9492bc07e1aed54  
**Job contractual:** 131597010277 — FAILURE  
**Job target:** 131597732193 — SKIPPED  
**Estado:** CORRECCIÓN IMPLEMENTADA; PENDIENTE DE VALIDACIÓN CI  
**Certificación funcional:** NOT_GRANTED

## 1. Evidencia primaria del run #211

El primer full run posterior al merge de PR #173 terminó con failure en el job contractual, paso 24 (Execute target-side overlay and INT8 receipt acceptance). Los 15 tests de E02–E15 en el job contractual pasaron, al igual que los tests de gateway, launcher y overlay/checkpoint. El test nuevo de mountpoint por intento también pasó.

Falló un test adicional de diagnóstico legacy: test_flatpak_diagnostic_compares_inherited_and_clean_guest_environments. La traza muestra que diagnose_flatpak_smoke() llamó expected_xdg_runtime_dir() y este rechazó la ausencia de HOST_BIND_NAME con TargetGateError. La suite del módulo registró 34 tests y FAILED (errors=1). El job target/independent fue SKIPPED y no se publicó el overlay del run.

Esta falla no demuestra un fallo de Flatpak/JASP ejecutado: el diagnóstico estaba bajo prueba unitaria con subprocess mock y el target job no se ejecutó.

## 2. Hallazgo de frontera de privilegios

La inspección del step contractual de workflow (.github/workflows/lunita-v18-direct-functional-validation.yml) demostró que invocaba:

    sudo -n env PATH="$PATH" LUNITA_ROOTFS_REAL=... LUNITA_ROOT=... LUNITA_XDG_STATE_HOME=... RUNNER_TEMP=... bash scripts/lunita/run_target_runtime_acceptance_in_container_v1.sh

El step no transmitía GITHUB_RUN_ID ni GITHUB_RUN_ATTEMPT al proceso iniciado a través de sudo/env. En el wrapper, la versión anterior construía HOST_BIND_NAME usando fallback local y 1. Por ello, la ruta ya no era el literal global /run/lunita-runtime-1000, pero el nuevo nombre podía seguir siendo idéntico entre varios workflow runs. La inspección prueba la omisión de propagación y el fallback; no prueba que run #211 haya creado o montado esa ruta, porque el target job quedó skipped.

## 3. Corrección implementada en fix/lunita-flatpak-runtime-env-propagation-20261113

- El step de GitHub Actions pasa explícitamente GITHUB_RUN_ID y GITHUB_RUN_ATTEMPT a sudo env.
- El wrapper valida que ambos valores existan y sean numéricos antes de crear estado, directorios temporales, modificar sysctls o preparar mounts.
- El wrapper no permite fallback local, cero, uno, nombre de branch ni identidad basada en hostname/tiempo.
- HOST_BIND_NAME se deriva únicamente como lunita-host-<GITHUB_RUN_ID>-<GITHUB_RUN_ATTEMPT> y se exportan ambas variables y HOST_BIND_NAME a los procesos descendientes.
- El wrapper emite LUNITA_WORKFLOW_IDENTITY con run ID, attempt y host bind name.
- target_runtime_acceptance_v1.py comprueba que HOST_BIND_NAME sea exactamente la composición del run ID y attempt; registra run_id, run_attempt, host_bind_name y XDG_RUNTIME_DIR en el recibo de aceptación.
- Se ajusta el fixture unitario del diagnóstico Flatpak para proporcionar identidad de workflow válida, y se añaden pruebas de ausencia, mismatch, unicidad por attempt y recibo.
- El workflow contractual ejecuta el job de contratos para PR cuyo destino sea la rama operativa. El job target/independent continúa limitado a push o workflow_dispatch sobre la rama operativa.

## 4. Condiciones de validación

El CI de PR debe probar bash -n, py_compile, las pruebas de contrato y el módulo target_acceptance_tests_v1.py. El full run posterior al merge debe demostrar que el run ID y attempt en los logs y el recibo coinciden con HOST_BIND_NAME, el mountpoint montado y XDG_RUNTIME_DIR observado; debe también pasar el cleanup de mount.

Después deben pasar, sobre el mismo HEAD y sin recombinar evidencia antigua: aceptación E01–E15, E04 INT8, smoke tests legacy, JASP de referencia/replay, inventario rootfs, empaquetado/round-trip estricto SquashFS, validación independiente, S32, stable release y certificado final enlazado al SHA-256 exacto de LUNITA.squashfs.

## 5. Estado

RUN_43337415331=FAILURE  
TARGET_ACCEPTANCE=NOT_REACHED  
SQUASHFS=NOT_EMITTED  
INDEPENDENT_VALIDATION=NOT_REACHED  
S32=NOT_REACHED  
STABLE_RELEASE=NOT_REACHED  
FUNCTIONAL_CERTIFICATE=NOT_GRANTED  
CORRECTION_BRANCH=fix/lunita-flatpak-runtime-env-propagation-20261113  
CORRECTION_STATUS=IMPLEMENTED_NOT_YET_CI_VALIDATED
