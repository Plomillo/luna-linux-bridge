# LUNITA v1.8 — Axiomas verificables de certificación funcional SquashFS

**Documento:** `LUNITA_SQUASHFS_ZERO_TRUST_CERTIFICATION_AXIOMS_V1`  
**Versión:** `1.0.0`  
**Estado normativo:** `MANDATORY_PRECONDITION_FOR_FUNCTIONAL_CERTIFICATION`  
**Doctrina:** `APPEND_ONLY; EXTEND_DO_NOT_REPLACE; FAIL_CLOSED`  
**Objetivo único:** `LUNITA.squashfs`  
**Candidato:** `G06_REBUILD_CANDIDATE_R1 / 1.8.0`  
**Repositorio:** `Plomillo/luna-linux-bridge`  
**Rama auditada:** `fix/lunita-v18-rootfs-bound-checkpoint-20261109`  
**HEAD auditado:** `08f932874ae38daf1deade88b201da7562078fe7`  
**Evidencia CI activa al fijar este documento:** workflow `43326401590`, job contractual `131559844370`, job de destino/independiente `131560894953`.

---

## 0. Decisión epistemológica y alcance

Este documento formaliza las condiciones necesarias y conjuntamente suficientes para emitir **una certificación funcional del artefacto SquashFS derivado**. No declara que esas condiciones ya se hayan satisfecho.

La unidad certificable no es una rama, un commit, un workflow, un ZIP ni una declaración del constructor: es la secuencia exacta de bytes de `LUNITA.squashfs`, identificada por su SHA-256, tamaño y recibos hash-bound.

La certificación se limita a `G06_REBUILD_CANDIDATE_R1 / 1.8.0`. No reconstruye ni reclama haber recuperado el rootfs histórico original; no modifica G06 congelado, bindings canónicos G08, referencias estadísticas empaquetadas ni etiquetas instrumentales preexistentes; no promueve automáticamente el candidato a una autoridad canónica ni concede G23/G24 canónicos.

**Estado observado al crear este documento:** el job contractual del workflow `43326401590` concluyó `success`; el job de destino `131560894953` seguía ejecutando el paso 7, reconstrucción del rootfs Ubuntu 24.04. Todavía no había evidencia de imagen SquashFS de esa ejecución, recibo de runtime de destino, validación independiente, S32, stable release ni certificado final. Por tanto, el estado demostrado era `IN_PROGRESS / NOT_CERTIFIED`.

## 1. Objetos formales

Sea:

- `M`: manifiesto congelado `LUNITA_V1_8_CANDIDATE_FREEZE.json`.
- `R`: rootfs candidato Ubuntu 24.04 amd64.
- `T`: recibo de aceptación de runtime de destino `LUNITA_TARGET_RUNTIME_ACCEPTANCE_*.json`.
- `J`: evidencia de regresión, identidad y replay de JASP.
- `V`: inventario completo del rootfs y cierre de dependencias.
- `I`: bytes del archivo `LUNITA.squashfs`.
- `P`: recibo de empaquetado `LUNITA_SQUASHFS_PACKAGE_RECEIPT.json`.
- `Q`: checksum `LUNITA.squashfs.sha256`.
- `N`: informe de validación independiente `BETA_INDEPENDENT_VALIDATION.json`.
- `S`: recibo S32 de validación/certificación operacional beta.
- `L`: recibo de stable release `LUNITA_STABLE_1_8`.
- `C`: certificado funcional final `LUNITA_FUNCTIONAL_CERTIFICATE.json`.

Definimos `H(x) = SHA256(bytes(x))`. Todo hash se calcula sobre los bytes reales del objeto, no sobre el nombre, ruta, etiqueta, tamaño declarado o hash de un contenedor ZIP.

## 2. Axiomas de confianza cero

### AX-LUN-001 — Identidad única del candidato

Toda evidencia admitida MUST identificar exactamente `candidate_id=G06_REBUILD_CANDIDATE_R1` y `version=1.8.0`, vinculados al manifiesto congelado `M`. Una identidad ausente, ambigua, duplicada o contradictoria produce `BLOCKED`.

### AX-LUN-002 — Autoridad del manifiesto congelado

`M` MUST cumplir el esquema `LUNITA_CANDIDATE_FREEZE/1.0`, mantener `freeze_status=FROZEN_CANDIDATE_NOT_CERTIFIED`, y acreditar `frozen_g06_mutated=false`, `canonical_g08_bindings_mutated=false` y `legacy_v1_7_launcher_replaced=false`. La huella `H(M)` MUST ser idéntica en todas las evidencias que la referencien.

### AX-LUN-003 — Identidad runtime observada, no autodeclarada

La identidad de una aplicación MUST derivarse de metadatos observados del runtime y de su salida de ejecución. Una variable de configuración que simplemente repita el valor esperado no es prueba de identidad.

Para JASP, la tupla obligatoria es:

- Flatpak deployment commit: `83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7`.
- Versión informada por los metadatos Flatpak instalados: `0.98.8`.
- Source commit comunicado por el proceso JASP: `b6cd3b0310be4e18e1b673ac11f14e55615c8fa1`.

Los tres identificadores son distintos por naturaleza y MUST verificarse en sus respectivas fuentes. Una etiqueta visual no reemplaza ninguna de estas pruebas.

### AX-LUN-004 — Runtime de destino completo

El recibo `T` MUST ser un recibo válido `LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0`, con estado funcional PASS, identidad del candidato coincidente y certificación no concedida antes del gate final. MUST acreditar:

- inferencia real E01;
- E02–E15 ejecutados, sin skips ni fallos, incluido el enrutamiento de comandos/agentes/motores;
- cuantización INT8 E04 y su gate de calidad;
- smoke tests del conjunto heredado completo, sin omisiones;
- integridad del overlay y preservación de G06/G08.

No se admite convertir cobertura parcial en cobertura completa.

### AX-LUN-005 — Inventario independiente del rootfs

El inventario `V` MUST recorrer el rootfs candidato exacto sin seguir enlaces simbólicos, registrar el manifiesto íntegro de entradas y hashes de archivos regulares, demostrar estabilidad del árbol antes/después, y cerrar todas las dependencias declaradas de dpkg. Se exige:

`status=PASS_ROOTFS_INVENTORY_AND_DEPENDENCY_CLOSURE`  
`inventory_errors_count=0`  
`tree_stable_during_scan=true`  
`dpkg_dependency_closure.status=PASS_DECLARED_PACKAGE_DEPENDENCIES_RESOLVED`

Tanto el manifiesto JSONL como el informe de inventario MUST tener hashes válidos y estar ligados al rootfs exacto del candidato.

### AX-LUN-006 — Inmutabilidad de la referencia JASP

El archivo fuente original Death Penalty MUST conservar exactamente el SHA-256 fijado:

`fc8b6f8faf0e4437c8e4ab4bd922b3e959a0d4549c813b229bc5708050851895`

La ejecución `flatpak_launch` MUST usar el fixture original empaquetado `/app/lunita-fixtures/DeathPenalty.jasp`. Su alias MUST ser un enlace simbólico cuyo destino resuelto coincida con el archivo fuente real, y ambos hashes MUST coincidir con el pin. La prueba de referencia original debe concluir con código de salida 0 y con identidad runtime JASP válida.

Los fixtures Reliability y WeightGain también MUST ejecutarse realmente y terminar con código 0 y runtime identity PASS. `BLOCKED_NOT_RUN`, ausencia de log, ejecución interrumpida o falta de recibo nunca equivale a PASS.

### AX-LUN-007 — Separación entre referencia histórica y replay determinista

La prueba de referencia original y el replay con seed controlado son controles distintos, con entradas y conclusiones distintas:

1. La prueba de referencia se ejecuta sobre el fixture original sin alterar opciones ni resultados almacenados.
2. El replay utiliza exclusivamente una copia temporal desechable derivada del fixture original.
3. La copia puede cambiar únicamente la opción activa de seed identificada por el inspector de fixture; la operación debe estar autorizada por recibo hash-bound.
4. Los demás miembros del archivo JASP, incluidos resultados históricos, deben permanecer byte-identical; el archivo fuente jamás se modifica.
5. Dos ejecuciones reales e independientes del mismo clon, con el mismo runtime identificado, MUST producir tablas recién calculadas con filas ordenadas exactamente iguales y SHA-256 idénticos.

`reference_comparison_status` MUST conservar su resultado explícito. Un mismatch histórico en la copia deliberadamente reseedeada no puede rotularse como PASS de referencia; puede registrarse separadamente de la reproducibilidad del replay. La certificación, sin embargo, exige que el caso de referencia original de AX-LUN-006 pase. No se permite cambiar el baseline histórico, regenerar resultados de referencia, introducir tolerancias después de observar el fallo ni presentar discrepancias estadísticas como simples diferencias de formato.

### AX-LUN-008 — Replay reproducible con evidencia primaria

El recibo de fixture MUST probar origen, destino temporal, SHA-256 original, SHA-256 del clon, miembro de configuración modificado, JSON pointer, valor anterior y posterior, número de miembros no activos preservados y validez de la propia evidencia. Los logs de ambas ejecuciones MUST conservar sus códigos reales de salida, runtime banner/source commit, comando, filas calculadas y hashes de esas filas.

La igualdad del replay se define por igualdad exacta de estructura ordenada y de SHA-256. No hay tolerancia numérica implícita. Cualquier política numérica distinta requiere especificación previa, por campo, justificación técnica y validación independiente antes de ejecutar la prueba.

### AX-LUN-009 — No sustitución del fallo por una variable sintética

Un código efectivo usado por un agregador nunca puede borrar los códigos originales de JASP. Los campos `save_subprocess_returncode` y `rerun_subprocess_returncode` (o sus equivalentes explícitos) MUST preservarse y ser auditables. Un `returncode=0` derivado de la aprobación de replay no prueba que el proceso JASP haya devuelto 0; la evidencia primaria permanece separada y visible.

### AX-LUN-010 — Integridad de empaquetado SquashFS

El empaquetador MUST:

- consumir el rootfs exacto cuya aceptación de destino pasó;
- rechazar enlaces inseguros y objetos no admitidos;
- demostrar que el rootfs fuente no cambió durante el empaquetado;
- ejecutar `mksquashfs`, comprobar el superblock con `unsquashfs` y extraer el sistema;
- demostrar igualdad del manifiesto completo entre el rootfs fuente y el rootfs extraído;
- emitir una imagen no vacía y un recibo `LUNITA_SQUASHFS_PACKAGE_RECEIPT/1.0` con estado PASS y certificación aún no concedida.

### AX-LUN-011 — Cierre criptográfico de la imagen

Sea `hI=H(I)`. Se exige simultáneamente:

- `P.image_sha256 = hI`;
- `P.image_bytes = size(I)`;
- `Q` contiene exactamente `hI  LUNITA.squashfs`;
- el SHA-256 de `Q` coincide con el declarado;
- `P` enlaza por ruta y hash el mismo recibo `T`;
- el estado de `T` es PASS;
- no existe otra imagen o recibo ambiguo que pueda sustituir el objeto certificado.

El SHA-256 del ZIP de GitHub Actions no es el SHA-256 interno de `LUNITA.squashfs` y nunca podrá presentarse como tal.

### AX-LUN-012 — Informe independiente completo

El informe `N` MUST ser `CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0`, estado `PASS_INDEPENDENT_VALIDATION`, perfil `V1_8_DIRECT`, candidato coincidente y manifiesto `H(M)) idéntico. MUST incluir y aprobar todos estos checks:

- `candidate_manifest_identity_sha256`
- `runtime_report_and_launcher_identity`
- `target_v1_8_runtime_acceptance_e01_e15_int8`
- `candidate_rootfs_inventory_and_dependency_manifest`
- `jasp_packaged_fixture_nonregression`
- `squashfs_image_and_package_binding`

Cada evidencia citada MUST existir, ser un archivo admisible y conservar el hash declarado. La validación JASP MUST incluir los cuatro casos requeridos, cada uno con resultado y evidencia íntegros. La imagen, checksum, recibo de empaquetado, manifiesto congelado y recibo de runtime MUST estar enlazados al mismo candidato.

### AX-LUN-013 — S32 no se infiere

S32 solo puede emitirse después de que `N` sea PASS y todas las verificaciones de identidad, integridad y hashes estén satisfechas. El recibo S32 MUST enlazar el hash de `N`, `T`, `M`, `I`, `Q` y `P`. La existencia de un archivo con nombre S32, un estado anterior o una prueba aislada no constituye emisión válida.

### AX-LUN-014 — Stable release no se infiere

El recibo `L` solo puede emitirse tras S32 válido. MUST enlazar el mismo informe independiente, runtime receipt, manifiesto, imagen exacta, checksum, package receipt y recibo S32. Debe ser inmutable y cualquier revalidación posterior debe conservar la historia y producir el estado apropiado sin sobrescribir recibos anteriores.

### AX-LUN-015 — Certificación funcional exacta

La función de certificación es:

`FUNCTIONAL_CERTIFIED(I) ⇔ AX-LUN-001 … AX-LUN-021 ∧ CERTIFICATE_BINDINGS_VALID(C,I)`

y además el certificado `C` MUST:

- declarar `status=CERTIFIED_FUNCTIONAL_CANDIDATE`;
- declarar `certification=GRANTED_FOR_VERSIONED_CANDIDATE_ONLY`;
- contener `H(I)`, tamaño exacto y rutas de la imagen/checksum;
- enlazar los hashes exactos de `P`, `Q`, `M`, `T`, `N`, `S` y `L`;
- declarar preservación de G06/G08;
- mantener G23/G24 canónicos y la promoción canónica como NOT_GRANTED/NOT_AUTHORIZED.

La certificación no existe hasta que el JSON del certificado es materializado y su integridad y bindings son verificados. Workflow success, artefacto publicado, package PASS, target PASS o independent PASS por separado no satisfacen la fórmula.

### AX-LUN-016 — Identidad de ejecución y no reutilización de evidencias

Toda ejecución de certificación MUST registrar workflow run ID, attempt, HEAD SHA, branch, job ID, timestamps, artefactos y hashes. Cualquier cambio de código, manifiesto, rootfs, runtime o configuración invalida la cadena de evidencias dependiente de ese objeto. Está prohibido recombinar un target receipt, inventory, informe JASP, imagen, S32 o stable release de ejecuciones distintas si no demuestran identidad criptográfica exacta de todos los objetos enlazados.

### AX-LUN-017 — Corrección obligatoria ante bloqueos

Todo bloqueo MUST producir el siguiente expediente:

`FAILURE → PRIMARY_EVIDENCE → ROOT_CAUSE → MINIMAL_CORRECTION → REGRESSION_TEST → FULL_REVALIDATION → INDEPENDENT_REVALIDATION`

No se permite cerrar un bloqueo mediante cambio de etiqueta, modificación de referencia, eliminación de una prueba, tolerancia retroactiva, sustitución de hash, reutilización de artefactos viejos o reducción de cobertura. Después de una corrección se reconstruye y valida de nuevo la cadena necesaria para el artefacto final exacto.

### AX-LUN-018 — Fallo cerrado y conservación

Ante cualquier hash faltante o distinto, identidad ambigua, recibo ausente, prueba no ejecutada, inventario incompleto, mismatch estadístico no resuelto, fallo de runtime, inconsistencia del paquete o gate sin PASS:

`CERTIFICATION=NOT_GRANTED`  
`RELEASE=NOT_ELIGIBLE`  
`NEXT_ACTION=DIAGNOSE_AND_REVALIDATE`

Los resultados fallidos se conservan como evidencia histórica inmutable. Se preservan el fixture original, los resultados de referencia, el manifiesto congelado, G06/G08, el checkpoint y la capacidad de rollback.


### AX-LUN-019 — Representación fiel de timestamps SquashFS

Los timestamps de inode se comparan en la resolución realmente representable por SquashFS: segundos Unix enteros. El manifiesto MUST derivar esos segundos mediante aritmética entera `st_mtime_ns // 1_000_000_000`, nunca mediante conversión float `int(st_mtime)`. La extracción MUST reproducir exactamente los segundos enteros, sin tolerancias ni normalización retrospectiva.

La regresión MUST incluir un timestamp de frontera como `1794523803.999999999`, cuyo valor esperado en SquashFS es `1794523803`. La prueba MUST empaquetar y extraer el archivo y demostrar igualdad del manifiesto. Un desfase de un segundo mantiene el paquete en BLOCKED y exige causa raíz/corrección/revalidación.


### AX-LUN-020 — Procedencia de versión JASP sin dependencia AppStream

La versión JASP no se obtiene por inferencia desde una etiqueta, un campo opcional ni una variable que repita el valor esperado. El constructor MUST enlazar criptográficamente: (1) el commit inmutable del manifiesto Flathub; (2) el Git blob SHA-1 y SHA-256 de ese manifiesto; (3) el commit fuente `jasp-desktop` que ese manifiesto declara; (4) el Git blob SHA-1 y SHA-256 del `CMakeLists.txt` en ese commit; y (5) la versión `project(JASP VERSION ...)` derivada de ese archivo. La versión resultante MUST coincidir con la versión aprobada del candidato.

El recibo del rootfs MUST conservar el manifiesto, el CMakeLists y el recibo de identidad; registrar además el deployment commit Flatpak instalado y sus hashes. La validación independiente MUST iniciar el proceso JASP real y exigir el banner de versión y source commit fijados. El campo amigable `Version` de `flatpak info` y las versiones declaradas únicamente en AppStream/appdata NO son evidencia suficiente ni fuente de autoridad: pueden estar ausentes o rezagadas respecto del código de la aplicación.


### AX-LUN-021 — Consumo independiente de la procedencia JASP en el target runtime

El validador de aceptación de destino MUST consumir el mismo contrato de identidad que produjo el builder. MUST comprobar la etiqueta y versión JASP fijadas (0.98.8), el marcador de procedencia Flathub/CMake, el deployment commit Flatpak real, el manifiesto Flathub, el CMakeLists del source commit y el recibo de identidad de fuente preservados dentro del rootfs. Debe volver a calcular SHA-256 y Git blob SHA-1, validar app-id, source commit y versión CMake; rechazar cualquier divergencia entre builder receipt, archivos preservados y deployment commit. No podrá usar el campo AppStream `Version` ni aceptar los antiguos campos/valores de esquema por compatibilidad implícita. La jerarquía representada y el validador deben concordar exactamente con JASP 0.98.8, conservando la etiqueta instrumental `Lupa`.

## 3. Predicado terminal y orden de admisión

La decisión terminal no es una suma de porcentajes ni una votación de jobs. Es una conjunción estricta:

`ADMIT(I) = IDENTITY ∧ TARGET_RUNTIME ∧ INVENTORY ∧ JASP_BASELINE ∧ JASP_REPLAY ∧ SQUASHFS_ROUNDTRIP ∧ PACKAGE_BINDING ∧ INDEPENDENT_VALIDATION ∧ S32 ∧ STABLE_RELEASE ∧ CERTIFICATE_BINDING`

`¬ADMIT(I) ⇒ CERTIFICATION=NOT_GRANTED`

La única secuencia permitida es:

`FREEZE → BUILD → TARGET_ACCEPTANCE → INVENTORY_AND_JASP → PACKAGE → INDEPENDENT_VALIDATION → S32 → STABLE_RELEASE → FINAL_CERTIFICATE → POST_VALIDATION`

No se permite saltar, invertir, fusionar silenciosamente ni heredar el resultado de un gate.

## 4. Matriz mínima de evidencia exigida para el cierre

| Gate | Evidencia primaria requerida | Condición de aceptación |
|---|---|---|
| Identidad | manifiesto congelado + recibo rootfs + runtime banners | IDs, versiones, commits y hashes coincidentes |
| Target runtime | recibo de destino | E01–E15, INT8 E04, ruta y smoke tests PASS |
| Inventario | informe y manifiesto completo | árbol estable, cero errores, dependencias cerradas |
| JASP referencia | log original + alias + hash fuente | fixture intacto, versión/commit correctos, RC 0 |
| JASP replay | dos logs, filas, dos hashes y recibo del clon | misma entrada hash-bound y salidas exactas iguales |
| Paquete | imagen + checksum + package receipt + extracción + timestamps enteros | superblock y round-trip PASS; fuente sin cambios; `st_mtime_ns // 1_000_000_000` exacto |
| Independiente | informe `N` | todos los checks requeridos PASS y hashes íntegros |
| S32 | recibo `S` | mismo `H(I)`, `H(P)`, `H(Q)`, `H(M)`, `H(T)`, `H(N)` |
| Stable release | recibo `L` | enlace exacto a S32 e identidades anteriores |
| Certificado | `C` | certificado candidate-only enlazado a la misma imagen exacta |

## 5. Fuentes de implementación auditadas

Este contrato se deriva de las rutas operativas observadas en HEAD `08f932874ae38daf1deade88b201da7562078fe7`:

- `LUNITA_V1_8_CANDIDATE_FREEZE.json`
- `scripts/lunita/build_rootfs_candidate_v1.sh`
- `scripts/lunita/package_candidate_squashfs_v1.py`
- `scripts/lunita/certify_candidate_squashfs_v1.py`
- `scripts/lunita/run_independent_certification_lane_in_container_v1.sh`
- `recovery/lunita-custoszv9/jasp_seed_fixture_v1.py`
- `recovery/lunita-custoszv9/lunita_stability_certification_lane_v1.py`
- `recovery/lunita-custoszv9/test_lunita_stability_certification_lane_v1.py`
- `recovery/lunita-custoszv9/audits/FAILURE_AUDIT_RUN_151_20261112.txt`

El informe `FAILURE_AUDIT_RUN_151_20261112.txt` documenta el fallo real del método de prueba anterior: una copia con seed alterado conservaba resultados de referencia producidos bajo configuración distinta; también documenta la divergencia de versión entre el JASP realmente ejecutado (0.98.8) y la antigua etiqueta 0.98.1. Los cambios posteriores incorporaron la separación entre fixture original y replay, metadatos runtime observados y validación de versión/source commit. Esas correcciones son cambios implementados, no evidencia de que la nueva ejecución completa haya terminado PASS.

## 5.1 — Bloqueo SquashFS por precisión temporal y corrección propuesta

La ejecución `43322862456` demostró que el empaquetador falló el round-trip en `opt/lunita/engines/runtime_engines_v1/vendor/python3.12/site-packages/charset_normalizer/__pycache__/constant.cpython-312.pyc`: el manifiesto fuente declaró `mtime_seconds=1794523804` y la extracción `1794523803`. La comparación estricta identificó el único campo diferente. No se rebaja ese control.

La auditoría atribuye como causa raíz probable la conversión `int(st_mtime)` desde float de doble precisión, que puede redondear hacia el segundo siguiente un timestamp nanosegundo situado justo bajo el límite. La solución propuesta usa segundos enteros derivados de `st_mtime_ns` y agrega una prueba de frontera que empaqueta/extrae un archivo con `1794523803.999999999`.

Implementación en revisión: PR [#171](https://github.com/Plomillo/luna-linux-bridge/pull/171), commit `3aac9f57efadf19194c9e411088095f173911b0b`. Al registrar esta revisión, la corrección estaba implementada en rama separada, pero aún no ejecutada contra el workflow completo ni integrada en la rama operativa. Por ello se clasifica como `IMPLEMENTED_NOT_YET_VALIDATED`, no como cerrado.


## 5.2 — Bloqueo de identidad de versión JASP en construcción rootfs

El workflow `43326401590`, HEAD `08f932874ae38daf1deade88b201da7562078fe7`, falló durante `scripts/lunita/build_rootfs_candidate_v1.sh` con `ROOTFS_BUILD_BLOCKED: JASP Flatpak metadata did not expose an installed version.` El builder ejecutaba `flatpak info --system org.jaspstats.JASP` y extraía la línea de texto `Version`; su ausencia detuvo la construcción antes del overlay final, los tests funcionales, la imagen y la certificación.

La auditoría identificó que `flatpak info` genera una salida amigable en la que el campo Version depende de metadatos AppStream; no debe tratarse como fuente necesaria ni como garantía de versión real. Además, en el commit fuente JASP fijado `b6cd3b0310be4e18e1b673ac11f14e55615c8fa1`, `CMakeLists.txt` declara `project(JASP VERSION 0.98.8.0)`, mientras `Tools/flatpak/org.jaspstats.JASP.appdata.xml` conserva como primer release `0.98.1`. El manifiesto Flathub del commit `95e467d83089fb292e5d0746e98e188fef6f9113` fija ese mismo commit fuente. El sitio oficial de JASP registra 0.98.8 con fecha 12 de octubre de 2026 y 0.98.1 con fecha 7 de julio de 2026.

Corrección implementada en el candidato de integración:

- Nuevo `scripts/lunita/verify_jasp_release_identity_v1.py`: compara los Git blob SHA-1 esperados, calcula SHA-256, valida app-id, source commit único y versión de CMake normalizada; sus pruebas negativas rechazan cambios de blob, versión y source commit.
- El builder descarga las dos fuentes mediante sus commits inmutables, invoca el verificador, elimina la dependencia del campo `Version` de `flatpak info` y guarda las fuentes y recibo en `/opt/lunita/metadata`.
- `ROOTFS_BUILD_RECEIPT.json` registra el deployment commit Flatpak, manifest commit/blob/hash, CMake blob/hash, source commit y la procedencia exacta de la versión.
- El gate independiente conserva la obligación de verificar el banner de ejecución real de JASP; el mapeo de fuente no reemplaza el test de runtime.
- El workflow contractual compila el verificador y ejecuta sus self-tests y unit tests.

La fuente de versión declarada como 0.98.8 no se autoriza por el valor codificado. Se demuestra por el contenido de los objetos upstream fijados y, posteriormente, por la salida del ejecutable real. La documentación de Flatpak distingue los metadatos de instalación y la presentación de información de aplicación; los metadatos AppStream son otra capa de catálogo.

Implementación actual en la rama de integración `audit/lunita-zero-trust-certification-axioms-20261112`; pendiente de revisión por CI y de integración con el constructor operativo. Estado: `IMPLEMENTED_NOT_YET_VALIDATED`.



## 5.3 — Desfase entre builder y target consumer para identidad JASP

La inspección del HEAD operativo `a41e7b9fdc000b1c95f08aa212082e23d28051ea` encontró que el nuevo builder emitía JASP 0.98.8 y el campo `flatpak_deployment_commit`, además del marcador `PINNED_FLATHUB_MANIFEST_AND_JASP_CMAKE_SOURCE_VERIFIED`. El consumidor `target_runtime_acceptance_v1.py` conservaba JASP 0.98.1, el marcador `EXACT_PINNED_FLATPAK_COMMIT_MAPPING` y esperaba `flatpak_commit`. También conservaba la jerarquía de presentación 0.98.1. Esto habría bloqueado la aceptación de destino aunque el constructor hubiese probado correctamente el origen.

La corrección se implementó en rama separada `fix/lunita-target-jasp-source-identity-20261112`: actualiza la jerarquía a 0.98.8, armoniza el schema consumidor con el builder, revalida en el rootfs los archivos manifiesto/CMake/recibo de identidad usando Git blob SHA-1 y SHA-256, vuelve a inspeccionar app-id/source commit/version y compara el deployment commit real. Se añadieron pruebas negativas de drift de manifest, source commit, app-id, versión CMake, cuarto componente, version_source y deployment commit.

La ejecución #43332281299 ya había construido y descargado el overlay anterior a esta corrección. Por ello sus pasos posteriores continuarán usando el consumidor previo; no puede incorporarse este cambio sin reconstruir el overlay y repetir el workflow completo. La corrección nueva está `IMPLEMENTED_NOT_YET_VALIDATED`, y su expediente está en `recovery/lunita-custoszv9/audits/TARGET_JASP_VERSION_CONSUMER_MISMATCH_20261112.md`.


## 6. Estado de certificación al fijar la integración

`LAST_OPERATIONAL_HEAD=08f932874ae38daf1deade88b201da7562078fe7`  
`LAST_FULL_WORKFLOW=43326401590`  
`LAST_FULL_WORKFLOW_RESULT=FAILURE_ROOTFS_BUILD_JASP_VERSION_METADATA_MISSING`  
`CONTRACT_JOB=PASS`  
`TARGET_JOB=FAIL_AT_ROOTFS_BUILD_STEP_7`  
`LUNITA_SQUASHFS_FROM_LAST_HEAD=NOT_EMITTED`  
`INDEPENDENT_VALIDATION=NOT_REACHED`  
`S32=NOT_REACHED`  
`STABLE_RELEASE=NOT_REACHED`  
`FUNCTIONAL_CERTIFICATE=NOT_GRANTED`

`INTEGRATION_BRANCH=audit/lunita-zero-trust-certification-axioms-20261112`  
`INTEGRATION_HEAD=d1d10b2ca8a914fa4b39f690d3cef37e059796e5`  
`SQUASHFS_TIMESTAMP_CORRECTION=INTEGRATED_NOT_YET_VALIDATED`  
`JASP_SOURCE_VERSION_CORRECTION=INTEGRATED_NOT_YET_VALIDATED`  
`JASP_SOURCE_IDENTITY_SELFTESTS=INTEGRATED_NOT_YET_EXECUTED_IN_CI`  
`NEXT_REQUIRED_ACTION=MERGE_TARGET_JASP_CONSUMER_FIX_AND_RUN_FULL_VALIDATION`

**No se autoriza una transición a CERTIFIED hasta la demostración completa de AX-LUN-001 a AX-LUN-021 sobre un único SHA-256 de `LUNITA.squashfs`.**
