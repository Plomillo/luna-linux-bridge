# LOUKSNAPG — resultado G24 del candidato de fábrica

- Workflow: [Cajita V9 materialization and Louksna1 governed factory #40792192212](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40792192212).
- SHA exacto de candidato: `4d67ec3d9b1163ee39f1ffbd59de5502cd0c3fa2`.
- Job G24: `123181522969`, ejecución en GitHub-hosted runner bajo 1 CPU y límite cgroup de 1 GiB.
- Evidencia G24: artifact ID `12861809751`, digest ZIP `9308c3a95ffaa2595f09a19466d61253aa32650815b4496fcde7cebd919484d6`.
- Telemetría: artifact ID `12862258474`, digest ZIP `d4663c2e79724af7cff688b6c259b124b1ddb2f0b8ad555007bab41997f767cc`.
- Decisión: `G24=NOT_GRANTED`; la publicación de candidato quedó omitida.

## Recursos y ejecución

| Comprobación | Resultado |
|---|---:|
| CPU | 1 hilo |
| Límite de memoria | 1.073.741.824 bytes |
| Pico de memoria observado | 990.986.240 bytes |
| Smoke de los seis motores de destino | 6/6 PASS, scope parcial |
| Adaptadores consumidores requeridos | 21; no establecidos |
| Pruebas sintéticas conocidas ejecutadas | 5 |
| Aceptación de calidad semántica | FALLA |
| Resultado G24 | NOT_GRANTED |

El runner permaneció bajo el límite establecido, pero esto sólo acredita la ejecución con recursos limitados. El smoke de seis destinos mide la ejecución técnica parcial y no equivale a la validación de las tareas consumidoras.

## Fallos funcionales por dominio

Las cinco tareas conocidas retornaron con código de salida cero, pero fallaron sus aserciones de calidad:

| Dominio | Tarea | Salida observada | Calidad |
|---|---|---|---|
| Cerebro / GPT-OSS | `e2e-cerebro-text-generation` | `ron amongronronron among amongron amongssronron` | FAIL |
| Whisper | `e2e-whisper-audio-pipeline` | `daughterziest manuscript ele` | FAIL |
| Traducción general | `e2e-seamless-translation` | `te te te apres te te te te who te te` | FAIL |
| Docling documental | `e2e-docling-image-extraction` | `onationonationonation underrated underrated underrated shitty underrated` | FAIL |
| Qwen / análisis avanzado | `e2e-qwen3-reasoning` | `irts airways` | FAIL |

El registro de evidencia informó `task_adapter_evidence_status=FAIL`, `task_adapter_return_code=3`, `task_adapter_pass_count=5` y `task_adapter_expected_count=5`. El contador “pass_count” cuenta salidas con `PASS_FUNCTIONAL_EXECUTION` y código cero, **no** tareas que superaron la calidad semántica. Por eso no contradice los cinco fallos anteriores, pero el nombre del campo es ambiguo y puede inducir a error. La corrección ya está incorporada en la rama: `task_adapter_execution_success_count` y `task_adapter_quality_pass_count` se separan, y `task_adapter_pass_count` pasa a significar calidad aceptada. Las pruebas unitarias de ese helper pasaron en el workflow de validación de rama #40793408840.

Existe además un vacío de cobertura de la suite frente a los cinco dominios pedidos: los cinco casos conocidos son Cerebro, Whisper, traducción general, Docling y Qwen. **No hay un caso funcional para traducción de lenguas antiguas**; el caso de Docling ocupa ese puesto en el total de cinco, aunque es un destino diferente. La evidencia del módulo antiguo registra `consumer_adapter=NOT_REGISTERED`, sin transductor compilado ni léxico operacional. Por eso el dominio antiguo no debe tratarse como superado ni sustituido silenciosamente por traducción general.

La evidencia G24 también dice `semantic_quality_equivalence=NOT_ESTABLISHED`, `all_21_target_adapters=NOT_ESTABLISHED`, `reference_quality_equivalence=NOT_ESTABLISHED`, y el gate terminó fail-closed. La integridad G23 del contenedor pasó, pero el mismo paquete no supera el G24 funcional. No existe certificación integral.

## Defecto de gobernanza del informe

- **Defecto concreto:** el campo `task_adapter_pass_count` cuenta sólo el estado de ejecución y exit code cero, pese a que todas las comprobaciones de calidad retornan `FAIL`.
- **Consecuencia:** una métrica con nombre “pass” puede interpretarse erróneamente como aprobación funcional aunque el gate global haya fallado.
- **Corrección:** emitir campos distintos como `task_adapter_execution_success_count` y `task_adapter_quality_pass_count`; calcular el segundo a partir de `quality_acceptance.status == "PASS"` y registrar la salida de forma explícita.
- **Verificación posterior:** repetir el cálculo con la evidencia existente y probarlo con fixtures que tengan ejecución correcta/calidad fallida y ejecución correcta/calidad aprobada. La decisión de certificación no se debe elevar hasta que los requisitos semánticos reales pasen.

Estado integral: `HOLD_NOT_CERTIFIED`; G23 sólo aprobó la integridad del paquete y G24 denegó la liberación por los resultados funcionales.
