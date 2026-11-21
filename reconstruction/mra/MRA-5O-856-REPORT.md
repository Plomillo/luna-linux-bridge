# MRA-5O-856 — informe de ejecución aditiva

Este informe no certifica el producto, el agente ni la plataforma.
La certificación global permanece `NOT_CERTIFIED`.
El entrenamiento de pesos permanece `NOT_AUTHORIZED`.
La conciencia no se afirma: `NOT_CLAIMED`.

## 1. Repositorio y cabeza

- Repositorio de trabajo: `Plomillo/luna-linux-bridge`.
- Rama de trabajo: `work/luna-v3-reconstruction-20261119`.
- Cabeza previa a esta integración: `ce14a8d316fd9c7e1c05acb4f370bde248e38f64`.
- Rama congelada `work/luna-v3-phase0-reference-freeze-20261119` permanece en `bb1e1010bd549a235590958aeb5d0371d636b25b`.
- La rama madre `automation/mtls-evidence-gate-20261013` no se movió.
- No se reescribió `Louksna.md` ni `reconstruction/mra/MRA-LUNA-5O-001.md`.

## 2. Aritmética

| Segmento | Identificadores | Cantidad | Estado de esta ejecución |
|---|---:|---:|---|
| Históricos | 001–036 | 36 | `HISTORICAL_PRESERVED` |
| Complementarios | 037–144 | 108 | `NOT_PRESENT` |
| Aditivos | 145–856 | 712 | ejecutados |
| Total | 001–856 | 856 | secuencia única, sin huecos |

`36 + 108 + 712 = 856`. Los 712 objetivos aditivos son distintos entre sí.
Los 108 complementarios no estaban en el repositorio. No se inventó un `PASS` para ellos.

## 3. Resultado medido

Fuente: `reconstruction/mra/MRA-5O-856-execution.json` y `reconstruction/mra/MRA-5O-856-cases.json`, producidos por `louksna-session --mra-856`.

| Estado | Cantidad |
|---|---:|
| `PASS_FUNCTIONAL` | 629 |
| `BLOCKED` | 83 |
| `HISTORICAL_PRESERVED` | 36 |
| `NOT_PRESENT` | 108 |
| `FAIL` | 0 |
| `CERTIFIED` | 0 |

- `bad`: vacío.
- `historical_failed`: 0.
- Evidencia histórica SHA-256: `497b4e108d300da29352b2a2fe4f2bd677658900cd152aca0f6b2ad82fce0638`.
- Coincide con la evidencia previa de los 36 casos. `mra.rs` no se reescribió para perseguir ese hash.
- `product_platform`: `NOT_CERTIFIED`.
- Cada fila lleva `weight_training=NOT_AUTHORIZED` y `consciousness=NOT_CLAIMED`.

La misma cuenta la reprodujo el verificador del paquete sobre el Python empaquetado. El fallo de la construcción aborta si aparece un `FAIL`, un `CERTIFIED`, un bloqueo sin condición de desbloqueo o un secreto.

## 4. Qué significa cada estado

- `PASS_FUNCTIONAL`: el worker produjo hechos y un módulo oráculo que no importa al worker calculó los mismos hechos. Un cambio deliberado del caso 145 deja de coincidir con el oráculo.
- `INDEPENDENTLY_VALIDATED` en esas filas significa esa comparación de módulos, no una certificación G24 del agente.
- `HISTORICAL_PRESERVED` / `NOT_ESTABLISHED`: el oráculo Rust de 001–036 vuelve a llamar a `run_suite`. Eso no es independencia metodológica. El veredicto operacional de esos 36 casos sigue siendo `GRANTED` solo en el alcance `MRA-5O-OPERATIONAL`.
- `NOT_PRESENT`: el expediente 037–144 no está en el árbol. El objetivo queda `UNKNOWN_DOSSIER_ABSENT`.
- `BLOCKED`: la herramienta, el hardware, la sesión o el corpus no estaban. La condición de desbloqueo viaja en la fila. No se sustituyó por una simulación presentada como la operación real.

Algunos oráculos de control son predicados estructurales débiles. Coincidir con ellos no eleva el caso a `CERTIFIED`.

## 5. Bloqueos que no se convirtieron en éxito

83 casos. Condición resumida, no una simulación:

- Corpus escriturístico o confesional ausente (`LOUKSNA_CORPUS_DIR` con edición, localizador y hash): 745, 747–753, 756, 757, 762–765, 768, 774, 776–779, 785–796, 801, 802, 841. No se inventaron citas.
- Plataforma gráfica real ausente: KDE 375, Wayland 376, portales 377, escritorio 378, audio 379, navegador 607, sesión de escritorio 608, aplicaciones móviles 297 y de escritorio 298.
- Herramientas o laboratorios ausentes: strace/perf, cgroup desechable, ACL, initramfs, systemd en ejecución, JIT, wasmtime/wasmer, LLVM, gRPC, NTP de laboratorio, firewall del anfitrión, netns desechable, OSV/NVD fechado, tokenizador del modelo, adaptador, CodeQL, runner propio, OIDC de workflow, Dependabot, protección remota de rama, firmware e imagen de disco.
- No se usó `dpkg --force-depends`, `kwin_wayland --virtual` ni Weston como certificación.
- El anfitrión de esta ejecución es Debian 12 bookworm, en contenedor, sin `/dev/dri` y sin sesión Wayland. El caso 383 permanece bloqueado hasta un segundo entorno real. El caso 383 registra que falta Debian 13 como segundo entorno, no que Debian 13 haya sido certificado.

## 6. Quinto orden, sin acreditación

Los casos 705–744 y 817–856 se ejecutaron como laboratorio. G1 se distingue de G0 en hechos comparados por el oráculo. La autoautorización de G1 queda rechazada. El caso 856 pasa porque registra que la acreditación metateológica no se concede sin corpus, no porque esa acreditación se haya otorgado.

Eso no es `M0 + G0 → M1 + G1 → M2` certificado sobre el agente completo. El alcance certificado de quinto orden es ninguno.

Los casos de mecanismo usan la frase de laboratorio `The courier delivered the letter on the third day.` marcada como no escriturística. `theological_certification` no se concede.

## 7. Entrenamiento de pesos y memoria

No hubo modificación de pesos. No hubo llamada al proveedor de chat: el fallo externo de cuota permanece fuera de esta ejecución y no se simuló una respuesta. La memoria de 15 capas y la voz no se redefinieron. El verificador del paquete volvió a sintetizar y a transcribir `hola, soy luna.`

## 8. Artefactos

Los candidatos anteriores no se sobrescribieron. Siguen en la copia de preservación:

| Artefacto | SHA-256 preservado |
|---|---|
| `LOUKSNA.deb` | `9a166bd5e5cf0f1fe507e8f9824447b6ae8aca769f30d6814892e2dc32061e35` |
| `LOUKSNA.sh` | `2e10e8f623e2365cccb2bdb6b26ebdb01674da40220631582aecf319ddf1b66d` |

Candidatos nuevos, después de incluir `mra_suite` y `--mra-856`:

| Artefacto | SHA-256 |
|---|---|
| `LOUKSNA.deb` | `1f88f3cdc3cce549b2a0ddfc1a4958b6c557c106bf3a530ee94817e0f2a2d43d` |
| `LOUKSNA.sh` | `7c23e8da3ef47d90d1e3f4c49fada51aa730ad46ca4c188291bc7d37acf47172` |

Árbol de payload: `c426f0ff65bd1b542aafa0a45dd502e49cb712741a9d16b4337c3e99d70166a5`.
Paridad deb/sh: el empaquetador la exigió y terminó con ese árbol.
Certificación escrita en el paquete: `NOT_CERTIFIED`.
Debian 13, KDE Plasma y Wayland real: `NOT_RUN`.

## 9. Integración

- `louksna-session --mra-856` localiza la suite empaquetada o la del árbol de fuentes, ejecuta el oráculo Python y rechaza recursión, certificación, entrenamiento de pesos y secretos en la salida.
- El hijo histórico solo relanza `--mra`, no `--mra-856`.
- El empaquetador copia `louksna/mra_suite` y falla el cierre si la suite no está verde en el sentido definido arriba.
- La corrida de CI anterior `44857103125` no cubre esta suite. El workflow vuelve a dispararse porque cambia `louksna/**`.

## 10. Lo que esta orden no cierra

El programa de 856 casos no está cerrado. Faltan los expedientes 037–144, 83 bloqueos externos y las puertas de Debian 13, KDE Plasma y Wayland real. Ningún promedio compensa eso. No hay certificación de producto, de plataforma, de quinto orden informático ni de quinto orden metateológico.
