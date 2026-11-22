# MRA-5O — cierre operacional 037-144 y reparación de bloqueos

Medido por `python3 louksna/mra_suite/suite.py` contra `louksna-session --mra`.
No certifica el producto, la plataforma ni una sesión Debian 13 KDE Plasma Wayland.

## Resultado medido

| Campo | Valor |
|---|---|
| Casos | 856, secuencia única |
| Históricos 001-036 | 36 `HISTORICAL_PRESERVED`, certificación de fila `NOT_CERTIFIED` |
| Evidencia histórica | `497b4e108d300da29352b2a2fe4f2bd677658900cd152aca0f6b2ad82fce0638` |
| `PASS_FUNCTIONAL` | 805 |
| Certificación de caso | 805, solo donde el oráculo independiente coincidió |
| `BLOCKED` | 15 |
| `bad` | vacío |
| `product_platform` | `NOT_CERTIFIED` |
| Debian 13 + KDE Plasma + Wayland | `NOT_RUN` |

Los 108 identificadores 037-144 dejaron de estar `NOT_PRESENT`. Cada uno ejecuta una operación y un módulo oráculo que no importa al worker. El caso 144 queda `PASS_FUNCTIONAL` / `CERTIFIED` en el alcance operacional: el cierre nombra la ausencia de sesión Debian 13 KDE Plasma Wayland y no la esconde. Esa fila no certifica la distribución.

## Bloqueos que siguen

297, 298, 334, 353, 368, 370, 375, 376, 377, 378, 379, 380, 383, 575, 608.

Quedan fuera porque en este entorno no hay SDK móvil, LLVM, ACL, índices apt utilizables sin tocar el anfitrión, systemd en ejecución, sesión KDE/Wayland/portales/audio, permiso para leer el namespace de pid 1, Debian 13 como segundo sistema, ni un runner self-hosted. No se sustituyeron por un compositor virtual ni por `--force-depends`.

## Reparaciones que sí corrieron

Certificado vencido con `openssl ca -startdate`, MBR y ext2 de laboratorio, traza `LD_DEBUG`, ELF `ET_CORE`, feed sintético fechado y marcado como no NVD, JIT `mmap`, intérprete const/add, `RLIMIT_AS`, escritura parcial, `dpkg --root` sin `--force-depends`, cpio newc, snapshot de árbol, TLS local, framing de longitud, NTP local sin tocar el reloj, `unshare --net`, filtro sin iptables, usuario `nobody`, tokenizador de bytes, adaptador sin cambiar pesos, hook git local, claims OIDC sin token real, commit de dependabot local, escáner de patrones, HTTP local, y fixtures sintéticos de exégesis/teología marcados `SYNTHETIC_FIXTURE` / `NOT_CLAIMED`.
