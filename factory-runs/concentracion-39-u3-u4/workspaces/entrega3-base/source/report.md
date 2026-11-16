---
title: "Entrega 3 — Base de datos organizada"
subtitle: "Planificación previa, atención ante distractores y concentración percibida"
author: "Valeria Galaz; Diego Norambuena; Paula Pizarro; Joel Quezada"
date: "Santiago de Chile, 16 de noviembre de 2026"
lang: es
---

<!-- BODY_START -->

## 1. Procedencia y estructura

La exportación de encuesta contiene **39 respuestas en cada una de seis preguntas**: edad, planificación antes de estudiar, continuidad de la tarea ante distractores, dificultad para mirar un objeto durante cinco minutos, dificultad para comprender un poema y esfuerzo para completar la prueba.

La fuente presenta frecuencias agregadas por categoría, no una matriz de respuestas individuales identificadas por participante. La base acompañante organiza pregunta, valor, etiqueta, frecuencia y porcentaje. No incluye ni simula microdatos personales.

## 2. Diccionario de variables

| Variable | Definición | Tipo | Codificación y dirección |
|---|---|---|---|
| Edad | Edad declarada | Cuantitativa | Años cumplidos |
| Planificación previa | Frecuencia con que se piensa qué hacer primero antes de estudiar | Ordinal, 1–5 | 1 = nunca; 5 = siempre. Valor alto = mayor frecuencia |
| Continuidad ante distractores | Frecuencia con que se continúa la tarea pese a algo que llama la atención | Ordinal, 1–5 | 1 = nunca; 5 = siempre. Valor alto = mayor frecuencia |
| Dificultad del objeto | Dificultad percibida al mirar un objeto durante cinco minutos | Ordinal, 1–5 | 1 = no me costó nada; 5 = me costó mucho. Valor alto = mayor dificultad |
| Dificultad del poema | Dificultad percibida para comprender el poema | Ordinal, 1–5 | 1 = no me costó nada; 5 = me costó mucho. Valor alto = mayor dificultad |
| Esfuerzo | Esfuerzo subjetivo para completar la prueba | Escala 0–10 | 0 = ningún esfuerzo; 10 = muchísimo esfuerzo |

## 3. Resumen de frecuencias

| Pregunta | Distribución de frecuencias | Porcentaje destacado |
|---|---|---:|
| Planificación | Nunca 0; casi nunca 0; algunas veces 9; casi siempre 12; siempre 18 | 76,9 % en casi siempre/siempre |
| Continuidad | Nunca 3; casi nunca 4; algunas veces 10; casi siempre 16; siempre 6 | 56,4 % en casi siempre/siempre |
| Dificultad del objeto | No costó 7; poquito 13; algo 10; bastante 7; mucho 2 | 51,3 % sin dificultad o leve |
| Dificultad del poema | No costó 25; poquito 6; algo 5; bastante 1; mucho 2 | 79,5 % sin dificultad o leve |
| Esfuerzo | 0:13; 1:2; 2:3; 3:6; 4:2; 5:7; 6:1; 7:2; 8:2; 9:0; 10:1 | 66,7 % entre 0 y 4 |

La hoja Frecuencias del libro XLSX conserva todas las categorías de edad y las alternativas de las cinco preguntas restantes, con valor, etiqueta, recuento, N y porcentaje sobre 39.

## 4. Descriptivos de referencia

| Variable | N | Media | Mediana | Moda | DE | Mín. | Máx. |
|---|---:|---:|---:|---:|---:|---:|---:|
| Edad | 39 | 40,87 | 43 | 33 | 13,51 | 18 | 66 |
| Planificación | 39 | 4,23 | 4 | 5 | 0,81 | 3 | 5 |
| Continuidad | 39 | 3,46 | 4 | 4 | 1,12 | 1 | 5 |
| Dificultad del objeto | 39 | 2,59 | 2 | 2 | 1,14 | 1 | 5 |
| Dificultad del poema | 39 | 1,69 | 1 | 1 | 1,13 | 1 | 5 |
| Esfuerzo | 39 | 2,95 | 3 | 0 | 2,80 | 0 | 10 |

## 5. Control de calidad y límites

Se verificó que cada pregunta reuniera 39 respuestas y que sus frecuencias sumaran ese total. Los porcentajes se calcularon como frecuencia/39 y se redondearon a un decimal. Las escalas conservan su sentido: en planificación y continuidad, un valor alto representa mayor frecuencia; en dificultad, representa mayor dificultad.

No hay identificadores individuales. Por tanto, no es posible comprobar duplicados por participante, enlazar respuestas entre preguntas, calcular correlaciones o determinar si quien planifica más es la misma persona que informa menor dificultad. Tampoco se dispone en esta exportación de registro individual de reclutamiento o consentimiento.

La expansión técnica de 39 valores por pregunta usada para presentar descriptivos univariados en las interfaces no constituye una base de participantes. Las seis distribuciones son independientes y no deben emparejarse. Para ítems ordinales se priorizan frecuencias, porcentajes, mediana y moda; las medias se incluyen como resumen complementario (Boone & Boone, 2012; Sullivan & Artino, 2013).

<!-- BODY_END -->

## Referencias

Boone, H. N., Jr., & Boone, D. A. (2012). Analyzing Likert data. *Journal of Extension, 50*(2), Article 48. https://doi.org/10.34068/joe.50.02.48

Fortenbaugh, F. C., DeGutis, J., & Esterman, M. (2017). Recent theoretical, neural, and clinical advances in sustained attention research. *Annals of the New York Academy of Sciences, 1396*(1), 70–91. https://doi.org/10.1111/nyas.13318

jamovi. (s. f.). *Descriptives (descriptives).* https://docs.jamovi.org/jmv/jmv_descriptives.html

Khodami, M. A., Battaglini, L., Jansarvatan, M., Kireeva, S., & Bagheri, S. (2024). Comparing self-report vs. performance measures of attentional control and efficiency. *NeuroSci, 5*(2), 114–127. https://doi.org/10.3390/neurosci5020008

Sullivan, G. M., & Artino, A. R., Jr. (2013). Analyzing and interpreting data from Likert-type scales. *Journal of Graduate Medical Education, 5*(4), 541–542. https://doi.org/10.4300/JGME-5-4-18
