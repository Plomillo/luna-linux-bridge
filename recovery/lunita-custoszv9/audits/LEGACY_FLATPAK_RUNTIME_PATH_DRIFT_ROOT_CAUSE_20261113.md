# Lunita v1.8 — Auditoría de causa raíz: ruta XDG divergente en delegación heredada

**Fecha:** 2026-11-13  
**Repositorio:** Plomillo/luna-linux-bridge  
**Workflow:** 43341112917 (run #217)  
**HEAD:** eff579756bd905930de9b22dcf7642c2c8e14a06  
**Job target:** 131609898416  
**Gate:** step 15 — Execute actual E01 inference and E02-E15 plus legacy application smoke tests  
**Clasificación:** ROOT_CAUSE_IDENTIFIED; CORRECTION_IMPLEMENTED_NOT_YET_CI_VALIDATED  
**Certificación funcional:** NOT_GRANTED

## 1. Evidencia primaria

El target receipt de run #217 registró `PASS_ROOTFS_BUILD_IDENTITY` y no reportó discrepancia en los metadatos JASP. En el log se acreditó la identidad de ejecución `run_id=43341112917`, `attempt=1`, `HOST_BIND_NAME=lunita-host-43341112917-1`, XDG runtime por intento y el contexto target con namespace/mount root del candidato.

La batería legacy bloqueó por:

    Legacy application/fault smoke test failed: jamovi-self-test rc=3

El diagnóstico Flatpak, que se ejecuta de forma separada y limitada, devolvió `returncode=0` en los modos `inherited` y `clean`. Ese diagnóstico no constituye el self-test completo de Jamovi ni puede sustituirlo. El target receipt fue bloqueado; no se llegó a emitir la imagen SquashFS.

## 2. Diferencia de rutas demostrada

El wrapper de namespace crea y monta el runtime de este intento en:

    /run/lunita-host-43341112917-1-runtime-1000

El helper `target_runtime_acceptance_v1.py` valida esa misma ruta y la usa en su diagnóstico Flatpak. Sin embargo, al delegar comandos heredados, `recovery/lunita-custoszv9/runtime_engines_v1/lunita_beta_v1_8.py` construía el entorno del launcher v1.7 con:

    XDG_RUNTIME_DIR=/run/lunita-runtime-1000

La ruta recibida por la aplicación heredada no era el mountpoint creado ni el directorio que el gate target acababa de validar. La divergencia es directamente verificable al comparar el wrapper, el recibo y la variable `guest_environment` de `run_legacy()`.

La evidencia demuestra la discrepancia de entorno y el retorno no cero del self-test. No determina por sí sola qué llamada interna de Jamovi causó rc=3; esa atribución más específica requiere reejecutar el self-test una vez corregida la ruta y analizar su log.

## 3. Corrección mínima implementada

En `fix/lunita-legacy-flatpak-runtime-identity-20261113`:

- Se añade `expected_target_runtime_directory(environment)` en la frontera v1.8.
- Exige `GITHUB_RUN_ID` y `GITHUB_RUN_ATTEMPT` ASCII numéricos.
- Exige `HOST_BIND_NAME == lunita-host-<run_id>-<attempt>`.
- Exige `XDG_RUNTIME_DIR == /run/<HOST_BIND_NAME>-runtime-1000`.
- Ante missing/mismatch, `run_legacy()` devuelve bloqueo antes de invocar el proceso delegado.
- La variable `guest_environment` entrega a v1.7 exactamente la ruta runtime validada; se elimina el literal global.
- Se mantiene byte-exacto el launcher legado v1.7, su hash y su ruta; la corrección no cambia su contenido ni lo reautoriza.
- Se agregan tests para derivación exacta, run/attempt mismatch, path XDG viejo, identidad no ASCII, propagación efectiva al comando delegado y denegación fail-closed.
- La misma cobertura valida el camino de chroot y el de pivot_root.

## 4. Condiciones de revalidación

El CI de PR debe pasar sintaxis y suites contractuales. Tras el merge, una nueva ejecución completa debe confirmar:

1. `GITHUB_RUN_ID`, `GITHUB_RUN_ATTEMPT`, `HOST_BIND_NAME` y `XDG_RUNTIME_DIR` concordantes en el wrapper y el target receipt.
2. El comando ejecutado por la frontera v1.8 hacia el launcher v1.7 contiene exactamente el runtime por intento montado.
3. El hash del launcher heredado es el mismo hash congelado previo; no hay modificación ni sustitución.
4. El self-test real de Jamovi termina rc=0 y conserva su log/hash; JASP y su prueba real también pasan.
5. E01–E15, E04 INT8, smoke tests heredados, JASP reference/replay, inventario rootfs y limpieza de mounts pasan.
6. El paquete `LUNITA.squashfs` y round-trip estricto pasan; imagen, checksum, package receipt, informe independiente, S32, stable release y certificado se enlazan al mismo SHA-256 de imagen.

Los logs, recibos y artefactos de run #217 o de runs previos no pueden mezclarse con la próxima cadena.

## 5. Estado

RUN_43341112917=FAILURE  
JASP_ROOTFS_IDENTITY=PASS  
JAMOVI_DIAGNOSTIC_INHERITED=PASS_RC0  
JAMOVI_DIAGNOSTIC_CLEAN=PASS_RC0  
JAMOVI_REAL_SELF_TEST=FAIL_RC3  
ROOT_CAUSE=STATIC_XDG_RUNTIME_DIR_IN_V1_8_LEGACY_DELEGATION  
TARGET_CLEANUP=PASS  
SQUASHFS_IMAGE=NOT_EMITTED  
INDEPENDENT_VALIDATION=NOT_REACHED  
S32=NOT_REACHED  
STABLE_RELEASE=NOT_REACHED  
FUNCTIONAL_CERTIFICATE=NOT_GRANTED  
CORRECTION_BRANCH=fix/lunita-legacy-flatpak-runtime-identity-20261113  
CORRECTION_STATUS=IMPLEMENTED_NOT_YET_CI_VALIDATED
