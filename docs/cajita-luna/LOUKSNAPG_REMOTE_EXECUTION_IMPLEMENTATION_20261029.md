# LOUKSNAPG — ejecución remota verificable de modelos (candidata)

**Estado:** implementación candidata; certificación global NOT_GRANTED.  
**Rama de trabajo:** louksnapg/remote-source-bound-runtime-20261029.  
**Objetivo:** ejecutar en un host GPU remoto los modelos originales fijados por revisión, manteniendo el artefacto distribuido compacto y verificando identidad, integridad y procedencia antes de aceptar resultados.

## Qué se incorporó

- cajita-luna-runtime/CAJITA_REMOTE_MODEL_POLICY.json fija IDs y revisiones inmutables de GPT-OSS-120B, Whisper large-v3-turbo, Seamless-M4T-v2-large y Qwen3-14B, junto con hashes de configuración/índice y los hashes de fragmentos que constaban en la evidencia del repositorio.
- cajita-luna-runtime/cajita_remote_execution.py implementa cliente HTTP con TLS obligatorio fuera de loopback, límites de tamaño/tiempo, HMAC-SHA256 de identidad, solicitud y respuesta, verificación de revisión/modelo, huella del inventario de pesos y evidencia de cada tarea. No registra entradas, audio, claves ni resultados completos en sus metadatos de evidencia.
- tools/louksnapg_remote_model_gateway.py es el gateway de host remoto: descarga la revisión exacta, comprueba config.json, el índice y cada fragmento de pesos contra la política, genera huellas completas y sirve una identidad firmada. Requiere GPU por defecto y procesa las solicitudes de forma secuencial para no multiplicar consumo de memoria/GPU.
- cajita_task_adapters.py tiene un modo de ejecución explícito LOUKSNAPG_REMOTE_MODE=required. Si el endpoint no existe, la identidad no coincide o falla una solicitud, la operación se cierra en error; no vuelve silenciosamente a los pesos compactos locales.
- tests/test_cajita_remote_execution.py prueba el protocolo HTTP con un servidor ficticio: identidad firmada, integridad HMAC, desajuste de revisión, clave incorrecta, respuesta manipulada, ausencia de endpoint y ausencia de fallback local.
- .github/workflows/louksnapg-remote-model-verification.yml ejecuta las comprobaciones del protocolo en GitHub Actions con un hilo y un límite de 1 GiB para el proceso de pruebas. No descarga pesos originales ni ejecuta inferencia de modelos.
- integrations/kestra/flows/25-louksnapg-remote-model-verification.yml proporciona monitorización de solo lectura de las ejecuciones de esa comprobación. No modifica Git, no despacha trabajos y no certifica.

## Identidades fuente registradas

| Dominio | Modelo | Revisión de origen | Comprobación fuente |
|---|---|---|---|
| D01_CEREBRO | openai/gpt-oss-120b | 3a173e3b55594eca0759580385b09870b99aa54a | SHA-256 de configuración e índice; 15 fragmentos fijados por ruta y tamaño; el gateway calcula las huellas de cada fragmento descargado. |
| D03_TRANSCRIPCION | openai/whisper-large-v3-turbo | 7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7 | SHA-256 del modelo original y de configuración fijados. |
| D04_TRADUCTOR_INTELIGENTE | facebook/seamless-m4t-v2-large | dff1eae6b5ed4de138247d6d6c5a37ef6ae20d46 | SHA-256 de configuración, índice y ambos fragmentos fijados. |
| D06_SISTEMA_INTELIGENTE | Qwen/Qwen3-14B | 40c069824f4251a91eefaf281ebe4c544efd3e18 | SHA-256 de configuración, índice y ocho fragmentos fijados. |

Antes de habilitar la ejecución en producción, el gateway compara esos valores contra el contenido que materializa desde la revisión inmutable. Un desacuerdo detiene el inicio; la configuración no se corrige automáticamente.

## Despliegue remoto requerido

El gateway se debe ejecutar **en un host de inferencia con GPU**, no en el PC LOUKSNA. Instala el build de PyTorch apropiado para el hardware y después las dependencias fijadas:

    python -m pip install -r tools/requirements-louksnapg-remote-gateway.txt

La instalación de PyTorch se deja separada intencionalmente para evitar instalar accidentalmente una distribución CPU-only que no pueda atender el modelo. El host debe tener disco y VRAM suficientes para el modelo asignado; el gateway de Cerebro necesita el modelo completo de aproximadamente 65 GB, aparte del espacio temporal y de runtime.

Genera una clave aleatoria de 32 bytes **en el entorno de secretos**, y configura el mismo valor HEX de 64 caracteres en el gateway de ese dominio y en el entorno de ejecución de Cajita. Utiliza una clave distinta para cada dominio. No guardes las claves en Git, artefactos CI, argumentos de la línea de comandos ni logs.

Ejemplo de variables del gateway, usando un gestor de secretos:

    LOUKSNAPG_GATEWAY_KEY_HEX=<secreto HEX de 64 caracteres>
    LOUKSNAPG_GATEWAY_KEY_ID=louksnapg-v1:D06_SISTEMA_INTELIGENTE
    LOUKSNAPG_GATEWAY_SOURCE_COMMIT=<commit Git completo de 40 caracteres que contiene este gateway>
    LOUKSNAPG_GATEWAY_CACHE=/var/lib/louksnapg/models

Luego ejecuta un proceso por dominio desde el checkout aprobado del repositorio; por ejemplo:

    python tools/louksnapg_remote_model_gateway.py \
      --domain-id D06_SISTEMA_INTELIGENTE \
      --bind 127.0.0.1 --port 8765

El listener está limitado a loopback por defecto. La publicación remota requiere un proxy de ingreso con TLS, autenticación de red y límite de acceso; no expongas el listener HTTP directamente a Internet. El LOUKSNAPG_GATEWAY_SOURCE_COMMIT debe ser un SHA de commit real y completo. El gateway no comienza la descarga del modelo si falta el SHA o si el preflight GPU falla. La opción --allow-cpu exige además LOUKSNAPG_GATEWAY_ALLOW_CPU=1 y está reservada a pruebas explícitas de un host remoto, nunca al PC LOUKSNA.

En el entorno que ejecuta el runtime, configura por dominio el endpoint HTTPS y su secreto en variables de entorno: LOUKSNAPG_REMOTE_CEREBRO_URL / LOUKSNAPG_REMOTE_CEREBRO_KEY_HEX, LOUKSNAPG_REMOTE_TRANSCRIPTION_URL / LOUKSNAPG_REMOTE_TRANSCRIPTION_KEY_HEX, LOUKSNAPG_REMOTE_TRANSLATION_URL / LOUKSNAPG_REMOTE_TRANSLATION_KEY_HEX y LOUKSNAPG_REMOTE_ANALYSIS_URL / LOUKSNAPG_REMOTE_ANALYSIS_KEY_HEX. Activa LOUKSNAPG_REMOTE_MODE=required solo después de desplegar y comprobar los endpoints correspondientes. Para Whisper, ese modo transmite el archivo de audio al host remoto por HTTPS; no se activa por defecto.

## Interpretación de pruebas y estado de dominio

El test de protocolo usa respuestas ficticias y demuestra el contrato de transporte y la política fail-closed, **no** que el modelo genere una respuesta correcta. La comprobación de política del gateway tampoco descarga pesos ni ejecuta inferencia. El gateway solo declara identidad una vez que ha verificado los archivos de origen y cargado el modelo en ese host.

La política incluye cuatro endpoints para modelos de referencia. La traducción de lenguas antiguas sigue bloqueada: no hay un transductor/léxico operacional ni un adaptador consumidor con identidad fuente demostrada. No se dirige esa operación al traductor general.

**No se ha ejecutado todavía inferencia real a través de un endpoint de GPU remoto ni se ha verificado la calidad semántica de la salida remota.** El PC permanece sin inferencia, descarga de modelos ni escrituras de runtime. La certificación de dominio y la certificación integral continúan pendientes hasta que haya un endpoint remoto configurado, el protocolo se pruebe contra los modelos cargados y pasen las tareas semánticas conocidas sobre el artefacto candidato exacto.
