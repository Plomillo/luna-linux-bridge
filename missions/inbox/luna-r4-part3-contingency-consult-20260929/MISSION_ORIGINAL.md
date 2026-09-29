# CONSULTA ARQUITECTÓNICA — LUNA R4 PART 3 / CONTINGENCIA DE MATERIALIZACIÓN

CLASS = ADVISORY_READ_ONLY
EXECUTION_AUTHORIZATION = NONE
MUTATION_AUTHORIZATION = NONE
PART_TRANSITION_AUTHORIZATION = NONE
AUTHORITY = Louksna.md
GOVERNOR = MetaOS
WORKER = CUSTOSZ V7
RUNTIME = CUSTOSZ_RUNTIME_V1
SUPERVISOR = SYMPHYLAX R1

## Contexto material observado

Estado vivo más reciente disponible desde LOUKSNA:

- current_part = PART_3
- part_name = CORE_ORCHESTRATION_AND_PROJECTS
- status = HOLD
- next = RETRY_AFTER_REMEDIATION
- blockers = projects_center, semantic_container
- projects_center_candidate = null
- semantic_container_candidate = null
- runner = true
- symphylax = true
- custosz = true
- runtime = true
- metaos = true
- authority = true
- project_workspace = true
- permission request = NONE

El controlador PART_3 actual verifica presencia operacional de Projects Center y Semantic Container en sus superficies de búsqueda. Se han observado candidatos históricos de Semantic Container fuera de esas superficies, pero con estados previos no certificados / G23-G24 no concedidos.

## Pregunta

Hipótesis solamente: si después de una búsqueda suficiente y trazable NO aparece un Projects Center o Semantic Container que pueda aceptarse legítimamente como artefacto operacional, ¿cuál debe ser la remediación arquitectónica correcta para cerrar PART_3 sin fabricar PASS, sin saltar PART_3 y sin degradar la gobernanza?

Evaluar, como mínimo, estas posibilidades:

1. materializar una proyección operacional gobernada a partir de un candidato existente cuya procedencia e identidad puedan demostrarse;
2. reconstruir/materializar un componente mínimo canónico desde fuentes autorizadas y contratos existentes;
3. demostrar equivalencia funcional con otra capacidad ya presente y tramitar formalmente una modificación del requisito;
4. mantener HOLD si ninguna de las anteriores puede demostrarse.

## Respuesta solicitada

CUSTOSZ / MetaOS / SYMPHYLAX deben responder únicamente con análisis y propuesta, sin ejecutar cambios.

Para cada alternativa viable, indicar:
- fuente exacta o clase de fuente admisible;
- evidencia mínima necesaria;
- hashes / identidad que deberían fijarse;
- checkpoint y rollback requeridos;
- validaciones funcionales;
- no-regresión;
- relación con Louksna.md;
- si requiere G23 previo, G24 previo o G23/G24 de PART_3;
- si requiere autorización humana;
- ubicación operacional recomendada, si procede;
- riesgo de falso positivo del actual check de presencia;
- criterio exacto para declarar projects_center=true o semantic_container=true de forma legítima.

Concluir con una recomendación arquitectónica preferida y una alternativa de respaldo, ambas NO ejecutivas.

## Restricciones

- NO ejecutar remediación.
- NO copiar, mover, promover, instalar, generar ni borrar artefactos.
- NO modificar el controlador.
- NO modificar Louksna.md.
- NO alterar criterios de PART_3.
- NO avanzar a PART_4.
- NO autocertificar.
- NO convertir presencia nominal en validez semántica.
- Preservar EXTEND_DO_NOT_REPLACE, FAIL_CLOSED, trazabilidad, procedencia, rollback y cadena EVIDENCE -> VALIDATION -> G23 -> G24.

Esta consulta es deliberativa. No constituye orden de implementación ni autorización material.
