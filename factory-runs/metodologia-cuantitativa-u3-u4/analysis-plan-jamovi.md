# Plan de análisis en Jamovi — Entrega 4

Este protocolo se ejecuta después de incorporar la base real y depurada de Entrega 3. La plantilla actual no tiene filas de participantes y no produce resultados.

1. Abrir Jamovi e importar datos_participantes.csv o la hoja Participantes del XLSX de Entrega 3. No importar por error la hoja Diccionario ni Ensayos_CAM cuando el análisis se realice a nivel de participante.
2. Verificar los niveles de medición: condición = nominal; semestre = ordinal; edad, responsabilidad, tiempos y porcentajes = continuos; ítems BFI-2-S = ordinales.
3. Ir a **Analyses → Exploration → Descriptives**. Seleccionar N, Missing, Mean, Median, SD, Minimum y Maximum para variables continuas. Para variables categóricas activar Frequency tables y Bar plot.
4. Añadir condición a **Split by** y generar descriptivos por grupo para responsabilidad_media, cam_error_total_pct y cam_rt_total_ms.
5. Generar histograma o caja para tiempos y errores. Para condición, usar gráfico de barras de frecuencias. Guardar/exportar las salidas directamente desde Jamovi.
6. Mantener por separado resultados generales y resultados separados por tamaño de conjunto (8, 16, 32). No combinar error y tiempo en una sola puntuación.
7. Reportar N válido y faltantes de cada variable. Explicar de manera explícita cualquier exclusión y conservar una copia inalterada de la base original.

**Lectura de hipótesis:** H1 se describe comparando tendencia central y dispersión del error y tiempo entre condiciones. H2 se explora mediante distribuciones y gráficos de responsabilidad frente a rendimiento. H3 requiere una interacción condición × responsabilidad en un modelo apropiado; una tabla descriptiva, por sí sola, no prueba moderación ni significación estadística. No ejecutar ni presentar una prueba inferencial como requerida sin revisión y autorización docente.
