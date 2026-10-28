# LOUKSNAPG — rechazo del experimento Whisper INT8 rango 64

- Ejecución: [GitHub Actions #40790372870](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40790372870)
- Evidencia: artifact ID `12861651078`; SHA-256 ZIP `2f4fbba545be408f2349e12c13ec5aebe31e9abd2f6c0f025c87a43744f9fb65`.
- Commit de código probado: `45ad1b1301ef4e0410b496a59f88698c2d153daf`.
- Decisión: `REJECT_CANDIDATE; GLOBAL_CERTIFICATION=NOT_GRANTED`.

## Resultados

La fuente oficial fijada `openai/whisper-large-v3-turbo@7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7`, peso SHA-256 `542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1`, se usó para una reconstrucción INT8 de rango 64, un hilo y runner hospedado. El SHA de la fuente coincide exactamente.

| Medida | Resultado |
|---|---:|
| Peso candidato | 69.366.096 bytes |
| Módulo físico, descriptor incluido | 71.931.049 bytes |
| Tope de módulo del experimento | 85.000.000 bytes |
| Error Frobenius relativo agregado | 0,7069607088284378 |
| Proyección de paquete global | 431.913.930 bytes |
| Máximo global | 479.000.000 bytes |
| Audio “hello world” | FALLA; salida `.,,` |
| LibriSpeech `1272-128104-0000` | FALLA; WER 1,0 frente a límite 0,25 |
| Promoción | NO |
| Certificación global | NOT_GRANTED |

La proyección global pasa, pero es una aproximación basada en el paquete base documentado en `d09f79a088781d26fc5b1c3e830db9abfb42c147`, el peso anterior y una reserva de metadatos de 1 MB. No sustituye el cálculo exacto del artefacto de distribución.

## Causa y decisión

La inferencia y el enrutamiento ejecutan sin error técnico, pero la salida no contiene palabras. El mismo corpus, audio, configuración fuente, revisión y SHA pasaron ambas tareas en [la prueba de referencia #40789767512](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40789767512). Por tanto, no es un defecto del fixture. El aumento de rango de 29 a 64 reduce el error de reconstrucción agregado de 0,7713949 a 0,7069607, pero no restaura la función de transcripción.

Esta evidencia descarta que el empaquetado secundario INT2/Q2 sea la única causa: el experimento R64 usa factores INT8 sin sidecar Q2 y sigue fallando. La pérdida está dominada por la aproximación de rango y/o por su efecto acumulado en el grafo. No se promueve la variante R64. El siguiente experimento R96 continúa en un entorno temporal y sólo puede producir un candidato si pasan ambas pruebas y la proyección conservadora del límite global. Ningún cambio en estos experimentos autoriza G23, G24 o certificación integral.
