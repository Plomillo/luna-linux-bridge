# LOUKSNAPG — estado verificado de GitHub, run 40309113060

**Decisión:** `HOLD_NOT_CERTIFIED`  
**Commit probado:** `5fab498b6faae08f59962861503b1a1202fcc83c`  
**Run de fábrica:** [40309113060](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40309113060)  
**Run del auditor auxiliar:** [40309113048](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40309113048)

Este informe es un snapshot histórico y comprobable de ese commit/run. No certifica commits posteriores.

## Artefacto y límites

El candidato `LOUKSNAPG.md` tiene 371.947.713 bytes y SHA-256 `3337c635d77d509e061768d573330345ff6673bafa8de828ad8b0bd3b1d52f7c`. Cabe bajo el límite integrado de 479.000.000 bytes por 107.052.287 bytes. El archivo runtime Cajita materializado tiene 370.889.623 bytes, SHA-256 `f6002bec4284265e74e680b3acf70954de74a3b7d5fb5cbd93bda4ba861981ec`, y cabe bajo el límite separado de 470.000.000 bytes por 99.110.377 bytes.

G23 pasó comprobaciones independientes de paquete, prefijo arquitectónico protegido, miembros del runtime, metadatos de identidad, hash y límites. El propio informe independiente marca el routing y el registro de módulos como `PASS_DECLARATION_ONLY`; ese resultado no acredita que las 21 tareas de usuario funcionen.

## Resultado funcional observado

| Target | Operación | Resultado de ejecución | Resultado semántico | Pico RSS |
|---|---|---:|---:|---:|
| `D01_CEREBRO_ROOT` | Generación de texto | Ejecuta, código 0 | **FAIL** — salida degenerada | 1.094.918.144 B |
| `D03_TRANSCRIPCION_ROOT` | Transcripción | Ejecuta, código 0 | **FAIL** — “daughterziest manuscript ele” | 756.387.840 B |
| `D04_TRADUCCION_GENERAL` | Traducción | Ejecuta, código 0 | **FAIL** — “te te te apres…” | 809.070.592 B |
| `D05_DOCLING` | Extracción documental | Ejecuta, código 0 | **FAIL** — no extrae el total esperado | 983.965.696 B |
| `D06_ANALISIS_AVANZADO` | Razonamiento | Ejecuta, código 0 | **FAIL** — no responde 4 | 692.490.240 B |

Cerebro excedió el límite de RSS de 1.073.741.824 bytes en **21.176.320 bytes**. En el conjunto de pruebas diagnósticas, el contador que distingue las capas muestra 5/5 ejecuciones con código cero, pero 0/5 resultados de calidad aprobados. Las comprobaciones usan fixtures sintéticos fijos: demuestran fallos de la versión probada, no equivalencia general con los modelos fuente.

El gate funcional detectó 34 motivos de bloqueo, incluidos `ALL_21_TARGET_FUNCTIONS_NOT_PASSED`, evidencia faltante de objetivos, ausencia de atestación G23 funcional, matriz de hosts incompleta, rollback funcional no acreditado y estado de calidad semántica no aprobado. Solo se registraron seis pruebas limitadas de motores de infraestructura con resultado PASS; no se deben contar como cobertura completa de consumidores.

Los metadatos aún registran pérdida extrema en compresión: GPT-OSS rango 1, error relativo Frobenius `0.9983363410727844`; Qwen3 rango 12, residual previo a INT8 `0.9964067735222465` y error agregado posterior `0.9964088220513415`. Con los pesos fuente pesados fuera de los límites de esta misión y sin evidencia de reconstrucción de los componentes descartados, estos factores no pueden certificarse como reparación funcional.

## Estado de los seis deberes obligatorios

1. **C1 — Trabajadores coordinados: HOLD.** CUSTOSZ V9 completó el trabajo acotado de construcción/emisión de evidencia; no consta una misión de reparación material de los cinco motores. Kestra no se ejecutó: la última auditoría emitió `NOT_CONFIGURED`, motivo `KESTRA_URL_OR_KESTRA_API_TOKEN_MISSING`, sin ID de ejecución.
2. **C2 — Reparación desde fuente oficial: HOLD.** Hay revisiones oficiales fijadas y el recuento de descargas de pesos grandes es cero; el recuento de reparaciones materiales verificadas es también cero. Fijar procedencia no repara los factores.
3. **C3 — Funciones primitivas: FAIL.** Los cinco tests de modelo ejecutaron, pero fallaron calidad; 21/21 objetivos no tienen evidencia funcional no sintética completa.
4. **C4 — Telemetría y auditoría: PASS_PARTIAL.** Los informes de G23/G24 y auditoría auxiliar están ligados al commit y a hashes del candidato, y se conservaron como artefactos de Actions. La telemetría de ejecución real de Kestra no existe porque no hubo despacho.
5. **C5 — Liberación gobernada: HOLD.** G23 integridad de distribución pasó; G23 funcional no está establecido; G24 no fue concedido; el job de publicación se saltó.
6. **C6 — Prohibiciones y recuperación: PASS para este run.** No se descargaron pesos pesados, no se utilizó Remote Commander, no se sustituyó silenciosamente el modelo, no se alteraron identidades canónicas y no se publicó el producto sin evidencia completa.

## Conclusión operativa

No hay un arreglo de decodificación demostrado por estos resultados que pueda recuperar la información de pesos perdida por la factorización de rango muy bajo. Maquillar los tests, aumentar el techo o sustituir los motores invalidaría el contrato. La ruta permitida exige reparar cada candidato con activos de peso permitidos y verificables, registrar hashes antes/después, volver a pasar pruebas de tarea reales, obtener una ejecución real de Kestra, terminar G23 funcional independiente y conseguir una decisión G24 firmada y separada. Hasta entonces, la decisión permanece `HOLD_NOT_CERTIFIED`.

El detalle máquina-legible está en `LOUKSNAPG_INTEGRAL_REPAIR_BLOCKERS_20261026_RUN40309113060.json`.
