---
title: "Entrega 4 — Análisis y presentación de resultados"
subtitle: "Planificación previa, atención selectiva y responsabilidad"
author: "Valeria Galaz; Diego Norambuena; Paula Pizarro; Joel Quezada"
date: "Santiago de Chile, noviembre de 2026"
lang: es
---

<!-- BODY_START -->

**Estado: estructura analítica preparada; resultados empíricos pendientes de la base real de Entrega 3.** Los archivos recibidos no contienen observaciones de participantes ni una salida de Jamovi. En consecuencia, las tablas que siguen son matrices de reporte y no resultados. No se asignan tamaños muestrales, medias, porcentajes, gráficos ni valores estadísticos ficticios.

## 1. Objetivo y continuidad de las hipótesis

El análisis continúa el marco teórico de octubre de 2026 y el protocolo de Entrega 3. Se examina si una planificación previa de cinco minutos se relaciona con el rendimiento en una tarea de atención selectiva, considerando la responsabilidad como rasgo medido. La condición experimental se codifica 0 = control activo y 1 = planificación. La responsabilidad se calcula con los seis ítems de dominio del BFI-2-S español: 4, 9, 11, 17R, 23R y 25R, recodificando los inversos antes de obtener el promedio.

Se conservan las hipótesis refinadas: **H1**, el grupo de planificación presentaría descriptivamente menos errores y/o menor tiempo de respuesta que el control; **H2**, una puntuación más alta de responsabilidad presentaría un patrón descriptivo asociado a mayor exactitud y/o menor tiempo de respuesta; **H3**, la diferencia entre condiciones podría variar según responsabilidad. H3 es una hipótesis de moderación y no puede declararse demostrada solo a partir de tablas descriptivas.

## 2. Preparación y validación de la base

La unidad de análisis es cada participante. La hoja Participantes debe contener una fila por código anónimo y la hoja Ensayos_CAM una fila por ensayo. Antes de abrir Jamovi se verifica: (a) que cada código sea único; (b) que todos los participantes incluidos tengan consentimiento registrado en un archivo separado; (c) que la condición sea 0 o 1; (d) que los 30 ítems BFI-2-S estén dentro del rango 1–5; (e) que los tiempos de respuesta estén en milisegundos positivos; (f) que los porcentajes de error estén entre 0 y 100; y (g) que las incidencias, abandonos y ensayos faltantes estén documentados.

Los ítems inversos de responsabilidad se recodifican como seis menos la respuesta original. El promedio del dominio se calcula solo cuando están disponibles los seis ítems puntuables. No se imputan respuestas faltantes de manera automática. Para la tarea CAM se conservan por separado tiempo medio de respuestas correctas y tasa de error: una respuesta más rápida acompañada de más errores puede reflejar un intercambio velocidad-exactitud, no necesariamente mejor atención. Se presentan también los indicadores por conjuntos de 8, 16 y 32 estímulos, cuando el registro original lo permita.

No se borran casos ni ensayos por conveniencia. Los tiempos extremos, respuestas constantes, fallos de carga y finalizaciones incompletas se revisan frente al protocolo y se informa cuántos registros se excluyeron y por qué. Los criterios exactos de depuración deben coincidir con la implementación CAM efectivamente utilizada y quedar fijados antes de examinar diferencias entre condiciones. La investigación CAM de referencia informó incidencias técnicas y pérdidas de datos en su tarea de atención selectiva, lo que justifica hacer visible este control (Pinelli et al., 2025).

## 3. Procedimiento en Jamovi

Abrir el XLSX de Entrega 3 o el CSV depurado. En la vista de datos, definir condición como nominal; semestre como ordinal; edad, responsabilidad_media, tiempos y porcentajes como continuos; e ítems BFI-2-S como ordinales. Confirmar que los códigos de valores faltantes no se hayan importado como ceros.

En **Analyses → Exploration → Descriptives**, mover a Variables las medidas que se van a resumir. Para variables categóricas, activar tablas de frecuencia y gráfico de barras. Para medidas continuas, seleccionar N, datos perdidos, media, mediana, desviación estándar, mínimo y máximo; añadir histograma o diagrama de caja cuando resulte pertinente. Situar condición en **Split by** para obtener resultados separados por grupo. Guardar las tablas y gráficos generados por Jamovi sin reconstruirlos manualmente (jamovi, s. f.).

## 4. Tablas y gráficos que deben completarse

**Tabla 1. Flujo y descripción de la muestra.** Informar número reclutado, consentimientos, participantes que completaron cada fase, registros excluidos y razón; añadir frecuencias de condición y distribución de edad/semestre. No incluir identificadores personales.

**Tabla 2. Responsabilidad y atención selectiva.** Para responsabilidad_media, cam_error_total_pct y cam_rt_total_ms, presentar N válido, perdidos, media, mediana, desviación estándar, mínimo y máximo. Añadir, en filas separadas, error y tiempo por tamaño de conjunto (8, 16 y 32).

**Tabla 3. Descripción por condición.** Repetir las estadísticas principales por condición 0 y 1, indicando N de cada grupo. Evitar interpretar diferencias sin mostrar la dispersión y los datos válidos.

**Figura 1. Distribución de participantes por condición.** Gráfico de barras basado en la frecuencia observada.

**Figura 2. Distribución del porcentaje de error por condición.** Diagrama de caja o gráfico apropiado, construido desde los datos reales.

**Figura 3. Rendimiento según tamaño del conjunto.** Gráfico de error y/o tiempo para 8, 16 y 32 estímulos; incluir solo si las columnas están completas y comparables.

En la versión final, cada tabla o figura debe llevar número, título y una explicación breve del patrón visible. Los campos numéricos aún no pueden completarse.

| Indicador | Resultado de Jamovi |
|---|---|
| N reclutado / N analizado | PENDIENTE: base real |
| N por condición 0 / 1 | PENDIENTE: base real |
| Responsabilidad: media y DE | PENDIENTE: base real |
| Error de atención selectiva: media y DE | PENDIENTE: base real |
| Tiempo de respuesta: media y DE | PENDIENTE: base real |
| Datos perdidos / exclusiones | PENDIENTE: auditoría de datos |

## 5. Diálogo con las hipótesis

Para H1, comparar descriptivamente la tasa de error y el tiempo de respuesta entre condiciones. Una media o mediana de error menor en planificación sería un patrón concordante con la hipótesis; si el error aumenta o no cambia, debe informarse sin ocultarlo. Si el tiempo baja pero el error sube, la interpretación debe reconocer el posible intercambio velocidad-exactitud.

Para H2, describir cómo se distribuyen las puntuaciones de responsabilidad y examinar gráficamente su relación con los indicadores de atención. La estadística descriptiva puede mostrar tendencias, pero no prueba por sí misma una asociación poblacional. Para H3, separar descriptivamente los patrones por condición y responsabilidad puede servir como exploración, pero una moderación exige modelar formalmente el término de interacción condición × responsabilidad. Ese análisis inferencial no forma parte del mínimo descriptivo solicitado y requeriría autorización y revisión metodológica antes de atribuirle conclusiones.

## 6. Alcances y limitaciones

La muestra propuesta es no probabilística y la meta de 60 participantes no fue establecida mediante análisis de potencia; por tanto, la generalización será limitada y la interacción moderadora podría ser difícil de estimar. El BFI-2-S cuenta con adaptación española, pero las evidencias consultadas no equivalen a validación chilena. La tarea CAM publicada fue estudiada con preadolescentes franceses; su adaptación a universitarios adultos debe declararse exploratoria. El diseño, el entorno del equipo, el dispositivo, el tiempo de aplicación y las fallas técnicas pueden influir en el rendimiento.

## 7. Conclusión provisional

No es posible concluir si los datos apoyan, matizan o contradicen H1–H3 mientras no exista una base real y una salida de Jamovi. El cierre de esta entrega requiere reemplazar los campos pendientes por tablas y gráficos exportados desde Jamovi, describir los resultados observados y explicitar discrepancias con las hipótesis. Esta restricción protege la trazabilidad entre el instrumento aplicado, las respuestas registradas y las conclusiones del equipo.

<!-- BODY_END -->

## Referencias

Gallardo-Pujol, D., Rouco, V., Cortijos-Bernabeu, A., Oceja, L., Soto, C. J., & John, O. P. (2022). Factor structure, gender invariance, measurement properties, and short forms of the Spanish adaptation of the Big Five Inventory-2. *Psychological Test Adaptation and Development, 3*(1), 44–69. https://doi.org/10.1027/2698-1866/a000020

Gollwitzer, P. M., & Sheeran, P. (2025). Psychology of planning. *Annual Review of Psychology, 76*, 303–328. https://doi.org/10.1146/annurev-psych-021524-110536

jamovi. (s. f.). *Descriptives (descriptives)*. https://docs.jamovi.org/jmv/jmv_descriptives.html

Pinelli, M., Palluel, E., Dessus, P., Joet, G., Eichenlaub, J.-B., Brugniaux, J. V., & Portrat, S. (2025). Computerized attention measure: A web-based open-source test battery to evaluate students’ attention. *Frontiers in Education, 10*, 1540817. https://doi.org/10.3389/feduc.2025.1540817

Hernández Sampieri, R., Fernández Collado, C., & Baptista Lucio, P. (2014). *Metodología de la investigación* (6.ª ed.). McGraw-Hill Education.
