# LOUKSNA ZONA DIRECTIVA — GitHub Interface Skeleton V0.2 HARDENED

## Dictamen definitivo de empaquetado y orden operacional

```text
===============================================================================
DICTAMEN DEFINITIVO DE EMPAQUETADO
LOUKSNA ZONA DIRECTIVA — GitHub Interface Skeleton V0.2 HARDENED
TIPO DE PROGRAMA, FORMATO .DEB, ESTRUCTURA INTERNA Y ORDEN OPERACIONAL
===============================================================================

DECISIÓN PRINCIPAL:
El programa debe ser una aplicación gráfica nativa de escritorio para Debian 13,
empaquetada como .deb amd64, con instalación por apt/dpkg, integración KDE,
menú de aplicaciones, iconos, metadatos, dependencias declaradas, configuración
separada, datos de usuario separados, evidencia auditable y rollback operativo.

FORMATO PRIMARIO:
.deb

ARQUITECTURA:
amd64

SISTEMA OBJETIVO:
Debian GNU/Linux 13 Trixie
KDE Plasma
AMD Ryzen 5 3500U
AMD Radeon Vega 8
8 GB RAM clase baja-media
NVMe KIOXIA
Usuario local no-root

NOMBRE DEL PAQUETE:
louksna-zona-directiva

NOMBRE DE APLICACIÓN:
LOUKSNA Zona Directiva

TÍTULO VISIBLE:
LOUKSNA ZONA DIRECTIVA

SUBTÍTULO VISIBLE:
GitHub Interface Skeleton V0.2 HARDENED

IDENTIDAD:
LOUKSNA ONLY

IDENTIDADES PROHIBIDAS:
No agregar asistentes.
No agregar agentes inventados.
No agregar coordinadores paralelos.
No agregar entidades aditivas.
No renombrar Louksna.
No convertir GitHub en autoridad.
No convertir el runtime en autoridad.
No convertir la UI en autoridad.

===============================================================================
01. TIPO DE PROGRAMA QUE DEBE SER
===============================================================================

CLASIFICACIÓN:
Aplicación gráfica de escritorio gobernada, con backend local ligero, interfaz
GitHub, auditoría, evidencia, configuración, chat/llamada y paneles operativos.

NO ES:
- no es una web suelta;
- no es sólo un dashboard;
- no es sólo un script;
- no es sólo un wrapper de GitHub;
- no es una extensión de navegador;
- no es un paquete Snap;
- no es Flatpak como formato primario;
- no es AppImage como formato primario;
- no es un servicio de fondo sin interfaz;
- no es un LLM local pesado;
- no es una identidad nueva.

SÍ ES:
- una app .deb de escritorio;
- una consola visual;
- una interfaz GitHub gobernada;
- una superficie de evidencia;
- un panel de decisión;
- un cliente local ligero;
- un controlador auditado de operaciones;
- una aplicación instalable y removible con apt/dpkg;
- una interfaz compatible con KDE;
- una referencia visual y operacional de Louksna.

TECNOLOGÍA RECOMENDADA:
Tauri 2
Rust backend
TypeScript frontend
React o Vue
CSS variables / Tailwind
SQLite local para cache y auditoría
Secret Service / libsecret para credenciales
GitHub REST API como integración primaria

TECNOLOGÍA NO RECOMENDADA COMO PRIMERA OPCIÓN:
Electron

RAZÓN:
Electron es viable, pero más pesado en RAM y tamaño. En una PC Ryzen 5 3500U
con 8 GB RAM, el criterio correcto es mantener la UI nítida y rica sin cargar un
Chromium completo si WebKitGTK del sistema puede usarse mediante Tauri.

===============================================================================
02. QUÉ SIGNIFICA “TODO ADENTRO”
===============================================================================

REGLA:
Todo lo que pertenezca a Louksna debe ir dentro del .deb.
Todo lo que sea dependencia del sistema debe declararse como dependencia,
no duplicarse.

TODO ADENTRO INCLUYE:
- binario principal;
- frontend compilado;
- assets gráficos;
- iconos;
- imágenes 8K canónicas;
- tipografías propias si tienen licencia válida;
- tema visual;
- archivos de configuración base;
- plantillas de evidencia;
- plantillas de reportes;
- contratos UI;
- manifest de componentes;
- mapas de rutas;
- metadatos AppStream;
- archivo .desktop;
- documentación;
- changelog;
- copyright;
- política de permisos;
- política de rollback;
- validadores locales ligeros;
- esquemas JSON;
- migraciones SQLite;
- scripts internos no destructivos;
- systemd user service opcional, deshabilitado por defecto.

TODO ADENTRO NO INCLUYE:
- Debian base;
- KDE Plasma;
- WebKitGTK del sistema;
- GTK del sistema;
- glibc;
- drivers GPU;
- kernel;
- GitHub completo;
- Node de desarrollo;
- Rust toolchain;
- secretos;
- tokens;
- credenciales;
- cachés temporales;
- repositorios clonados por el usuario;
- datos privados de GitHub;
- logs personales históricos no generados por la app.

REGLA DE DEPENDENCIAS:
Las dependencias de sistema se declaran en DEBIAN/control.
Las dependencias internas de Louksna se empaquetan bajo /opt/louksna-zona-directiva.
Las dependencias de desarrollo no entran al paquete final.
Los secretos jamás entran al paquete final.

===============================================================================
03. ESTRUCTURA FINAL DEL .DEB
===============================================================================

PAQUETE:
louksna-zona-directiva_0.2.0-hardened_amd64.deb

ESTRUCTURA INTERNA:

/
├── DEBIAN/
│   ├── control
│   ├── postinst
│   ├── prerm
│   ├── postrm
│   ├── conffiles
│   └── md5sums
│
├── opt/
│   └── louksna-zona-directiva/
│       ├── bin/
│       │   ├── louksna-zona-directiva
│       │   └── louksna-zona-directiva-safe-mode
│       │
│       ├── lib/
│       │   └── louksna/
│       │       ├── github/
│       │       │   ├── api_client.schema.json
│       │       │   ├── permissions.schema.json
│       │       │   ├── repository.schema.json
│       │       │   ├── pull_request.schema.json
│       │       │   ├── workflow.schema.json
│       │       │   └── artifact.schema.json
│       │       │
│       │       ├── evidence/
│       │       │   ├── evidence.schema.json
│       │       │   ├── chain_of_custody.schema.json
│       │       │   ├── hash_verification.schema.json
│       │       │   ├── validation_report.schema.json
│       │       │   ├── g23_report.schema.json
│       │       │   └── g24_certificate.schema.json
│       │       │
│       │       ├── governance/
│       │       │   ├── louksna_authority_policy.json
│       │       │   ├── puac2_gate_matrix.json
│       │       │   ├── no_silent_operations_policy.json
│       │       │   ├── rollback_policy.json
│       │       │   ├── non_regression_policy.json
│       │       │   └── identity_boundary_policy.json
│       │       │
│       │       ├── runtime/
│       │       │   ├── runtime_state.schema.json
│       │       │   ├── checkpoint.schema.json
│       │       │   ├── audit_event.schema.json
│       │       │   ├── local_cache.schema.json
│       │       │   └── safe_mode.schema.json
│       │       │
│       │       └── migrations/
│       │           ├── 0001_init.sql
│       │           ├── 0002_github_cache.sql
│       │           ├── 0003_evidence_ledger.sql
│       │           ├── 0004_audit_log.sql
│       │           └── 0005_rollback_index.sql
│       │
│       ├── share/
│       │   ├── ui/
│       │   │   ├── index.html
│       │   │   ├── assets/
│       │   │   ├── css/
│       │   │   ├── js/
│       │   │   └── manifest.json
│       │   │
│       │   ├── canonical-ui/
│       │   │   ├── 01_louksna_zona_directiva_centro_de_mando_8k.png
│       │   │   ├── 02_louksna_zona_directiva_repositorios_8k.png
│       │   │   ├── 03_louksna_zona_directiva_pull_requests_8k.png
│       │   │   ├── 04_louksna_zona_directiva_evidencia_8k.png
│       │   │   ├── 05_louksna_zona_directiva_chat_llamada_8k.png
│       │   │   └── 06_louksna_zona_directiva_configuracion_8k.png
│       │   │
│       │   ├── design/
│       │   │   ├── louksna_zona_directiva_tokens.json
│       │   │   ├── louksna_zona_directiva_component_map.json
│       │   │   ├── louksna_zona_directiva_layout_rules.json
│       │   │   ├── louksna_zona_directiva_visual_contract.md
│       │   │   └── louksna_zona_directiva_ui_traceability_matrix.csv
│       │   │
│       │   ├── templates/
│       │   │   ├── issue_template.md
│       │   │   ├── pull_request_template.md
│       │   │   ├── evidence_report.md
│       │   │   ├── validation_report.md
│       │   │   ├── g23_report.md
│       │   │   ├── g24_certificate.md
│       │   │   └── rollback_report.md
│       │   │
│       │   ├── docs/
│       │   │   ├── README.md
│       │   │   ├── SECURITY.md
│       │   │   ├── PRIVACY.md
│       │   │   ├── OFFLINE_MODE.md
│       │   │   ├── GITHUB_PERMISSIONS.md
│       │   │   ├── EVIDENCE_MODEL.md
│       │   │   ├── ROLLBACK_MODEL.md
│       │   │   └── PUAC2_COMPLIANCE.md
│       │   │
│       │   └── icons/
│       │       ├── louksna.svg
│       │       ├── louksna-16.png
│       │       ├── louksna-32.png
│       │       ├── louksna-48.png
│       │       ├── louksna-64.png
│       │       ├── louksna-128.png
│       │       ├── louksna-256.png
│       │       └── louksna-512.png
│       │
│       └── VERSION
│
├── usr/
│   ├── bin/
│   │   └── louksna-zona-directiva -> /opt/louksna-zona-directiva/bin/louksna-zona-directiva
│   │
│   ├── share/
│   │   ├── applications/
│   │   │   └── louksna-zona-directiva.desktop
│   │   │
│   │   ├── icons/
│   │   │   └── hicolor/
│   │   │       ├── scalable/apps/louksna-zona-directiva.svg
│   │   │       ├── 64x64/apps/louksna-zona-directiva.png
│   │   │       ├── 128x128/apps/louksna-zona-directiva.png
│   │   │       ├── 256x256/apps/louksna-zona-directiva.png
│   │   │       └── 512x512/apps/louksna-zona-directiva.png
│   │   │
│   │   ├── metainfo/
│   │   │   └── io.louksna.zonadirectiva.metainfo.xml
│   │   │
│   │   ├── doc/
│   │   │   └── louksna-zona-directiva/
│   │   │       ├── README.md
│   │   │       ├── changelog.gz
│   │   │       ├── copyright
│   │   │       └── third_party_licenses/
│   │   │
│   │   └── mime/
│   │       └── packages/
│   │           └── louksna-zona-directiva.xml
│   │
│   └── lib/
│       └── systemd/
│           └── user/
│               └── louksna-zona-directiva-bridge.service
│
└── etc/
    └── opt/
        └── louksna-zona-directiva/
            ├── defaults.json
            ├── policy.json
            └── logging.json

===============================================================================
04. RUTAS DE USUARIO EN TIEMPO DE EJECUCIÓN
===============================================================================

CONFIGURACIÓN USUARIO:
~/.config/louksna-zona-directiva/config.json
~/.config/louksna-zona-directiva/github.json
~/.config/louksna-zona-directiva/appearance.json
~/.config/louksna-zona-directiva/policies.json

DATOS USUARIO:
~/.local/share/louksna-zona-directiva/louksna.db
~/.local/share/louksna-zona-directiva/evidence/
~/.local/share/louksna-zona-directiva/reports/
~/.local/share/louksna-zona-directiva/checkpoints/
~/.local/share/louksna-zona-directiva/exports/

CACHE:
~/.cache/louksna-zona-directiva/github/
~/.cache/louksna-zona-directiva/artifacts/
~/.cache/louksna-zona-directiva/thumbnails/
~/.cache/louksna-zona-directiva/runtime/

LOGS:
~/.local/state/louksna-zona-directiva/logs/
~/.local/state/louksna-zona-directiva/audit/
~/.local/state/louksna-zona-directiva/crash/

SECRETOS:
Secret Service / libsecret.
No guardar tokens en texto plano.
No guardar credenciales dentro del .deb.
No imprimir tokens en logs.
No exportar tokens en paquetes de evidencia.

===============================================================================
05. CONTROL FILE DEL PAQUETE
===============================================================================

Package:
louksna-zona-directiva

Version:
0.2.0-hardened

Architecture:
amd64

Section:
utils

Priority:
optional

Maintainer:
Louksna Local <local@louksna.invalid>

Homepage:
local / project-bound

Description:
LOUKSNA Zona Directiva - GitHub Interface Skeleton V0.2 HARDENED
 Governed desktop interface for GitHub repositories, pull requests, evidence,
 chat/call coordination, configuration, traceability, validation, rollback and
 non-regression workflows under Louksna authority.

DEPENDS BASE:
${shlibs:Depends}
${misc:Depends}
ca-certificates
xdg-utils
hicolor-icon-theme
shared-mime-info
desktop-file-utils
libgtk-3-0 | libgtk-3-0t64
libwebkit2gtk-4.1-0
libsecret-1-0
libayatana-appindicator3-1 | libappindicator3-1
git

RECOMMENDS:
gh
openssl
jq

SUGGESTS:
firefox-esr
kdialog
wl-clipboard

NO DEPENDENCY:
nodejs runtime
npm runtime
rustc runtime
cargo runtime
electron runtime
Debian ISO
KDE reinstall
Docker
large local LLM
GPU compute stack

RATIONALE:
El usuario final no necesita toolchains de desarrollo para ejecutar el programa.
El .deb debe contener la app compilada. Las toolchains pertenecen al entorno de
build, no al runtime.

===============================================================================
06. STACK DE BUILD
===============================================================================

BUILD STACK:
Rust stable
Cargo
Tauri CLI
Node.js sólo build-time
pnpm o npm sólo build-time
TypeScript
React o Vue
Vite
SQLite library binding
Debian packaging tools
dpkg-deb
lintian
desktop-file-validate
appstreamcli
sha256sum

BUILD HOST:
Puede ser tu PC o GitHub Actions.
Para tu PC, preferible compilar una vez, sin procesos pesados permanentes.
Para reproducibilidad, preferible GitHub Actions o contenedor Debian 13 controlado.

BUILD OUTPUTS:
dist/
target/release/louksna-zona-directiva
src-tauri/target/release/bundle/deb/louksna-zona-directiva_0.2.0-hardened_amd64.deb
SHA256SUMS
BUILD_EVIDENCE.json
LINTIAN_REPORT.txt
INSTALL_TEST_REPORT.txt

===============================================================================
07. MODELO GITHUB
===============================================================================

INTEGRACIÓN PRIMARIA:
GitHub REST API

INTEGRACIÓN SECUNDARIA:
GitHub CLI gh, opcional

AUTENTICACIÓN:
OAuth device flow o fine-grained token.
Preferir GitHub App o OAuth cuando se formalice distribución.
Fine-grained token aceptable para fase local controlada.

PERMISOS MÍNIMOS:
contents: read
metadata: read
pull_requests: read/write sólo si se crearán o comentarán PRs
issues: read/write sólo si se crearán issues
actions: read para workflows/artifacts
actions: write sólo si se dispararán workflows
checks: read
statuses: read
administration: evitar salvo configuración avanzada explícita

PRINCIPIO:
Least privilege.

NO HACER:
No pedir repo completo si no hace falta.
No pedir admin por defecto.
No almacenar token en texto plano.
No mostrar token.
No incluir token en logs.
No meter token en el .deb.
No meter credenciales en artifacts.
No meter secretos en capturas.

===============================================================================
08. BASE DE DATOS LOCAL
===============================================================================

ENGINE:
SQLite

FILE:
~/.local/share/louksna-zona-directiva/louksna.db

TABLES:
repositories
pull_requests
issues
workflows
artifacts
evidence
audit_events
checkpoints
rollback_pointers
settings
github_accounts
permission_scopes
chat_sessions
call_sessions
transcripts
decisions
tasks
validation_runs
g23_runs
g24_runs

ENCRYPTION:
No meter secretos en SQLite salvo cifrado explícito.
Tokens deben ir a Secret Service / libsecret.
La DB puede contener metadatos no secretos y hashes.

BACKUP:
Exportable a JSON/ZIP.
Export debe excluir secretos.
Export debe incluir manifest, hashes y evidencia.

===============================================================================
09. SECCIONES UI QUE DEBEN EXISTIR
===============================================================================

01 Centro de mando
02 Repositorios
03 Pull Requests
04 Evidencia
05 Chat / Llamada
06 Configuración

PROHIBIDO:
Agregar secciones no declaradas sin contrato.
Agregar CI/CD como sección independiente si no está en el set canónico actual.
CI/CD puede existir como panel interno, no como identidad ni sección principal.
Gobernanza puede existir como panel dentro de Configuración, no como sección nueva.
Trazabilidad puede existir dentro de Evidencia, no como sección nueva.
Estadísticas pueden existir dentro de Centro de mando, no como sección nueva.

RATIONALE:
El set de seis imágenes aceptadas por el usuario fija la navegación canónica
visual preliminar para esta versión.

===============================================================================
10. ORDEN DE IMPLEMENTACIÓN
===============================================================================

FASE 0 — FREEZE DE ESPECIFICACIÓN
Input:
- bloque monolítico UI;
- seis imágenes aceptadas;
- Louksna.md;
- PUAC2;
- specs PC.

Output:
- ui_spec.md
- design_tokens.json
- component_map.json
- traceability_matrix.csv

FASE 1 — PROTOTIPO ESTÁTICO
Implementar seis pantallas sin backend real:
- Centro de mando;
- Repositorios;
- Pull Requests;
- Evidencia;
- Chat / Llamada;
- Configuración.

Output:
- UI renderizable;
- screenshots;
- visual diff contra referencias;
- informe de legibilidad.

FASE 2 — BACKEND LOCAL
Implementar:
- SQLite;
- settings;
- audit log;
- evidence ledger;
- config;
- safe mode;
- secret store abstraction.

Output:
- app abre sin GitHub;
- modo offline;
- config persistente;
- logs locales.

FASE 3 — GITHUB READ-ONLY
Implementar:
- auth;
- listar repositorios;
- listar PRs;
- listar workflows;
- listar artifacts;
- cache local;
- refresh manual.

Output:
- conexión GitHub read-only;
- no mutación;
- evidencia de conexión.

FASE 4 — OPERACIONES CONTROLADAS
Implementar:
- crear issue;
- comentar PR;
- disparar workflow;
- generar reporte;
- exportar evidencia.

Output:
- confirmación previa;
- log de acción;
- rollback pointer cuando aplique.

FASE 5 — PAQUETE .DEB
Implementar:
- .desktop;
- iconos;
- metainfo;
- systemd user service opcional;
- postinst/prerm;
- lintian;
- install test;
- uninstall test.

Output:
- .deb instalable;
- apt install funciona;
- apt remove limpia binarios sin borrar datos usuario;
- purge opcional pregunta/limpia config sistémica.

FASE 6 — VALIDACIÓN PUAC2
Ejecutar:
- positive tests;
- negative tests;
- boundary tests;
- rollback tests;
- non-regression tests.

Output:
- validation_report.json
- evidence_package.zip

FASE 7 — G23 / G24
G23:
validación independiente.

G24:
certificación.

ACTIVE:
sólo después de G24 y autorización explícita.

===============================================================================
11. REGLA DE PAQUETE AUTOCONTENIDO
===============================================================================

SE DEBE INCLUIR DENTRO DEL .DEB:
- app compilada;
- UI final;
- seis referencias visuales 8K;
- tokens de diseño;
- schemas;
- plantillas;
- docs;
- iconos;
- desktop file;
- metainfo;
- políticas;
- migraciones DB;
- servicio user opcional;
- validadores de integridad;
- README de instalación;
- README de permisos GitHub;
- política de privacidad;
- política de seguridad.

NO SE DEBE INCLUIR DENTRO DEL .DEB:
- node_modules de desarrollo;
- target debug;
- cachés;
- .git;
- tokens;
- secretos;
- logs personales;
- repositorios clonados;
- binarios no usados;
- modelos pesados;
- Debian ISO;
- KDE;
- dependencias de sistema duplicadas;
- toolchains de compilación;
- Docker images;
- basura temporal.

===============================================================================
12. PRESUPUESTO DE RECURSOS PARA TU PC
===============================================================================

RAM TARGET:
Idle: menor a 300 MB ideal.
Uso normal: menor a 600 MB.
Picos tolerables: menor a 1 GB.
No usar LLM local pesado.

CPU TARGET:
Idle casi nulo.
Polling bajo.
Sin loops visuales pesados.
Sin indexación permanente en segundo plano.
Sin recompilar en runtime.

GPU TARGET:
Efectos visuales moderados.
Animaciones reducibles.
No WebGL obligatorio.
Modo reduced-motion.

DISK TARGET:
.deb objetivo: 80 MB - 350 MB según inclusión de imágenes 8K.
Datos usuario: separado del paquete.
Cache: limpiable con política.
Evidencia: exportable.

NETWORK:
Sólo GitHub API cuando el usuario conecte cuenta.
No telemetría externa silenciosa.
No llamadas ocultas.
No descarga de dependencias durante uso normal.

===============================================================================
13. COMPORTAMIENTO DE INSTALACIÓN
===============================================================================

INSTALL:
sudo apt install ./louksna-zona-directiva_0.2.0-hardened_amd64.deb

POSTINST:
- registrar desktop file;
- actualizar icon cache;
- actualizar mime database si aplica;
- no iniciar servicios automáticamente salvo modo permitido;
- no pedir credenciales;
- no descargar componentes;
- no tocar PROYECTOS;
- no tocar Debian/KDE base.

FIRST RUN:
- mostrar bienvenida;
- confirmar modo Louksna only;
- mostrar permisos GitHub requeridos;
- permitir modo offline;
- permitir conectar GitHub;
- crear config usuario;
- crear DB usuario;
- registrar primer audit event.

REMOVE:
sudo apt remove louksna-zona-directiva

REMOVE POLICY:
- borra binarios;
- conserva datos de usuario;
- conserva config de usuario;
- no borra evidencia.

PURGE:
sudo apt purge louksna-zona-directiva

PURGE POLICY:
- borra config sistémica;
- no borrar datos usuario sin confirmación explícita dentro de la app o script separado.

===============================================================================
14. SEGURIDAD
===============================================================================

TOKEN STORAGE:
libsecret / Secret Service.

TOKEN DISPLAY:
Never raw.

LOG REDACTION:
Required.

GITHUB PERMISSIONS:
Minimum viable permission.

CONFIG CHANGES:
Confirmación requerida.

VOICE COMMANDS:
No operación destructiva sólo por voz.

CHAT COMMANDS:
Proponen, no ejecutan silenciosamente.

NETWORK:
Explicit GitHub endpoints.
No analytics externa por defecto.
No telemetry silenciosa.

UPDATES:
No auto-update silencioso.
Usar .deb firmado o hash verificado.
Mostrar versión actual y versión candidata.
Rollback disponible.

===============================================================================
15. VALIDACIONES OBLIGATORIAS DEL .DEB
===============================================================================

PACKAGE VALIDATION:
dpkg-deb -I package.deb
dpkg-deb -c package.deb
lintian package.deb
desktop-file-validate usr/share/applications/louksna-zona-directiva.desktop
appstreamcli validate io.louksna.zonadirectiva.metainfo.xml
sha256sum package.deb

INSTALL VALIDATION:
sudo apt install ./package.deb
command -v louksna-zona-directiva
gtk-launch louksna-zona-directiva
dpkg -L louksna-zona-directiva
dpkg -s louksna-zona-directiva

RUNTIME VALIDATION:
open app;
render six sections;
offline mode works;
GitHub disconnected state works;
connect GitHub;
read repositories;
read PRs;
read artifacts;
evidence ledger writes;
config persists;
remove token;
safe mode opens.

UNINSTALL VALIDATION:
sudo apt remove louksna-zona-directiva
binary removed;
desktop removed;
icons removed;
user data preserved.

PURGE VALIDATION:
sudo apt purge louksna-zona-directiva
system config removed;
user data not silently destroyed.

===============================================================================
16. DECISIÓN FINAL
===============================================================================

FINAL_PROGRAM_TYPE:
Native governed Debian desktop application.

FINAL_PACKAGE:
louksna-zona-directiva_0.2.0-hardened_amd64.deb

FINAL_STACK:
Tauri 2 + Rust + TypeScript frontend + SQLite + libsecret + GitHub REST API.

FINAL_INSTALL_TARGET:
Debian 13 KDE amd64.

FINAL_IDENTITY:
LOUKSNA only.

FINAL_APP_SECTIONS:
1 Centro de mando
2 Repositorios
3 Pull Requests
4 Evidencia
5 Chat / Llamada
6 Configuración

FINAL_BUNDLING_RULE:
Everything belonging to Louksna goes inside the .deb.
System dependencies are declared, not duplicated.
Secrets never go inside.
Debian/KDE are never bundled or reinstalled.

FINAL_OPERATIONAL_STATUS:
SPECIFICATION_READY_FOR_PACKAGING_PLAN
IMPLEMENTATION_NOT_STARTED
CERTIFICATION_PENDING
ACTIVE_FALSE

===============================================================================
END
===============================================================================
```
