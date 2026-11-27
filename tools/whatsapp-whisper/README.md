# WhatsApp + Whisper large-v3-turbo

Pipeline reproducible para reconstruir una exportación de WhatsApp y transcribir notas de voz localmente con faster-whisper y el modelo `large-v3-turbo`.

## Privacidad

Este repositorio es público. No subas el ZIP, el TXT original, audios, transcripciones ni códigos de verificación. Los resultados se generan en `.local/`, excluida de Git. Para compartir resultados, prepara primero una copia revisada y anonimizada; no publiques datos de terceros ni credenciales.

## Requisitos e instalación

- Python 3.10–3.12.
- FFmpeg disponible en PATH (para OPUS/OGG y otros formatos).
- GPU NVIDIA/CUDA recomendada; CPU admitida, pero puede ser lenta.

```bash
cd tools/whatsapp-whisper
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
ffmpeg -version
```

## Ejecución

Desde la raíz del repositorio:

```bash
python tools/whatsapp-whisper/transcribe.py --zip /ruta/exportacion.zip --output .local/whatsapp-analysis --model large-v3-turbo --language es
```

El programa crea `conversation.md`, `audio_transcripts/` con TXT y JSON segmentado por tiempos, y `manifest.json` con hashes, parámetros y estado por audio. El modelo se descarga en la primera ejecución.

## Pruebas

Las pruebas del parser no requieren descargar Whisper ni instalar FFmpeg:

```bash
python -m unittest discover -s tools/whatsapp-whisper/tests -v
```

GitHub Actions ejecuta estas pruebas al modificar el pipeline o sus pruebas.

## Límites y auditoría

- Modelo declarado: Whisper `large-v3-turbo` mediante faster-whisper; no se afirma que se haya ejecutado hasta que el pipeline termine y el manifiesto registre cada audio.
- Whisper no identifica de forma fiable a los interlocutores. La etiqueta de emisor procede del mensaje de WhatsApp, no de diarización acústica.
- Los audios fallidos quedan registrados y no se sustituyen por transcripciones inventadas.
- Revisar nombres propios, ruido, solapamientos y modismos.
- El script procesa localmente y no envía el ZIP a GitHub ni a un servicio externo.
- No publicar resultados privados sin consentimiento y revisión de datos personales.
