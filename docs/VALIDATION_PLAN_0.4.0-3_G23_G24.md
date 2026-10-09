# Plan de validación gobernable y anti-parálisis — Louksna Linux Bridge 0.4.0-3

Estado del documento: PLAN DE EJECUCIÓN Y CRITERIOS DE ACEPTACIÓN; NO ES EVIDENCIA DE PRUEBAS EJECUTADAS NI CERTIFICACIÓN.
Candidato objetivo: `work/louksna-zd-v04-03-mtls-provisioning-20261008`
Commit de referencia al redactar: `14b77e94bf2ffa445920781f8cd6e0adf3208c05`
PR: https://github.com/Plomillo/luna-linux-bridge/pull/48
Alcance: gateway mTLS de solo lectura, provisionador local, paquete Debian 0.4.0-3.
Invariantes: no tocar rama 2; no modificar ni sustituir Louksna.md/PUAC2.md; no activar systemd; no declarar G23/G24 por herencia; no alterar material de confianza preexistente.

## 1. Regla de autoridad y estados

Los resultados se registran separadamente por commit y SHA-256 del paquete:

- BUILD: compilación y empaquetado.
- G23: validación independiente del candidato y del conjunto de evidencias.
- G24: certificación independiente explícita sobre evidencias G23 inmutables.
- HOST_INTEGRATION, ROLLBACK y POSTBOOT: pruebas operacionales distintas.
- ACTIVE: solo tras G23 PASS, G24 PASS, autorización explícita de activación y verificación postactivación.

Estados permitidos por control: `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED_EXTERNAL`, `NOT_APPLICABLE_WITH_RATIONALE`. El estado global es FAIL/HOLD si una prueba crítica falla, falta evidencia, el hash no coincide o la independencia no está demostrada. No convertir `NOT_RUN` en `PASS`; no ocultar fallos; no rebajar controles para obtener un resultado verde.

G23 exige ejecutor independiente del implementador. G24 exige revisor/certificador distinto del ejecutor G23, cuando sea viable, y una decisión firmada o trazable. Si la organización no puede aportar estos roles, declarar `BLOCKED_EXTERNAL`, no autoaprobar.

## 2. Flujo anti-parálisis (límites de avance)

1. Congelar el SHA candidato y calcular SHA-256 del paquete y del bundle de evidencia.
2. Ejecutar primero validaciones baratas y aisladas: sintaxis, tests unitarios, pruebas negativas de configuración, contenido/permisos del paquete e identidad de artefactos.
3. Si una prueba falla, registrar fallo reproducible, abrir un defecto con severidad, preservar logs y continuar solo con pruebas independientes que no dependan del control fallido. No seguir hacia activación.
4. Por defecto, máximo 2 intentos de reparación por defecto y 1 reejecución completa de regresión después de la corrección. Si persiste, detener el bucle y emitir `BLOCKED_EXTERNAL` o `FAIL` con causa, evidencia requerida, responsable y siguiente acción concreta. No son límites para reducir pruebas: una nueva causa raíz permite un defecto nuevo, con justificación.
5. Cada bloqueo debe tener dueño/rol, precondición faltante, comando o procedimiento para resolverlo, artefacto esperado y condición de salida. Si la única dependencia pendiente es acceso físico/host o revisor externo, terminar el trabajo local en estado HOLD y entregar el paquete de evidencias parciales.
6. Las pruebas destructivas se ejecutan solo en VM/host de prueba aislado y restaurable; nunca sobre la instalación productiva sin autorización explícita y checkpoint comprobado.
7. No esperar indefinidamente: registrar timeout, conservar salida parcial, terminar el proceso hijo con seguridad, restaurar el checkpoint y reportar. No interpretar timeout como PASS.
8. Cierre de iteración: tabla de controles PASS/FAIL/BLOCKED, hashes, defectos abiertos, riesgo residual y próxima acción autorizada. No declarar finalizado el release mientras queden bloqueos críticos.

## 3. Matriz mínima de pruebas

### A. Identidad, paquete y reproducibilidad
- Verificar versión Debian 0.4.0-3, dependencias y archivos instalados.
- Verificar que el provisionador tenga modo previsto y que `sh -n` pase.
- Comparar los blob IDs de `Louksna.md` y `PUAC2.md` con la línea base autorizada.
- Guardar commit exacto, workflow/run ID, versiones de SO/Python/OpenSSL/dpkg, hash SHA-256 del .deb y hashes del conjunto de evidencia.
- Repetir build en entorno limpio cuando sea posible; registrar diferencias de reproducibilidad, sin afirmar reproducibilidad binaria si no se probó.

### B. Configuración fail-closed
Casos positivos y negativos para `read_config`:
- JSON válido y esquema exacto.
- JSON malformado, claves extra o faltantes, schema incorrecto, pins no hexadecimales/longitud incorrecta.
- Archivo o ancestro symlink; rutas relativas; archivo no regular; permisos de grupo/mundo; propietario incorrecto; ancestro no root-owned o escribible por grupo/mundo.
- Certificado/CA modificado después de fijar el pin; colisión de pins; clave privada con permisos inseguros.
- Asegurar que cada caso negativo falla de forma controlada y no inicia listener ni altera confianza del sistema.

### C. Criptografía y handshake real
En entorno aislado, con certificados sintéticos y claves temporales:
- Cliente válido y certificado fijado correcto: handshake TLS 1.3 mTLS exitoso; prueba de extremo a extremo a `/v1/status` y `/v1/observe`.
- Cliente ausente, no confiable, expirado, pin incorrecto, certificado distinto aunque emitido por la CA, EKU incorrecto, certificado CA presentado como leaf y cadena inválida: rechazo antes de entregar datos.
- Certificado servidor expirado/no confiable, SAN/hostname no coincidente y pin alterado: rechazo del cliente. Verificar explícitamente validación de hostname del cliente; no basta con que el servidor valide al cliente.
- Intentos de TLS < 1.3, conexión no-loopback, métodos POST/PUT/DELETE, rutas no registradas, query duplicada/malformada, body inesperado, presupuesto `watch` excedido, exceso de clientes y desconexión abrupta.
- Confirmar que errores de autenticación no filtran certificados, rutas sensibles, secretos ni datos del ledger en las respuestas/logs.
- Registrar versión OpenSSL/Python, comando, exit code, stdout/stderr saneados, tiempo, certificado de prueba y hashes; nunca publicar claves privadas.

### D. Provisionador y limpieza ante fallos
- Ejecutar en VM limpia como usuario no-root vía sudo, en cada etapa con fallos inducidos (openssl, escritura config, validación runtime).
- Precrear CONFIG/TLS/CLIENT y symlinks: debe negarse a sobrescribir; comprobar hashes/bytes anteriores intactos.
- Verificar propietario/modo de cada directorio/archivo, pins contra los archivos reales y schema contra el gateway instalado.
- Interrumpir el proceso en puntos controlados; comprobar limpieza solo de artefactos nuevos y que no se borran datos previos. Revisar específicamente que la rutina de limpieza no pueda seguir symlinks ni borrar rutas fuera del conjunto creado.
- Verificar que el proceso no habilita/inicia systemd, no modifica sudoers, firewall, DNS, almacenes de certificados del sistema ni archivos G23/G24/OWNER.
- Inspeccionar la política de la CA local: clave de CA eliminada tras firmar; registrar evidencia de eliminación y no tratar esta CA como autoridad G23/G24.

### E. Límites de API y aislamiento
- GET permitido solo en rutas documentadas; mutaciones HTTP devuelven 405.
- Listener ligado a `127.0.0.1`; no aceptar clientes no-loopback ni más de `MAX_CLIENTS`.
- Límite de tamaño JSON, query, frames, intervalo y longitud de ruta; asegurar terminación dentro del presupuesto.
- Confirmar que no expone captura de pantalla, archivos de proyecto, comandos arbitrarios, sudo remoto ni acceso a shell.
- Probar carga concurrente y desconexiones; verificar que el semáforo se libera también en errores/denegaciones. Investigar si la mezcla de `verify_request` y `process_request_thread` puede liberar el semáforo dos veces en una ruta de rechazo antes de aceptar el comportamiento como seguro.

### F. Estado del host, rollback y postboot
- Antes: inventario con hashes/permisos/servicios, configuración de confianza y estado systemd.
- Durante: no activar el servicio como parte de provisión o instalación del paquete.
- Rollback: en host de ensayo, restaurar snapshot/checkpoint; demostrar que se vuelve al estado previo, verificar hashes e integridad y que no queda listener/proceso.
- Postboot: reiniciar el host de ensayo, comprobar que el servicio continúa deshabilitado/no iniciado y que no hay activación accidental ni cambio de confianza.
- Pruebas reales de host requieren autorización y un host/VM designado; si no existe, `BLOCKED_EXTERNAL`, no simulación presentada como prueba real.

## 4. Evidencia obligatoria por ejecución

Cada registro contiene: `run_id`, `test_id`, timestamp UTC, actor/rol, commit SHA, branch, workflow/job URL, OS/kernel, versiones de herramientas, precondiciones, comando exacto, código de salida, resultado observado, resultado esperado, hashes SHA-256, ubicación de logs, defect ID, checkpoint/rollback pointer, estado y firma/identidad del revisor. Redactar secretos y datos personales; nunca adjuntar claves privadas.

Estructura recomendada del bundle:
```
evidence/0.4.0-3/<commit-sha>/
  manifest.json
  build/
  unit-negative/
  tls-integration/
  provisioner-failure-injection/
  host-rollback/
  postboot/
  G23-independent-review.md
  G24-certification-decision.md
  SHA256SUMS
```
Las carpetas G23/G24 deben quedar explícitamente `NOT_RUN` hasta que sus responsables emitan decisión. El manifest identifica los archivos que no existen todavía; no crear resultados ficticios.

## 5. Criterios de aceptación de G23

G23 solo puede aprobar si:
- La especificación, amenaza, límites de confianza y supuestos están revisados.
- Todos los tests críticos de B–F tienen evidencia suficiente y PASS, o una excepción aprobada formalmente que no rebaje controles críticos.
- No hay defectos críticos/altos abiertos ni discrepancias de hashes/procedencia.
- El paquete exacto está ligado al commit exacto; el bundle es íntegro y verificable.
- Se verificó la preservación de los artefactos canónicos y ausencia de cambios colaterales.
- Un validador independiente documentó método, resultados, limitaciones y decisión.

Si falta acceso al host, pruebas de handshake real, rollback/postboot o independencia, G23 queda HOLD/BLOCKED; no se sustituye con CI.

## 6. Criterios de aceptación de G24

G24 requiere:
- Revisor distinto que examine la evidencia G23 inmutable y el mismo SHA de commit/paquete.
- Verificación de firmas/identidades, hashes, trazabilidad, defectos y limitaciones.
- Evaluación independiente de no regresión, controles fail-closed y rollback.
- Decisión explícita `CERTIFIED` o `REJECTED/HOLD`, con responsable, fecha UTC, alcance exacto, artefactos/hash y justificación.
- Sin propagación automática desde G23 y sin activación implícita.

## 7. Investigación técnica y referencias

1. Karen Scarfone, Murugiah Souppaya y Donna Dodson, *Secure Software Development Framework (SSDF) Version 1.1*, NIST SP 800-218 (2022). DOI: https://doi.org/10.6028/NIST.SP.800-218. Marco de prácticas de desarrollo seguro, mitigación de vulnerabilidades y evidencia de ciclo de vida.
2. David Brumley et al., *Using Frankencerts for Automated Adversarial Testing of Certificate Validation in SSL/TLS Implementations*, IEEE Symposium on Security and Privacy (2014). Texto abierto: https://pmc.ncbi.nlm.nih.gov/articles/PMC4232952/ . El trabajo generó millones de certificados adversariales y encontró discrepancias y fallos reales; fundamenta pruebas negativas y combinaciones inusuales de extensiones/cadenas.
3. Suphannee Sivakorn et al., *HVLearn: Automated Black-box Analysis of Hostname Verification in SSL/TLS Implementations*, IEEE Symposium on Security and Privacy (2017). PDF del congreso: https://www.ieee-security.org/TC/SP2017/papers/414.pdf . El estudio detectó violaciones de especificación y muestra por qué la validación de hostname requiere casos específicos, no solo verificar que TLS conecta.
4. RFC 8446, *The Transport Layer Security (TLS) Protocol Version 1.3*: https://www.rfc-editor.org/rfc/rfc8446 . Base normativa del protocolo TLS 1.3.
5. RFC 5280, *Internet X.509 Public Key Infrastructure Certificate and CRL Profile*: https://www.rfc-editor.org/rfc/rfc5280 . Base normativa de perfiles y validación de certificados X.509.

Las referencias fundamentan el diseño de pruebas, pero no demuestran que este repositorio ya las haya superado. El trabajo académico sobre TLS no sustituye la ejecución de las pruebas en este candidato.

## 8. Estado inicial verificado y limitaciones

Al redactar este plan, PR #48 estaba abierto y en borrador. CI del paquete había pasado en un commit anterior conocido, pero la evidencia del propio workflow declara G23/G24 `NOT_EXECUTED` y rollback/postboot `NOT_TESTED_ON_HOST`. El paquete del artefacto no se ha inspeccionado aquí como una instalación de host. El código debe someterse a revisión y pruebas antes de cualquier uso operacional.

Decisión actual: `HOLD_FOR_G23_G24`. Siguiente acción autorizada: implementar la matriz de pruebas automatizadas no destructivas en esta rama de PR, ejecutar CI, corregir defectos con evidencia y preparar el bundle. Las pruebas de host, G23 y G24 quedan condicionadas a acceso real y revisores independientes.