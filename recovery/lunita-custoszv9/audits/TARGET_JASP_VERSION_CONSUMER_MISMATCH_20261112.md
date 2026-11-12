# Auditoría de incompatibilidad — Consumo de identidad JASP en aceptación de destino

**Auditoría:** `TARGET_JASP_VERSION_CONSUMER_MISMATCH_20261112`  
**Repositorio:** `Plomillo/luna-linux-bridge`  
**HEAD del workflow activo:** `a41e7b9fdc000b1c95f08aa212082e23d28051ea`  
**Workflow:** `43332281299`  
**Job de destino:** `131580478339`  
**Paso actual observado al investigar:** 7 — reconstrucción del rootfs Ubuntu 24.04  
**Consumidor auditado:** `recovery/lunita-custoszv9/runtime_engines_v1/target_runtime_acceptance_v1.py`

## 1. Hallazgo

La corrección de procedencia JASP añadida al builder y al recibo raíz aún no estaba reflejada en el validador que consume ese recibo. El código de destino conservaba tres expectativas obsoletas:

1. La jerarquía JSON/texto esperaba `JASP 0.98.1`, mientras el builder actualizado genera y enlaza `JASP 0.98.8`.
2. La lista de aplicaciones esperaba `lupa.version=0.98.1` y `version_source=EXACT_PINNED_FLATPAK_COMMIT_MAPPING`, mientras el constructor actualizado registra `0.98.8` y `PINNED_FLATHUB_MANIFEST_AND_JASP_CMAKE_SOURCE_VERIFIED`.
3. El validador leía `lupa.flatpak_commit`, mientras el recibo actualizado registra la clave explícita `lupa.flatpak_deployment_commit`.

El consumidor rechazaba así un recibo correctamente producido por el nuevo constructor. No se trata de una discrepancia del ejecutable ni justifica cambiar de nuevo la versión o debilitar el recibo.

## 2. Corrección implementada

En `target_runtime_acceptance_v1.py`:

- La jerarquía canónica y su representación textual del candidato derivado pasan a exigir exactamente JASP 0.98.8; la etiqueta instrumental `Lupa` permanece sin cambios.
- La tabla de aplicaciones distingue la procedencia de jamovi y JASP. El JASP exige el marcador de procedencia Flathub/CMake, la versión 0.98.8 y el deployment commit Flatpak 83ec9d…; no consulta el campo AppStream `Version`.
- La validación utiliza la clave explícita `flatpak_deployment_commit` para JASP y conserva la clave histórica `flatpak_commit` para jamovi.
- Se añade una verificación independiente de los archivos preservados dentro de `/opt/lunita/metadata`: manifiesto Flathub, `CMakeLists.txt` de JASP y recibo de identidad de fuente.
- Se vuelven a calcular SHA-256 y Git blob SHA-1; se analiza el manifiesto para comprobar app-id y source commit único, se deriva la versión del `project(JASP VERSION ...)` real y se coteja cada campo del recibo. El marcador AppStream usado como fuente de versión debe ser `false`.
- El recibo de aceptación de destino incluye el resultado de esa verificación.

## 3. Pruebas de regresión añadidas

`target_acceptance_tests_v1.py` incorpora pruebas que exigen:

- aceptación de la identidad coherente del manifiesto fuente y versión CMake 0.98.8.0;
- rechazo de source commit distinto;
- rechazo de versión CMake distinta;
- rechazo de un cuarto componente distinto de cero;
- rechazo de app-id distinto;
- rechazo del marcador de versión heredado;
- rechazo de un deployment commit distinto del pin;
- coherencia de etiqueta JASP 0.98.8 con la jerarquía preservada.

No se modifican resultados estadísticos, fixtures JASP, deployment commit, source commit, G06 congelado, G08, la etiqueta `Lupa` ni los gates de aceptación.

## 4. Estado y alcance

La corrección se ha implementado en rama separada `fix/lunita-target-jasp-source-identity-20261112`, desde el HEAD que inició el workflow #43332281299. Ese workflow ya había construido su overlay con el validador previo; sus bytes descargados no pueden recibir retroactivamente este cambio. El workflow activo debe terminar y conservar su resultado. La corrección requiere una nueva ejecución completa después de integrarse.

`ROOT_CAUSE=BUILDER_CONSUMER_SCHEMA_AND_VERSION_DRIFT`  
`CORRECTION=IMPLEMENTED`  
`UNIT_TESTS=ADDED_NOT_YET_EXECUTED_IN_CI`  
`CURRENT_WORKFLOW_TARGET_VALIDATOR=OLD_CHECKED_OUT_BYTES`  
`NEXT_RUN_REQUIRES_NEW_OVERLAY_AND_ROOTFS`  
`FUNCTIONAL_CERTIFICATION=NOT_GRANTED`

**Cierre:** solo tras una nueva ejecución en la que el constructor, el validador de destino y el lane independiente acepten la misma versión y los mismos hashes de procedencia JASP podrá considerarse resuelto este bloqueo.
