# Lunita v1.8 — Auditoría de causa raíz: colisión del mountpoint Flatpak

**Fecha:** 2026-11-13  
**Repositorio:** Plomillo/luna-linux-bridge  
**Rama que produjo la evidencia:** fix/lunita-v18-rootfs-bound-checkpoint-20261109  
**HEAD:** a41e7b9fdc000b1c95f08aa212082e23d28051ea  
**Workflow:** 43332281299 (run #184)  
**Job contractual:** 131579662707 — SUCCESS  
**Job de destino:** 131580478339 — FAILURE  
**Gate:** step 15, ejecución de E01 y E02–E15 más smoke tests heredados  
**Clasificación:** ROOT_CAUSE_IDENTIFIED; CORRECTION_IMPLEMENTED_NOT_YET_CI_VALIDATED  
**Certificación funcional:** NOT_GRANTED

## 1. Evidencia primaria

El log de GitHub Actions del job 131580478339 registra, tras activar los controles del user namespace:

    USERNS_SYSCTL_ACTIVE kernel.apparmor_restrict_unprivileged_userns=0 (original=1)
    USERNS_SYSCTL_ACTIVE kernel.unprivileged_userns_clone=1 (original=1)
    BLOCKED: target Flatpak runtime mountpoint already exists: /run/lunita-runtime-1000
    Process completed with exit code 2.

El estado del workflow confirma que el job contractual terminó SUCCESS y que el job de destino terminó FAILURE. El paso 15 fue el primer gate fallido. Los pasos posteriores de refresh del runtime JASP, empaquetado y round-trip SquashFS, validación independiente, certificación S32 y publicación stable quedaron SKIPPED.

El overlay fue aplicado aditivamente, pero su recibo declaró APPLIED_ADDITIVELY_NOT_CERTIFIED. El checkpoint registró 10.507 entradas y tree SHA-256 2145b638517cb926841be8a8b4c26eb44ef77d20b1030106bafad9ae6e6433ab. Esto es evidencia del checkpoint/overlay, no de aceptación funcional del target ni de una imagen SquashFS.

No se emitió LUNITA.squashfs en esta ejecución. El artefacto overlay y el artefacto de evidencia auxiliar no son sustitutos de la imagen ni habilitan certificación.

## 2. Mecanismo causal demostrado

El wrapper scripts/lunita/run_target_runtime_acceptance_in_container_v1.sh realizaba dos operaciones relevantes:

1. Generaba un HOST_BIND_NAME por workflow e intento y montaba RUNNER_TEMP bajo /run/HOST_BIND_NAME.
2. Montaba recursivamente el /run del host sobre ROOTFS/run mediante mount --rbind /run "$ROOTFS/run".

Sin embargo, después de pivot_root, el segundo bind de Flatpak usaba un nombre global y constante:

    RUNTIME_BIND_TARGET=/run/lunita-runtime-1000

El control previo a mkdir y mount rechazaba correctamente cualquier entrada existente en ese destino. Como /run ya correspondía al /run del host montado recursivamente, la ruta observada no era un espacio aislado del rootfs ni estaba garantizada como libre para esta ejecución. La entrada ya existente activó la denegación fail-closed.

La causa técnica inmediata queda demostrada: colisión entre un destino de montaje global fijo y una entrada preexistente en el /run compartido del host. El log no identifica quién creó esa entrada ni cuándo; el origen de la entrada previa queda deliberadamente como desconocido.

Este fallo ocurrió antes de la ejecución de la suite target E01–E15 y de los smoke tests legacy. No constituye evidencia de que esos motores o JASP hayan fallado; tampoco constituye evidencia de que hayan pasado.

## 3. Corrección mínima implementada

En la rama fix/lunita-flatpak-runtime-mount-collision-20261113:

- HOST_BIND_NAME se valida como componente de ruta seguro antes de utilizarse.
- El destino pasa a ser /run/${HOST_BIND_NAME}-runtime-1000, único por workflow run e intento.
- El mismo destino dinámico se exporta como XDG_RUNTIME_DIR dentro del namespace pivot_root.
- target_runtime_acceptance_v1.py deriva la ruta esperada desde HOST_BIND_NAME y conserva las comprobaciones de directorio real, UID/GID 1000 y modo 0700.
- Los entornos de procesos Flatpak y de pruebas heredan la ruta derivada, no un literal distinto.
- Las pruebas contractuales cubren unicidad entre intentos, identidad insegura, path incorrecto, symlink/no-directorio, UID, GID y modo.
- La comprobación fail-closed de colisión se conserva. No se borra, reutiliza ni sobrescribe ninguna entrada preexistente.

La limpieza sigue limitada al destino que el intento actual creó y montó. Un reintento de GitHub usa otro attempt number y por tanto otro nombre de mountpoint.

## 4. Criterios de revalidación

La corrección no se considera cerrada por inspección del diff. El siguiente run sobre el HEAD integrado debe demostrar, con logs y recibos del mismo commit:

1. El target XDG_RUNTIME_DIR termina en el identificador de ejecución e intento actual.
2. El mountpoint dinámico se crea, monta, es escribible por UID 1000 y supera las verificaciones de owner/group/mode.
3. El cleanup desmonta y elimina el destino creado por ese intento y verifica que no queden mounts target activos.
4. E01 y E02–E15, incluida E04 INT8, pasan; los smoke tests heredados pasan.
5. Se ejecutan los gates JASP de referencia y replay sobre la identidad real del runtime fijado.
6. El rootfs completo se inventaría, empaqueta y extrae con igualdad estricta de manifiesto.
7. La validación independiente, S32, stable release y certificado final enlazan el mismo SHA-256 de LUNITA.squashfs.

Cualquier incumplimiento mantiene CERTIFICATION=NOT_GRANTED. Los artefactos de los runs 43332281299 y anteriores no pueden recombinarse con el futuro run para cerrar la cadena.

## 5. Estado al registrar esta auditoría

CORRECTION_BRANCH=fix/lunita-flatpak-runtime-mount-collision-20261113  
CORRECTION_HEAD_AT_AUDIT=ef77aedc08b1134f0b69feea293bf07ad5349c99  
CORRECTION_STATUS=IMPLEMENTED_NOT_YET_CI_VALIDATED  
NEW_FULL_RUN=NOT_STARTED  
LUNITA_SQUASHFS=NOT_EMITTED_BY_RUN_184  
INDEPENDENT_VALIDATION=NOT_REACHED  
S32=NOT_REACHED  
STABLE_RELEASE=NOT_REACHED  
FUNCTIONAL_CERTIFICATE=NOT_GRANTED
