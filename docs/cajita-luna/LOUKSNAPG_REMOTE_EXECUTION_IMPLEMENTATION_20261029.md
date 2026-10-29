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


---

## Addendum de trazabilidad — checkpoint 2026-10-29

**Rama revisada:** louksnapg/remote-source-bound-runtime-20261029.  
**Estado integral vigente:** HOLD_NOT_CERTIFIED.  
**No hubo ejecución de inferencia a través de los gateways remotos.**

### Evidencia remota comprobada

- Protocolo, identidad de origen y gobierno Kestra: workflow [40811146272](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40811146272), conclusión success. El log registra 10 pruebas aprobadas, auditoría de fuentes PASS_SOURCE_METADATA, ALL_PINNED y validación estática de Kestra aprobada.
- Preflight del banco semántico: workflow [40811146709](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40811146709), la fase sin inferencia concluyó con éxito; pasó PASS_ROUTE_PREFLIGHT_ONLY y 8 pruebas unitarias. La tarea viva posterior terminó antes de instalar dependencias.
- Artefacto de preflight: [12870630672](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40811146709/artifacts/12870630672), SHA-256 del ZIP 223c63e410f40ac8ab54ab990d6260497d37ee56ee3033d4d1777e54dcdace66.
- Informe de bloqueo de configuración: artefacto [12870392250](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40811146709/artifacts/12870392250), SHA-256 del ZIP 272e8d46b6fe0182dd260b8fcd106cbbc938c9023e7e8e24cd436d7c998f2975. Faltaban los ocho nombres de variables esperados: URL y clave HMAC para Cerebro, Whisper, traducción y análisis. El informe no incluye valores secretos. dependencies_installed=false, model_inference_executed=false y remote_endpoint_contacted=false.
- La política actual fija las cuatro revisiones, los hashes de configuración/índice y todos los hashes de pesos; el trust binding actualizado del gateway es 77bc2fcdbf4054c9d108f8fcb18d1f097be757a3 / 43888da74ca8efd6110274e57ff7f0d6824775ce27e81533f87adc35752b2d64. La prueba de protocolo valida esta identidad y no ejecuta modelos.

### Decisión G23/G24 del candidato anterior

El candidato de la ejecución de fábrica [40810168715](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40810168715), producido desde el commit anterior 885baff3999833ff2ddb28fa683042b0327776bf, superó fabricación y G23 independiente. La decisión G24 fue NOT_GRANTED: 5 de 5 tareas se ejecutaron, pero 0 de 5 cumplieron la aceptación semántica; las seis pruebas de arranque/forward de motores pasaron solo en el alcance declarado. Los resultados representativos fueron texto degenerado para Cerebro, Whisper y Seamless, y respuesta incorrecta de Qwen. La traducción antigua sigue BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE, sin fallback al traductor general.

Datos del candidato de esa revisión, no de la nueva fabricación en curso:
- LOUKSNAPG.md: 371.957.072 bytes; SHA-256 c104a005f4afdf3762ff51799f883ccbbbe9b3159b7cd028f81c97921fe3e9d1.
- Runtime .macrodown: 370.898.737 bytes.
- G23 evidence ZIP ID 12869793710, SHA-256 33edb6a386269f31adb75efd6d0f71ea5d5e7626f4c830774ae0143410aa0b00.
- G24 evidence ZIP ID 12869864752, SHA-256 c637e9e672bd116e77934118e334aa9e74232c8ce24b929ce10ceaf4b1c77818.
- G24 telemetry ZIP ID 12870073790, SHA-256 14c7aef59656b29b0c88c335b6abb072b78dd8301f09547e6f657ac0f13dd47d.

### Construcción actual, equipo local y límites

Se corrigió .github/workflows/cajita-louksna1-factory.yml para que cambios en CAJITA_REMOTE_MODEL_POLICY.json, cajita_remote_execution.py, el gateway y el auditor de fuentes disparen una nueva fabricación. Workflow [40811334086](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40811334086) está fabricando el candidato desde el HEAD actualizado; hasta su finalización no se declara hash ni G23/G24 para esa nueva versión.

La PC LOUKSNA no se utilizó para inferencia, descarga de pesos ni modificaciones del runtime. Su checkout local sigue en otra rama y contiene cambios previos ajenos a este trabajo; no se hizo checkout, reset ni limpieza. Kestra está activo como servicio, pero su API local no respondió, por lo que se validó el flujo de monitorización en GitHub Actions; no se afirma que Kestra haya orquestado en vivo la reparación.

**Bloqueadores de certificación actuales:** configuración ausente para los cuatro endpoints remotos; fallo semántico 0/5 del candidato empaquetado anterior; recurso/adaptador de traducción antigua no disponible; nueva fabricación pendiente de G23/G24. No se concedió certificación ni se publicó el candidato fallido.
