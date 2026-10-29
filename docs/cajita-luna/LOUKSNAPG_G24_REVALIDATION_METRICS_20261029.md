# LOUKSNAPG — G24 revalidación tras corregir la métrica de calidad

- Workflow: [Cajita V9 materialization and Louksna1 governed factory #40793408906](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40793408906).
- Commit probado: `60a725e32e33c3f38c0b451003699922ac07d87a`.
- Job G23: `123185006392`, `PASS` sólo para integridad del contenedor.
- Job G24: `123185586454`, `NOT_GRANTED`.
- G23 evidencia: artifact ID `12861769894`, SHA-256 ZIP `aad1962227452b02bd68a0d7a830eb2e570032a0392388b0cf4978d633f26a96`.
- G24 evidencia: artifact ID `12863206182`, SHA-256 ZIP `42a77eac01ed54bec328ef4e06fcbcb6b3c175ef9685a08a9907701c0ed61e9d`.
- Telemetría G24: artifact ID `12862592985`, SHA-256 ZIP `09ed98223a92d9f908ce8043de1c94e1210c44ff1d989820d3275b61b5924667`.

## Resultado exacto

| Métrica | Resultado |
|---|---:|
| SHA-256 de `LOUKSNAPG.md` | `59244b34f5a3cb9b7236c4cf6c9bb4f4fec25dc8903e9be0f4299dd8de7e547d` |
| Runtime ZIP | 370.889.834 bytes |
| Documento Louksna1 | 11.651.408 bytes |
| Distribución combinada | 382.541.242 bytes |
| Límite combinado | 490.000.000 bytes |
| Smoke de inicio de los seis dominios | PASS |
| Smoke de seis destinos de infraestructura | 6/6 PASS; scope parcial |
| Éxitos técnicos de las cinco tareas modeladas | 5 |
| Pases de calidad semántica de esas tareas | **0** |
| Pico de RAM bajo cgroup | 931.495.936 bytes de 1.073.741.824 |
| CPU | 1 |
| G24 | `NOT_GRANTED` |

La métrica corregida informa `task_adapter_execution_success_count=5`, `task_adapter_quality_pass_count=0` y `task_adapter_pass_count=0`; `task_adapter_evidence_status=FAIL`, `task_adapter_return_code=3`. Los cinco procesos devolvieron código cero, pero las cinco aserciones de calidad fallaron. Los seis smoke tests de destino sólo confirman ejecución de interfaces muy acotadas, no el cometido funcional del motor.

Esta versión del harness todavía tenía cinco tareas de modelo —Cerebro, Whisper, traducción general, Docling y Qwen— y no ejecutaba una tarea de traducción antigua. La corrección de cobertura se añadió después y se está validando en el run `40794248442`, commit `c7915f9bf4fa9bd9db9d0c91baa55042f5f03ce0`. No se deben mezclar estas evidencias de distintos commits.

## Decisión

El paquete quedó bloqueado antes de publicación. G23 confirma integridad de distribución; G24 demuestra que las tareas funcionales no satisfacen sus comprobaciones conocidas. La certificación integral sigue `NOT_GRANTED`.
