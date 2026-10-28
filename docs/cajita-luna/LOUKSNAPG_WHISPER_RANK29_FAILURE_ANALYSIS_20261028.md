# LOUKSNAPG — análisis forense del candidato Whisper rank-29

- Fecha de ejecución: 2026-10-28 UTC.
- Rama de reparación: `louksnapg/phase4-resume-20261028`.
- Candidato de código ensayado: `a79b27b4950e82913cae753584a260b171a8ab65`.
- Ejecución: [40783316873](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40783316873).
- Artefacto de evidencia: `louksnapg-whisper-int8-evidence-40783316873`, artifact ID `12858640646`, SHA-256 del ZIP `ef176445ee021c27ee8f019dddfeac4a8a0820d885188194a91ce8ce181b8e68`.
- Decisión: `REJECT_CANDIDATE; GLOBAL_CERTIFICATION=NOT_GRANTED`.

## Defecto y consecuencia demostrados

El candidato de Whisper de rango uniforme 29 ejecuta la ruta `D03_TRANSCRIPCION_ROOT` y devuelve salidas no vacías, por lo que la prueba de ejecución por sí sola pasa. Sin embargo, ambas pruebas de tarea fallan:
- Audio sintético conocido “hello world”: no aparece ninguna de las dos palabras esperadas.
- Audio público grabado LibriSpeech `1272-128104-0000`, muestra de 5,855 s: `WER=0.941176`, frente al límite de aceptación experimental `WER<=0.25`.

El audio y la transcripción se obtuvieron del conjunto `hf-internal-testing/librispeech_asr_dummy`, revisión `5be91486e11a2d616f4ec5db8d3fd248585ac07a`. El SHA-256 del Parquet observado coincidió con el esperado: `4e69a06fa5edc90921e5e7e39a7084881f8b3ed9c805c574f4f39c6fde27c603`. La falla no puede atribuirse a un archivo de prueba cambiado sin más evidencia.

## Integridad, presupuesto y aproximación

El archivo original de pesos Whisper large-v3-turbo se descargó del repositorio oficial `openai/whisper-large-v3-turbo`, revisión `7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7`, y el hash completo observado coincide con el fijado: `542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1`.

La reconstrucción de rango 29 sin empaquetado secundario de 2 bits produjo:
- Pesos: `34,877,996` bytes; SHA-256 `46145ea45d26f0e0014f595fc221092eca1f4cd997826c909d6bd6892c332807`.
- Directorio físico del módulo, incluido el descriptor: `37,442,965` bytes.
- Capacidad de módulo fijada: `40,000,000` bytes.
- Error relativo agregado de reconstrucción de factores: `0.7713949353768056`.
- Se factorizaron 235 matrices, se preservaron 350 vectores y las dos matrices de posiciones.
- El pico RSS del proceso de construcción fue `2,051,551,232` bytes en el runner hospedado; cada una de las dos tareas de ejecución estuvo por debajo de 700 MB. La restricción local de 1 GiB no se aplicó al runner; en la PC no se cargaron pesos ni se ejecutó inferencia.

Por tanto, **el techo de tamaño sí se cumple y la calidad funcional no**. El dato de error de reconstrucción de 0,7714 indica una pérdida grande en los factores; la WER elevada demuestra repercusión funcional. Esto señala que la representación/rango es insuficiente para la tarea ensayada. No demuestra todavía que no exista ningún defecto secundario en el cargador, las escalas o el preprocesamiento, así que la causa debe confirmarse con una comparación equivalente contra el modelo fuente.

## Relación con CUSTOSZ V9 y prevención de regresiones

Los recibos de la misión histórica `WHISPER_TRANSCRIPTION_LOWRANK_INT8_20261021T123845Z` ya documentaban fallos de runtime en iteraciones tempranas (configuración de generación, sesgo/tipo de datos en Conv1d, LayerNorm y timeout). El runtime de la rama actual incorpora adaptaciones para la configuración de generación y la ejecución ya no se detiene por esos errores; ahora llega a producir texto, pero falla la calidad. Esto constituye un modo de fallo diferente: no se debe repetir sin más las reparaciones anteriores de interfaz.

El último ensayo se ejecutó como trabajo de GitHub Actions, no mediante el worker local CUSTOSZ V7. No se promovió el archivo de factores, no se modificaron pesos canónicos y no se propagó la certificación.

## Corrección necesaria y verificación siguiente

1. Comparar el modelo fuente exacto large-v3-turbo con **la misma muestra real de LibriSpeech y el mismo criterio WER**, no sólo con el audio sintético.
2. Registrar el texto normalizado de salida únicamente para las dos fixtures públicas/sintéticas, para poder distinguir un error de preprocesamiento/decodificación de una pérdida del modelo.
3. Si la fuente supera la prueba y el candidato sigue fallando, retirar la vía de promoción automática para este candidato y evaluar una representación/candidato diferente como experimento aislado. No se debe promover un modelo diferente ni reemplazar automáticamente la identidad del motor.
4. Ejecutar la repetición sólo en GitHub-hosted runner con un hilo y con evidencia ligada al SHA exacto. La PC sigue en modo de inspección ligera.

El workflow sólo puede habilitar una promoción si ambas pruebas pasan, pero el estado actual `FAIL_FUNCTIONAL_OR_QUALITY_GATE` no cumple esa condición y deja la promoción omitida. No hay certificación de Whisper ni integral.
