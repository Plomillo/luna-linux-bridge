# Whisper-WebUI — integración de transcripción desde YouTube

## Estado de la integración

Whisper-WebUI está incorporado como submódulo Git en `vendor/whisper-webui`.

- **Repositorio upstream:** https://github.com/jhj0517/Whisper-WebUI
- **Rama upstream:** `master`
- **Commit fijado:** `c3bb3b18e959826b28b1192486a8d5b361b6a4e0`
- **Licencia upstream:** Apache-2.0
- **Motor ASR predeterminado:** faster-whisper
- **Entrada de YouTube:** pestaña YouTube de la interfaz.

El commit está fijado deliberadamente para que la integración sea reproducible y no cambie silenciosamente cuando avance el repositorio upstream.

## Qué hace

La aplicación ofrece una interfaz web donde se pega una URL de YouTube y se ejecuta la transcripción sobre el audio descargado. El código upstream implementa `transcribe_youtube()`, obtiene el audio a través de `pytubefix` y lo procesa con el pipeline Whisper. **La descarga de YouTube de esta versión utiliza pytubefix, no yt-dlp.** El motor predeterminado es faster-whisper.

Formatos de salida documentados: SRT, WebVTT y TXT. La biblioteca faster-whisper admite además marcas de tiempo por segmento y por palabra cuando se habilitan.

## Inicializar el submódulo

En un clon existente del repositorio:

```bash
git submodule update --init --recursive
```

Para clonar directamente esta rama incluyendo el proyecto:

```bash
git clone --branch feature/whisper-webui-youtube-transcription --recurse-submodules https://github.com/Plomillo/luna-linux-bridge.git
```

## Ejecución según la documentación upstream

Desde el directorio del submódulo, revisar primero el README y la configuración de Docker del proyecto:

```bash
cd vendor/whisper-webui
docker compose build
docker compose up
```

La documentación upstream estima una imagen Docker de aproximadamente 7 GB. La configuración predeterminada de instalación local está orientada a CUDA 12.8/NVIDIA; antes de desplegar en CPU, GPU distinta o un proveedor remoto hay que ajustar y validar la configuración de dependencias y recursos.

## Límite importante: incorporación no equivale a servicio publicado

Este cambio incorpora y fija el código fuente en el repositorio. **No deja por sí solo una interfaz web permanentemente alojada ni ejecuta transcripciones desde GitHub.** GitHub Pages sirve contenido estático y no puede ejecutar el modelo Whisper. Para pegar una URL y transcribir sin usar el PC, el siguiente paso operativo es desplegar este submódulo en un servicio remoto con CPU/GPU y almacenamiento temporal adecuados, o implementar un trabajo bajo demanda en GitHub Actions.

No se han añadido credenciales, claves de API ni cambios a la rama principal.
