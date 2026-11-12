# Auditoría de causa raíz — Bloqueo de versión JASP durante rootfs build

**Auditoría:** `JASP_SOURCE_VERSION_PROVENANCE_ROOT_CAUSE_20261112`  
**Repositorio:** `Plomillo/luna-linux-bridge`  
**Workflow:** `43326401590`  
**HEAD que falló:** `08f932874ae38daf1deade88b201da7562078fe7`  
**Job:** `131560894953`  
**Step:** 7 — Rebuild Ubuntu 24.04 rootfs only when the exact base cache is absent  
**Resultado observado:** `ROOTFS_BUILD_BLOCKED: JASP Flatpak metadata did not expose an installed version.`

## 1. Evidencia primaria del fallo

El constructor ejecutó:

```bash
JASP_INFO="$(flatpak info --system org.jaspstats.JASP)"
JASP_OBSERVED_VERSION="$(awk -F': *' '$1 == "Version" { print $2; exit }' <<<"$JASP_INFO")"
[ -n "$JASP_OBSERVED_VERSION" ] || fail "JASP Flatpak metadata did not expose an installed version."
```

La ejecución instaló y actualizó la app Flatpak JASP fijada y verificó su deployment commit, pero el comando de inspección no produjo el campo textual esperado. La construcción terminó con código 2. No se alcanzaron los motores reales, los smoke tests posteriores, empaquetado SquashFS, la validación independiente ni la certificación.

## 2. Causa raíz

La implementación confundía una propiedad de presentación/catálogo con una identidad de versión obligatoria. La salida amigable de `flatpak info` depende de información AppStream, que puede estar ausente o no reflejar la revisión del código desplegada. El campo no es una prueba suficientemente fiable para bloquear o certificar la versión real del ejecutable.

La inspección del origen JASP revela dos hechos concretos:

1. Flathub manifest commit `95e467d83089fb292e5d0746e98e188fef6f9113`, fechado 2026-10-12, declara el source commit `b6cd3b0310be4e18e1b673ac11f14e55615c8fa1` para `jasp-stats/jasp-desktop`.
2. En ese source commit, el `CMakeLists.txt` contiene `project(JASP VERSION 0.98.8.0)`. El `Tools/flatpak/org.jaspstats.JASP.appdata.xml` del mismo commit todavía enumera `0.98.1` como su primera entrada de release.

Por tanto, AppStream/appdata no es una fuente de versión segura para el caso. El código de construcción sí determina 0.98.8. La versión pública oficial JASP 0.98.8 aparece publicada el 12 de octubre de 2026; su página de versiones diferencia 0.98.8 y 0.98.1.

## 3. Evidencia de origen fijada

| Objeto | Identidad |
|---|---|
| Flathub manifest commit | `95e467d83089fb292e5d0746e98e188fef6f9113` |
| Flathub manifest Git blob SHA-1 | `1aec5921883d56388c91627b09ba9cf6eb07c1d6` |
| Flathub manifest app-id | `org.jaspstats.JASP` |
| JASP source commit | `b6cd3b0310be4e18e1b673ac11f14e55615c8fa1` |
| JASP CMakeLists Git blob SHA-1 | `d57ba1e22d4cd00f3848034dc09737498b91346b` |
| CMake project version | `0.98.8.0` |
| Public runtime version normalized | `0.98.8` |
| Flatpak deployment commit pin | `83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7` |

Los SHA-1 indicados son Git blob identities devueltos por GitHub para los bytes exactos de los archivos. El nuevo verificador los vuelve a calcular sobre los bytes descargados y además registra SHA-256 del contenido.

## 4. Corrección implementada

Archivos modificados:

- `scripts/lunita/verify_jasp_release_identity_v1.py`
- `scripts/lunita/test_verify_jasp_release_identity_v1.py`
- `scripts/lunita/build_rootfs_candidate_v1.sh`
- `.github/workflows/lunita-v18-direct-functional-validation.yml`

El helper nuevo verifica:
- SHA-1 Git blob de manifiesto Flathub y CMakeLists.
- SHA-256 de ambos archivos.
- app-id Flathub.
- existencia de exactamente un source git `jasp-desktop` y coincidencia con el source commit esperado.
- versión `project(JASP VERSION ...)`, normalizada solo cuando el cuarto componente es `.0`.
- igualdad con la versión aprobada 0.98.8.

El builder descarga los archivos desde URL de commits inmutables, ejecuta el helper, deja de depender del campo `Version` de `flatpak info` y conserva los archivos y recibo en:

- `/opt/lunita/metadata/JASP_FLATHUB_MANIFEST.json`
- `/opt/lunita/metadata/JASP_SOURCE_CMAKE_LISTS.txt`
- `/opt/lunita/metadata/JASP_SOURCE_RELEASE_IDENTITY.json`

El recibo del rootfs enlaza el deployment commit real, manifest commit/blob/hash, source commit, CMake blob/hash y SHA-256 del recibo. El lane independiente mantiene además la exigencia de iniciar JASP y validar su banner de versión y source commit reales; la evidencia de origen no suplanta la ejecución del binario.

El gate contractual compila el helper y ejecuta self-tests y unit tests que aceptan la identidad exacta y rechazan deriva en el hash del manifiesto, source commit o versión CMake.

## 5. No-regresión y estado

No se cambia el deployment commit JASP, source commit, versión esperada, fixture .jasp, resultados históricos, G06 congelado, bindings G08 ni instrumento etiquetado `Lupa`. No se elimina el test de identidad runtime. No se convierte una cadena de versión hardcodeada en evidencia: la versión se deriva de contenido externo inmutable y se verifica luego contra el proceso real.

`PRIMARY_FAILURE_EVIDENCE = PASS`  
`ROOT_CAUSE = APPSTREAM_DISPLAY_VERSION_USED_AS_MANDATORY_SOURCE`  
`SOURCE_PROVENANCE_CORRECTION = IMPLEMENTED`  
`HELPER_SELF_TESTS = ADDED_NOT_YET_EXECUTED_IN_CI`  
`FULL_ROOTFS_REBUILD = PENDING`  
`JASP_RUNTIME_BANNER_VALIDATION = PENDING`  
`FUNCTIONAL_CERTIFICATION = NOT_GRANTED`

La corrección está en la rama de integración `audit/lunita-zero-trust-certification-axioms-20261112`. El código no se considera validado hasta que el CI contractual pase, la reconstrucción complete el runtime y el lane independiente pase todos los casos JASP con versión 0.98.8 y el source commit exacto.
