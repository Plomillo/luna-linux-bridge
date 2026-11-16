# Auditoría forense — Entregas 3 y 4

**Estudio:** Planificación previa, atención selectiva y responsabilidad  
**Equipo:** Valeria Galaz; Diego Norambuena; Paula Pizarro; Joel Quezada  
**Institución:** UNIACC. Santiago de Chile, noviembre de 2026  
**Ejecución:** LUNITA, informe independiente. Las Entregas 3 y 4 originales quedan congeladas y no se reescribieron.  
**Datos vigentes:** resumen de Google Forms, n = 27. El resumen anterior de 26 respuestas queda sustituido y no se usa.

## Artefacto

| Pieza | Resultado |
|---|---|
| Repositorio | `Plomillo/luna-linux-bridge`, rama `main` consultada |
| `LUNITA.squashfs` en git | No está como blob en `main`. Solo existe el workflow `lunita-v18-direct-functional-validation.yml` |
| Copia local | `/tmp/lunita-evidence/lunita-v1-8-squashfs-candidate/LUNITA.squashfs`, 3 576 823 808 bytes |
| Superbloque | Anuncia 3 993 154 438 bytes. `unsquashfs` falla: `read_id_table: failed to read id index table` / EOF |
| Montaje | No se montó. La imagen local está truncada |
| Motor R usado | `/tmp/renv/bin/Rscript`, R 4.5.3 (2026-03-11), el R presente en el entorno de trabajo de Lunita |
| CSV `frecuencias_agregadas_n27.csv` en el repositorio | No estaba en el árbol ni en el disco. Se reconstruyó, con ese nombre, solo con las frecuencias de la Parte IV. No se inventaron personas |

## Hallazgos

### F01 — Ruptura entre protocolo e instrumento. Gravedad: crítica. Estado: abierto

El protocolo congelado de Entrega 3 mide responsabilidad con BFI-2-S (30 ítems; dominio en 4, 9, 11, 17R, 23R, 25R) y atención con la tarea CAM (sets de 8, 16 y 32; 6 ensayos de práctica y 90 de prueba; tiempo y error). El formulario aplicado tiene seis preguntas: edad, planificación de estudio en dos semanas, continuidad ante distracciones, dificultad de mirar un objeto cinco minutos, dificultad de un poema y esfuerzo 0–10.

No hay otro archivo en el repositorio con los 30 ítems ni con ensayos CAM. La responsabilidad BFI y los indicadores CAM no pueden calcularse.

### F02 — No hay microdatos. Gravedad: crítica. Estado: abierto

Lo disponible son seis distribuciones marginales. No hay CSV individual, códigos anónimos ni emparejamiento entre preguntas. Por eso no se calcularon correlaciones, ni tablas cruzadas, ni la interacción condición × responsabilidad. Hacerlo con las marginales sería fabricar asociaciones.

### F03 — La muestra observada no es la muestra planificada. Gravedad: alta. Estado: documentado

El protocolo propone estudiantes universitarios de 18 años o más, meta exploratoria 60, sin análisis de potencia. Lo observado es n = 27. Edad: mínimo 18, máximo 66, media 42,30, mediana 44, moda 33 (tres personas), DE muestral 14,44. Solo tres personas tienen 18 o 19 años (11,1 %). La meta de 60 no se alcanzó y no se informa como si se hubiera alcanzado.

### F04 — H1, H2 y H3 no son examinables. Gravedad: alta. Estado: abierto, hipótesis conservadas

- **H1** exige condición (planificación vs control activo) y error o tiempo CAM. La plantilla de esas columnas tiene 0 filas. No hay asignación 1:1.
- **H2** exige responsabilidad BFI y exactitud o tiempo. No están.
- **H3** exige la interacción. No se declara demostrada. No se estimó.

La pregunta «¿pensaste qué ibas a hacer primero?» no es la condición experimental. Es un autorreporte retrospectivo.

### F05 — Las actividades de cinco minutos no son las del diseño. Gravedad: alta. Estado: documentado

Mirar un objeto no es la planificación «si-entonces» ni la búsqueda visual. El poema no es el control de lectura neutral. El esfuerzo 0–10 no es el dominio de responsabilidad. Se analizan como lo que son.

### F06 — Consentimiento y asignación no están en la base. Gravedad: alta. Estado: pendiente de evidencia

El protocolo pide consentimiento en archivo separado y no registrar nombre ni RUT. El formulario pide no escribir nombre ni RUT: eso se cumple en el instrumento. No se entregó el archivo de consentimientos ni la secuencia de asignación. No se afirma que existan ni que no se hayan pedido en terreno; se afirma que no están en el material auditado.

### F07 — El resumen de 26 respuestas no puede mezclarse. Gravedad: media. Estado: cerrado para el análisis

El encargo sustituye ese resumen por el de 27. Cambian, entre otras, las frecuencias de «algunas veces» en planificación (5 → 6), «casi siempre» en continuidad (9 → 10), «me costó algo» en el objeto (7 → 8), «no me costó nada» en el poema (18 → 19) y el recuento 3 del esfuerzo (3 → 4). La mediana del esfuerzo pasa de 2,5 a 3 y la media de 2,92 a 2,93. Esos valores viejos no entran en las tablas.

### F08 — Redondeo de porcentajes. Gravedad: baja. Estado: resuelto en R

Varias filas de la Parte IV suman 99,9 % por redondeo a un decimal. R calculó el porcentaje exacto `100 * frecuencia / 27`. Redondeado a un decimal, coincide con los porcentajes declarados. No hay error de recuento: cada variable suma 27.

### F09 — Cifras declaradas de edad y esfuerzo. Gravedad: nula. Estado: verificado

R 4.5.3, DE con divisor n−1:

| Indicador | Declarado | Calculado | Coincide al redondeo pedido |
|---|---:|---:|---|
| Media de edad | 42,30 | 42,296296 | sí |
| Mediana de edad | 44 | 44 | sí |
| Moda de edad | 33 | 33 | sí |
| DE de edad | 14,44 | 14,435 | sí, a dos decimales |
| Media de esfuerzo | 2,93 | 2,925926 | sí |
| Mediana de esfuerzo | 3 | 3 | sí |
| Moda de esfuerzo | 0 | 0 | sí |
| DE de esfuerzo | 2,91 | 2,908 | sí, a dos decimales |

### F10 — Pauta docente de Entrega 4. Gravedad: informativa. Estado: ausencia registrada

No hay en el repositorio una rúbrica distinta del propio trabajo de Entrega 4. No se inventó una pauta. Ese trabajo sigue siendo la referencia de lo que el equipo se propuso analizar, no de lo que el formulario midió.

### F11 — Referencias. Gravedad: baja. Estado: no se alteraron

Gallardo-Pujol et al. (2022), Soto y John (2017), Gollwitzer y Sheeran (2025) y Pinelli et al. (2025) se citan en los documentos congelados para instrumentos que este formulario no aplicó. La cita no es falsa como ficha bibliográfica; es inaplicable como respaldo de los datos de Google Forms. Hernández Sampieri et al. (2014) y la página de descriptivos de jamovi no quedaron comprobadas contra un ejemplar en esta ejecución. No se borraron de los originales.

## Ejecución de los tres motores

Hecha después de la auditoría, sobre el mismo CSV.

| Motor | Qué corrió | Qué no corrió |
|---|---|---|
| R 4.5.3 | `/tmp/renv/bin/Rscript`, descriptivos y gráficos | — |
| jamovi | `descriptives()` del paquete jmv 2.8.0, con `jmvcore` cargado en el R de Lunita | La ventana de jamovi. No hay binario en el sistema y el squashfs no monta |
| JASP | `.descriptivesDescriptivesTable_subFunction` y `.descriptivesMedian` (tipo 7) del módulo `jaspDescriptives` | La aplicación JASP |

En las seis variables la diferencia máxima de media y de DE entre los tres fue 0. Eso certifica los descriptivos univariados, no el estudio. La moda que se informa es la de la tabla de frecuencias. JASP, en variables de escala, calcula otra moda (densidad); no se usó, para no mezclar definiciones. No hay correlaciones.

Registro: `salidas/CERTIFICACION.json` y `salidas/validacion_cruzada_motores_reales.csv`.

## Lo que la auditoría no hace

No reescribe Entrega 3 ni Entrega 4. No completa medias CAM. No asigna personas a condición 0 o 1. No puntúa BFI. No declara certificación metodológica del estudio: el estudio, con este instrumento, no puede responder H1–H3.
