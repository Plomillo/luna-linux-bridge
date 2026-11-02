# LOUKSNAPG2 — revisión operativa V4: reparación por motor

**Base:** `louksnapg2/puac2-alternative-20261029`, commit de referencia `23a4b49a9774265f43cdc8a6e5c088a9fd672d80`.
**Método:** extensión append-only de V3; no se altera V1/V2/V3 ni los pesos originales.
**Tope de distribución:** `490000000` bytes.
**Certificación global:** `NOT_GRANTED`.

## Actualización de evidencias

### Foma

Foma está materializado desde `foma-master.zip` y tiene un consumidor runtime dedicado. Las operaciones del consumidor pasan por `flookup` con un transductor binario registrado en `foma_transducers/manifest.json`, que exige ruta relativa, bytes y SHA-256. No se permite fallback general a GPT-OSS ni SeamlessM4T.

La nueva acción CUSTOSZ V9 debe compilar una copia temporal del código fuente con `make -j1 check` y ejecutar una prueba sintética `cat → dog`. Esa evidencia valida el motor de estados finitos y la herramienta, no un traductor de latín o griego. El manifiesto de recursos lingüísticos sigue sin transductores aprobados; por tanto, la traducción real de esas lenguas continúa en HOLD.

La actualización del descriptor de Foma requiere mantener sincronizados los SHA-256 en `module_registry.json` y `CAJITA_DISTRIBUTION_MODULE_REGISTRY.json`. La discrepancia detectada por la ejecución PUAC2 fue documental/integridad del módulo y queda corregida en esta revisión.

### Whisper large-v3-turbo

El experimento 41539943984 sí construyó candidatos full-rank GGML:
- Q4_0: 473.992.235 bytes; SHA-256 `6e670d7569d1ed261cb8a4e554138f0ba6a17be7c64f079145061f93bac54e80`.
- Q5_0: 574.041.195 bytes.

La evaluación no alcanzó inferencia: el proceso no encontró `fullrank_manifest.json` en la disposición extraída por GitHub Actions. Por tanto, no existe WER válido para Q4/Q5 en ese run.

Las proyecciones de paquete informadas por el generador son 836.570.159 bytes para Q4_0 y 936.619.119 bytes para Q5_0. Ambas superan 490.000.000 bytes. Q4/Q5 quedan fuera de promoción incluso antes de una futura evaluación semántica, salvo que otra arquitectura reduzca el tamaño total sin pérdida funcional.

La corrección de transporte prepara un directorio por candidato con el manifiesto en la raíz y usa un resolver con búsqueda acotada, rechazo de symlinks y exigencia de exactamente un manifiesto. La siguiente ejecución debe validar la lectura real del candidato y registrar WER, sin asumir que el fallo de ruta fue fallo del modelo.

### PUAC2 / CUSTOSZ V9

El autodiagnóstico de CUSTOSZ V9 dio PASS 12/12. La ejecución del trabajador no produjo candidato y quedó en `BLOCKED_NO_REPAIR_EXECUTED`; el log de salida anterior no exponía suficiente detalle de la acción interna. La revisión amplía la evidencia de salida con estado del coordinador, acciones completadas, resultado de cada acción y motivo de fallo.

El trabajador añade una acción bounded para compilar y probar Foma, pero no declara reparación de pesos. Las rutas de GPT-OSS, Whisper, SeamlessM4T, Docling y Qwen3 siguen sin recuperación semántica demostrada.

## Estado por motor

| Motor | Estado actual |
|---|---|
| Foma | Código fuente presente; consumidor conectado; build/smoke sujeto a nueva ejecución CUSTOSZ; sin transductores latinos/griegos |
| Granite Docling 258M | Q4 materializado; generación inválida; comparación FP16/Q4 pendiente |
| GPT-OSS-120B | Reconstrucción previa rank-1, error relativo 0,998336; no reparación aprobada |
| Whisper large-v3-turbo | Q4/Q5 construidos; evaluación sin WER por error de layout; ambos exceden proyección global |
| SeamlessM4T v2 large | Traducción degenerada; sin reparación aprobada |
| Qwen3-14B | Reconstrucción previa rank-12, error relativo aprox. 0,996409; no reparación aprobada |

## No-regresión y promoción

No se modifican los pesos originales ni se propaga certificación de las pruebas de compilación, hash, empaquetado o ejecución. Cada motor necesita su suite semántica independiente y el paquete exacto debe superar el límite total de 490.000.000 bytes. G23 y G24 permanecen separados. Promoción canónica y certificación global permanecen denegadas.
