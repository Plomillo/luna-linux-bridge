# Lunita v1.8 — Auditoría de discrepancia de versión y esquema de recibo JASP

**Fecha:** 2026-11-13  
**Repositorio:** Plomillo/luna-linux-bridge  
**Rama del run fallido:** fix/lunita-v18-rootfs-bound-checkpoint-20261109  
**HEAD del run:** 2d66baf8f52ba90070a42ae6bec5f4794b8c745d  
**Workflow:** 43339097069 (run #215)  
**Job target:** 131603445497  
**Gate:** step 15 — Execute actual E01 inference and E02-E15 plus legacy application smoke tests  
**Resultado:** ROOT_CAUSE_IDENTIFIED; CORRECTION_IMPLEMENTED_NOT_YET_CI_VALIDATED  
**Certificación funcional:** NOT_GRANTED

## 1. Evidencia primaria

El log del job 131603445497 registró identidad efectiva run_id=43339097069, attempt=1 y HOST_BIND_NAME=lunita-host-43339097069-1. El directorio XDG fue aceptado como bind privado escribible por UID 1000; el proceso de UID 1000 creó un user namespace desde el mount root candidato; el contexto fue private mount namespace + pivot_root. Esto demuestra que la corrección de AX-LUN-021/022 superó su primera ejecución real.

El target receipt fue emitido con status BLOCKED_TARGET_RUNTIME_ACCEPTANCE, certification NOT_GRANTED, y el error:

    TargetGateError: Flatpak app identity/version mismatch: org.jaspstats.JASP

SHA-256 del recibo bloqueado: 839a58404497c72372fe04b5972a15bd972f1fafa3ee80db9c2d4b2c46376d62.

Los pasos de verificación de unmount, recopilación de evidencia, cleanup final y subida de evidencia terminaron SUCCESS. El job no llegó a finalizar la aceptación E01–E15/legacy ni a ejecutar el gate JASP real. El rechazo se produjo al cotejar identidad declarada en el recibo del rootfs; por tanto, no demuestra que el deployment Flatpak instalado ni el binario JASP estuvieran defectuosos.

## 2. Identidad de release respaldada por el builder y la fuente

El constructor scripts/lunita/build_rootfs_candidate_v1.sh fija:

- JASP_VERSION=0.98.8
- JASP_COMMIT=83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7
- JASP_SOURCE_COMMIT=b6cd3b0310be4e18e1b673ac11f14e55615c8fa1
- JASP_FLATHUB_MANIFEST_COMMIT=95e467d83089fb292e5d0746e98e188fef6f9113
- JASP_FLATHUB_MANIFEST_BLOB_SHA1=1aec5921883d56388c91627b09ba9cf6eb07c1d6
- JASP_SOURCE_CMAKE_BLOB_SHA1=d57ba1e22d4cd00f3848034dc09737498b91346b

El verificador scripts/lunita/verify_jasp_release_identity_v1.py fija EXPECTED_VERSION=0.98.8 y emite la procedencia PINNED_JASP_CMAKE_PROJECT_VERSION. El proyecto CMake debe declarar 0.98.8.0 y normaliza a 0.98.8. La identidad independiente en lunita_stability_certification_lane_v1.py también fija 0.98.8 y el mismo commit de fuente b6cd3b0310be4e18e1b673ac11f14e55615c8fa1.

## 3. Defectos comprobados en el verificador target previo al fix

El código previo a la corrección tenía tres contradicciones independientes con el builder:

1. EXPECTED_LABEL_HIERARCHY, su representación textual y la tupla de aplicaciones esperaban JASP 0.98.1, mientras que el builder, la verificación fuente, los metadatos y el lane independiente fijaban 0.98.8.
2. El bucle genérico exigía version_source=EXACT_PINNED_FLATPAK_COMMIT_MAPPING para Jamovi y JASP. El constructor emite ese valor para Jamovi, pero para JASP emite PINNED_FLATHUB_MANIFEST_AND_JASP_CMAKE_SOURCE_VERIFIED.
3. El bucle genérico leía flatpak_commit para ambas apps. El recibo del builder de Jamovi contiene flatpak_commit; el recibo de JASP contiene flatpak_deployment_commit.

El primer defecto explica el error visible. Los defectos segundo y tercero habrían bloqueado el mismo gate después de corregir la versión; se identificaron mediante inspección comparada de los contratos, sin presentarlos como errores runtime observados.

## 4. Corrección implementada en fix/lunita-jasp-version-contract-coherence-20261113

- JASP target label y expected version se alinean con 0.98.8.
- Se define una tabla de identidad Flatpak por aplicación: Jamovi conserva su versión, fuente y campo flatpak_commit; JASP conserva la versión 0.98.8, fuente PINNED_FLATHUB_MANIFEST_AND_JASP_CMAKE_SOURCE_VERIFIED y campo flatpak_deployment_commit.
- Ambos deployments se verifican contra los commits exactos fijados y contra la salida observada de flatpak info --system --show-commit.
- El target verifica la carpeta metadata y los tres archivos de procedencia JASP; exige archivos regulares y no symlinks, calcula SHA-256 y Git blob SHA-1, valida app-id, único commit fuente, versión CMake, recibo de identidad y flags de procedencia.
- El source release receipt queda enlazado al manifiesto Flathub, CMakeLists.txt, JASP source commit, Flatpak deployment commit y sus hashes.
- Se añaden pruebas contractuales de coherencia entre builder, source verifier, target helper, workflow, etiquetas y validador independiente; pruebas positivas/negativas del verificador de procedencia y prueba del Git blob object header.
- El contrato se amplía append-only a AX-LUN-023.

## 5. Condiciones pendientes de validación

El CI contractual debe validar la sintaxis y todos los tests nuevos. Tras integrar el cambio, un nuevo push full run debe, sobre el HEAD exacto:

1. ejecutar el target rootfs gate y comprobar el commit JASP real, su versión y la integridad de los tres metadatos de fuente;
2. ejecutar E01–E15, E04 INT8, smoke tests heredados y la suite JASP de referencia/replay;
3. empaquetar LUNITA.squashfs y pasar el round-trip con manifiesto estricto y timestamps exactos;
4. emitir artefacto de imagen, checksum y recibo de package enlazados al SHA-256 interno de la imagen;
5. pasar validación independiente, S32, stable release y certifier final enlazados al mismo SHA-256 de LUNITA.squashfs.

Los artefactos y recibos de runs anteriores no pueden completar esta cadena.

## 6. Estado al crear la corrección

RUN_43339097069=FAILURE  
TARGET_RUNTIME=BLOCKED_ROOTFS_JASP_RECEIPT_IDENTITY  
WORKFLOW_IDENTITY=PASS  
XDG_RUNTIME_DIR=PASS  
PIVOT_ROOT_NAMESPACE=PASS  
TARGET_UNMOUNT_AND_CLEANUP=PASS  
JASP_ACTUAL_EXECUTION=NOT_REACHED  
SQUASHFS_IMAGE=NOT_EMITTED  
INDEPENDENT_VALIDATION=NOT_REACHED  
S32=NOT_REACHED  
STABLE_RELEASE=NOT_REACHED  
FUNCTIONAL_CERTIFICATE=NOT_GRANTED  
CORRECTION_BRANCH=fix/lunita-jasp-version-contract-coherence-20261113  
CORRECTION_STATUS=IMPLEMENTED_NOT_YET_CI_VALIDATED
