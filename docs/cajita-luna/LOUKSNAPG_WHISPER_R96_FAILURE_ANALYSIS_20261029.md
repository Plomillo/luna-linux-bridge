# LOUKSNAPG — rechazo del experimento Whisper INT8 uniforme de rango 96

- Ejecución: [GitHub Actions #40790908490](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40790908490).
- Evidencia: artifact ID `12860744864`; SHA-256 ZIP `c85e204dcf5e40aac664e231a090786c26a8a85cfff4696e3d25f33ec5207491`.
- Commit exacto probado: `9eb5c2dd46deec9aa9842688ad3ed4bd8d304ce2`.
- Fuente fijada y verificada: `openai/whisper-large-v3-turbo@7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7`, SHA-256 `542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1`.
- Decisión: `REJECT_CANDIDATE`; ninguna promoción, cambio canónico de pesos ni certificación.

## Resultados con el mismo corpus y política de decodificación

| Métrica | Resultado |
|---|---:|
| Pesos candidato | 100.898.040 bytes |
| Módulo completo con descriptor | 103.462.998 bytes |
| Tope de módulo experimental | 110.000.000 bytes |
| Error Frobenius relativo agregado post-INT8 | 0,6633812149734326 |
| Proyección conservadora del paquete | 463.445.874 bytes |
| Límite global | 479.000.000 bytes |
| Audio sintético conocido | FALLA; salida sólo de puntuación |
| LibriSpeech 1272-128104-0000 | FALLA; WER 3,235294 (límite 0,25) |
| RSS pico del proceso de construcción en runner | 2.198.585.344 bytes |
| Promoción | NO |

La revisión del corpus, el Parquet y la transcripción está fijada y coincide en hash. La prueba upstream equivalente en [Actions #40791114109](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40791114109) usa la misma política de decodificación integrada y vuelve a pasar ambos casos: “Hello world” y LibriSpeech con WER 0,058824. No se atribuye el fallo al fixture ni a un error de decodificación común a la fuente.

## Causa funcional y acción correctiva

R29, R64 y R96 fallan las mismas pruebas, aunque sus errores de reconstrucción mejoran gradualmente (0,7714 → 0,7070 → 0,6634). En R96, la salida para voz real es texto multilingüe degenerado con 55 palabras normalizadas frente a 17 palabras de referencia. La compresión uniforme de rango bajo descarta demasiada señal; el simple incremento de rango no recupera la transcripción.

**No continuar con otra subida uniforme de rango.** Se inició un experimento adaptativo aislado que asigna rango 192 a las matrices FFN `encoder.fc2`, 64 a `encoder.fc1` y atención del encoder, 128 a las matrices del decoder, 96 a la embedding de tokens y 16 como base restante. El perfil está fijado por nombres de tensor, no cambia el repositorio fuente y debe pasar las mismas dos tareas además de los controles de tamaño. No se autoriza ningún reemplazo de modelo ni promoción automática.

## Recursos y gobernanza

La inferencia pesada sólo se ejecutó en GitHub-hosted runner con un hilo. El pico de RSS de construcción superó 2 GiB en el runner, no en la PC. En la PC no se descargaron pesos, no se ejecutó inferencia, no se instalaron dependencias y no se escribieron archivos de runtime durante la inspección. El tamaño global aquí es una proyección contra el paquete base documentado, no la medición exacta de un paquete final; hace falta volver a medir el contenedor completo. G23, G24 y la certificación global siguen `NOT_GRANTED`.
