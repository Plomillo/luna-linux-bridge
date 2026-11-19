# LUNA V3 — Fase 0. Auditoria de la especificacion contra el repositorio

Registro: `PHASE_0_REFERENCE_FREEZE`
Estado del producto: `NOT_CERTIFIED`
Estado de liberacion: `NOT_CERTIFIED_UNTIL_TESTED`

Este archivo no es `LOUKSNA.deb`, no es `LOUKSNA.sh`, no es G23 y no es G24.
No fusiona ramas. No mueve `automation/mtls-evidence-gate-20261013`.

## 1. Lo que la especificacion pide, verificado

| Referencia | Valor declarado | Observado el 2026-11-19 | Resultado |
|---|---|---|---|
| Repositorio | `Plomillo/luna-linux-bridge` | Publico, rama por defecto `main` | PASS |
| Rama UI | `work/louksna-zona-directiva-v0.3-functional-20261006` | Existe | PASS |
| SHA UI | `ec8e4abb9d57ea9708fc273856227b5c41329b3f` | Es la punta actual de esa rama | PASS |
| Rama madre | `automation/mtls-evidence-gate-20261013` | Existe | PASS |
| SHA madre congelado | `9130bca95fc9a9400e51a80f7afc56ca7d47758c` | El commit existe | PASS |
| Punta viva de la rama madre | no declarada como sustituto | `efc5d8b0a541cf801422f3ae77ca04efb8f1fce3` | DRIFT |
| Ancestro comun | `01d28c319af6a644168c621ab01b8e69dc1c0a0e` | `merge_base` confirmado | PASS |
| UI por delante | 31 | 31 respecto del SHA madre congelado | PASS |
| Madre por delante | 268 | 268 respecto del SHA congelado; 273 respecto de la punta viva | PASS contra el SHA; DRIFT contra la rama |
| Relacion | `DIVERGED` | `diverged` | PASS |
| Fusion automatica | `FALSE` | No ejecutada | PASS |

La comparacion de tres vias usada fue la de GitHub
`9130bca95fc9a9400e51a80f7afc56ca7d47758c...ec8e4abb9d57ea9708fc273856227b5c41329b3f`:
`status=diverged`, `ahead_by=31`, `behind_by=268`,
`merge_base=01d28c319af6a644168c621ab01b8e69dc1c0a0e`.

## 2. Causa raiz del desfase de la rama madre

El SHA congelado sigue siendo valido como objeto git, pero dejo de ser la punta de
`automation/mtls-evidence-gate-20261013`. Despues de `9130bca` hay 5 commits,
todos del bot `custosz-v7-runtime-bot`, con mensaje `kedb(directiva): evidence search tick`:

- `cb9a14b002bc0b0c9e93b8825e4a02f83675c583` — 2026-11-18T03:51:26Z
- `5f274b596fd6e975ac2cd40c19d52a3a20da94e1` — 2026-11-18T13:26:36Z
- `eba2ba22d655aecc0a9982b8b6e37357ebbf6a1c` — 2026-11-18T22:20:17Z
- `a89d75e71c46181246f4849cfbdf37460cc05b49` — 2026-11-19T03:50:41Z
- `efc5d8b0a541cf801422f3ae77ca04efb8f1fce3` — 2026-11-19T13:53:44Z

El propio SHA congelado tambien es un tick de ese bot
(`kedb(directiva): evidence search tick 2026-11-17T22:38:40Z`).

Consecuencia: la rama madre no es una linea de producto quieta. Es una rama viva de
busqueda de evidencia. Reconstruir contra el nombre de la rama, sin el SHA, cambia
la linea base en silencio. La reconstruccion queda anclada a los SHA de la
especificacion, no a la punta viva.

## 3. Lo que realmente hay en el SHA de interfaz

`ec8e4abb` no contiene una aplicacion ejecutable 0.3.0 ya materializada.
La raiz de ese commit es:

- `.github/workflows/`
- `governance/zona-directiva-v03/12_STAGE_GOVERNANCE_CONTRACT.md`
- `LOUKSNA_ZONA_DIRECTIVA_GITHUB_INTERFACE_V0.2_HARDENED/` con un monolito de empaquetado y seis PNG de referencia 8K
- `scripts/missions/` con materializador, preflight, functionalizer y plantillas
- `scripts/missions/v03_templates/App.tsx`, `main.rs`, `styles_add.css`
- `Louksna.md` de 11536067 bytes, `PUAC2.md`, `SKELETON_CANONICO_REFERENCIA.txt`

La interfaz funcional no esta versionada como arbol de aplicacion. La produce, si el
workflow llega a completarse, `.github/workflows/louksna-zd-v03-functional.yml`:

1. Toma un shell visual V0.2 del commit `94f999f28f6ac371e1a768312a69704af96fd7a7`.
2. Lo rematerializa con `louksna_zd_candidate_materializer.py`.
3. Lo parchea con `louksna_zd_v03_functionalizer.py`.
4. Compila Tauri 2 (`webkit2gtk 4.1`) y empaqueta `louksna-zona-directiva_0.3.0-functional_amd64.deb`.
5. Prueba instalacion en `debian:13-slim` dentro de Docker, no en KDE Plasma ni en una sesion Wayland.
6. Sube un artefacto de desarrollo con `active: false`, `g23: NOT_RUN_FOR_V03`, `g24: NOT_RUN_FOR_V03`.

El propio functionalizer declara, en el texto que escribe, que no estan reclamados:

- chat remoto salvo bridge configurado y round-trip real;
- voz / llamada de extremo a extremo;
- autorizacion ACTIVE.

El backend de plantilla es lectura GitHub (token fine-grained en Secret Service),
SQLite local, ledger y chat local. No es GitHub App, no es escritura de contenidos,
no es Piper, no es Whisper, no es Chatterbox, no es `LOUKSNA.deb` ni `LOUKSNA.sh`.

No hay release publicado con esos dos nombres. Los releases recientes son LUNITA,
UMOT y un borrador de Whisper. No sustituyen la entrega pedida.

## 4. Inventario de capacidades contra la especificacion congelada

| Capacidad exigida | Estado en `ec8e4abb` | Clasificacion |
|---|---|---|
| Seis apartados visuales | Plantilla React + PNG de referencia, no GUI instalada | PRESERVED_AS_TEMPLATE |
| Identidad visual 0.3 ejecutable | No esta en el arbol; se genera en CI | NOT_IN_TREE |
| Wayland nativo sobre KDE Plasma | No probado; el chequeo es `debian:13-slim` | NOT_IMPLEMENTED |
| Icono minimalista de luna llena | El workflow recorta el PNG del centro de mando | NOT_IMPLEMENTED |
| `LOUKSNA.deb` y `LOUKSNA.sh`, mismo payload | Ausentes | NOT_IMPLEMENTED |
| Piper `es_ES-sharvard-medium` speaker 1 | Ausente | NOT_IMPLEMENTED |
| Whisper.cpp + modelo | Ausente en este SHA | NOT_IMPLEMENTED |
| Chatterbox secundario con workflow y cliente | Ausente | NOT_IMPLEMENTED |
| Voice router | Ausente; el boton de microfono esta deshabilitado | NOT_IMPLEMENTED |
| Memoria de 15 capas | SQLite de ajustes, chat y evidencia solamente | NOT_IMPLEMENTED |
| GitHub App, tokens de instalacion, escritura, Git Database API | Token PAT de solo lectura | REPLACED_WITH_JUSTIFICATION pendiente |
| Webhooks firmados | Ausentes | NOT_IMPLEMENTED |
| Plan, un consentimiento, autonomia, checkpoints | Ausentes como motor | NOT_IMPLEMENTED |
| G23 y G24 del producto instalado | El workflow los marca `NOT_RUN` | NOT_IMPLEMENTED |
| Presupuesto 1 GiB / 1 nucleo del arbol completo | No medido | NOT_IMPLEMENTED |

## 5. Contradicciones internas que no se pueden resolver bajando el criterio

1. La especificacion prohibe redisenar la GUI 0.3 y, a la vez, exige un icono nuevo de luna llena. El icono es un cambio visual autorizado por el apartado 35.2; el resto del layout no lo es.
2. La especificacion prohibe entregar capturas en lugar de la interfaz. En el SHA fuente, las seis pantallas existen como PNG, no como aplicacion.
3. La especificacion prohibe evidencia ficticia. El workflow V0.3 ya se niega a marcar voz, bridge remoto y certificacion. Reactivar esas casillas sin una prueba fisica incumpliria la propia especificacion nueva y la del candidato.
4. La especificacion exige instalacion limpia en Debian 13 Trixie + KDE Plasma + Wayland, y prohibe usar XWayland como sustituto. Un `dpkg` correcto dentro de `debian:13-slim` no certifica esa plataforma.
5. La especificacion exige internalizar Whisper, Piper y el runtime, y a la vez prohibe computo pesado local y un techo de 1 GiB para todo el arbol de procesos. Eso es un requisito de medicion, no un hecho. Chatterbox no puede declararse local hasta pasar esa medicion.
6. La especificacion exige un modelo abierto de razonamiento en `ubuntu-latest` sin GPU y sin API de pago, pero tambien dice que no se presupone que un modelo quepa. Mientras no haya una medicion real, el motor remoto esta `BLOCKED`, no seleccionado.
7. La rama madre se mueve sola. Tratar su nombre como baseline congelada es falso.

## 6. Bloqueos externos de esta ejecucion

No se fabricaron `LOUKSNA.deb` ni `LOUKSNA.sh` en este registro.

Causa: producirlos aqui y llamarlos entrega certificada violaria los apartados 29, 36.4, 36.5, 39 y 41. El candidato real no esta materializado en el arbol; la certificacion exigida requiere una sesion limpia Debian 13 / KDE Plasma / Wayland, que este registro no ejecuto; y no existe una GitHub App autorizada cuyas claves puedan entrar al paquete (y no deben entrar).

Estado de las funciones no probadas: `BLOCKED` para la certificacion de plataforma y para el motor remoto no medido. Estado del producto: `NOT_CERTIFIED`.

## 7. Siguiente fase permitida

Fase 1, todavia sin fusion:

- Inventariar el commit visual `94f999f28f6ac371e1a768312a69704af96fd7a7`, que el workflow V0.3 usa como shell y que no es el SHA congelado de la especificacion.
- Materializar el candidato en un arbol versionado, sin declarar voz ni escritura GitHub.
- No avanzar la rama madre.
- No publicar un paquete con nombre `LOUKSNA` hasta que el payload canonico exista y se haya probado en la plataforma exigida.

G23: `PENDING_EVIDENCE`.
G24: `PENDING_G23`.
