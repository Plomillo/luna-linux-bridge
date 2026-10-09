# README — conclusiones finales verificables de CUSTOSZ V7 / LUNA R4

## Estado

`RESEARCH_MISSION_STATUS=CUSTOSZ_AND_RUNTIME_MATERIAL_RESEARCH_PASS`

Esta fase de investigación y preparación terminó correctamente dentro del techo máximo de 20 minutos definido por el propietario. Este README consolida los resultados finales y sustituye, como estado vigente, los bloqueos preliminares que quedaron resueltos durante los reintentos gobernados.

No constituye G23/G24, no activa CUSTOSZ/MetaOS/Runtime como producción y no autoriza F3-DISK.

## Cadena de misión realmente ejecutada

| Etapa | Evidencia | Resultado |
|---|---|---|
| Despacho nativo inicial | [run 36374826968](https://github.com/Plomillo/luna-linux-bridge/actions/runs/36374826968) | CUSTOSZ V7 ejecutado sobre el runner LOUKSNA; workspace real `LUNA_PROJECT` resuelto; misión `MIS-31e208fc59964c059f03` registrada; heartbeat `SUPERVISORY_ACTIVE`. |
| Auditoría read-only CUSTOSZ + Runtime | [run 36374864210](https://github.com/Plomillo/luna-linux-bridge/actions/runs/36374864210) | 14 comprobaciones; runtime selftest/journal PASS; CUSTOSZ `v07-status` y `v07-selftest` PASS; duración 2.198 s. |
| Continuación nativa acotada | [run 36376439810](https://github.com/Plomillo/luna-linux-bridge/actions/runs/36376439810) | Misión `MIS-6d75cad1fb234f099a4d` registrada como continuación de la anterior; workspace real resuelto; heartbeat `SUPERVISORY_ACTIVE`; presupuesto activo restante 1192.802 s. |
| Investigación material CUSTOSZ + Runtime | [run 36376796627](https://github.com/Plomillo/luna-linux-bridge/actions/runs/36376796627) | `global_step_gate=1`; `material_execution_proven=true`; `result=PASS`; evidencia encadenada y resultado publicado. |

La continuación nativa se registró con el trabajo pesado explícitamente asignado a `GITHUB_HOSTED_ONLY`. La pequeña operación de registro en LOUKSNA se ejecutó con `nice -n 10` y un límite de memoria virtual de 256 MiB; la investigación material se ejecutó en `ubuntu-latest`, no sobre la RAM del dispositivo del propietario.

## Identidades verificadas

| Objeto | SHA-256 verificado |
|---|---|
| A0 — `Louksna.md` | `5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9` |
| A1 — `LOUKSNAMEJORADA.md` | `2114188988126aa7a9650c131526c9d7c54ad351db315635569a317114f4eb51` |
| PUAC2 | `c872ab8d31e0e301de93ab06047294424d309d947f225e62148cee8265b15869` |
| CUSTOSZ V7 | `dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2` |
| Runtime staging seleccionado | `a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67` |
| MetaOS | `5d8f1239e3a0b452be722078760b000afc22af0a64f93ffb0a1f74024f15aed0` |
| Skeleton R4 | `fb9fad37994e684ad54b1ffc2762660eebcb8e41bd9c4ba685ffac55217d5b0f` |
| Misión maestra | `f4811c8c5b6ab6186f70b69620972ae49c3e2718a956d6cfae72df07c19ac5da` |

## CUSTOSZ V7

El artefacto real fue ejecutado en GitHub-hosted durante la etapa material y también sobre el runner LOUKSNA para el registro de misión.

- Versión reportada: `7.0.0-candidate`.
- Autoridad: `Louksna.md`.
- Doctrina: `EXTEND_DO_NOT_REPLACE`.
- Nueve familias declaradas.
- 72 capacidades declaradas.
- `v07-selftest=PASS`.
- `self_certification=false`.
- Certificación reportada por el propio artefacto: `EXTERNAL_G23_G24_REQUIRED`.
- Estado `active=false`: el selftest no constituye activación ni certificación.

## CUSTOSZ_RUNTIME_V1

El runtime staging se cargó y ejecutó materialmente en GitHub-hosted.

- `runtime_id=CUSTOSZ_RUNTIME_V1`.
- Selftest: `PASS`.
- Evidence journal: `true`.
- Despacho material: `PASS`.
- `material_execution_proven=true`.
- `global_step_gate=1`.
- Evidence chain head: `7c478e39b3b047835f7298d476a8a1832512296b361935c394fe7e2e70c84ebb`.

El runtime staging seleccionado tiene SHA-256 `a79e1386...`, mientras el Skeleton declara el pin genérico `4e9bf0e7...`. La identidad del archivo staging y su funcionamiento aislado están demostrados; **la relación de variante/procedencia con el pin del Skeleton todavía debe reconciliarse antes de una activación de producción en el host**.

## Dos arquitecturas y PUAC2

A0 y A1 fueron recuperadas desde sus ramas respectivas y sus identidades byte-exactas fueron verificadas durante el despacho material.

PUAC2 se confirmó como `2.0.0-CANDIDATE`; los marcadores D01–D10 están presentes. Su propia documentación conserva `G23=NO_CONCEDIDA` y `G24=NO_CONCEDIDA`. Por tanto, PUAC2 puede definir requisitos de aseguramiento, pero no autocertificarse ni sustituir G23/G24.

La equivalencia/admisión semántica completa A0 ↔ A1 sigue siendo un trabajo independiente pendiente; la comprobación de hashes no la demuestra.

## LUNA R4 y contenedor semántico

El Skeleton R4 verificado declara Debian GNU/Linux 13 Trixie como objetivo y conserva `INSTALLATION_PERFORMED=FALSE` para ese documento de referencia.

Estado CAS observado:

- Objetos esperados: 252.
- Objetos presentes en la rama GitHub: 4.
- Objetos pendientes de transferencia: 248.
- La evidencia histórica de origen ya había verificado SHA-256 de los 252 objetos.
- `source_content_hash_validation_pending=true` en el estado actual de transferencia.

Transferencia CAS completa y funcionamiento del runtime semántico son gates distintos.

## Firefox

El propietario confirmó expresamente que Firefox ya está desinstalado. Esta misión no repitió ni programó nuevamente su eliminación.

## Lo que esta misión NO hizo

- No instaló componentes de LUNA R4 en el host.
- No activó el runtime staging como runtime de producción.
- No modificó Windows 11.
- No modificó EFI/GPT/particiones.
- No movió, borró ni reformateó PROYECTOS.
- No reinició el equipo.
- No concedió G23 ni G24.
- No convirtió el PASS de selftest en certificación.
- No declaró resuelta la discrepancia de pin del runtime.

## Conclusiones exactas

1. CUSTOSZ V7 **sí recibió una misión nativa** en el workspace real y posteriormente registró una continuación gobernada.
2. El CUSTOSZ_RUNTIME_V1 staging **sí ejecutó una investigación material** ligada a la misión de continuación y superó el protocolo `SR-EXEC-BOUND-FME-01` en GitHub-hosted.
3. El trabajo pesado de esta etapa no utilizó la RAM del dispositivo del propietario.
4. Las identidades A0, A1, PUAC2, CUSTOSZ, MetaOS, Runtime, Skeleton y misión fueron comprobadas.
5. La investigación no autoriza todavía una instalación autónoma en el host: G23/G24 aplicables siguen en HOLD.
6. La discrepancia entre el SHA-256 del runtime staging y el pin genérico del Skeleton debe resolverse por procedencia/variante.
7. A0/A1 requieren aún la evidencia completa de equivalencia/admisión semántica.
8. El contenedor semántico conserva 248 objetos pendientes de transferencia Git LFS.
9. La siguiente fase debe producir la matriz diferencial real de componentes R4 y lotes de instalación probados en sandbox antes de intervenir el host.
10. La retirada de Windows continúa siendo objetivo obligatorio de la misión global, pero F3-DISK conserva su expediente, recuperación demostrada y autorizaciones H2/H4 + G23/G24 específicas.

## Próximos hitos autorizados de investigación/preparación

1. Reconciliar la variante del runtime staging contra el pin del Skeleton y su procedencia original.
2. Completar la comparación/admisión A0 ↔ A1 sin mutar los documentos canónicos.
3. Completar los 248 objetos CAS pendientes desde un checkout limpio aislado y verificar los hashes desde el destino.
4. Construir la matriz diferencial `Skeleton ↔ host ↔ artefactos materializados`.
5. Preparar y probar en sandbox los lotes de instalación R4.
6. Someter el puente de consentimiento/ejecución a prueba independiente antes de autorizar instalación real.

## Evidencia principal

- [Misión maestra](MISION_MAESTRA_DEFINITIVA.md)
- [Resultado material CUSTOSZ + Runtime](CUSTOSZ_RUNTIME_R4_RESULT.json)
- [Evidencia inicial](RESEARCH_EVIDENCE.json)
- [Orden GitHub #5](https://github.com/Plomillo/luna-linux-bridge/issues/5)
- [PR #6](https://github.com/Plomillo/luna-linux-bridge/pull/6)
- [Run material final 36376796627](https://github.com/Plomillo/luna-linux-bridge/actions/runs/36376796627)
