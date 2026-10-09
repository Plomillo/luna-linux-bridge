# Análisis de causa raíz y remediación — candidato 0.4.0-3

**Estado:** REMEDIACIÓN PARCIAL IMPLEMENTADA; RELEASE EN HOLD.  
**PR:** [#48](https://github.com/Plomillo/luna-linux-bridge/pull/48)  
**Rama candidata:** `work/louksna-zd-v04-03-mtls-provisioning-20261008`  
**Invariantes:** la rama base `work/louksna-zd-v04-master-20261007` y los blobs canónicos de `Louksna.md` y `PUAC2.md` no se modifican; no se activa systemd; G23/G24 no se heredan ni se autocertifican.

## 1. Hallazgos, dependencia causal y salida exigida

| ID | Causa raíz | Remediación de código aplicada | Lo que sigue bloqueando el cierre |
|---|---|---|---|
| RC-01 | El workflow silenciaba el resultado de `lintian` con `|| true`; el estado verde no demostraba conformidad de empaquetado. | El workflow conserva salida/código de lintian, marca `HOLD_LINTIAN`, publica evidencia diagnóstica y falla en la compuerta final ante cualquier etiqueta `E:` o código distinto de cero. Se añadió una prueba de regresión de esta política. | `debian/copyright` no existe y tampoco hay `LICENSE`/`COPYING` en la raíz. No se inventará titularidad ni licencia. El titular autorizado debe aportar la declaración legal veraz antes de que lintian pueda quedar limpio. |
| RC-02 | La limpieza de fallos usaba `rm -rf` sobre directorios completos; una carrera o contenido agregado durante la ejecución podía borrar datos no generados por esta invocación. Las señales no terminaban explícitamente el proceso tras limpiar. | La limpieza ahora elimina nombres de artefactos concretos y usa `rmdir` solo para directorios creados por esta ejecución; HUP/INT/TERM salen por la ruta `EXIT`; las escrituras de la identidad de cliente se ejecutan bajo el UID invocante, no como root a través de ancestros controlados por el usuario; el rollback elimina nombres de artefactos concretos. Se valida además la integridad básica de los directorios de política. | Aún falta prueba de inyección de fallos e interrupciones en VM desechable/restaurable. La revisión estática no se presenta como prueba operacional. |
| RC-03 | El workflow hacía checkout de la rama móvil en vez del SHA que disparó el evento; ejecuciones concurrentes podían compilar otro commit y atribuirle evidencia incorrectamente. | Checkout fijado a `${{ github.sha }}`; se comprueba `HEAD == GITHUB_SHA`; el manifiesto registra SHA disparador, SHA compilado, ref del workflow y estado de lintian. | Verificar en el run completado que el SHA del evento, el commit compilado, el paquete y el manifiesto coincidan. |
| RC-04 | La identidad de ejecución no está especificada de forma coherente: la configuración y la clave de servidor son root-owned y el servicio systemd omite `User=`, lo que implica root por defecto; documentación previa habla de contexto del propietario. | El contrato del paquete aclara que la instalación no provisiona automáticamente confianza ni activa el servicio. | La implementación actual exige UID 0: `read_config(enforce_root=True)` exige política/configuración y ancestros root-owned, y `guarded_file` exige que la clave de servidor pertenezca al UID efectivo. Se declaró `User=root`/`Group=root` explícitamente en la unidad y se añadió aislamiento systemd (`ProtectSystem=strict`, `ProtectHome=read-only`, `PrivateDevices`, `NoNewPrivileges`, restricciones de kernel/SUID y `ReadWritePaths` limitado al estado). No se relajaron las comprobaciones de propiedad. | Es una resolución explícita para este candidato, no una prueba de que root sea la arquitectura de menor privilegio. La identidad dedicada requiere rediseñar el contrato de secretos/configuración y su validación, no cambiar permisos a ciegas. Falta verificar la unidad con systemd y probar el servicio instalado bajo esta identidad en VM restaurable; mantenerlo desactivado hasta entonces. |
| RC-05 | Tests sintéticos/unitarios prueban partes del gateway, no prueban la provisión real, servicio instalado, rollback del host ni postboot. | La matriz de validación ya separa build, integración host, rollback/postboot, G23 y G24. | Hace falta VM/host autorizado y restaurable, handshake real bajo la identidad declarada, rollback verificado y comprobación postboot. G23 debe ser independiente del implementador; G24 debe revisar la evidencia G23 inmutable. |
| RC-06 | La metadata declara `Maintainer: Louksna Project <maintainers@louksna.invalid>`, un dominio reservado/no entregable, por lo que no constituye un contacto operativo de mantenimiento. | El hallazgo queda registrado; no se inventó una dirección real. | El responsable autorizado debe proporcionar un contacto mantenedor válido antes de publicar/distribuir el paquete. |

## 2. Base técnica y académica usada

1. **Debian Policy / DEP-5, Machine-readable debian/copyright** — [formato oficial](https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/) y [guía de archivos requeridos](https://www.debian.org/doc/debian-policy/ch-source.html#copyright-information). El fichero no es un adorno: documenta titularidad y licencias de forma parseable. Como el repositorio no aporta licencia ni declaración de copyright suficiente, la acción correcta es bloquear y solicitar datos autorizados, no fabricar una licencia permisiva.
2. **NIST SP 800-218, Secure Software Development Framework (SSDF)** — [publicación oficial](https://csrc.nist.gov/pubs/sp/800/218/final). Fundamenta controles integrados al ciclo de desarrollo, evidencia verificable, revisión y tratamiento explícito de vulnerabilidades; no convierte una build verde en certificación.
3. **Brumley et al., “Using Frankencerts for Automated Adversarial Testing of Certificate Validation in SSL/TLS Implementations,” IEEE S&P 2014** — [texto abierto](https://pmc.ncbi.nlm.nih.gov/articles/PMC4232952/). Fundamenta casos adversariales de cadenas/campos de certificados, no solo el camino feliz.
4. **RFC 8446, TLS 1.3** — [RFC Editor](https://www.rfc-editor.org/rfc/rfc8446). Norma protocolar para el handshake TLS 1.3; no prueba por sí misma la configuración correcta del producto.
5. **systemd.exec** — [documentación oficial](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html). La identidad `User=/Group=`, directorios de estado y restricciones de ejecución deben definirse explícitamente y probarse; omitir `User=` en un servicio de sistema no significa “usuario propietario”.
6. **PUAC2 / Louksna governance contract** — la cadena `SOURCE → INPUT → OPERATION → OUTPUT → TEST → VALIDATION → INDEPENDENT_VALIDATION → CERTIFICATION` exige procedencia por commit/artefacto y separa implementación de validación/certificación. Los blobs canónicos deben permanecer idénticos.

## 3. Evidencia y criterios de salida

- **Build/package:** el run debe referenciar un único SHA; el artefacto debe tener SHA-256 registrado; `lintian` debe terminar sin errores y el fichero de evidencia no puede reportar `PASS` si la compuerta de empaquetado falla.
- **Provisionador:** pruebas de no-sobrescritura para archivo/directorio/symlink preexistentes; inyección de fallo en OpenSSL, escritura de config y validación runtime; señales; verificación de que la limpieza no elimina artefactos ajenos.
- **mTLS:** identidad de cliente autorizada acepta; cliente no autorizado, pin erróneo, CA/uso extendido de clave incorrectos, certificado de servidor con SAN incorrecto o certificado expirado se rechazan; TLS 1.3 y loopback se verifican en la integración real.
- **Runtime:** la identidad declarada para este candidato es `root`, coherente con las comprobaciones de propiedad actuales. La unidad limita el sistema de archivos de solo lectura y permite escritura únicamente en el directorio de estado declarado; verificar sintaxis/directivas con `systemd-analyze verify` y después confirmar lectura de clave/configuración, escritura de estado, restricciones efectivas y ausencia de activación involuntaria en una VM restaurable.
- **Host rollback/postboot:** prueba en VM/host autorizado con checkpoint antes/después, hashes y verificación de ausencia de listener/activación involuntaria.
- **G23:** `NOT_EXECUTED/HOLD` hasta evidencia completa revisada por una persona/rol independiente.
- **G24:** `NOT_EXECUTED` hasta decisión explícita de un certificador independiente sobre el mismo SHA y bundle inmutable.
- **ACTIVE:** prohibido mientras exista cualquier bloqueo crítico, discrepancia de hash, falta de independencia o falta de autorización.

## 4. Límites y decisión actual

Las correcciones de CI, procedencia, limpieza y declaración explícita de identidad reducen fallos de raíz, pero no prueban la seguridad completa. El titular de copyright/licencia, el contacto mantenedor válido, la VM de integración/rollback y los roles G23/G24 son dependencias distintas; no deben colapsarse en un solo “PASS”. Mantener PR abierto, no fusionar, no publicar release y no activar systemd hasta que cada salida esté respaldada por evidencia.

## 5. Actualización de evidencia CI — 2026-10-09 UTC

Los runs #27, #28 y #29 finalizaron. En los tres, las etapas de build/test, comprobación de integridad y extracción del paquete, compilación Python, y `systemd-analyze verify` completaron con éxito. Los tres fallan exclusivamente en la compuerta final de Lintian por el mismo error observado en el log:

`E: louksna-linux-bridge: no-copyright-file`

- [Run #27](https://github.com/Plomillo/luna-linux-bridge/actions/runs/37866918714), evento SHA `ceb77b8ec0444d7226cf3937d943cb22c4909690`.
- [Run #28](https://github.com/Plomillo/luna-linux-bridge/actions/runs/37866926737), evento SHA `812a222dd39f03c1e100a6018cb72069b6a0f9b7`.
- [Run #29](https://github.com/Plomillo/luna-linux-bridge/actions/runs/37866936716), evento SHA `e36059660a371082b92ae906d97e43c14eaa5202`. SHA-256 del paquete de diagnóstico construido por ese run: `a7a744221e8f67355236ff7c46e7d144c634ef53dde0bcba4fc2997e9affda27`. No es un artefacto de release.

Los logs también avisaron que `--no-tag-display-limit` está obsoleto. Se cambió el workflow a `--tag-display-limit 0`; el nuevo commit debe producir una ejecución que compruebe ese cambio. Este arreglo de CLI no altera el bloqueo de copyright.

## 6. Alcance de la voz y del paquete Debian

La unidad empaquetada actual es `louksna-linux-bridge`, descrita como puente local de telemetría mTLS de solo lectura. El conjunto de instalación declarado en `debian/rules` contiene módulos Python, JSON de runtime, scripts de provisión, plantillas systemd y documentación. La evidencia disponible no identifica un archivo de voz ni incorpora la licencia exacta de la voz seleccionada. Por tanto, la autorización de esa voz no puede sustituir el inventario de copyright de todos los archivos incluidos en este paquete. Debe añadirse al inventario de componentes solo si la voz/modelo/artefactos relacionados realmente se distribuyen en este paquete o son una dependencia descargada/instalada por él.

## 7. Matriz operativa pendiente

- **Bloqueo Debian crítico:** obtener la declaración autorizada de titularidad y licencia del código/documentación efectivamente incluidos; producir `debian/copyright` en formato DEP-5; volver a ejecutar Lintian sin silenciar errores.
- **Contacto del paquete:** reemplazar `maintainers@louksna.invalid` únicamente con un contacto real autorizado y actualizar coherentemente `debian/control` y `debian/changelog`.
- **Inventario de terceros:** registrar versiones, origen, copyright y licencia de cada dependencia/componente realmente distribuido; confirmar que las dependencias de sistema se declaran correctamente y que no se incrustan sin licencia.
- **Pruebas de provisión:** ejecutar fault injection e interrupciones en VM desechable/restaurable; demostrar que no se sobrescriben ni eliminan archivos ajenos.
- **Prueba de runtime:** `systemd-analyze verify` pasa en CI, pero sigue faltando instalar y probar el servicio en VM, bajo el usuario explícito, con configuración/clave de prueba, aislamiento efectivo y sin activación involuntaria.
- **Host/rollback/postboot:** falta evidencia en host/VM autorizada con checkpoint, hashes, ausencia de listener inesperado y restauración comprobada.
- **G23/G24:** permanecen `NOT_EXECUTED`; requieren validación y certificación independientes sobre un bundle inmutable.
- **Publicación/activación:** prohibidas hasta resolver las compuertas aplicables. Los artefactos CI actuales son solo diagnósticos.

No se elige ni se infiere una licencia para el proyecto a partir de que una voz pueda usarse legalmente. Tampoco se inventa un contacto mantenedor. El cierre debe basarse en evidencia de los titulares/derechos aplicables y de la composición real del paquete.


## 8. Pruebas operacionales añadidas a CI (pendientes de resultado)

Se añadió al workflow una prueba en el runner efímero de GitHub que instala el .deb construido en esa misma ejecución, ejecuta el provisionador real con identidad de usuario explícita y valida:
- schema y permisos/propiedad root del fichero de política;
- existencia y tipo de las rutas de certificado/clave;
- permisos 0600 de la clave privada del servidor;
- EKU serverAuth y clientAuth;
- coincidencia del pin SHA-256 del certificado de cliente;
- validación de la cadena del certificado de servidor;
- servicio desactivado y detenido después de instalar/provisionar.

La misma etapa elimina únicamente el estado que ella misma creó y luego inyecta un fallo controlado en la primera llamada a OpenSSL. El criterio es que el error se propague con código 71 y no quede /etc/louksna ni el directorio de identidad de cliente parcialmente creado. La prueba no utiliza datos de confianza preexistentes: aborta antes de modificar el runner si /etc/louksna ya existe. Esto prueba el camino de éxito y un rollback temprano en CI, pero no sustituye pruebas de señales, fallos tardíos, carrera de directorios ni rollback/postboot en una VM restaurable.

Se corrigió además el orden del provisionador: VALIDATED solo se establece después de completar limpieza de temporales y publicación de permisos/propiedad de la identidad de cliente, manteniendo el trap de rollback activo hasta ese punto. La documentación de identidad de servicio ya no afirma simultáneamente que la clave es del usuario y que la unidad corre como root.

El inventario técnico nuevo está en [PACKAGE_COMPONENT_INVENTORY.md](PACKAGE_COMPONENT_INVENTORY.md). Enumera los archivos que se empaquetan y las dependencias declaradas sin fingir que el inventario técnico equivale a autorización legal. No se encontró voz/modelo TTS en los archivos copiados por las reglas del paquete. La licencia de una voz ajena a este paquete no acredita la licencia del código incluido.

**Estado de evidencia:** la ejecución CI que incluye estas pruebas aún debe revisarse. No se declara que hayan pasado hasta observar su resultado real. El bloqueo legal DEP-5 y el contacto de mantenimiento válido continúan abiertos; no se habilita publicación, activación ni G23/G24 por la incorporación de pruebas.

### Ajuste adicional de runtime

La unidad ahora declara `StateDirectory=louksna/remote-bridge` y `StateDirectoryMode=0700`. Esto hace explícita la creación del directorio de estado administrado por systemd bajo /var/lib, en vez de depender de que una ruta permitida por `ReadWritePaths` exista previamente. La directiva se somete a `systemd-analyze verify` en CI y queda incluida en la prueba de regresión; su funcionamiento efectivo todavía debe confirmarse en VM.
