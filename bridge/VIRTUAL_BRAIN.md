# Cerebro virtual 120B — incorporación aditiva y sustituible

Estado: CANDIDATE_UNCERTIFIED. Se conserva Louksna.md como autoridad; el modelo es un asesor, no Maestro, G23, G24 ni ejecutor root.

## Comprobación técnica
La inferencia puede ejecutarse en un proveedor externo, mientras LOUKSNA conserva de forma local una interfaz única de acceso, orquestación, memoria, procedencia y controles. No se descargan pesos. El servicio remoto es dependencia opcional y NO equivale a tener el modelo físicamente dentro del equipo. El código de este candidato usa llamadas OpenAI-compatible Chat Completions a las URLs exactas de Groq o Hugging Face.

## Adaptador
- `bridge/virtual_brain.py`: interfaz Python `VirtualBrain.infer`, estado y CLI; `bridge/VIRTUAL_BRAIN.json`: modelos, proveedores y controles de egress/coste explícitos. El estado solo describe credenciales presentes, nunca revela su contenido.
- Modelo compartido lógico: `openai/gpt-oss-120b`; proveedores permitidos `groq` o `huggingface`. Sin failover silencioso, ejecución root, ingesta de documentos o acceso al escritorio.
- Precondiciones para un prompt real: consentimiento explícito de transferencia externa, clave de proveedor exclusivamente como variable de entorno `GROQ_API_KEY` o `HF_TOKEN`. Hugging Face requiere aceptación adicional de posibles cargos. El plan gratuito de Groq tiene límites variables: puede devolver 429.
- Límites iniciales: prompt hasta 16 KiB, salida hasta 1024 tokens, timeout de 20 segundos y respuesta hasta 512 KiB. Respuesta no validada como verdad ni certificación.
- Sin servidores de inferencia ni pesos en GitHub. No se asigna al núcleo portátil de 479.000.000 bytes. No hay coste generado durante pruebas simuladas.
- `python3 -B bridge/virtual_brain.py status` informa preparación. Una invocación de inferencia solo se prueba en vivo tras configurar una credencial autorizada y consentir el texto enviado: `printf 'prueba sin secretos' | python3 -B bridge/virtual_brain.py infer --provider groq --allow-outbound-model-data`.
- Esta variante es una interfaz para conectar al planificador/servicio persistente existente en un cambio adicional sujeto a controles G23/G24. Esta publicación NO lo conecta automáticamente ni valida disponibilidad externa real.

## Condiciones antes de producción
Verificar conectividad real, cuota/coste, seguridad de secretos, privacidad de los prompts, latencia y errores, revisar por CUSTOSZ V7, obtener decisiones G23/G24 aplicables e integrar como capacidad explícitamente autorizada del gestor gobernado. Si el proveedor falla o no hay red, retener el estado de la misión y usar solo alternativas ya autorizadas. El control remoto y la observación visual siguen siendo líneas independientes.
