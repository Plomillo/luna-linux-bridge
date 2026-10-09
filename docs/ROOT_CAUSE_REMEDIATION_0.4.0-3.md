# Análisis de causa raíz y remediación — candidato 0.4.0-3

**Estado:** REMEDIACIÓN PARCIAL IMPLEMENTADA; RELEASE EN HOLD.  
**PR:** [#48](https://github.com/Plomillo/luna-linux-bridge/pull/48)  
**Rama candidata:** `work/louksna-zd-v04-03-mtls-provisioning-20261008`  
**Invariantes:** la rama base `work/louksna-zd-v04-master-20261007` y los blobs canónicos de `Louksna.md` y `PUAC2.md` no se modifican; no se activa systemd; G23/G24 no se heredan ni se autocertifican.

## 1. Hallazgos, dependencia causal y salida exigida

| ID | Causa raíz | Remediación de código aplicada | Lo que sigue bloqueando el cierre |
|---|---|---|---|
| RC-01 | El workflow silenciaba el resultado de `lintian` con `|| true`; el estado verde no demostraba conformidad de empaquetado. | El workflow conserva salida/código de lintian, marca `HOLD_LINTIAN`, publica evidencia diagnóstica y falla en la compuerta final ante cualquier etiqueta `E:` o código distinto de cero. Se añadió una prueba de regresión de esta política. | `debian/copyright` no existe y tampoco hay `LICENSE`/`COPYING` en la raíz. No se inventará titularidad ni licencia. El titular autorizado debe aportar la declaración legal veraz antes de que lintian pueda quedar limpio. |
| RC-02 | La limpieza de fallos usaba `rm -rf` sobre directorios completos; una carrera o contenido agregado durante la ejecución podía borrar datos no generados por esta invocación. Las señales no terminaban explícitamente el proceso tras limpiar. | La limpieza ahora elimina nombres de artefactos concretos y usa `rmdir` solo para directorios creados por esta ejecución; HUP/INT/TERM salen por la ruta `EXIT`; el directorio de identidad de cliente permanece root-privado mientras se generan y validan los archivos. Se valida además la integridad básica de los directorios de política. | Aún falta prueba de inyección de fallos e interrupciones en VM desechable/restaurable. La revisión estática no se presenta como prueba operacional. |
| RC-03 | El workflow hacía checkout de la rama móvil en vez del SHA que disparó el evento; ejecuciones concurrentes podían compilar otro commit y atribuirle evidencia incorrectamente. | Checkout fijado a `${{ github.sha }}`; se comprueba `HEAD == GITHUB_SHA`; el manifiesto registra SHA disparador, SHA compilado, ref del workflow y estado de lintian. | Verificar en el run completado que el SHA del evento, el commit compilado, el paquete y el manifiesto coincidan. |
| RC-04 | La identidad de ejecución no está especificada de forma coherente: la configuración y la clave de servidor son root-owned y el servicio systemd omite `User=`, lo que implica root por defecto; documentación previa habla de contexto del propietario. | El contrato del paquete aclara que la instalación no provisiona automáticamente confianza ni activa el servicio. | Diseñar y probar la identidad de runtime y permisos como una decisión explícita de amenaza/privilegios. No rebajar `read_config` ni relajar permisos para hacer pasar pruebas. No ejecutar el servicio hasta resolverlo. |
| RC-05 | Tests sintéticos/unitarios prueban partes del gateway, no prueban la provisión real, servicio instalado, rollback del host ni postboot. | La matriz de validación ya separa build, integración host, rollback/postboot, G23 y G24. | Hace falta VM/host autorizado y restaurable, handshake real bajo la identidad declarada, rollback verificado y comprobación postboot. G23 debe ser independiente del implementador; G24 debe revisar la evidencia G23 inmutable. |

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
- **Runtime:** identidad declarada, permisos de clave, lectura de configuración y escritura de estado deben funcionar juntos bajo la identidad real del servicio.
- **Host rollback/postboot:** prueba en VM/host autorizado con checkpoint antes/después, hashes y verificación de ausencia de listener/activación involuntaria.
- **G23:** `NOT_EXECUTED/HOLD` hasta evidencia completa revisada por una persona/rol independiente.
- **G24:** `NOT_EXECUTED` hasta decisión explícita de un certificador independiente sobre el mismo SHA y bundle inmutable.
- **ACTIVE:** prohibido mientras exista cualquier bloqueo crítico, discrepancia de hash, falta de independencia o falta de autorización.

## 4. Límites y decisión actual

Las correcciones de CI, procedencia y limpieza reducen fallos de raíz, pero no prueban la seguridad completa. El titular de copyright/licencia, la identidad final del servicio, la VM de integración/rollback y los roles G23/G24 son dependencias distintas; no deben colapsarse en un solo “PASS”. Mantener PR abierto, no fusionar, no publicar release y no activar systemd hasta que cada salida esté respaldada por evidencia.
