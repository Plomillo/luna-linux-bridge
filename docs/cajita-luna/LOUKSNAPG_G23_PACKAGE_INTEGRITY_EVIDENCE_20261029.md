# LOUKSNAPG — G23 de integridad de distribución (alcance limitado)

- Workflow: [Cajita V9 materialization and Louksna1 governed factory #40792192212](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40792192212).
- SHA exacto de origen: `4d67ec3d9b1163ee39f1ffbd59de5502cd0c3fa2`.
- Artefacto que G23 revisó: `LOUKSNAPG.md`, SHA-256 `0d61c5867daf85e98bf32f252e1996964f47a1d589c27f9705e7f59979a1e16a`.
- Evidencia G23: artifact ID `12862003405`, SHA-256 ZIP `add89da5395b936a024745c740536fd269ae967fc4548648af29898ed2f5461a`.
- Estado: `PASS_DISTRIBUTION_INTEGRITY_SCOPE_ONLY`.
- Certificación integral: `NOT_GRANTED`.

La comprobación independiente sobre un runner hospedado volvió a calcular hashes y tamaños del contenedor, el documento Louksna1, el runtime, los seis paquetes de pesos, los registros de módulos y la reconstrucción de recursos externalizados. Resultados: `package_sha256=a216fe1dc4ff011f1c87453cafdedc4fb3933fc7a131d8f05bf3ad2c87d40e05`, `package_bytes=370889830`, `louksna1_sha256=f64e6925ff6a22b009fe592da3eda5c373ec788127a5b2dc9b824548bdf1e798`, `louksna1_bytes=11651408`, `combined_bytes=382541238`, tope combinado 490.000.000 bytes. Los cinco objetivos basados en modelos conservan sus hashes registrados; el estado `weights_manifest_valid=PASS` y `size_gate=PASS`.

Esta prueba sólo valida integridad de distribución, estructura, identidad de pesos y los smoke tests registrados en su alcance. El propio sobre G23 dice que los 21 adaptadores consumidores y la equivalencia de calidad semántica no están establecidos; el registro de módulos y rutas es declarativo. Por ello no puede elevarse a una certificación integral de los cinco dominios.

El job G24 bajo 1 CPU y 1 GiB estaba ejecutándose al registrar esta evidencia. Su resultado se documentará aparte. La certificación global permanece `NOT_GRANTED`.
