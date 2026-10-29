# LOUKSNAPG — rechazo del perfil adaptativo Whisper R192 V1

- Ejecución: [GitHub Actions #40792213949](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40792213949).
- Evidencia: artifact ID `12861434013`; SHA-256 ZIP `6e4a67fa917d99f2e0919c0adc614641d020f0bcf7c1b8a9470859a9a80ead56`.
- Código probado: `fed13c2195d0b64af44b1fae85e528ddd642d252`.
- Perfil: `WHISPER_ADAPTIVE_R192_DECODER128_ENCODER_FFN192_ATTN64_EMBED96_BASE16_V1`.
- Decisión: `REJECT_CANDIDATE`; no promoción.

## Resultados

| Métrica | Resultado |
|---|---:|
| Pesos | 107.229.544 bytes |
| Módulo con descriptor | 109.822.191 bytes |
| Error Frobenius agregado | 0,6826945306114637 |
| Proyección global conservadora | 469.777.378 / 479.000.000 bytes |
| Audio sintético conocido | FALLA; salida `,,,...,,` |
| LibriSpeech | FALLA; WER 1,0 (límite 0,25) |
| RSS pico en construcción hospedada | 2.210.463.744 bytes |
| Certificación/promoción | NOT_GRANTED / NO |

El peso de origen `openai/whisper-large-v3-turbo@7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7` conservó el SHA-256 fijado `542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1`. El Parquet y el WAV de LibriSpeech fueron los mismos ya validados. La referencia original pasó ambas pruebas.

## Qué aprendimos y corrección posterior

La V1 elevó `encoder.fc2` a rango 192 y el decoder a 128, pero bajó todas las proyecciones de atención del encoder a rango 64. La peor reconstrucción por matriz se concentró después en `model.encoder.layers.*.self_attn.out_proj.weight` y varias `v_proj.weight` (errores relativos entre ~0,939 y ~0,947). El error agregado empeoró frente a R96 uniforme (0,66338). El presupuesto sí se cumplió; la calidad no.

La V2 redistribuye el mismo presupuesto de forma dirigida: encoder `fc2=192`, `fc1=32`, `self_attn.out_proj=128`, `self_attn.v_proj=96`, resto de atención encoder 64, decoder 128, embedding 96 y rango base 16. La revisión se ejecuta como candidato separado, con el mismo corpus y las mismas pruebas. Si vuelve a fallar, se detendrá la factorización de bajo rango para Whisper: no se autoriza un reemplazo silencioso del modelo y no se seguirán aumentando rangos sin evidencia. El paquete completo debe medirse de forma exacta; la proyección actual no es una medición final de lanzamiento.
