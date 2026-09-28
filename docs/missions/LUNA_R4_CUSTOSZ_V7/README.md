# README — Misión LUNA R4 para CUSTOSZ V7

## Orden íntegra y plazo

[Misión íntegra publicada en GitHub, issue #5](https://github.com/Plomillo/luna-linux-bridge/issues/5).

**Destinatario:** CUSTOSZ V7. **Coordinador:** SYMPHYLAX R1. **Gobernador:** MetaOS. **Límite estricto de investigación:** 20 minutos desde el acuse de recepción verificable. Si termina antes, debe entregar inmediatamente el informe. El límite es para la investigación y preparación documental, **no** una licencia para omitir pruebas ni una orden de ejecutar en veinte minutos la instalación integral de LUNA R4.

## Estado del envío

- `MISSION_PUBLISHED_IN_GITHUB=TRUE` — issue #5 contiene íntegra la misión.
- `WORKER_RECEIPT=NOT_VERIFIED`.
- `WORKER_RESEARCH_STARTED=NOT_VERIFIED`.
- `WORKER_CONCLUSIONS=NOT_YET_RECEIVED`.
- `AUTOMATED_HOST_EXECUTION=NOT_AUTHORIZED_BY_THIS_FILE`.
- `G23_G24_NEW_SCOPE=HOLD`.

**No presentar esta publicación como prueba de que CUSTOSZ recibió, ejecutó o finalizó el encargo.**

## Conclusiones forenses anteriores al despacho

Estas conclusiones pertenecen a la auditoría de GitHub previa, **no** a una investigación nueva ejecutada por CUSTOSZ:

| Elemento | Conclusión comprobable | Referencia |
|---|---|---|
| LOUKSNA original | `Louksna.md` está en `main`; mantiene la autoridad canónica. | [main/Louksna.md](https://github.com/Plomillo/luna-linux-bridge/blob/main/Louksna.md) |
| LOUKSNA mejorada | `LOUKSNAMEJORADA.md` fue incorporada íntegramente a staging; no tiene certificación operacional heredada. | [PR #4](https://github.com/Plomillo/luna-linux-bridge/pull/4) |
| PUAC2 | `2.0.0-CANDIDATE`; extensión pendiente de admisión formal, G23/G24 no concedidas. | [main/PUAC2.md](https://github.com/Plomillo/luna-linux-bridge/blob/main/PUAC2.md) |
| SYMPHYLAX R1 | Inventario de 11.746 archivos SHA-256; no demuestra competencia integral de instalación. | [Run 36352624122](https://github.com/Plomillo/luna-linux-bridge/actions/runs/36352624122) |
| Contenedor semántico | 252 objetos superaron SHA-256 en el host; 248 aún pendientes de transferencia a GitHub tras fallo por worktree no limpio. | [Run 36357166014](https://github.com/Plomillo/luna-linux-bridge/actions/runs/36357166014) |
| Candado estático | Once pruebas negativas pasaron en GitHub-hosted; no hay evidencia de puente autenticado ni ejecución real. | [Run 36370225725](https://github.com/Plomillo/luna-linux-bridge/actions/runs/36370225725) |
| LUNA R4 | Skeleton recuperado; documento PART 0–9 íntegro aún no identificado de manera concluyente. | [PR #3](https://github.com/Plomillo/luna-linux-bridge/pull/3) |
| Firefox | El propietario confirma que está desinstalado. | Confirmación expresa del propietario; estado del host pendiente de cotejo de solo lectura. |

## Informe que debe entregar CUSTOSZ V7

CUSTOSZ debe actualizar este README mediante un commit y enlazar aquí su PR o commit. La versión completada debe contener **únicamente hechos respaldados** y consignar los siguientes campos:

```text
MISSION_ID:
WORKER_ID_AND_VERSION:
ACK_RECEIVED_UTC:
RESEARCH_START_UTC:
RESEARCH_END_UTC:
ELAPSED_SECONDS:    # debe ser <= 1200
SOURCE_COMMIT_SHA:
VERIFIED_SOURCES_AND_HASHES:
EXACT_CONCLUSIONS:
CONTRADICTIONS_AND_RESOLUTION:
ARTIFACTS_CREATED_WITH_SHA256:
TESTS_ACTUALLY_EXECUTED:
TESTS_NOT_EXECUTED:
AUTHORIZED_ACTIONS_COMPLETED:
ACTIONS_NOT_PERFORMED:
BLOCKERS:
G23_STATUS_AND_SCOPE:
G24_STATUS_AND_SCOPE:
NEXT_AUTHORIZED_MILESTONE:
RESEARCH_DEADLINE_STATUS:
EVIDENCE_LINKS:
```

No atribuir a CUSTOSZ las comprobaciones de la auditoría previa. Si el plazo se agota, publicar `RESEARCH_TIME_LIMIT_REACHED`, registrar el trabajo efectivamente terminado y conservar como pendientes todas las tareas restantes.

## Frontera de autorización

La presente orden solo transmite investigación y preparación por GitHub. **No** concede permisos para formatear, cambiar EFI/GPT, borrar Windows, desplazar PROYECTOS, instalar paquetes en el host o reiniciar autónomamente. Las operaciones sobre disco requieren expedientes G23/G24 y autorización H2/H4 específica, con copias independientes y restauración demostrada. El objetivo final sigue siendo LUNA R4 completa y Windows 11 ausente como sistema anfitrión.
