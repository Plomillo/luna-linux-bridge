# LOUKSNAPG — auditoría de reparación funcional e identidad upstream

- Fecha de auditoría: 2026-10-26 UTC.
- Rama de trabajo: `louksnapg/official-model-functional-repair-20261026`.
- Alcance: revisión de código, metadatos y contratos; no se descargaron pesos originales grandes de los proveedores.
- Autoridad: `Louksna.md`; `EXTEND_DO_NOT_REPLACE`; preservación de las identidades y de los bloques canónicos.
- Estado de liberación: `HOLD`. Esta nota no concede G23, G24 ni certificación global.

## Hallazgos que impiden certificar

1. **Cerebro / GPT-OSS.** `cajita-luna-runtime/1. Cerebro/compression_metadata.json` declara `randomized_truncated_svd_rank1_plus_symmetric_int8_factor_quantization`, rango 1 y error relativo Frobenius agregado de `0.9983363410727844`. Ese error documenta una pérdida de reconstrucción extrema; volver a empaquetar esos factores no recupera la información perdida. La variante exacta upstream debe quedar fijada por repositorio, revisión y hashes. Fuentes oficiales: https://github.com/openai/gpt-oss y https://github.com/openai/gpt-oss/blob/main/README.md.

2. **Transcripción / Whisper Turbo.** Los metadatos indican factorización SVD de rango 29 y `quality_equivalence=NOT_ESTABLISHED`. El test correcto es transcribir audio conocido y comparar palabras/segmentos esperados; salida no vacía o un proceso con código 0 no basta. La documentación oficial distingue claramente transcripción de traducción y advierte que `turbo` no está entrenado para la tarea de traducir voz no inglesa a inglés. Fuente oficial: https://github.com/openai/whisper.

3. **Traducción / SeamlessM4T v2 Large.** Los metadatos registran rango 4, 864 matrices factorizadas y `quality_equivalence=NOT_ESTABLISHED`. La tarea primitiva válida incluye texto-a-texto con códigos de idioma fuente y destino; cada prueba debe verificar idioma de destino, contenido semántico de un conjunto de casos y ausencia de texto degenerado. Fuentes oficiales: https://github.com/facebookresearch/seamless_communication y https://github.com/facebookresearch/seamless_communication/blob/main/docs/m4t/README.md.

4. **Inteligencia documental / Granite Docling 258M.** La tarjeta oficial lo describe como un modelo multimodal imagen-texto-a-texto integrado con Docling, con salida de estructura documental/DocTags. La prueba debe usar la ruta de inferencia oficial compatible y verificar la extracción del campo objetivo, no dar por buena una cadena de salida arbitraria. Fuente oficial: https://huggingface.co/ibm-granite/granite-docling-258M.

5. **Análisis avanzado / Qwen3.** La configuración empaquetada tiene `hidden_size=5120`, `intermediate_size=17408`, 40 capas, 40 cabezas de atención y `tie_word_embeddings=false`, que corresponden a `Qwen/Qwen3-14B`; se fijó el repositorio oficial y la revisión del checkpoint `40c069824f4251a91eefaf281ebe4c544efd3e18`. Se corrigió el gate que comparaba erróneamente esta configuración con Qwen3-0.6B. Esa reparación elimina un falso bloqueo de identidad, pero no certifica inferencia: los pesos candidatos son factores SVD de rango 12, `quality_equivalence=NOT_ESTABLISHED`, y la prueba de respuesta conocida sigue fallando. La inferencia correcta debe mantener modelo, tokenizer y generación ligados a la misma revisión oficial. Fuentes oficiales: https://huggingface.co/Qwen/Qwen3-14B/blob/40c069824f4251a91eefaf281ebe4c544efd3e18/config.json, https://github.com/QwenLM/Qwen3 y https://github.com/QwenLM/Qwen3/blob/main/docs/source/inference/transformers.md.

## Defecto de gobernanza encontrado

`tools/cajita_task_e2e.py` se define a sí mismo como un harness sintético, declara `PASS_SYNTHETIC_END_TO_END_EXECUTION_ONLY`, `semantic_quality_equivalence=NOT_ESTABLISHED` y `all_21_target_adapters=NOT_ESTABLISHED`. El workflow de fábrica, sin embargo, convierte el código de salida cero de ese harness en `PASS_FOR_DECLARED_SYNTHETIC_FUNCTIONAL_E2E_SCOPE` para su señal de puerta G24. Ese resultado solo demuestra el alcance sintético declarado y no debe habilitar una aprobación integral.

Se añade `tools/louksnapg_integral_gate.py` para exigir evidencia real, ligada al commit y al SHA-256 exactos del paquete; los 21 identificadores de destino sin omisiones ni duplicados; comportamiento funcional observado; procedencia upstream fijada para los cinco destinos basados en modelos; matriz de hosts; rollback; vínculos de axiomas y bloques; y G23 verificado criptográficamente para el mismo sujeto. No requiere igualdad de calidad con un modelo de referencia sin cuantizar: exige que cada componente cumpla su función primitiva con pruebas conductuales pertinentes.

La suite unitaria del gate utiliza fixtures sintéticos únicamente para probar el propio validador. Esos fixtures nunca son evidencia del producto. El flujo debe tratar el informe sintético actual como `HOLD`.

## Reparación material necesaria antes de la certificación integral

- Recuperar los tensores upstream exactos desde las fuentes oficiales **solo cuando se autorice expresamente y se habilite almacenamiento/ejecución para el tamaño real**; en esta intervención no se descargarán esos pesos.
- Rehacer la compresión sobre los tensores fuente con cuantización calibrada y validación de reconstrucción; el repaquetado de factores de rango muy bajo no recupera señal.
- Conservar checkpoints y SHA-256 de entrada/salida, tokenizer, configuración, código de inferencia y métricas por modelo. No cambiar silenciosamente las identidades de los motores.
- Ejecutar pruebas de tarea con audio, documentos e instrucciones deterministas; rechazar texto degenerado y comprobar los resultados; registrar la huella de cada entrada/salida y la revisión upstream.
- Completar las 21 funciones de destino, G23 independiente, G24 separado, matriz de host, rollback probado y no-regresión. Si falta un requisito, el estado es `HOLD`, no certificación.

## Cadena de evidencia en esta rama

`SOURCE → INPUT_HASHES → CUSTOSZ_V9_BOUNDED_ACTION → REAL_FUNCTIONAL_EVIDENCE → INDEPENDENT_G23 → KESTRA_AUDIT → G24`.

El trabajador de construcción no certifica su propia salida. Kestra puede auditar el sobre de evidencia y fallar cerrado, pero no suplanta la inferencia real, la validación independiente ni el firmante G24. No se ejecuta Remote Commander.
