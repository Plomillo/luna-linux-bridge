# LOUKSNAPG — rechazo del perfil adaptativo Whisper R192 V2

- Ejecución: [GitHub Actions #40792606343](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40792606343).
- Evidencia: artifact ID `12862337742`; SHA-256 ZIP `d75a02596e72aead95efddd179817ecf00b1343a25938d774210d82b8219d730`.
- Commit exacto probado: `ab311582b6f5902bf42bfed9170908f8ca28060e`.
- Perfil: `WHISPER_ADAPTIVE_R192_DECODER128_ENCODER_FFN192_OUTPROJ128_V96_OTHERATTN64_FC1_32_EMBED96_BASE16_V2`.
- Decisión: `REJECT_CANDIDATE`; promoción omitida.

## Resultados confirmados

| Métrica | Resultado |
|---|---:|
| Pesos INT8 | 108.556.864 bytes |
| Módulo físico con descriptor | 111.149.511 bytes |
| Tope del módulo experimental | 125.000.000 bytes |
| Error Frobenius relativo agregado | 0,688145008983582 |
| Proyección global conservadora | 471.104.698 / 479.000.000 bytes |
| Audio sintético “hello world” | FALLA; salida sólo de puntuación |
| LibriSpeech `1272-128104-0000` | FALLA; WER 1,0 (límite 0,25) |
| Pico RSS del proceso constructor en runner | 2.211.532.800 bytes |
| Certificación / promoción | NOT_GRANTED / NO |

La fuente `openai/whisper-large-v3-turbo@7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7` mantiene el SHA-256 comprobado `542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1`. La misma fuente pasa el audio conocido y la muestra real con la misma política de decodificación; por tanto, el fixture no es la causa.

## Evaluación de V1 → V2

La V1 asignaba rango 192 a encoder `fc2`, 64 a atención encoder, 128 al decoder y 16 como base. Sus peores reconstrucciones estaban en `encoder.self_attn.out_proj` y `v_proj`, pero su error agregado era 0,6826945 y devolvió sólo puntuación.

La V2 incrementó esos mapas de atención: `out_proj=128`, `v_proj=96`, otras matrices de atención 64, `encoder.fc2=192`, redujo `encoder.fc1=32`, decoder 128 y token embedding 96. Sin embargo, el error agregado empeoró a 0,6881450 y las peores matrices pasaron a las capas `encoder.fc1` (errores relativos ~0,93–0,96). La transcripción siguió devolviendo `,,,...,,` para ambos audios y WER 1,0.

**Conclusión operativa:** detener los barridos uniformes y adaptativos de rango bajo como solución a Whisper. Tres aumentos uniformes (29/64/96) y dos perfiles adaptativos R192 fallaron los mismos criterios semánticos mientras consumían progresivamente más espacio. No hay evidencia de que más iteraciones de reasignación de estos mismos factores restauren la transcripción; no se continuará gastando margen de distribución sin una hipótesis distinta y medible.

## Próximo paso autorizado y limitado

Antes de tocar otra vez los pesos, realizar análisis estático y un experimento acotado sobre la reconstrucción de la capa de salida/tensores concretos sólo si puede formularse y verificarse una hipótesis técnica nueva. Toda prueba posterior debe usar el mismo checkpoint oficial, fijar de forma reproducible los factores por SHA, comprobar los mismos dos audios, y medir el paquete combinado real. Una fuente distinta como whisper-tiny no debe sustituir automáticamente la identidad large-v3-turbo.

No se modificó el runtime canónico: `canonical_runtime_mutated=false`. La inferencia pesada fue exclusivamente en runner hospedado con un hilo; no hubo inferencia ni descarga local de modelos. La proyección de 471.104.698 bytes no es la medición exacta del paquete final. G23/G24 son puertas independientes, no conceden por sí solas certificación funcional; estado global `NOT_GRANTED`.
