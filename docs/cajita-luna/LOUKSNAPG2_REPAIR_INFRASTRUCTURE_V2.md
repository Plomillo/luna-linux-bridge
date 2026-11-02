# LOUKSNAPG2 — auditoría forense y endurecimiento de infraestructura V2

**Ámbito:** exclusivamente `LOUKSNAPG2` en `louksnapg2/puac2-alternative-20261029`.  
**Commit base auditado:** `804e471c0eea2cbac4f9923572df7f095022372b`.  
**Política:** append-only, fail-closed, originales inmutables, candidato separado, sin promoción automática.  
**Estado de esta revisión:** `CONTROL_PLANE_TESTED / MODEL_REPAIR_BLOCKED / GLOBAL_CERTIFICATION_NOT_GRANTED`.

## 1. Dictamen autocrítico

La infraestructura anterior no alcanzó el objetivo solicitado. No reparó los pesos compactos que fallaban, no reconstruyó una distribución reparada y no obtuvo certificación integral. La existencia de workflows, informes, hashes, smoke tests y firmas no resolvía la deficiencia funcional del artefacto.

El error principal fue de diseño de flujo: la misión se denominaba reparación, pero el ejecutor principal construía un paquete. La construcción, la identidad de fuentes y la integridad del ZIP podían aparecer como PASS sin que se hubiera ejecutado una sola operación de reparación sobre un modelo. A continuación se enumeran los defectos y la corrección realizada en esta rama.

## 2. Fallos raíz encontrados

### 2.1 El trabajador no reparaba modelos

`tools/louksnapg2_worker_mission.py` verifica el paquete CUSTOSZ V9 y ejecuta `tools/louksnapg2_candidate_action.py`. Esa acción ejecuta la fábrica `tools/cajita_runtime_factory.py`, empaqueta los documentos/runtime y llama al validador independiente del contenedor. No existe en esa secuencia una ejecución de adaptadores de reparación, ajuste de pesos, cuantización correctiva o reconstrucción por dominio.

El trabajador anterior publicaba `worker_status=PASS` cuando el candidato se había construido y su hash coincidía. Eso convertía un PASS de empaquetado en una señal ambigua de éxito de la misión de reparación.

**Corrección V2:** el informe separa `task_status=PASS_CANDIDATE_BUILD_ONLY` de `worker_status=BLOCKED_NO_REPAIR_EXECUTED`. Declara `repair_execution_performed=false`, `repair_status=BLOCKED_NO_MODEL_REPAIR_ADAPTERS_EXECUTED` y etiqueta el paquete como `REPACKAGED_UNREPAIRED_BASELINE`. El código de salida cero significa únicamente que la tarea de construcción terminó correctamente; no significa reparación, certificación ni liberación.

### 2.2 La construcción del candidato no admitía salidas reparadas

`tools/louksnapg2_candidate_action.py` invoca la fábrica sobre las fuentes del repositorio. La fábrica copia el runtime a staging, verifica los pesos antes y después y exige que sus identidades no cambien. No recibe un manifiesto de reparación ni aplica salidas independientes de adaptadores al runtime empaquetado.

Por tanto, incluso un hipotético resultado reparado producido fuera de esta secuencia no estaba conectado al constructor final. Ésta es una desconexión funcional crítica: no existía una ruta verificable `repair output -> runtime reconstruction -> candidate bundle -> inference on exact candidate`.

**Estado:** identificado; la puerta G24 ya exige que los originales y las salidas reparadas sean miembros verificables del candidato, pero el mecanismo que aplica esas salidas al runtime final aún no está implementado. No se ha simulado esa integración.

### 2.3 La puerta G24 aceptaba declaraciones de evidencia demasiado débiles

Los contratos anteriores aceptaban hashes con formato válido y campos declarativos de estado sin exigir que las salidas, datasets, informes held-out y checkpoints existieran realmente y coincidieran con sus hashes. Un digest sintácticamente válido no prueba que el archivo exista ni que su contenido sea el declarado.

**Corrección V2:** G24 exige evidencia de ejecución GPU aislada, identidad del runner/job/imagen, commit exacto, seis adaptadores, entradas y salidas en el ZIP candidato, ficheros laterales reales para código/datasets/checkpoint/informe, tamaño y SHA-256 verificados, y un informe held-out con inferencia real y cero casos fallidos. También rechaza rutas inseguras, traversal y symlinks. La puerta continúa independiente del trabajador.

### 2.4 Contradicción entre modos de ejecución

El diseño anterior mezclaba dos actividades diferentes: inferencia de evaluación del runtime y reparación de pesos. La evaluación CPU/offline puede demostrar comportamiento del candidato en un conjunto de pruebas; no prueba que se haya ejecutado reparación GPU. La política previa que trataba `LOCAL_OFFLINE` como evidencia de reparación contradecía P03 de la misión, que exige reparación aislada con GPU.

**Corrección V2:** el preflight CPU se etiqueta `PASS_CPU_DIAGNOSTIC_ONLY`; el G24 reforzado sólo reconoce `PASS_ISOLATED_GPU_REPAIR`. La evaluación de inferencia y la operación de reparación son evidencias separadas. La política LOCAL_OFFLINE histórica queda supersedida como criterio de reparación, no como modo diagnóstico.

### 2.5 La canalización integral estaba desactivada por configuración

El workflow principal `.github/workflows/louksnapg2-puac2-certification.yml` condicionaba `build_candidate` a la variable `LOUKSNAPG2_ENABLE_CUSTOSZ_V9_WORKFLOW=true`. Sin esa variable, la rama podía recibir un push y la certificación integral quedar omitida.

**Corrección V2:** la activación depende de la rama objetivo. Los requisitos operativos se evalúan dentro de los jobs y los bloqueos deben producir HOLD/NOT_CERTIFIED, no una omisión silenciosa del flujo.

### 2.6 Cobertura funcional incompleta por ausencia de fixture

La evaluación principal llamaba a Docling sin suministrar el archivo de imagen requerido por el caso de aceptación. Ese caso estaba condenado a fallar antes de evaluar correctamente el motor.

**Corrección V2:** se crea un fixture determinista de factura con número 4821 y total 37.50, se conserva bajo el workspace y se pasa explícitamente mediante `--docling-image`. El ajuste de ruta evita escribir la imagen en una ruta temporal inexistente dentro de un heredoc literal.

### 2.7 Éxito de ejecución confundido con calidad semántica

La evaluación histórica tuvo inferencia real y código de ejecución satisfactorio, pero sus 13 casos no cumplieron los criterios semánticos. En la evidencia del commit `97cf82685143732599c291def37d43c49a22ce95`, el resultado fue **0/13**. La comparación pre-Q2 y Q4 no mejoró los dominios evaluados. Reducir la precisión de almacenamiento de los mismos factores no reconstruyó la información perdida.

**Corrección V2:** el gate mantiene separados `execution_status`, `quality_criterion_passed`, estado del dominio y decisión de certificación. Ningún código cero ni hash de origen puede elevar un caso funcional fallido a PASS.

## 3. Evidencia de causa raíz funcional heredada

La reevaluación V3 del 30 de octubre registró:

- 13 casos ejecutados, 0 aprobados y 13 fallidos.
- Identidad de cinco pesos compactos y preflight de runtime aprobados; esos estados no representaron calidad.
- GPT-OSS: representación rank-1 con error relativo agregado de reconstrucción INT8 aproximado de 0.998336.
- Qwen3: rank-12 con error relativo agregado aproximado de 0.996409.
- Whisper: intentos R29/R64/R96/adaptativo R192 no aprobados.
- SeamlessM4T: candidato de traducción degenerado; adaptador reparador no implementado.
- Granite Docling: la carga del modelo no acreditó extracción documental; el caso de factura falló.
- Traducción antigua: no existía un transductor compilado/consumidor certificado independiente; Foma como herramienta de compilación no equivale a un recurso lingüístico `.fst/.hfst` desplegado.

La misma reevaluación indicó que los factores pre-Q2 y las variantes Q4 probadas no mejoraron los casos semánticos. El problema no era simplemente una etiqueta incorrecta ni un paquete que faltaba volver a comprimir: los modelos compactos no conservaban suficiente capacidad funcional para pasar las tareas de aceptación.

## 4. Cambios aplicados en esta rama

| Componente | Cambio |
|---|---|
| `tools/louksnapg2_custoszv9_repair_worker.py` | Separación de éxito de auditoría/build y éxito de reparación; sin PASS falso de reparación. |
| `tools/louksnapg2_automated_certifier.py` | G23 acepta sólo auditoría/build; G24 exige ejecución GPU y artefactos reales enlazados al candidato. |
| `.github/workflows/louksnapg2-custoszv9-repair.yml` | Incluye la rama objetivo; el CPU preflight queda como diagnóstico, no como reparación. |
| `tools/louksnapg2_worker_mission.py` | Declara explícitamente que CUSTOSZ V9 sólo construye el candidato y no ejecuta reparación de pesos. |
| `tools/louksnapg2_puac2_gate.py` | G23 separa build de reparación; G24 verifica GPU, archivos, hashes, salidas diferentes, validación held-out y rollback. |
| `tools/louksnapg2_functional_eval.py` | La evidencia declara `NOT_EXECUTED` para reparación cuando no existen adaptadores/runner. |
| `.github/workflows/louksnapg2-puac2-certification.yml` | Activación para la rama objetivo sin la variable que omitía el build; fixture real de Docling suministrado al evaluador. |
| `tests/test_louksnapg2_puac2_gate.py` | Fixtures con ZIP y ficheros reales, no sólo hashes inventados; pruebas negativas para evidencia faltante y ausencia de GPU. |

No se modificaron los pesos originales ni se promocionó candidato alguno.

## 5. Validación automática observada

Workflow de pruebas de contratos: [run 41389187941](https://github.com/Plomillo/luna-linux-bridge/actions/runs/41389187941), commit probado `a6f7af4c4279bfa89d373d428db3d6000e2a79a7`.

Resultado: **PASS**, 22 pruebas distribuidas así:

- 7 pruebas del certificador G23/G24 reforzado.
- 8 pruebas de predicados direccionales de calidad funcional.
- 7 pruebas de la puerta terminal PUAC2, incluidas evidencias ZIP reales y rechazos de archivos ausentes/GPU no demostrada.

Esta validación certifica el comportamiento del contrato y de sus controles con fixtures. No demuestra que los modelos estén reparados. El commit de la rama en la última actualización de esta nota es `804e471c0eea2cbac4f9923572df7f095022372b`; la ejecución principal de construcción y evaluación asociada a ese commit estaba en curso, sin decisión G23/G24 terminal observada al redactar esta nota.

## 6. Bloqueos que siguen impidiendo reparar el artefacto

1. **No hay adaptadores de reparación aprobados para GPT-OSS, SeamlessM4T, Granite Docling o Qwen3.** La presencia de cinco pesos compactos y sus hashes no aporta el entrenamiento, datos de calibración ni pesos docentes completos necesarios para recuperar información perdida.
2. **Whisper sigue EXPERIMENTAL_FAILED.** El script existente es un experimento CPU INT8 con ensayos fallidos y no está enlazado al pipeline PUAC2 de esta rama; su workflow de promoción apunta a otra rama.
3. **No hay evidencia de un runner GPU remoto disponible y provisionado para esta misión.** El runner Ubuntu-hosted utilizado por la evaluación actual es CPU. No se registra un job GPU aprobado que haya ejecutado la reparación.
4. **La reconstrucción final todavía no consume un manifiesto de reparación.** Aun con salidas de adaptadores, falta conectarlas a un overlay de runtime separado, actualizar bindings/manifest de manera trazable, construir el paquete desde ese overlay y ejecutar las 13 pruebas sobre el paquete exacto.
5. **Traducción antigua sigue bloqueada** hasta que exista un transductor/lexicón compilado, versionado, hash-pinned y conectado a un consumidor real. La existencia de Foma y Trealla como software no satisface ese requisito.

Estos bloqueos son funcionales, no decorativos. No deben resolverse bajando umbrales, sustituyendo un dominio por otro, aceptando sólo hashes o repitiendo los rangos de cuantización ya fallidos.

## 7. Criterio terminal

El estado sólo puede cambiar siguiendo esta cadena:

`SOURCE_IDENTITY -> DOMAIN_REPAIR_ADAPTER -> ISOLATED_GPU_EXECUTION -> REPAIR_OUTPUT -> RUNTIME_OVERLAY -> EXACT_CANDIDATE_BUILD -> REAL_INFERENCE -> HELD_OUT_SEMANTIC_VALIDATION -> INDEPENDENT_G23 -> SIGNED_G24 -> ROLLBACK_VERIFICATION`.

- G23 puede certificar integridad/identidad del paquete; no calidad semántica.
- G24 sólo puede emitir CERTIFIED cuando los seis dominios obligatorios, los 13 casos, las salidas reparadas, la equivalencia semántica declarada, la evidencia GPU y el rollback pasan sobre el mismo commit y digest.
- La ausencia de cualquiera de esos es HOLD/NOT_CERTIFIED.
- No se autoriza modificar pesos originales, merge, promoción canónica ni propagación de certificación desde un dominio parcial.

**Dictamen V2:** el plano de control y los contratos de prueba están endurecidos y tienen una ejecución de tests aprobada; el plano de reparación de modelos todavía no está operativo para los seis dominios. Por tanto, la infraestructura aún no puede declararse integralmente certificada y `LOUKSNAPG2` no debe publicarse como artefacto reparado.
