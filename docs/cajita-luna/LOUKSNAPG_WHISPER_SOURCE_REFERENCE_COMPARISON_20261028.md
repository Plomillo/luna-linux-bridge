# LOUKSNAPG — comparación del Whisper fuente frente al candidato comprimido

- Fecha de evidencia: 2026-10-28 UTC.
- Fuente original fijada: `openai/whisper-large-v3-turbo`, revisión `7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7`.
- Prueba de referencia: [GitHub Actions #40789767512](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40789767512).
- Evidencia descargable: `louksnapg-whisper-reference-evidence-40789767512`, artifact ID `12861830043`, SHA-256 ZIP `1fdce158cf737920944b9876038dae2fe26838f30437d195bc90010e014008a6`.
- La referencia es evidencia diagnóstica del modelo fuente; no es una certificación del motor comprimido ni del paquete.

## Integridad de la fuente y las entradas

- Peso fuente: `1,617,824,864` bytes.
- SHA-256 fijado y observado: `542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1`.
- Audio sintético “hello world”: SHA-256 `88ebeb4aba0b257c2b9669356aaa5dfc7e974638ee3a76fdbcc510cb41de8eb6`.
- Audio real público: `hf-internal-testing/librispeech_asr_dummy`, revisión `5be91486e11a2d616f4ec5db8d3fd248585ac07a`, muestra `1272-128104-0000`, duración `5.855` segundos, 16 kHz.
- SHA-256 del Parquet esperado y observado: `4e69a06fa5edc90921e5e7e39a7084881f8b3ed9c805c574f4f39c6fde27c603`.
- SHA-256 de la transcripción de referencia: `9ed9a726f8b973252de284bf878668198435473d4af80795424178eff5e7fb48`.

## Resultados equivalentes

| Prueba | Whisper fuente | Candidato comprimido rank-29 INT8 |
|---|---|---|
| Audio conocido “hello world” | PASS; devuelve “Hello world.” | FAIL; no devuelve ninguna de las dos palabras esperadas |
| Voz grabada LibriSpeech | PASS; WER `0.058824` (límite `0.25`) | FAIL; WER `0.941176` |
| Ejecución de tarea | PASS | PASS, pero salida semánticamente incorrecta |
| Certificación | No es objeto de certificación en este ensayo | NOT_GRANTED; candidato rechazado |

La fuente pasa ambos casos con los mismos criterios utilizados para el candidato. Esto descarta que el error de la prueba anterior se deba simplemente a un archivo de audio cambiado o a una expectativa inválida. La diferencia observada está en la representación comprimida y/o su camino consumidor. El candidato INT8 rank-29 registra además un error Frobenius agregado de `0.7713949353768056`; la reconstrucción pierde una proporción grande de la señal original.

## Recursos y límites

- Inferencia únicamente en el runner hospedado de GitHub Actions, un hilo CPU, `torch==2.7.1+cpu`.
- Pico RSS de referencia: `5,546,655,744` bytes en el runner; no se aplicó al runner el límite local de 1 GiB.
- PC local: no se cargaron los pesos de 1.62 GB ni se ejecutó inferencia.
- La prueba tardó aproximadamente 72 segundos de tiempo medido de ejecución tras instalar dependencias y descargar el modelo.
- La referencia no modifica ni se promueve al runtime del producto.

## Acción autorizada en curso

El candidato rank-29 fue rechazado. Se ha iniciado un segundo ensayo aislado con rango 64 y tope físico del módulo de 85,000,000 bytes; se comprueba además una proyección conservadora del paquete bajo el máximo global de 479,000,000 bytes. La proyección no reemplaza la medición exacta del paquete final. La promoción sólo puede ejecutarse si ambas tareas funcionales pasan, los hashes coinciden y la proyección no supera el límite; aun así, G23/G24 y la certificación integral siguen independientes y pendientes.

**Estado vigente: `WHISPER_RANK29=REJECTED`; `WHISPER_RANK64=EXPERIMENTAL_PENDING`; `GLOBAL_CERTIFICATION=NOT_GRANTED`.**
