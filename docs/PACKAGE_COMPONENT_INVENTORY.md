# Inventario de componentes del paquete Debian 0.4.0-3

**Estado:** inventario técnico provisional; no sustituye debian/copyright ni constituye autorización de distribución.  
**Paquete:** louksna-linux-bridge  
**Fuente de instalación:** debian/rules, debian/louksna-linux-bridge.docs, debian/control.

## Archivos del proyecto incluidos

| Fuente | Destino / mecanismo | Estado de derechos |
|---|---|---|
| bridge/*.py | /usr/lib/louksna/bridge/ | Titular y licencia del código no demostrados por el árbol inspeccionado; requiere declaración autorizada. |
| bridge/*.json | /usr/lib/louksna/bridge/ | Determinar si cada archivo es original, derivado o incorpora material de terceros; requiere revisión. |
| scripts/provision-mtls-local.sh | /usr/lib/louksna/bridge/provision-mtls-local.sh y documentación | Titular/licencia no declarados en el material localizado. |
| bridge/deploy/*.service.in, *.timer.in | /usr/share/louksna/deploy/ | Titular/licencia no declarados en el material localizado. |
| bridge/MTLS_READONLY_GATEWAY.md, bridge/LIVE_TRANSPORT.md, bridge/README.md | /usr/share/louksna/ y documentación Debian | Titular/licencia no declarados en el material localizado. |
| bridge/CONTRACT.v0.json | /usr/lib/louksna/bridge/ y /usr/share/doc/louksna-linux-bridge/ | Contrato del proyecto; no se presume que sea una licencia de software. Derechos de redistribución por confirmar. |

## Dependencias declaradas

### Construcción (Build-Depends)

- build-essential
- debhelper-compat (= 13)
- dpkg-dev
- python3
- openssl

### Ejecución (Depends / Recommends)

- python3 (>= 3.10)
- openssl
- systemd recomendado, no dependencia obligatoria.

No se encontró requirements.txt ni requirements.lock en la ruta raíz de bridge/; la instalación declarada no copia paquetes Python de terceros ni un árbol site-packages. El código de runtime debe seguir verificándose contra sus importaciones reales antes de afirmar que el inventario de dependencias está completo. Las dependencias del sistema se obtienen de los repositorios Debian; no se incrustan sus binarios ni sus textos de licencia en este paquete según las reglas de instalación revisadas.

## Componentes externos y voz

La rama y las reglas de empaquetado inspeccionadas no identifican un archivo de voz, modelo TTS ni artefacto de voz descargado por el instalador. Por tanto, no hay evidencia para incluir una licencia de voz en este paquete concreto. Si la voz pertenece a otro componente/proyecto, su licencia debe registrarse en el inventario de ese artefacto, con proveedor, versión/revisión, URL de licencia, alcance de uso, atribución y restricciones de redistribución. No se debe extender esa licencia al código de este paquete ni afirmar que el paquete redistribuye la voz sin que el manifiesto lo demuestre.

## Evidencia legal que falta para cerrar DEP-5

1. Declaración del titular autorizado para el código original y los documentos/contratos originales incluidos.
2. Licencia exacta aplicable a cada grupo de archivos y el texto completo que deba acompañar al paquete.
3. Revisión de historial y de cualquier contenido copiado/derivado para detectar copyright de terceros.
4. Contacto real autorizado de mantenimiento. maintainer email actual maintainer@louksna.invalid no es un contacto operativo y no se sustituirá por una dirección inferida.
5. Generación de debian/copyright DEP-5 desde esos datos, seguida de Lintian y revisión independiente.

**Regla de salida:** este inventario no autoriza redistribución. Mientras los derechos del material original no estén acreditados y Lintian no pase, el paquete permanece en HOLD y los artefactos de CI son diagnósticos, no releases.
