# Informe independiente. No sustituye Entrega 3 ni Entrega 4.
Esos dos textos quedan congelados. Este archivo solo registra la auditoría y el cálculo sobre el resumen vigente de 27 respuestas.

## Imagen
LUNITA.squashfs del artefacto lunita-v1-8-squashfs-certified, run 43730042509, se verificó en esta sesión:
21e6503fb7c531b1f452c9983dba157a5988e183c9fd8247807409988132fbab
No se pudo montar aquí: el sandbox no instala squashfs-tools (falla setgroups). Por eso Jamovi y JASP de dentro de la imagen no se ejecutaron. No hay proyecto .omv ni .jasp generado. Inventarlos sería un archivo vacío, no un análisis.

## Comprobación n=27
Todas las tablas suman 27.
Edad: media exacta 42,296... se informa 42,30. Mediana 44. Moda 33. DE muestral 14,435... se informa 14,44. Mínimo 18. Máximo 66. Rango 48. Concuerda con la Parte IV.
Esfuerzo: suma de puntos 79. Media 79/27 = 2,9259... se informa 2,93. Mediana 3 (posición 14 del orden). Moda 0. DE muestral 2,908... se informa 2,91. Mínimo 0. Máximo 10. Concuerda.
Planificación: 0, 0, 6 (22,2 %), 7 (25,9 %), 14 (51,9 %).
Continuidad: 2, 4, 6, 10, 5. Porcentajes a un decimal suman 99,9 por redondeo.
Objeto: 3, 10, 8, 4, 2. Igual, 99,9 por redondeo.
Poema: 19, 4, 1, 1, 2. Suma 100,0 a un decimal.
El resumen de 26 respuestas queda sustituido. La persona adicional, respecto de ese resumen, cambia planificación (Algunas veces 5 a 6), continuidad (Casi siempre 9 a 10), objeto (Algo 7 a 8), poema (No me costó nada 18 a 19) y esfuerzo (el 3 pasa de 3 a 4 casos). Eso es una lectura de las dos tablas, no un microdato identificado.

## Qué no se puede hacer
No hay filas emparejadas. No hay correlación.
No hay BFI-2-S: responsabilidad no se calcula.
No hay CAM: no hay RT ni porcentaje de error ni conjuntos 8/16/32.
No hay condición 0/1. H1, H2 y H3 se conservan en los documentos congelados y aquí no se declaran apoyadas ni rechazadas.
Gallardo-Pujol et al. (2022), citado en la Entrega 3 congelada junto a la tarea de búsqueda visual, es la adaptación española del BFI-2, no la CAM. La CAM es Pinelli et al. (2025). Eso queda como hallazgo; el párrafo original no se reescribe.

## Descriptivo permitido
21 de 27 dijeron planificar el estudio casi siempre o siempre (7+14).
La continuidad ante distracción tiene moda en "casi siempre" (10/27).
Mirar el objeto costó nada o un poco a 13 de 27 (3+10).
El poema no costó nada a 19 de 27.
El esfuerzo tiene moda 0 (9/27) y media 2,93.
Edad media 42,30, con casos desde 18 hasta 66: el criterio "universitarios de 18 o más" no queda verificado persona a persona, y la media no parece la de un curso solo de primer año.

## Archivos de este paquete
frecuencias_agregadas_n27.csv
base_agregada_n27.xlsx
fig_edad.png, fig_planificacion.png, fig_continuidad.png, fig_objeto.png, fig_poema.png, fig_esfuerzo.png
analisis_n27.R (reproducible; Rscript no está en este sandbox)
