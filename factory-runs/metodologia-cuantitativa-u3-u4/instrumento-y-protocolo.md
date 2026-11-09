# Instrumento, intervención y protocolo de aplicación

## 1. Batería de medidas

### 1.1. Responsabilidad: BFI-2-S en español

Aplicar la **forma completa de 30 ítems BFI-2-S en español**, no solo los seis reactivos de responsabilidad. El formulario oficial está disponible sin coste para investigación en el [PDF del Colby College](https://www.colby.edu/wp-content/uploads/2022/07/bfi2s-form-spanish.pdf). La adaptación española fue estudiada por Gallardo-Pujol et al. (2022), junto con las versiones BFI-2 y BFI-2-XS. El estudio informa resultados prometedores para las formas abreviadas, pero recomienda replicación adicional. La evidencia citada procede de muestras españolas; no equivale a validación local en Chile.

- Respuestas: 1 = Muy en desacuerdo; 2 = Algo en desacuerdo; 3 = Neutral, sin opinión; 4 = Algo de acuerdo; 5 = Muy de acuerdo.
- Dominio Responsabilidad: ítems 4, 9, 11, 17R, 23R y 25R.
- Inversión: para los ítems 17, 23 y 25, recodificar como 6 menos la respuesta original.
- Puntuación: promedio de los seis ítems ya recodificados; rango 1–5. Exigir los seis valores válidos; no imputar ni prorratear respuestas faltantes.
- Administrar el instrumento completo respetando el orden, redacción y opciones del formulario oficial. No alterar su lenguaje ni presentarlo como validado para Chile.

### 1.2. Rendimiento: búsqueda visual de atención selectiva

Se propone como referencia la tarea de atención selectiva visual del proyecto abierto CAM (Computerized Attention Measure). El protocolo publicado solicita identificar un objetivo visual entre distractores, con conjuntos de 8, 16 y 32 estímulos; registra errores y tiempo de respuesta, e incorpora seis ensayos de práctica y 90 ensayos de prueba (Pinelli et al., 2025). El código del proyecto está publicado en [GitLab CAM](https://gitlab.com/mpinelli/CAM).

**Advertencia de validez:** el estudio CAM se realizó con preadolescentes en escuelas francesas, no con universitarios adultos chilenos. Su confiabilidad publicada no puede transferirse automáticamente a esta muestra. La adaptación de instrucciones/administración para UNIACC debe pilotearse, describirse como exploratoria y someterse a revisión docente. El informe CAM también documentó pérdidas técnicas importantes en la tarea de atención selectiva; por eso se registra finalización, ensayos válidos e incidencias por separado. No usar este desempeño para diagnóstico clínico.

Medidas por participante: tiempo medio de respuesta en milisegundos para respuestas correctas; porcentaje de error; y los mismos indicadores desglosados por tamaño de conjunto (8, 16 y 32). No combinar velocidad y exactitud en un índice único sin justificación previa.

## 2. Manipulación experimental de planificación

**Condición 1 — planificación (5 minutos).** Entregar una hoja uniforme y pedir al participante que: (a) formule la meta de responder con precisión; (b) identifique el rasgo objetivo y los distractores antes de iniciar; (c) escriba una intención del tipo “si me distraigo, vuelvo a buscar el objetivo y sigo la regla de respuesta”; y (d) indique cómo mantendrá un ritmo cuidadoso sin sacrificar exactitud. No enseñar respuestas de los ensayos ni practicar con estímulos de prueba.

**Condición 0 — control activo (5 minutos).** Lectura silenciosa de un texto neutral de extensión semejante, sin instrucciones de planificar, organizar, priorizar o controlar la atención. Ambos grupos reciben la misma instrucción estándar de la tarea después de esos cinco minutos.

La revisión de Gollwitzer y Sheeran (2025) aborda los planes “si-entonces” y su relación posible con el control atencional y otras funciones cognitivas. Esto justifica examinar la intervención, pero no permite anticipar el resultado de esta muestra.

## 3. Secuencia de aplicación

1. Verificar edad igual o superior a 18 años y obtener consentimiento informado voluntario.
2. Asignar un código anónimo; no escribir nombre, RUT, correo ni calificación académica en la base.
3. Aplicar el BFI-2-S completo.
4. Asignar al azar 1:1 a planificación o control activo y registrar la variable condicion (1 o 0). Conservar la secuencia de asignación en un archivo separado.
5. Aplicar la condición durante cinco minutos, con cronómetro uniforme.
6. Dar la misma instrucción CAM y realizar la tarea; guardar los datos por ensayo y el resumen por participante.
7. Registrar fallos técnicos, abandono, respuestas incompletas y desviaciones. No excluir a alguien por obtener puntuación alta o baja en responsabilidad o por su rendimiento.

## 4. Población, reclutamiento y resguardo

Propuesta operativa: estudiantes universitarios de UNIACC mayores de 18 años, muestreo por conveniencia, meta exploratoria de 60 participantes (30 por condición). No se realizó análisis de potencia; por ello esta meta no asegura potencia suficiente para probar moderación. La participación debe ser voluntaria, sin vínculo con notas, y puede abandonarse sin sanción. Guardar consentimientos por separado de los datos; restringir el acceso a los cuatro integrantes y reportar resultados agregados.

## 5. Diccionario mínimo y control de calidad

La hoja Participantes contiene una fila por persona; Ensayos_CAM, una fila por ensayo. id_participante debe ser único y no identificable. Los códigos de respuesta del BFI-2-S son enteros 1–5; los tiempos se registran en milisegundos; los porcentajes en escala 0–100. Usar celdas vacías para datos realmente faltantes, nunca cero como sustituto. Revisar duplicados, valores fuera de rango, ausencia de consentimiento, finalización de tarea y eventos técnicos antes de importar a Jamovi.

## Referencias de instrumento

Gallardo-Pujol, D., Rouco, V., Cortijos-Bernabeu, A., Oceja, L., Soto, C. J., & John, O. P. (2022). Factor structure, gender invariance, measurement properties, and short forms of the Spanish adaptation of the Big Five Inventory-2. *Psychological Test Adaptation and Development, 3*(1), 44–69. https://doi.org/10.1027/2698-1866/a000020

Gollwitzer, P. M., & Sheeran, P. (2025). Psychology of planning. *Annual Review of Psychology, 76*, 303–328. https://doi.org/10.1146/annurev-psych-021524-110536

Pinelli, M., Palluel, E., Dessus, P., Joet, G., Eichenlaub, J.-B., Brugniaux, J. V., & Portrat, S. (2025). Computerized attention measure: A web-based open-source test battery to evaluate students’ attention. *Frontiers in Education, 10*, 1540817. https://doi.org/10.3389/feduc.2025.1540817
