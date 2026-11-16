# Reconciliación y propuesta

Los documentos originales siguen congelados. Este texto dice cómo conviven los 27 registros resumidos con la base vacía del protocolo, y qué puede hacerse después sin inventar datos.

## Dos bases, no una sola con huecos rellenados

| Base | Filas | Qué contiene |
|---|---:|---|
| `datos/frecuencias_agregadas_n27.csv` | 53 niveles, 6 variables, cada una con frecuencia total 27 | Solo lo que Google Forms resumió |
| `datos/plantilla_vacia_protocolo_original.csv` | 0 | Columnas del protocolo: código, consentimiento, condición, 30 ítems BFI, responsabilidad, ensayos CAM, tiempo, error. Vacía a propósito |

Unirlas en una tabla de 27 personas y dejar CAM o BFI en blanco sería fingir que esas 27 personas pasaron por el experimento. No se hizo. Las marginales tampoco se expandieron a 27 filas de «participantes»: servirían para una sola variable y, si se pegaran entre sí, fabricarían parejas que no existen.

## Qué pregunta observa cada ítem

Hay seis preguntas, no veintisiete. Veintisiete es el número de respuestas.

| Ítem aplicado | No es | Sí alcanza para |
|---|---|---|
| Edad | Criterio cumplido de «estudiante universitario» | Describir quién respondió |
| Planificación antes de estudiar | Condición experimental ni intención si-entonces | Describir un hábito de las últimas dos semanas |
| Continuar la tarea pese a distracciones | Error o tiempo de la CAM | Describir atención autopercibida en el estudio cotidiano |
| Mirar un objeto 5 minutos | Búsqueda visual ni manipulación de planificación | Describir dificultad sentida en esa actividad |
| Poema | Control activo del protocolo | Describir dificultad sentida de esa lectura |
| Esfuerzo 0–10 | Responsabilidad ni rendimiento objetivo | Describir el esfuerzo declarado al terminar |

## Qué se puede decir con los números ya calculados

Cálculo en R 4.5.3 sobre las frecuencias, sin casos inventados.

La planificación autopercibida está cargada hacia el extremo alto: nadie marcó «nunca» ni «casi nunca»; 14 de 27 (51,9 %) marcaron «siempre» y 7 (25,9 %) «casi siempre». Mediana 5, media 4,30, DE 0,82. Eso describe el autorreporte. No demuestra que un grupo haya planificado y otro no.

La continuidad ante distracciones está más repartida. La moda es «casi siempre» (10/27, 37,0 %). Hay 6 personas en «nunca» o «casi nunca» (22,2 % sumados). Media 3,44, mediana 4, DE 1,19.

Mirar el objeto costó poco o algo a la mayoría: moda «un poquito» (10/27, 37,0 %), más 8 en «algo» (29,6 %). Solo 2 dijeron «mucho». Media 2,70, mediana 3, DE 1,10.

El poema resultó fácil para la mayoría: 19 de 27 (70,4 %) «no me costó nada». Mediana 1, media 1,63, DE 1,21.

El esfuerzo declarado es bajo: media 2,93, mediana 3, moda 0 (9 personas, 33,3 %), DE 2,91, rango 0–10. Una persona marcó 10. No se interpreta como responsabilidad ni como buen o mal rendimiento CAM.

La edad (media 42,30, mediana 44, máximo 66) obliga a no llamar a este grupo «muestra de estudiantes universitarios de la meta de 60» sin una nota de divergencia.

## Hipótesis, sin convertirlas en resultados

| Hipótesis | Estado con estos datos |
|---|---|
| H1, menos errores o menos tiempo en planificación que en control | No examinable. Falta la condición y falta la CAM |
| H2, más responsabilidad con más exactitud o menos tiempo | No examinable. Falta BFI-2-S y falta la CAM |
| H3, la diferencia entre condiciones varía según responsabilidad | No examinable. Una moderación no sale de tablas descriptivas, y aquí ni siquiera hay columnas para el producto condición × responsabilidad |

Se conservan las tres hipótesis como plan. No se reemplazan por hipótesis nuevas hechas a la medida del formulario, porque eso cambiaría el estudio en silencio. Si el equipo quiere hipótesis del formulario, tienen que formularse aparte y decirse como tales. Abajo van solo como propuesta, no como hallazgo.

## Propuesta de complemento, sin datos ficticios

**Ola 0, ya recogida.** Se archiva el formulario y este resumen n = 27 como piloto de factibilidad y como registro de lo que el campo hizo en vez del protocolo. Producto válido de Entrega 3 si la docencia acepta un informe de divergencia: base organizada de lo real, más este informe. No es la base del experimento.

**Ola 0b, solo si aparece el CSV individual de Google Forms.** Ahí sí se podrían asociar las seis preguntas entre sí (Spearman, porque son ordinales, y la edad y el esfuerzo como cuantitativas). Seguiría sin haber BFI, CAM ni condición. Hasta que ese archivo exista, las asociaciones quedan prohibidas. No se simula.

**Ola 1, todavía no hecha.** Nueva base, la plantilla vacía que ya está creada, con filas solo cuando haya una persona real:

1. Código anónimo. Sin nombre y sin RUT.
2. Consentimiento en un archivo distinto.
3. Asignación aleatoria 1:1 guardada aparte, codificada 0 o 1.
4. BFI-2-S completo. Responsabilidad solo con 4, 9, 11 y los inversos 17, 23 y 25, recodificados como 6 menos la respuesta, y solo si los seis ítems están.
5. CAM informatizada, una fila por ensayo, sets 8, 16 y 32, práctica y prueba separadas, tiempo de aciertos y error por separado.
6. La planificación de cinco minutos y la lectura neutral, como intervención, no como pregunta retrospectiva.

Los 27 actuales no se recodifican hacia atrás como grupo experimental o control. Si alguna de esas personas vuelve a participar, entra con un código nuevo de la Ola 1. No se pega su edad de la Ola 0 salvo que el CSV individual y un código común lo permitan, cosa que hoy no existe.

**Qué puede hacer cada motor cuando haya microdatos, y no antes.** R, jamovi y JASP deben leer el mismo CSV de personas, con los mismos tipos (condición nominal, ítems ordinales, tiempos continuos) y el mismo filtro de casos. Hoy los tres solo pueden repetir los descriptivos de cada marginal. Cruzarlos entre preguntas no es un análisis: es una invención.

**Criterio para no cerrar en falso.** La Entrega 4 original deja las celdas CAM y BFI en «PENDIENTE». Deben seguir así. Las tablas nuevas son las de este informe (edad, cuatro Likert y esfuerzo). Confirmar con la docencia si la Unidad 3 se cierra con la divergencia documentada o si pide reaplicar el protocolo antes del 16 de noviembre de 2026.

## Hipótesis de trabajo solo para una ola futura

No son resultados. No sustituyen a H1–H3.

- **P1.** En el formulario ya aplicado, si algún día hay microdatos, la planificación autopercibida y la continuidad ante distracciones tenderían a ir juntas. Hoy no se puede mirar.
- **P2.** La dificultad de mirar el objeto y el esfuerzo declarado describirían la carga sentida de la actividad breve. Hoy solo se conocen por separado: el objeto se concentra en dificultad baja-media y el esfuerzo tiene moda 0.
- **P3.** H1–H3 se retoman únicamente en la Ola 1, con CAM y BFI, y H3 solo si se modela la interacción y la docencia lo autoriza. Con n previsto 60 y sin potencia, una interacción seguirá siendo frágil: eso ya lo decía la Entrega 4 y se mantiene.
