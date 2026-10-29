# LOUKSNAPG — evidencia de fabricación e integridad del candidato

- Ejecución de fábrica: [GitHub Actions #40792192212](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40792192212).
- Commit de origen: `4d67ec3d9b1163ee39f1ffbd59de5502cd0c3fa2`.
- Trabajador de empaquetado: `CUSTOSZV9`, limitado a fabricación/verificación de paquete; no fue certificador independiente.
- Artefacto `louksna1-candidate`: artifact ID `12861793020`, tamaño ZIP `741,734,250` bytes, digest del ZIP `4f9a8d632226fb3a71e93134b272a9a471a1d8b6dd23c611beeacaa5f1c7077a`.
- Artefacto `louksna1-document`: artifact ID `12861174792`, tamaño ZIP `909,168` bytes, digest del ZIP `ea8ca357b3a9784b41b718f8a5a2ce4f661fa56de493d3a2e26f2ce33ff614eb`.
- Backup rollback de fuentes: artifact ID `12861653446`, ZIP `165,376,747` bytes, digest `a52ecf0fc784cfd878da7fea4e463031f02fc997dc9e4aee48bb69a7b0301fd3`.

## Medición exacta del contenedor construido

| Métrica | Evidencia |
|---|---:|
| Archivo runtime Cajita | 370.889.830 bytes |
| Documento Louksna1 | 11.651.408 bytes |
| Distribución combinada | 382.541.238 bytes |
| Límite combinado | 490.000.000 bytes |
| Árbol runtime sin compresión | 447.510.653 bytes |
| SHA-256 del runtime archive | `a216fe1dc4ff011f1c87453cafdedc4fb3933fc7a131d8f05bf3ad2c87d40e05` |
| SHA-256 del documento | `f64e6925ff6a22b009fe592da3eda5c373ec788127a5b2dc9b824548bdf1e798` |
| SHA-256 del `LOUKSNAPG.md` empaquetado | `0d61c5867daf85e98bf32f252e1996964f47a1d589c27f9705e7f59979a1e16a` |
| Límite de runtime Cajita | 470.000.000 bytes |
| Contenedor y miembros | PASS |
| Registro de módulos y rutas | Declaración PASS; no demuestra funcionalidad |
| Certificación global | `NOT_GRANTED` |

La fábrica informó `PASS_MANUFACTURED_CANDIDATE_PENDING_G23_G24`. La validación independiente del contenedor obtuvo `budget_status=PASS`, `container_integrity=PASS`, `runtime_member_integrity=PASS`, `single_distribution_container=PASS`, y preservación de identidad/prefijo protegida. Expresamente dejó `functional_status=NOT_ESTABLISHED_BY_CONTAINER_INTEGRITY_CHECK`, `module_registry=PASS_DECLARATION_ONLY`, `runtime_routing_registry=PASS_DECLARATION_ONLY`, y certificación global `NOT_GRANTED`.

## Alcance y no-regresión

La fabricación y la reconstrucción de los seis pesos pasaron los checks de tamaño/hash; también pasó el autocheck del helper CUSTOSZ V9. Esto demuestra integridad y distribución del candidato de origen `4d67ec3d...`, no el funcionamiento de los motores. El artefacto se generó antes del experimento adaptive R192 V2 y conserva los pesos de Whisper de la línea base; no se debe confundirlo con una candidata que incorpore una reparación funcional posterior.

La inspección local no descargó el ZIP de 741 MB ni cargó pesos. La verificación funcional y la validación independiente siguieron ejecutándose en runners hospedados. La certificación permanece detenida hasta que G23/G24 se vinculen a la versión exacta y se demuestre la calidad semántica de los cinco dominios y las 21 tareas consumidoras.
