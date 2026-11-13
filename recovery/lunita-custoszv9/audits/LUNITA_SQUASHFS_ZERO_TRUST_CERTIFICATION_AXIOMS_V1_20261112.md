# LUNITA v1.8 — Axiomas verificables de certificación funcional SquashFS

**Documento:** `LUNITA_SQUASHFS_ZERO_TRUST_CERTIFICATION_AXIOMS_V1`  
**Versión:** `1.4.0`  
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

`FUNCTIONAL_CERTIFIED(I) ⇔ AX-LUN-001 … AX-LUN-024 ∧ CERTIFICATE_BINDINGS_VALID(C,I)`

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


### AX-LUN-021 — Aislamiento del mountpoint Flatpak por ejecución e intento

El constructor de aceptación monta el /run del host dentro del rootfs candidato mediante un bind recursivo. En consecuencia, los nombres bajo /run pertenecen a un espacio compartido con el runner y no pueden tratarse como rutas globales libres ni como estado exclusivo del rootfs.

El identificador HOST_BIND_NAME MUST derivarse del ID de workflow y del número de intento, validarse como componente de ruta seguro (lunita-host-[A-Za-z0-9-]+) y ser único entre ejecuciones e intentos. El destino de montaje MUST ser /run/${HOST_BIND_NAME}-runtime-1000; queda prohibido reutilizar el destino global fijo /run/lunita-runtime-1000.

El wrapper MUST comprobar que el destino específico no exista ni sea symlink antes de crearlo; si existe, MUST abortar sin borrarlo, reutilizarlo ni sobrescribirlo. El origen temporal MUST conservar propietario UID/GID 1000 y modo 0700. El proceso de destino MUST recibir exactamente el mismo XDG_RUNTIME_DIR que fue montado, y su verificador MUST derivar la ruta esperada desde HOST_BIND_NAME, exigir directorio real y comprobar UID/GID 1000 y modo 0700.

La limpieza MUST desmontar y retirar exclusivamente el destino creado por el intento actual y verificar el estado de los mounts. Las pruebas MUST demostrar que dos intentos distintos producen rutas distintas, que las identidades inseguras se rechazan y que un path XDG distinto, symlink, owner, group o mode incorrectos se deniegan.

La existencia de una ruta fija previa en el /run del host es evidencia de colisión, no autorización para eliminarla. Tal colisión produce BLOCKED hasta una corrección que aísle el nombre por ejecución y una revalidación completa del candidato.


### AX-LUN-022 — Propagación íntegra de la identidad de ejecución a través del límite de privilegios

La unicidad del mountpoint no se considera demostrada solo porque el wrapper construya una cadena con formato de run/attempt. El origen de identidad MUST ser el contexto real de GitHub Actions que ejecuta el workflow actual. El step invocador MUST pasar explícitamente GITHUB_RUN_ID y GITHUB_RUN_ATTEMPT a través del comando sudo/env que cruza el límite de privilegios; no se permite confiar en una conservación implícita de variables filtradas por sudo.

El wrapper MUST exigir ambos valores, no vacíos y numéricos, antes de crear archivos de estado, modificar sysctls o preparar mounts. MUST derivar HOST_BIND_NAME únicamente de esos dos valores y MUST abortar si cualquiera falta o no satisface el formato. Se prohíben valores fallback como local, 0, 1 o cualquier identidad constante que permita compartir mountpoints entre ejecuciones. No se permite inferir la identidad del branch, del nombre del job, del hostname del runner ni de la hora.

Las pruebas contractuales MUST inspeccionar el step de GitHub Actions para acreditar que ambos valores son transmitidos explícitamente a sudo/env, y deben demostrar que el wrapper no contiene fallback fijo. Las pruebas del helper MUST demostrar que una identidad ausente o insegura se rechaza y que el diagnóstico de Flatpak usa exactamente el XDG_RUNTIME_DIR del intento actual. Un fallo de propagación mantiene TARGET_RUNTIME=BLOCKED, aunque los demás tests unitarios pasen.

La validación de este axioma debe ocurrir en el workflow completo sobre el commit integrado: el run ID y attempt registrados en los logs y recibos MUST coincidir con el nombre de runtime mountpoint realmente creado, con el XDG_RUNTIME_DIR observado por el proceso y con el cleanup realizado. El verificador independiente MUST rechazar el recibo target cuando falte workflow_identity, el run ID/attempt no sea numérico, HOST_BIND_NAME no sea la composición exacta de ambos valores o el XDG_RUNTIME_DIR registrado no coincida con el mountpoint validado; el informe independiente conserva esta identidad junto con el hash del recibo.

### AX-LUN-023 — Coherencia multi-capa de identidad de release JASP y esquema de recibo

La identidad del release JASP MUST ser idéntica y verificable a través del constructor del rootfs, la verificación de fuente, el recibo del builder, la aceptación del target, la jerarquía de etiquetas y la validación independiente del binario ejecutado. La versión canónica del candidato en este baseline es `0.98.8`, derivada del proyecto CMake fijado (`0.98.8.0`) y de la combinación exacta del manifiesto Flathub y el commit de fuente JASP registrados; no se toma AppStream como autoridad ni se permite sustituir la versión por una etiqueta descriptiva.

Para JASP, la aceptación MUST validar conjuntamente: application ID `org.jaspstats.JASP`; versión `0.98.8`; commit de despliegue Flatpak fijado; `version_source=PINNED_FLATHUB_MANIFEST_AND_JASP_CMAKE_SOURCE_VERIFIED`; campo de recibo `flatpak_deployment_commit`; commit del manifiesto Flathub; SHA-1 Git blob del manifiesto; commit fuente JASP; SHA-1 Git blob de `CMakeLists.txt`; SHA-256 de ambos archivos y del recibo de identidad fuente; app ID y commit fuente extraídos del manifiesto; versión de proyecto CMake; y flags de identidad del recibo fuente. Cada archivo de metadatos MUST ser regular, no symlink, y concordar byte a byte con su SHA-256 registrado.

El contrato MUST ser específico por aplicación y no aplicar a JASP los campos de Jamovi: Jamovi usa `flatpak_commit` y `EXACT_PINNED_FLATPAK_COMMIT_MAPPING`; JASP usa `flatpak_deployment_commit` y la procedencia de versión verificada contra Flathub/CMake. La aceptación MUST comparar el commit observado por `flatpak info --system --show-commit` contra el commit exacto fijado de la aplicación; un recibo con el nombre de campo, origen, versión o commit incorrecto produce BLOCKED.

La suite contractual MUST probar coherencia entre el builder, el verificador de identidad fuente, el target helper, el workflow/jerarquía y la versión/commit fijados por el validador independiente. La aceptación target MUST producir evidencia de la verificación de manifiesto, fuente CMake y recibo de identidad; el validador independiente MUST comprobar posteriormente el banner de la aplicación realmente ejecutada con la versión y commit fuente exactos. Una prueba de código o de metadatos no sustituye la ejecución real de JASP.

Cualquier divergencia entre estas capas exige corrección append-only y una ejecución completa nueva. Está prohibido rebajar la versión esperada, omitir campos de recibo, convertir el campo faltante en opcional, aceptar AppStream ambiguo o reciclar la evidencia de una ejecución distinta.


### AX-LUN-024 — Propagación del runtime XDG validado a través de la delegación heredada

El runtime Flatpak por intento que se crea dentro del namespace del candidato MUST ser exactamente el runtime usado por todos los procesos Flatpak que ejecuta la aceptación target, incluidos los comandos que la capa v1.8 delega al launcher heredado v1.7. La aceptación MUST demostrar continuidad de identidad y ruta desde GitHub Actions (`GITHUB_RUN_ID`, `GITHUB_RUN_ATTEMPT`) hasta `HOST_BIND_NAME`, el mountpoint XDG creado, el entorno del helper target, el entorno entregado al launcher heredado y los procesos de aplicación.

Antes de delegar a v1.7, el wrapper v1.8 MUST validar que los IDs sean ASCII numéricos, que `HOST_BIND_NAME` sea exactamente `lunita-host-<run_id>-<attempt>` y que `XDG_RUNTIME_DIR` sea exactamente `/run/<HOST_BIND_NAME>-runtime-1000`. Cualquier ausencia o discrepancia MUST abortar con `BLOCKED` antes de ejecutar el launcher. El entorno invitado MUST recibir exactamente ese `XDG_RUNTIME_DIR`; queda prohibida toda ruta literal global o fallback como `/run/lunita-runtime-1000`.

El launcher v1.7 congelado MUST permanecer byte-exacto, con hash y referencia inmutables. La corrección se realiza únicamente en la frontera de delegación v1.8 y sus recibos/pruebas. Las pruebas MUST demostrar que la delegación construye el comando para el launcher heredado con el mismo valor validado, que IDs ausentes/no ASCII/mismatch y una ruta XDG antigua se deniegan sin ejecutar el proceso, y que los caminos de chroot y pivot_root conservan la identidad. Los diagnósticos Flatpak con `subprocess` simulado o chequeos de archivos de paquete no sustituyen el self-test real.

El recibo target MUST registrar la identidad de workflow, el runtime directory validado y los resultados de cada self-test Jamovi/JASP con sus códigos de retorno y logs/hashes. La aceptación y el validador independiente MUST rechazar un self-test bloqueado o un recibo cuya identidad del proceso delegado no concuerde con el mountpoint. La finalización del cleanup/unmount debe probar que se desmontó exclusivamente el runtime de ese intento.

Una prueba de diagnóstico que devuelve PASS no permite inferir PASS de la aplicación; solo el self-test real bajo el runtime por intento satisface este axioma.

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
| Target runtime | recibo de destino + identidad HOST_BIND_NAME + GITHUB_RUN_ID/ATTEMPT propagados a través de sudo + mountpoint XDG_RUNTIME_DIR | E01–E15, INT8 E04, mountpoint único por intento UID/GID 1000 modo 0700, ruta y smoke tests PASS |
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
- `scripts/lunita/run_target_runtime_acceptance_in_container_v1.sh`
- `recovery/lunita-custoszv9/runtime_engines_v1/target_runtime_acceptance_v1.py`
- `recovery/lunita-custoszv9/runtime_engines_v1/target_acceptance_tests_v1.py`
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



## 5.3 — Bloqueo de runtime por colisión de mountpoint en /run y corrección

El workflow 43332281299 (run #184), sobre HEAD a41e7b9fdc000b1c95f08aa212082e23d28051ea, pasó el job contractual 131579662707 y falló en el job de destino 131580478339, step 15 (Execute actual E01 inference and E02-E15 plus legacy application smoke tests). El log primario registra:

    BLOCKED: target Flatpak runtime mountpoint already exists: /run/lunita-runtime-1000

El wrapper ya aislaba el bind temporal del host con HOST_BIND_NAME, pero fijaba el destino del segundo bind en el nombre global /run/lunita-runtime-1000. El mismo wrapper hace mount --rbind /run "$ROOTFS/run"; por tanto, la comprobación se realiza contra el /run del host visible en el namespace privado. La ruta fija ya existía y el control fail-closed abortó con código 2 antes de ejecutar E01–E15. No se ha demostrado qué proceso creó la entrada previa; no se atribuye ese origen sin evidencia.

Por esa causa, los pasos de refresh JASP, empaquetado SquashFS, lane independiente, S32 y stable release quedaron omitidos. El run no emitió LUNITA.squashfs; el artefacto de overlay y el archivo de evidencia del job no sustituyen la imagen ni son certificados. No se reutilizan para la siguiente ejecución.

La corrección propuesta en la rama fix/lunita-flatpak-runtime-mount-collision-20261113 cambia el destino a /run/${HOST_BIND_NAME}-runtime-1000, valida el identificador antes de usarlo como componente de ruta y hace que el recibo de aceptación derive la ruta esperada desde el mismo identificador. Añade regresiones para unicidad entre intentos, identidad insegura, path incorrecto, tipo de entrada, UID/GID y modo. La corrección mantiene el rechazo de cualquier colisión y no elimina estado preexistente. Estado en esta revisión: IMPLEMENTED_NOT_YET_VALIDATED_BY_CI.


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
`NEXT_REQUIRED_ACTION=MERGE_INTEGRATION_AND_RUN_FULL_VALIDATION`

**No se autoriza una transición a CERTIFIED hasta la demostración completa de AX-LUN-001 a AX-LUN-022 sobre un único SHA-256 de `LUNITA.squashfs`.**


## 7. Estado actualizado — run #184 y remediación subsiguiente (13-11-2026)

Esta sección amplía el snapshot histórico de §6; no reemplaza los resultados fallidos ni les atribuye un PASS retroactivo.

OPERATIONAL_HEAD_AT_RUN_184=a41e7b9fdc000b1c95f08aa212082e23d28051ea  
WORKFLOW_RUN=43332281299  
WORKFLOW_RESULT=FAILURE  
CONTRACT_JOB=131579662707 / SUCCESS  
TARGET_JOB=131580478339 / FAILURE_STEP_15  
BLOCKER=STATIC_HOST_RUN_MOUNTPOINT_COLLISION  
ROOTFS_OVERLAY=APPLIED_ADDITIVELY_NOT_CERTIFIED  
TARGET_RUNTIME=BLOCKED  
SQUASHFS_PACKAGE_STEP=SKIPPED  
INDEPENDENT_VALIDATION=NOT_REACHED  
S32=NOT_REACHED  
STABLE_RELEASE=NOT_REACHED  
FUNCTIONAL_CERTIFICATE=NOT_GRANTED

La remediación está en la rama fix/lunita-flatpak-runtime-mount-collision-20261113. Su HEAD de trabajo al preparar esta revisión es cfe687753c0f6c2b43bbf019ad6229552dfcb9f6. Incluye cambios en el wrapper de namespace, en el verificador de runtime y en las pruebas contractuales. La incorporación de AX-LUN-021 y esta auditoría forma parte de la misma corrección documental. El estado sigue siendo IMPLEMENTED_NOT_YET_VALIDATED_BY_CI: aún no existe un nuevo run de extremo a extremo sobre el commit corregido.

NEXT_REQUIRED_ACTION=REVIEW_AND_INTEGRATE_REMEDIATION_THEN_RUN_FULL_VALIDATION_ON_EXACT_HEAD

## 8. Propagación de identidad no demostrada — run #211 (13-11-2026)

Esta sección conserva el resultado del primer pipeline posterior al merge de AX-LUN-021 y registra la siguiente corrección requerida. No se modifica retroactivamente el resultado del run.

RUN=43337415331 (#211)  
HEAD=7cea08fd33e36f894f98103af9492bc07e1aed54  
CONTRACT_JOB=131597010277  
CONTRACT_RESULT=FAILURE_AT_STEP_24  
TARGET_JOB=131597732193 / SKIPPED  
SQUASHFS_IMAGE=NOT_EMITTED  
INDEPENDENT_VALIDATION=NOT_REACHED  
S32=NOT_REACHED  
STABLE_RELEASE=NOT_REACHED  
FUNCTIONAL_CERTIFICATE=NOT_GRANTED

El log primario demuestra que la prueba test_runtime_mount_target_is_scoped_to_workflow_attempt PASS y que la prueba test_flatpak_diagnostic_compares_inherited_and_clean_guest_environments falló porque diagnose_flatpak_smoke() llamó a expected_xdg_runtime_dir() sin que el fixture de prueba definiera HOST_BIND_NAME. El resultado fue TargetGateError: HOST_BIND_NAME is missing or unsafe for a runtime mount path; la suite de 34 tests terminó FAILED (errors=1). No fue una prueba funcional de Flatpak/JASP real.

La revisión del workflow reveló además una condición de despliegue que no quedaba cubierta: el step llama a sudo -n env PATH=... bash wrapper, pero no transmitía GITHUB_RUN_ID ni GITHUB_RUN_ATTEMPT. El wrapper anterior usaba fallback local y 1; por tanto, aun habiendo corregido el nombre fijo /run/lunita-runtime-1000, el nombre resultante podía repetirse entre ejecuciones. La inspección del step y del wrapper demuestra esta omisión de propagación; no se presenta como un fallo observado en una ejecución real de mountpoint porque el target job fue skipped.

La nueva rama fix/lunita-flatpak-runtime-env-propagation-20261113 incorpora:
- propagación explícita de GITHUB_RUN_ID y GITHUB_RUN_ATTEMPT a través de sudo/env;
- rechazo fail-closed de ambas variables ausentes o no numéricas antes de crear estado;
- eliminación del fallback local;
- fixture válido para el test del diagnóstico y comprobación del XDG_RUNTIME_DIR derivado;
- tests que verifican la transmisión de ambas variables en el workflow y prohíben el fallback;
- ejecución del job contractual para pull requests cuya base sea la rama operativa, sin habilitar el job target en PR.

El contrato se amplía con AX-LUN-022. Estado de esta corrección en el momento de documentar: IMPLEMENTED_NOT_YET_VALIDATED_BY_CI. Requiere que la PR ejecute el job contractual en PASS y que después un push a la rama operativa ejecute de extremo a extremo el target runtime, el empaquetado SquashFS, la validación independiente, S32, stable release y certificado final sobre un único HEAD e imagen exacta.

## 9. Aseguramiento del recibo de identidad y gate independiente — rama correctiva

La rama fix/lunita-flatpak-runtime-env-propagation-20261113 añade una verificación de identidad al lector independiente latest_target_runtime_acceptance(). Antes de aceptar el recibo como target PASS, exige:

- workflow_identity con run_id y run_attempt numéricos;
- host_bind_name exactamente igual a lunita-host-<run_id>-<run_attempt>;
- workflow_identity.xdg_runtime_dir exactamente igual a /run/<host_bind_name>-runtime-1000;
- bloque xdg_runtime_dir con estado PASS_XDG_RUNTIME_DIR_UID1000_PRIVATE y la misma ruta.

El lector devuelve workflow_identity y xdg_runtime_dir junto con el receipt_sha256; por tanto el informe independiente conserva la procedencia que se validó. Se agregan pruebas negativas para identidad ausente e intento discordante, más prueba positiva para el recibo válido.

El step contractual de pull requests cuyo destino es la rama operativa se habilita para validar esta lógica antes del merge. El job target/independent sigue limitado a push o workflow_dispatch sobre la rama operativa; no se habilita una aceptación target parcial ni se reutilizan recibos históricos.

Estado de esta ampliación: IMPLEMENTED_NOT_YET_VALIDATED_BY_CI. El run #211 permanece FAILURE y no se altera.



## 10. Run #215 — discrepancia real entre release JASP y contrato target (13-11-2026)

Esta sección es una adición al historial; mantiene inalterado el resultado de #211, los fallos anteriores y la evidencia ya registrada.

RUN=43339097069 (#215)  
HEAD=2d66baf8f52ba90070a42ae6bec5f4794b8c745d  
TARGET_JOB=131603445497  
TARGET_STEP=15 / Execute actual E01 inference and E02-E15 plus legacy application smoke tests  
TARGET_RESULT=FAILURE  
WORKFLOW_RESULT=FAILURE  
FUNCTIONAL_CERTIFICATE=NOT_GRANTED  
SQUASHFS_IMAGE=NOT_EMITTED

El propio wrapper acreditó la identidad de ejecución: `run_id=43339097069`, `attempt=1`, `HOST_BIND_NAME=lunita-host-43339097069-1`. El montaje XDG devolvió `PASS_XDG_RUNTIME_DIR_UID1000_BIND`; la inspección del directorio confirmó UID/GID 1000 y modo 0700. El proceso creó el user namespace desde el mount root candidato y declaró `PASS_TARGET_ROOTFS_EXECUTION_CONTEXT: private mount namespace + pivot_root`. Los pasos de verificación de desmontaje, recopilación de evidencia, cleanup final y subida de evidencia terminaron SUCCESS.

La aceptación se bloqueó antes de completar la batería target por `TargetGateError: Flatpak app identity/version mismatch: org.jaspstats.JASP`. El recibo target bloqueado registra SHA-256 `839a58404497c72372fe04b5972a15bd972f1fafa3ee80db9c2d4b2c46376d62`, con `certification=NOT_GRANTED` y la identidad exacta del workflow antes mencionada. Este error ocurre al validar el recibo de construcción; no constituye evidencia de que JASP se haya iniciado o que su funcionalidad haya fallado. La verificación target no llegó a la prueba real de JASP ni a la suite completa E01–E15/legacy.

La inspección comparada de los archivos fijados reveló tres incoherencias en `target_runtime_acceptance_v1.py`:
1. el helper target esperaba JASP `0.98.1`, pero el constructor, el manifiesto/CMake source verifier, la jerarquía y el lane independiente fijan `0.98.8`;
2. exigía para ambos Flatpak `version_source=EXACT_PINNED_FLATPAK_COMMIT_MAPPING`, pero el builder registra para JASP `PINNED_FLATHUB_MANIFEST_AND_JASP_CMAKE_SOURCE_VERIFIED`, mientras Jamovi sí usa la primera;
3. leía `flatpak_commit` para toda aplicación, pero el recibo de JASP registra `flatpak_deployment_commit`; Jamovi usa `flatpak_commit`.

La corrección en la rama `fix/lunita-jasp-version-contract-coherence-20261113` alinea la versión de target con `0.98.8`, diferencia los dos esquemas de recibo según la aplicación y añade revalidación de los bytes/sha256 de manifiesto Flathub, fuente CMake y recibo de identidad; valida Git blob SHA-1, app ID, commit fuente, versión CMake, commits de despliegue y flags de procedencia. Se agregan tests de coherencia cross-layer y tests positivos/negativos de la verificación del source release.

La corrección amplía el contrato con AX-LUN-023. Estado al documentar: `IMPLEMENTED_NOT_YET_CI_VALIDATED`. Requiere PASS contractual, nuevo full run sobre el HEAD integrado, aceptación real de JASP, ejecución de la suite target completa, round-trip SquashFS estricto y validación independiente/S32/stable/certificador sobre el SHA-256 exacto de la imagen.

## 11. Run #217 — desalineación XDG en delegación del launcher heredado (13-11-2026)

RUN=43341112917 (#217)  
HEAD=eff579756bd905930de9b22dcf7642c2c8e14a06  
TARGET_JOB=131609898416  
TARGET_STEP=15 / Execute actual E01 inference and E02-E15 plus legacy application smoke tests  
TARGET_RESULT=FAILURE  
FUNCTIONAL_CERTIFICATE=NOT_GRANTED  
SQUASHFS_IMAGE=NOT_EMITTED

El target pasó la identidad del rootfs JASP: el log registra `PASS_ROOTFS_BUILD_IDENTITY`; JASP quedó validado a `0.98.8`, deployment commit `83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7`, source commit `b6cd3b0310be4e18e1b673ac11f14e55615c8fa1`, metadatos del manifiesto y CMake. El recibo target también conservó run_id `43341112917`, attempt `1`, HOST_BIND_NAME `lunita-host-43341112917-1` y el XDG runtime por intento. No se observó una discrepancia JASP en este run.

El self-test real de Jamovi fue bloqueado: `jamovi-self-test rc=3`. El diagnóstico Flatpak heredado y limpio devolvió `returncode=0` en ambos casos, pero es un diagnóstico con finalidad limitada y no sustituye el self-test.

La inspección del código `recovery/lunita-custoszv9/runtime_engines_v1/lunita_beta_v1_8.py` demuestra que `run_legacy()` construía el entorno invitado con la ruta fija `XDG_RUNTIME_DIR=/run/lunita-runtime-1000`, mientras que el wrapper y el mountpoint real del run #217 usan `/run/lunita-host-43341112917-1-runtime-1000`. Por tanto, la aplicación heredada recibía una ruta distinta de la montada y validada. Esta discrepancia de código, más el rc=3 del self-test, constituye la causa técnica identificada; no prueba por sí sola una causa interna adicional dentro de Jamovi.

El job pasó los pasos de desmontaje/verificación de mounts, cleanup y subida de evidencia. El gate anterior al empaquetado impidió emitir `LUNITA.squashfs`; por lo tanto no se ejecutaron el round-trip final, la validación independiente, S32, stable release ni el certifier.

La corrección en `fix/lunita-legacy-flatpak-runtime-identity-20261113` cambia únicamente la frontera v1.8: exige IDs de workflow ASCII numéricos, HOST_BIND_NAME exacto y XDG_RUNTIME_DIR idéntico al mountpoint validado; pasa ese path a la variable de entorno invitada que se entrega a la launcher v1.7. Añade pruebas para la ruta dinámica, denegación ante identidad/ruta ausente o discrepante, y verificación de que el comando delegado usa el mismo XDG en contexto de target. El launcher v1.7 congelado no se modifica ni se sustituye. El contrato se amplía con AX-LUN-024.

Estado al registrar esta auditoría: `IMPLEMENTED_NOT_YET_CI_VALIDATED`. Un nuevo run completo posterior a la integración debe repetir los gates, ejecutar los self-tests reales Jamovi y JASP, y solo entonces continuar con el empaquetado y certificación.

## 6. Addendum append-only — AX-LUN-025 y AX-LUN-026

**Registro de evidencia:** 2026-11-13 UTC. Revisión del workflow #220, run 43342684248, job de destino/validación independiente 131615414711, rama operativa fix/lunita-v18-rootfs-bound-checkpoint-20261109, HEAD 3db072d393d62f9b033cdf70832d2d66df7ff534. Este addendum extiende AX-LUN-001…024 y no los reemplaza. La fotografía de estado histórica del encabezado y sus conclusiones anteriores se conserva sin edición.

### AX-LUN-025 — Separación semántica entre la referencia original y el replay determinista

El gate JASP MUST distinguir dos propiedades independientes: (a) la ejecución del fixture original coincide con la referencia almacenada; (b) dos ejecuciones del mismo clon desechable con seed controlado generan resultados recién calculados idénticos entre sí. La segunda propiedad no implica la primera.

El fixture original empaquetado MUST permanecer byte-identical y mantener el SHA-256 fijado. Su ejecución real en el runtime identificado MUST terminar con código de proceso 0 y superar la comparación de referencia. Toda divergencia estructural o estadística mantiene el gate de referencia en BLOCKED. La identidad correcta del runtime, el inicio de JASP, el sandbox y la repetibilidad separada no absuelven ese fallo.

El replay puede demostrar exclusivamente reproducibilidad cuando el recibo hash-bound del clon es válido; solo se modifica la opción seed activa autorizada; se preservan el archivo fuente y los resultados históricos; ambas ejecuciones usan el mismo runtime verificado; sus filas calculadas y hashes coinciden exactamente; el clon permanece estable y se elimina; y los códigos reales de ambos procesos quedan conservados.

Cuando las dos ejecuciones del replay coincidan entre sí pero difieran de la referencia histórica, el estado MUST ser PASS_DETERMINISTIC_REPLAY_REFERENCE_MISMATCH_RECORDED, con reference_comparison_status=BLOCKED_STORED_REFERENCE_MISMATCH y acceptance_scope=DETERMINISTIC_REPLAY_ONLY. Este estado nunca puede presentarse como PASS_JASP_STRICT_ROUNDTRIP ni como aprobación de referencia. El agregador y el informe independiente pueden registrar el subgate de replay como aprobado, pero el fixture original sigue siendo requisito obligatorio e independiente.

Los códigos de salida originales de los procesos JASP MUST permanecer visibles. Un returncode sintético derivado de la repetibilidad no reemplaza ni modifica save_subprocess_returncode ni rerun_subprocess_returncode. El estatus general JASP permanece BLOCKED mientras el fixture original no supere su gate.

### AX-LUN-026 — Procedencia de referencia y comparación semántica de resultados JASP

Cada comparación JASP MUST preservar evidencia enlazada por hash del archivo fuente .jasp, identidad de despliegue Flatpak, versión y source commit del runtime, módulo y análisis activos, configuración y estado de seed, resultados almacenados, filas recién calculadas, número de modelos visitados, términos de cada modelo, valores P(M|data) y BF01 cuando existan, códigos reales de salida, comandos y hashes de logs y tablas.

Un cambio en el número de modelos, términos incluidos, orden sustantivo o valores estadísticos constituye mismatch semántico, no diferencia cosmética. Si no se conoce la procedencia del productor de los resultados almacenados (versión, source commit, módulo, opciones y configuración de seed), MUST registrarse BLOCKED_REFERENCE_PROVENANCE_UNKNOWN. No se atribuirá causalidad a versión, algoritmo, módulo o aleatoriedad sin evidencia que discrimine esas hipótesis.

Cualquier baseline candidata nueva exige especificación previa de los datos, el runtime, el módulo, las opciones, las semillas y el criterio de aceptación; generación controlada y trazable; revisión independiente de los resultados frente a evidencia estadística primaria; y versionado separado. La referencia histórica y su SHA-256 permanecerán conservados y no serán sobrescritos. Se prohíben la búsqueda oportunista de seeds, las tolerancias retroactivas, la sustitución de filas y la regeneración automática de resultados esperados.

### Evidencia observada en run #220 — no certificatoria

- Runtime observado: JASP 0.98.8; source commit b6cd3b0310be4e18e1b673ac11f14e55615c8fa1; deployment commit 83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7. La identidad runtime fue PASS.
- Fixture original Death Penalty: SHA-256 fc8b6f8faf0e4437c8e4ab4bd922b3e959a0d4549c813b229bc5708050851895. La evidencia registra que la fuente no cambió.
- La prueba del fixture original produjo cuatro modelos calculados con P(M|data)/BF01 de 0.514/1.000, 0.358/1.434, 0.127/4.043 y 0.002/342.3. La referencia almacenada contenía cuatro modelos diferentes, con 0.508/1.000, 0.394/1.289, 0.094/5.404 y 0.004/127.0. JASP informó The results are different y devolvió JASP_UNITTEST_RC=1. SHA-256 del log: 2af5fe0b099f01c1ab5b7467fbb7ab4ffc4679955b8dfe30c024f4f881a5463f.
- El replay reseedeado utilizó un clon con SHA-256 4b642cc13549f99f1b386791c3a670e6fb9cc34430f564ad68820bde46af4c2f. Save y rerun generaron las mismas tres filas; su SHA-256 fue ef1f4ec4493aea848c9449f6ca96864a1cd95e353544601c6edf52fb284a1a32. Ambos procesos conservaron RC=1 al comparar contra la referencia histórica, que tenía cuatro filas. El estado de comparación fue BLOCKED_STORED_REFERENCE_MISMATCH. Log save: e613a1af36a963b24c5440939ca2630ed5b4f35fa4b926e4bde8f6baecf92bdd. Log rerun: 613ac30e6d20ee8f14256edb550894b9d3731184d8e67c43221df4eb2b7a4ebf.
- Los casos Reliability y WeightGain pasaron con RC=0. Los smoke tests heredados E01–E15 y el empaquetado/round-trip SquashFS del job fueron satisfactorios. La validación independiente JASP falló; el certifier, S32 y stable release fueron omitidos.

**Conclusión forense:** se demostró una discrepancia estadística y estructural entre los resultados almacenados y los recalculados. La evidencia disponible no determina si su origen es la configuración no determinista del análisis original, la procedencia del resultado almacenado, el estado histórico de opciones/semilla o una interacción entre dichos factores. Por tanto ROOT_CAUSE=UNRESOLVED y REFERENCE_PROVENANCE=UNKNOWN hasta obtener la procedencia primaria. JASP_REFERENCE_GATE=BLOCKED y FUNCTIONAL_CERTIFICATION=NOT_GRANTED.

### Extensión del predicado terminal

La admisión anterior queda ampliada sin sustituir sus condiciones: ADMIT(I) = ADMIT_PREVIOUS(I) AND AX-LUN-025 AND AX-LUN-026. Ningún artefacto ni recibo de ejecuciones anteriores se hereda automáticamente.

### AX-LUN-027 — Procedencia histórica parcial verificable y atribución limitada de referencias JASP

La procedencia de un resultado almacenado MUST representarse por dimensiones separadas: identidad del archivo fuente; identidad del contenedor que incorpora el archivo; identidad/version declarada en los resultados; procedencia del proceso que copió o extrajo el archivo; revisión de código efectivamente ejecutada; módulo estadístico binario/fuente y dependencias; opciones de análisis y estado de seed; y evidencia de ejecución del productor. No se permite colapsar estas dimensiones en un único booleano UNKNOWN/PASS.

Cuando la identidad del fixture sea corroborada por el mismo Git blob SHA en repositorios oficiales independientes, el resultado se clasificará SOURCE_ARTIFACT_IDENTITY=VERIFIED. Cuando el JSON/HTML histórico cite explícitamente una versión de JASP, se clasificará PRODUCER_VERSION_DECLARED, no PRODUCER_EXECUTION_VERIFIED. Una revisión obtenida de la historia pública como el último commit visible antes de una ejecución automatizada puede registrarse SOURCE_REVISION_INFERRED, nunca como el SHA exacto ejecutado, salvo que el recibo primario lo declare. La identidad del módulo, bibliotecas R, sistema, configuración de opciones y ejecución generadora permanecerán UNKNOWN si no existe recibo primario independiente.

Un workflow de copia/extracción que no lanza JASP ni evalúa el análisis NO constituye evidencia de recálculo estadístico. Su recibo solo acredita la operación de extracción/publicación que el código ejecuta. La fecha de commit o la fecha de extracción no puede presentarse como fecha de ejecución del análisis.

Una procedencia parcial verificada se expresará como REFERENCE_PROVENANCE=PARTIALLY_RECONSTRUCTED, con estado explícito por dimensión y sin eliminar los campos desconocidos. La hipótesis de divergencia entre versiones puede priorizar diagnóstico comparativo, pero no constituye ROOT_CAUSE. La prueba causal exige reproducir la referencia con un runtime y módulo identificados o aislar mediante comparación controlada las versiones, módulos, dependencias y opciones que explican la divergencia.

Para una referencia histórica citada como JASP 0.97.1 y un runtime de destino JASP 0.98.8, MUST mantenerse el gate de compatibilidad estadística BLOCKED mientras no se demuestre una de estas alternativas admisibles: (a) el runtime histórico identificado reproduce la referencia almacenada sobre el fixture original byte-identical; o (b) se especifica y aprueba independientemente un baseline nuevo, versionado por separado, calculado con el runtime de destino y una configuración predefinida, determinista y trazable. En la alternativa (b), el baseline histórico, su SHA y sus valores siguen preservados; el cambio debe documentarse como nueva línea de referencia, no como PASS retroactivo de la referencia histórica.

Se prohíbe inferir la versión productora solo a partir de la fecha de actualización, inferir una revisión exacta del checkout a partir de la rama móvil, equiparar una extracción a un recálculo, inferir el módulo cargado desde el manifiesto de módulos disponibles, o atribuir causalidad exclusivamente a un cambio de versión. Cualquier ausencia de evidencia mantiene la dimensión en UNKNOWN y bloquea la certificación cuando sea exigida por el predicado.

**Aplicación observada al fixture Death Penalty (evidencia pública consultada el 2026-11-13 UTC):** el archivo `.jasp` original coincide por Git blob SHA `5da69f932e17a10bfb887552b6ca283efc87d338` en `jasp-stats/jasp-desktop` (commit `9d91e61b354b48f00bc384e3ed7827a10aa36dee`) y `jasp-stats/jasp-data-library` (commit `bb7d9ca73a98d43269fa783e09a80f32c65cb903`). El archivo de resultados histórico de Data Library tiene blob SHA `f4ef4723cd4ecf001c8c0418e828570bbbb7856e`; el HTML publicado tiene blob SHA `aee7f2f220c88e791fa72ad4d8f8723488799e7f`. El JSON incluye la cita JASP 0.97.1, `samplingMethod=auto`, `samplingMethodManualSamples=10000`, `seed=1` y `setSeed=false`. El workflow oficial de Data Library ejecuta `dataGatherScript.py`, que copia los archivos `.jasp` y extrae `index.html` y recursos sin lanzar JASP ni recalcular análisis. Su run #121 (ID `26766614970`) finalizó success el 2026-06-01; los logs del job ya no están disponibles (HTTP 410). La historia pública de `jasp-desktop/development` identifica `9d91e61b354b48f00bc384e3ed7827a10aa36dee` como último commit anterior al inicio del workflow, y CMake declara JASP 0.97.1, pero el SHA exacto consumido por ese checkout no quedó ligado a un recibo del run. Por ello, el estado admisible es: archivo fuente VERIFIED; versión citada DECLARED; revisión de origen INFERRED; ejecución productora, módulo exacto, dependencias y opciones efectivas UNKNOWN. La raíz del mismatch sigue UNRESOLVED.

### Extensión del predicado terminal — AX-LUN-027

`ADMIT_CURRENT(I) = ADMIT_PREVIOUS(I) AND AX-LUN-025 AND AX-LUN-026 AND AX-LUN-027`. Esta extensión no otorga PASS al fixture original, no autoriza el cambio del baseline histórico y no modifica el alcance candidate-only de la certificación.


### AX-LUN-028 — Referencias de evidencia inválidas no deben abortar el informe independiente

La validación de cada referencia de evidencia MUST ser fail-closed y contener los errores de datos de entrada. Un `evidence_path` ausente, `null`, vacío, de tipo distinto de string, mal formado, inexistente, simbólico, no legible o cuyo contenido no coincida con el SHA-256 declarado MUST producir exclusivamente un subgate BLOCKED para esa evidencia y, por consecuencia, impedir el PASS agregado. La validación MUST NOT lanzar una excepción no controlada que aborte la generación del informe independiente, la persistencia de evidencia o la fase de diagnóstico.

La ausencia o invalidez de una referencia no puede convertirse en PASS, en evidencia no requerida, ni en un resultado sintético. Los códigos de salida de procesos, estados JASP originales, hashes y causas permanecen separados. El informe agregado MUST conservar el identificador del caso, motivo de bloqueo y referencia inválida, sin omitir el resto de controles ni alterar evidencia histórica. Una referencia inválida nunca puede satisfacer un predicado de certificación por el mero hecho de que el proceso principal haya terminado o de que otro subgate haya pasado.

**Evidencia correctiva run #224:** el job independiente recibió un caso JASP con `evidence_path=null`; la conversión directa `pathlib.Path(None)` produjo `TypeError` en `jasp_case_accepted` y abortó la creación del informe. El arreglo valida el tipo y contenido del path, captura excepciones de acceso/lectura y devuelve BLOCKED; una prueba de regresión reproduce el caso null y verifica que el informe termina de forma bloqueada.

### Extensión del predicado terminal — AX-LUN-028

`ADMIT_CURRENT(I) = ADMIT_PREVIOUS(I) AND AX-LUN-025 AND AX-LUN-026 AND AX-LUN-027 AND AX-LUN-028`. Este control de robustez de referencias no relaja ningún requisito de evidencia JASP, ni otorga PASS al resultado histórico discrepante.


## 7. Addendum append-only — AX-LUN-029: separación entre receta pública de release y prueba de ejecución histórica

**Registro de evidencia:** 2026-11-13 UTC. La revisión pública de fuentes oficiales permite reforzar la reconstrucción de procedencia del fixture Death Penalty, sin convertir metadatos de publicación en evidencia de ejecución productora.

### AX-LUN-029 — Receta histórica verificable no equivale a ejecución productora verificada

La procedencia de JASP MUST distinguir, como mínimo, cuatro identidades no intercambiables: (1) commit del repositorio de manifiestos Flathub; (2) commit fuente de `jasp-desktop` referenciado por ese manifiesto; (3) commit OSTree del despliegue Flatpak instalado; y (4) ejecución concreta que generó los resultados almacenados. Ninguna de estas identidades puede sustituir o inferir silenciosamente a otra.

Para la línea histórica declarada como JASP 0.97.1 se verificó en los repositorios oficiales:

- Commit de manifiesto Flathub: `9ed450fdd8abaf61139b2ff7271c6949e73ac9e4`, fechado 2026-06-05, con verificación criptográfica GitHub `verified=true`.
- Blob del manifiesto `org.jaspstats.JASP.json`: `c77a5f158ab86b0a5be776768478984668d9f282`.
- Commit de código fuente `jasp-desktop` fijado por la receta: `28be3fee5c7ce2119f1945acd0254eb4fb8cb6e2`; su `CMakeLists.txt` declara `project(JASP VERSION 0.97.1.0)`.
- Receta de plataforma: KDE Platform/SDK 6.10 y Qt WebEngine BaseApp 6.10; R 4.5.2 con SHA-256 `0d71ff7106ec69cd7c67e1e95ed1a3cee355880931f2eb78c530014a9e379f20`.
- Bundle de módulos x86_64 declarado en `deps/modules.json`: `Flatpak-x86_64-ModulesDir-04-05.tar.xz`, SHA-256 `26ca4801f8fa9bda6cc920c6009af129bb0f33e5d409a096d130bc761f308ce0`.

Estos datos acreditan una **receta pública de construcción 0.97.1 con fuentes e insumos fijados**. No acreditan el commit OSTree del despliegue Flatpak histórico ni que esa receta exacta fuera la que ejecutó el análisis que produjo los resultados almacenados del fixture. Por tanto, `HISTORICAL_RELEASE_RECIPE=VERIFIED`; `HISTORICAL_SOURCE_COMMIT=VERIFIED`; `HISTORICAL_OSTREE_DEPLOYMENT_COMMIT=UNKNOWN`; `HISTORICAL_PRODUCER_EXECUTION=UNKNOWN` mientras no aparezca un recibo primario enlazado al cálculo original.

La prueba diagnóstica admisible MUST reconstruir o instalar la receta histórica en un `FLATPAK_SYSTEM_DIR` y perfil de usuario aislados, registrar el hash de todos los manifiestos, archivos fuente, módulos, dependencias, artefactos construidos, runtime/base commits y recibos de despliegue; confirmar la versión desde el binario/fuente ejecutados; y ejecutar el fixture original byte-identical con red no compartida. El test MUST conservar el código real de salida y comparar estructura, número de modelos, términos y valores estadísticos contra la referencia almacenada, sin redondeo, tolerancias añadidas, búsquedas de seeds, parches de formato, hooks de arranque ni mutación de archivos.

Si la receta histórica aislada reproduce exactamente la referencia, el resultado se clasifica `HISTORICAL_RECIPE_COMPATIBILITY=REPRODUCED`, no `HISTORICAL_PRODUCER_EXECUTION=PROVEN`. Si no reproduce, la compatibilidad permanece `BLOCKED` y la causa raíz sigue `UNRESOLVED`. En ambos casos la procedencia de la ejecución productora original solo se elevará a VERIFIED mediante evidencia primaria vinculada a aquella ejecución concreta.

La prueba histórica es diagnóstica y separada: MUST NOT reemplazar, actualizar ni cambiar el JASP objetivo 0.98.8 del candidato; MUST NOT alterar el fixture original, los resultados guardados, el hash histórico, las tolerancias ni el predicado de aceptación; y MUST NOT convertir un replay determinista en una aprobación de la referencia almacenada. La alternativa de establecer un baseline nuevo continúa sujeta a AX-LUN-027 y exige especificación anticipada, revisión independiente y versionado separado, conservando intacta la referencia histórica.

### Evidencia de fuente primaria incorporada a AX-LUN-029

- Flathub 0.97.1 manifest commit: `https://github.com/flathub/org.jaspstats.JASP/commit/9ed450fdd8abaf61139b2ff7271c6949e73ac9e4`.
- Upstream JASP source commit pinned by that manifest: `https://github.com/jasp-stats/jasp-desktop/commit/28be3fee5c7ce2119f1945acd0254eb4fb8cb6e2`.
- Pinned source CMake file: `https://github.com/jasp-stats/jasp-desktop/blob/28be3fee5c7ce2119f1945acd0254eb4fb8cb6e2/CMakeLists.txt`.

**Estado:** `SPECIFIED_WITH_PRIMARY_SOURCE_EVIDENCE; HISTORICAL_RUNTIME_REPLAY_NOT_YET_EXECUTED; CERTIFICATION_NOT_GRANTED`.

### Extensión del predicado terminal — AX-LUN-029

`ADMIT_CURRENT(I) = ADMIT_PREVIOUS(I) AND AX-LUN-029`. Esta extensión añade separación de procedencia y una prueba diagnóstica reproducible; no convierte la receta en ejecución histórica probada, no aprueba el mismatch ni altera los requisitos de los axiomas anteriores.


## 8. Addendum append-only — AX-LUN-030: identidad post-mutación y cierre entre la imagen y el rootfs sometido a validación independiente

**Registro de evidencia:** 2026-11-13 UTC. Auditoría estática del orden de ejecución del workflow v1.8, del actual refresco Flatpak/JASP, del inventario independiente del rootfs y del certifier final.

### AX-LUN-030 — La imagen empaquetada y el rootfs realmente validado deben ser el mismo estado material

Sea `R_P` el árbol de rootfs cuya representación canónica se usó para construir `I=LUNITA.squashfs`, y sea `R_V` el árbol de rootfs presente cuando concluyen las pruebas de la validación independiente. La certificación MUST probar `Manifest(R_P)=Manifest(R_V)` mediante el mismo algoritmo canónico de inventario usado por el empaquetador, no por igualdad de nombres, rutas, tamaños totales o informes PASS independientes.

El recibo de empaquetado MUST exponer la identidad y SHA-256 del manifiesto canónico `Manifest(R_P)`. El informe independiente MUST recalcular sobre el rootfs efectivamente sometido a pruebas el mismo manifiesto canónico y registrar su SHA-256 como `observed_post_validation_rootfs_manifest_sha256`. El certifier MUST exigir igualdad exacta de ambos hashes y MUST incluir ambas referencias en la cadena de evidencia. Si no se puede recomputar el manifiesto, si cualquier entrada o metadato difiere, si la comparación se refiere a otra ruta/rootfs o si los algoritmos/versiones no son los mismos, la validación independiente y la certificación MUST quedar BLOCKED.

La comparación es necesaria porque el empaquetador verifica el estado del árbol al construir y extraer la imagen, mientras que la regresión independiente se ejecuta posteriormente sobre el rootfs de trabajo. Dos PASS separados no demuestran por sí solos que no hubo modificación entre esas etapas. La igualdad del manifiesto canónico cierra ese intervalo y demuestra que el rootfs sometido a las pruebas posteriores representa exactamente el árbol del que se construyó la imagen.

### AX-LUN-030A — Identidad íntegra de runtimes y binarios modificados después de la aceptación inicial

Toda actualización, reemplazo o parche ejecutado después del recibo de aceptación del runtime de destino y antes de construir la imagen MUST quedar identificado por un recibo de mutación hash-bound. En particular, el refresco del runtime JASP MUST registrar:

- referencia Flatpak y commit OSTree exacto del runtime KDE finalmente desplegado, además del commit de la aplicación JASP;
- referencia/commit del SDK usado para construir dependencias Qt; versión Qt observada; etiqueta o commit fuente de QtHttpServer; SHA-256 del archivo fuente descargado y de los binarios construidos;
- SHA-256 antes y después de los binarios JASP y bibliotecas Qt reemplazadas; SHA-256 del script de parcheo; sitios de parche esperados y observados; y resultado post-escritura;
- identidad completa del manifiesto Flathub, commit fuente JASP y versión CMake observada.

La identidad del commit Flatpak de la aplicación no acredita, por sí sola, los bytes posteriores a un parche local o a un reemplazo de bibliotecas. Los hashes pre/post y el manifiesto final del rootfs MUST conservar esa distinción. La prueba funcional de JASP MUST ejecutarse contra los binarios post-mutación exactos que quedan incluidos en `I`; su recibo MUST referenciar los hashes de dichos binarios y el commit OSTree del runtime que realmente cargó. Un log de consola sin hash ligado al recibo no satisface este axioma.

La aceptación inicial E01–E15 puede seguir vinculada a su propio recibo y estado temporal; no puede presentarse como prueba retrospectiva de una versión JASP/Qt modificada después. La regresión JASP posterior y la igualdad de manifiestos del AX-LUN-030 son los controles que verifican el estado final. Ningún parche o actualización posterior a esas pruebas puede ocurrir sin repetir las pruebas afectadas y revalidar la igualdad del manifiesto.

Estos requisitos NO autorizan actualización flotante no registrada, mutación de fixture, modificación de resultados históricos, ajuste de tolerancias, parche estadístico ni reemplazo del JASP 0.98.8 objetivo por el runtime histórico 0.97.1. Los diagnósticos históricos del AX-LUN-029 permanecen aislados y separados.

### Hallazgo estático que motiva AX-LUN-030 — no equivale a fallo de ejecución

El flujo de validación actual construye y verifica `LUNITA.squashfs` antes de ejecutar el worker de validación independiente. El recibo de empaquetado conserva `source_rootfs_manifest_sha256`, y el informe independiente conserva un inventario del rootfs; sin embargo, el certifier inspeccionado exige por separado la validez del recibo de paquete y del inventario y no compara explícitamente el hash del manifiesto canónico de origen con un manifiesto recalculado post-validación bajo el mismo algoritmo. Esta brecha de vínculo estático debe cerrarse antes de conceder la certificación.

Además, el paso de refresco JASP mantiene fijado el commit de aplicación, actualiza el runtime KDE al tip publicado y reemplaza bibliotecas Qt; luego aplica una modificación binaria al formatter JASP. Los logs observados muestran commits/versiones durante el paso, pero la evidencia estructurada consultada no exponía aún un único recibo que ligara los hashes pre/post de todos esos binarios y los commits OSTree finales al caso JASP ejecutado. La aceptación de este cambio exige implementar y comprobar ese recibo, no inferir que el commit de aplicación identifica el estado posterior.

**Estado:** `STATIC_GAP_IDENTIFIED; SPECIFIED_NOT_IMPLEMENTED; CERTIFICATION_NOT_GRANTED`.

### Extensión del predicado terminal — AX-LUN-030

`ADMIT_CURRENT(I) = ADMIT_PREVIOUS(I) AND AX-LUN-030 AND AX-LUN-030A`. Una imagen con round-trip correcto no queda certificada mientras la identidad del rootfs validado después del empaquetado y los binarios/runtime efectivamente probados no estén cerrados criptográficamente contra los bytes de la imagen.


## 9. Addendum append-only — AX-LUN-031: prueba de implementación no equivale a certificación funcional

**Registro de evidencia:** 2026-11-13 UTC. Este axioma registra la implementación de los controles AX-LUN-030/030A y el resultado de su aceptación contractual. No modifica las declaraciones históricas contenidas en el addendum 8; complementa su estado con nueva evidencia.

### AX-LUN-031 — Cierre de implementación, validación y certificación como estados distintos

La implementación de un control, su aceptación contractual automatizada, su ejecución sobre el candidato real, la validación independiente y la emisión del certificado MUST mantenerse como estados epistémicos separados. Ningún estado inferior autoriza inferir uno superior.

Para el cierre AX-LUN-030/030A quedan registrados los siguientes artefactos de implementación:

- `recovery/lunita-custoszv9/lunita_stability_certification_lane_v1.py`: recálculo del manifiesto canónico del rootfs después de la validación independiente, generación del recibo de cierre y verificación del recibo de mutación JASP/Qt antes de ejecutar los casos.
- `scripts/lunita/package_candidate_squashfs_v1.py`: implementación canónica de `tree_manifest`, reutilizada directamente por la validación post-pruebas y por el certificador final.
- `scripts/lunita/certify_candidate_squashfs_v1.py`: comprobación independiente del recibo de cierre, verificación del hash del recibo y nueva recomputación del manifiesto vivo en el punto de emisión; exige además la comprobación de identidad JASP post-mutación.
- `scripts/lunita/test_certify_candidate_squashfs_v1.py`: fixture de certificación con manifiesto canónico real y prueba negativa de mutación del rootfs posterior al empaquetado.
- `scripts/lunita/record_jasp_runtime_mutation_receipt_v1.py`: emisión fail-closed del recibo `LUNITA_JASP_RUNTIME_POST_MUTATION_RECEIPT/1.0`; no exige falsamente que el ejecutable `bin/JASP` cambie si la modificación ocurre en un recurso Qt interno.
- `scripts/lunita/patch_jasp_certification_runtime_v1.py`: registro de SHA-256 pre/post de cada recurso formatter realmente modificado, junto con la ruta y el número de sitios afectados.
- `scripts/lunita/refresh_jasp_runtime_v1.sh` y `.github/workflows/lunita-v18-direct-functional-validation.yml`: propagación, conservación y entrega del recibo de mutación a la fase independiente y a la colección de evidencia.

### Evidencia contractual registrada

La revisión `535ad0107fe4935c212df8d0c4e219e9360b6338` completó correctamente el workflow contractual `43359676224` (job `131669941407`) con conclusión `success`. Esa ejecución verifica compilación, contratos y pruebas unitarias/negativas de la implementación, incluido el generador de recibos JASP/Qt, el cierre de manifiestos y el resto de contratos v1.8. La validación de destino fue omitida correctamente en el evento pull request; por ello, el resultado contractual no constituye una ejecución funcional sobre el rootfs candidato real.

Los fallos de ejecuciones contractuales anteriores se conservan como historial de desarrollo y diagnóstico; no se presentan como aprobaciones. El resultado `success` citado corresponde únicamente a la revisión SHA exacta indicada arriba.

### Condición de paso restante

AX-LUN-030/030A solo podrán considerarse validados funcionalmente cuando una nueva ejecución completa, posterior a la integración de esta revisión en la rama operativa, pruebe sobre el mismo `G06_REBUILD_CANDIDATE_R1/1.8.0`:

1. La regeneración y comparación exacta del manifiesto post-validación contra el manifiesto de origen del paquete, usando la misma implementación canónica.
2. La verificación en vivo de los commits OSTree de aplicación/runtime/SDK y de los hashes post-mutación de cada recurso formatter, bibliotecas Qt, scripts y recibos.
3. La ejecución JASP en el entorno realmente empaquetado, con logs, retornos y hashes ligados al recibo de mutación.
4. La validación independiente completa, el recibo S32 y la elegibilidad de stable release ligados al SHA-256 de la misma imagen SquashFS, checksum, recibo de paquete y manifiesto candidato.
5. La emisión por el certificador final de `CERTIFIED_FUNCTIONAL_CANDIDATE`, sin promociones canónicas ni concesión automática de G23/G24.

Si una prueba JASP conserva `BLOCKED_STORED_REFERENCE_MISMATCH`, el replay determinista solo podrá registrarse como tal y NO podrá elevarse a aprobación de referencia estricta. La causa raíz de la discrepancia histórica deberá resolverse mediante evidencia reproducible y revisión independiente, o permanecer explícitamente bloqueada.

**Estado al registrar este addendum:** `IMPLEMENTED; CONTRACT_CI_PASS_ON_SHA_535ad0107fe4935c212df8d0c4e219e9360b6338; REAL_TARGET_VALIDATION_PENDING; INDEPENDENT_VALIDATION_PENDING; S32_PENDING; FUNCTIONAL_CERTIFICATION_NOT_GRANTED`.

### Extensión del predicado terminal — AX-LUN-031

`ADMIT_CURRENT(I) = ADMIT_PREVIOUS(I) AND AX-LUN-031`. Ningún certificado puede ser emitido a partir de aceptación contractual aislada, artefactos de una revisión distinta o evidencia que no cierre criptográficamente sobre la misma imagen candidata.

## 10. Addendum append-only — AX-LUN-032: coherencia de mutación del recurso formatter embebido en el ejecutable JASP

**Registro de evidencia:** 2026-11-13 UTC. Auditoría del job real `131674850383` del workflow `43361008267`, ejecutado sobre HEAD `b4eb2b7324e5befc4c893de44895ebbb97a3645a`.

### AX-LUN-032 — La identidad de una mutación binaria debe describir el objeto realmente modificado

El parcheador de formato JASP inspecciona recursos Qt comprimidos que pueden residir dentro del propio ejecutable `files/bin/JASP`. Cuando el log identifica ese ejecutable como ruta modificada, el recibo MUST registrar la transición real de su SHA-256 anterior a posterior. La declaración `binary_unchanged_by_formatter_patch` MUST ser equivalente a `before_sha256 == after_sha256`; `formatter_patch.changed_jasp_binary` MUST ser equivalente a `before_sha256 != after_sha256`. Ambas declaraciones MUST concordar con un único registro de recurso parcheado cuya ruta canónica sea exactamente la del ejecutable y cuyos hashes anterior, posterior y observado coincidan. Una mutación fuera del ejecutable MUST quedar respaldada por los registros exactos de esos otros recursos; ningún campo podrá fijarse en `False` con independencia de los bytes reales.

La ausencia de fila, filas duplicadas, hash inconsistente, ruta distinta, indicador contradictorio o transición no explicada MUST producir BLOCKED. El recibo MUST conservar tanto la identidad OSTree de la aplicación/runtime como la identidad byte-level post-mutación; el commit Flatpak no sustituye a la segunda. Las pruebas funcionales MUST operar sobre el ejecutable y runtime resultantes que quedan incluidos en la imagen.

### Evidencia de causa raíz — run #253

El job `131674850383` registró que el parcheador modificó exactamente:

- Ruta: `/home/runner/work/_temp/lunita-rootfs/var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/bin/JASP`.
- SHA-256 antes: `8f57a4b80b3853fb454bbce3cd42c4844d3fb56e37f98a6833df02e25853fef7`.
- SHA-256 después: `3ece91409e1a726661c9a26075e9160858a4cd6f759514d1349d63521341b9a4`.
- Sitios: `call_sites=1`, `latex_sites=1`.
- El emisor del recibo declaraba `formatter_patch.changed_jasp_binary=false` y el verificador exigía simultáneamente `application.binary_unchanged_by_formatter_patch=true`. Esa contradicción fija bloqueó el recibo aunque el log, los hashes pre/post y el cambio real estuvieran presentes.
- Consecuencia observada: `BLOCKED_JASP_POST_MUTATION_RUNTIME_IDENTITY`; los cuatro casos de regresión no se ejecutaron (`case_count=0`). No es válido clasificar esos casos como fallos funcionales JASP ni como PASS.

### Condición de validación

El contrato debe aceptar tanto (a) una mutación embebida en `bin/JASP`, demostrada por una única fila de parche con hashes coincidentes, como (b) una mutación externa de un recurso Qt con el ejecutable sin cambios. Debe rechazar una transición binaria que no tenga la fila correspondiente. El self-test del emisor y las pruebas unitarias del verificador MUST reproducir estos tres escenarios. Después, una nueva ejecución íntegra en HEAD posterior debe demostrar: recibo válido; ejecución real de los cuatro casos JASP; informe independiente PASS; cierre exacto del manifiesto post-validación; recibo S32; y certificado final unido al SHA-256 interno de la misma imagen.

**Estado al registrar:** `ROOT_CAUSE_IDENTIFIED_FROM_REAL_LOGS; IMPLEMENTATION_PATCHED_IN_BRANCH; CONTRACT_TESTS_PENDING; REAL_TARGET_RERUN_PENDING; CERTIFICATION_NOT_GRANTED`.

### Extensión del predicado terminal — AX-LUN-032

`ADMIT_CURRENT(I) = ADMIT_PREVIOUS(I) AND AX-LUN-032`. Este axioma no debilita ningún control de integridad: convierte los indicadores estáticos contradictorios en una comprobación derivada de hashes reales y mantiene fail-closed cualquier discrepancia.

## 11. Addendum append-only — AX-LUN-033: cierre verificable del ciclo de vida de procesos JASP

**Registro de evidencia:** 2026-11-13 UTC. Análisis del job real 131689968018 del workflow 43365648019, HEAD 36708abc13ec8c83f55161a14b3b254703671c29; inspección del ejecutor independiente y de la corrección aislada incorporada en fix/lunita-jasp-process-tree-timeout-20261113.

### AX-LUN-033 — Ninguna ejecución JASP puede cerrar su recibo mientras conserve procesos descendientes activos

Toda invocación JASP incluida en la validación independiente MUST ejecutarse dentro de una sesión y un grupo de procesos propios, con un límite temporal explícito de 300 segundos por caso. La captura de salida MUST usar un destino que no permita que un descriptor heredado por un descendiente mantenga bloqueada la recolección después de terminar el lanzador directo.

Una terminación normal solo puede aceptarse si no queda ningún miembro no-zombie/no-exited en el grupo de procesos de la invocación. Si el límite se agota, el supervisor MUST enviar SIGTERM al grupo completo, esperar el periodo de gracia, enviar SIGKILL si todavía existen miembros, recolectar el proceso directo y comprobar nuevamente el cierre del grupo. La imposibilidad de demostrar el cierre MUST producir BLOCKED; nunca puede convertirse en PASS, en timeout benigno ni en un recibo de evidencia completo.

El requisito se aplica, sin excepción, a los casos JASP originales y al replay determinista. La finalización del lanzador, la existencia de un código de salida o el cierre del pipe principal no equivalen a la terminación del árbol de procesos.

### Contrato de identidad y cierre — política de identidad univalente

Cada ejecución se identifica por la tupla completa:

JASPInvocation = (run_id, run_attempt, case_id, invocation_id, process_group_id, executable_sha256, runtime_ostree_commit).

Dos registros solo podrán tratarse como la misma invocación si existe una correspondencia verificable que preserve todos los componentes de esa tupla. La igualdad de nombre de caso, comando, versión o nombre de archivo no constituye por sí sola una identidad. La evidencia de cierre pertenece a esa invocación concreta y no puede transportarse a otro run, attempt, caso, binario, runtime o imagen.

El predicado de aceptación es:

ACCEPT_JASP(i) = BOUNDED(i) AND ISOLATED(i) AND PROCESS_GROUP_CLOSED(i) AND OUTPUT_CAPTURED(i) AND EVIDENCE_HASH_BOUND(i).

PROCESS_GROUP_CLOSED(i) exige cero miembros vivos del grupo después de la terminación o limpieza. Cualquier miembro que permanezca activo, cualquier error de inspección o cualquier imposibilidad de verificar la identidad del grupo produce BLOCKED. Este contrato define la identidad operacional que debe conservar la evidencia; no declara una demostración externa de la equivalencia de tipos ni una propagación automática de certificación.

### Evidencia de implementación y límite de la evidencia

La revisión 25617dcc521edcea795f5d47dd6e72540d9bc3f5 incorpora run_bounded_process_tree, sesión dedicada, captura a archivo temporal, terminación SIGTERM/SIGKILL y detección de descendientes persistentes. Su ejecución contractual 43377000287 terminó success; la suite del ejecutor independiente registró 132 pruebas correctas, incluida test_timeout_terminates_descendants_without_waiting_for_inherited_output_pipe.

Esa ejecución fue un evento pull_request: el job de destino real fue skipped. Por ello acredita la implementación contractual y la regresión del supervisor, no la validación funcional de la imagen.

La ejecución real 43365648019, sobre HEAD 36708abc13ec8c83f55161a14b3b254703671c29, ya había pasado la construcción del rootfs, E01–E15 y aplicaciones heredadas, la generación de LUNITA.squashfs y su round-trip. Su job independiente permanecía en el paso de JASP. Los logs del job en curso no estuvieron disponibles para lectura en esta auditoría; por ello el bloqueo se clasifica como INDEPENDENT_JASP_LIFECYCLE_UNRESOLVED, no como prueba de que un caso JASP concreto haya fallado ni como causa raíz demostrada a partir de esos logs.

### Condición de validación

La validación exige una nueva ejecución completa posterior a la integración que demuestre, sobre una sola imagen y un solo SHA-256 interno: ejecución limitada de los cuatro casos JASP; cierre del grupo de procesos en cada caso; informe independiente PASS; manifiesto post-validación idéntico al manifiesto de empaquetado; recibo S32; stable release; y certificado funcional final. Ninguna evidencia de 43365648019, 43377000287 u otra revisión podrá mezclarse para completar esa cadena.

**Estado al registrar:** AXIOM_APPENDED; PROCESS_TREE_REGRESSION_PASS_ON_PR_HEAD; REAL_TARGET_REVALIDATION_PENDING; CERTIFICATION_NOT_GRANTED.

### Extensión del predicado terminal — AX-LUN-033

ADMIT_CURRENT(I) = ADMIT_PREVIOUS(I) AND AX-LUN-033. El certificado queda denegado si cualquier invocación JASP no satisface el límite temporal, aislamiento, captura de salida y cierre verificable del grupo de procesos en el mismo candidato.


## 12. Addendum append-only — AX-LUN-034: recibos hash-bound por invocación JASP y admisión independiente

**Registro de evidencia:** 2026-11-13 UTC. Revisión de la implementación AX-LUN-033, del formato de informes de JASP, de la función que construye la validación independiente, de S32 y del certificador final de SquashFS.

### AX-LUN-034 — La terminación de procesos debe quedar materializada en un recibo identificable y verificable

Toda invocación JASP que pueda contribuir a la aceptación del candidato MUST producir un objeto estructurado `LUNITA_JASP_PROCESS_TREE_RECEIPT/1.0`. El recibo MUST ligar, como mínimo, el run ID, run attempt, case ID, UUID único de invocación, process-group ID, session ID, SHA-256 del ejecutable JASP post-mutación, commit OSTree del runtime Flatpak, hash del comando, timeout, marcas temporales de inicio/fin, código de salida, señales de limpieza, miembros vivos remanentes y hash/tamaño de la salida capturada.

La validación de un recibo MUST comprobar el conjunto completo de la tupla `JASPInvocation` de AX-LUN-033. La identidad no puede reconstruirse por coincidencia de nombres ni transferirse entre runs, attempts, casos, invocaciones, ejecutables, runtimes o imágenes. Los UUID de invocación deben ser únicos dentro del conjunto admitido. El recibo debe conservarse dentro del informe o log cuya ruta y SHA-256 son incluidos en el mapa de evidencia independiente; no basta un indicador booleano desacoplado del recibo.

El conjunto requerido para el candidato v1.8 consta de exactamente cinco invocaciones:

1. `flatpak_launch`;
2. `reliability`;
3. `weight_gain`;
4. `death_penalty_save`;
5. `death_penalty_rerun`.

El gate independiente `jasp_process_tree_lifecycle` MUST exigir los cinco recibos, UUID distintos, run ID y attempt coincidentes con el recibo del runtime objetivo, hashes idénticos al recibo de mutación JASP/Qt, process-group y session ID coherentes, timeout no activado, cero miembros vivos y estado `PASS_PROCESS_GROUP_CLOSED` para cada ejecución admitida. Las invocaciones que excedan el límite, incluso cuando la limpieza posterior cierre correctamente el grupo, conservan estado BLOCKED y no pueden convertirse en PASS funcional.

La generación de la validación independiente, la emisión S32 y el certificador final MUST exigir explícitamente este gate. El certificador final MUST volver a comprobar la cantidad de recibos, su esquema, la identidad de workflow/runtime y el cierre de procesos antes de emitir `CERTIFIED_FUNCTIONAL_CANDIDATE`. La ausencia de un recibo, una referencia no legible, un hash distinto, un UUID duplicado, una identidad de runtime distinta o un proceso vivo remanente producen BLOCKED.

### Condición de no regresión

Las referencias JASP históricas, los valores estadísticos originales y los resultados de cada replay permanecen independientes de los recibos de ciclo de vida. Un recibo correcto solo acredita la identidad y terminación de esa invocación; no convierte un mismatch estadístico histórico en PASS estricto ni autoriza mutar fixtures, resultados guardados o tolerancias.

**Estado al registrar:** `SPECIFIED_APPEND_ONLY; INVOCATION_RECEIPT_IMPLEMENTATION_ADDED; UNIT_AND_CONTRACT_VALIDATION_PENDING; REAL_TARGET_REVALIDATION_PENDING; CERTIFICATION_NOT_GRANTED`.

### Extensión del predicado terminal — AX-LUN-034

`ADMIT_CURRENT(I) = ADMIT_PREVIOUS(I) AND AX-LUN-034`. Ninguna imagen podrá recibir certificación funcional si los cinco recibos de invocación JASP no están presentes, son únicos, verificables y ligados al mismo runtime, ejecutable, run y evidencia independiente.
