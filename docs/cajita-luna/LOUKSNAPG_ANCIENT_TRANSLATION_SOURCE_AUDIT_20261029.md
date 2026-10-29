# LOUKSNAPG — Auditoría de fuentes para traducción de lenguas antiguas

**Fecha:** 2026-10-29  
**Rama:** louksnapg/remote-source-bound-runtime-20261029  
**Estado:** BLOCKED_NO_APPROVED_SOURCE_BOUND_TRANSLATION_ENGINE  
**Certificación integral:** NOT_GRANTED

## 1. Resultado ejecutivo

La ruta canónica de traducción antigua se identifica correctamente y permanece cerrada cuando falta el consumidor o el recurso. La evidencia G24 más reciente registra:

- route_diagnostic: PASS_ROUTE_IDENTIFIED_FAIL_CLOSED
- ancient_target_adapter: NOT_REGISTERED
- functional_translation_status: BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE
- general_translation_fallback_selected: false
- execution_authorized: false

Se inspeccionaron fuentes públicas para distinguir analizadores morfológicos, traductores de griego moderno, lexicones/alineamientos y una posible MT interlineal de griego antiguo a inglés. No se descargó ningún peso ni se incorporó ningún recurso al runtime como parte de esta auditoría.

## 2. Fuentes revisadas y decisión de encaje

### Apertium apertium-grc — morfología, no traducción interlingüe

- Repositorio: https://github.com/apertium/apertium-grc
- Último commit observado: 18c09c5e59dfded391c31cc392daf17923c4d7a7
- README Git blob: 100b93820ade4c16225673b4ca62bb3ade63c313
- El README identifica un paquete monolingüe de griego antiguo para análisis morfológico, generación morfológica y etiquetado POS; enumera fuentes lexd/twol/rlx y un modo de prueba grc-morph.
- Decisión: no satisface la función de traducir frases. Puede investigarse como auxiliar morfológico, pero no certificarse como traductor.

### Apertium apertium-ell-eng — griego moderno, no antiguo

- Repositorio: https://github.com/apertium/apertium-ell-eng
- Último commit observado: 613b767bd90d17b1b576cc818a90e05940bef8bc
- La pareja ell-eng es de griego moderno-inglés; el código ell no corresponde al griego antiguo grc.
- Decisión: excluido como solución para la ruta antigua. Conectarlo allí sería una sustitución de dominio.

### OpenGreekAndLatin GRC-LAT-Dynamic-lexicon — datos de alineación, no un motor listo

- Repositorio: https://github.com/OpenGreekAndLatin/GRC-LAT-Dynamic-lexicon
- Último commit observado: c72abbb0ef391f7d3b3154013702cb1fab29f465
- Su README describe extracción de relaciones léxicas y alineación de textos paralelos; la descripción del corpus incluye 104 documentos Ancient Greek-English y 59 Latin-English.
- Decisión: posible recurso de investigación o de evaluación, pero no demuestra un endpoint de traducción de frases, transductor compilado ni adaptador de producción.

### Open Greek Dilemma — lematización, POS y análisis sintáctico

- Repositorio: https://github.com/open-greek/dilemma
- Último commit observado: fbbc6da9fa0bd5bb77e474d833173bd27a2fc654
- README Git blob: f93798ee355855b7c08ce8b79d59171eecdb52f6
- El README documenta lematización diacrónica en griego antiguo, medieval/bizantino y moderno, con lookup, reglas, normalización dialectal y modelos auxiliares.
- Decisión: no es traducción interlingüe de frases; no se registra como motor sustituto.

### Josolon ancient-greek-dictionary — consulta lexicográfica, no MT

- Repositorio: https://github.com/Josolon/ancient-greek-dictionary
- Último commit observado: 37cf02b7efc8706479c44e10b4ff33480d0421aa
- README Git blob: bbb85b899272159ccaf9d9268d9d051c7b607467
- Describe el léxico Liddell–Scott–Jones y búsquedas de formas flexionadas, declinaciones y partes principales de verbos.
- Decisión: diccionario/lookup, no traducción automática contextual de frases.

### mrapacz/interlinear-en-mt5-large-t-w-t-normalized-bh — candidato antiguo-inglés, no aprobado aún

- Modelo: https://huggingface.co/mrapacz/interlinear-en-mt5-large-t-w-t-normalized-bh
- La ficha pública describe traducción interlineal de griego antiguo a inglés con alineación palabra por palabra, arquitectura MT5ForConditionalGeneration y base mT5-large. La propia ficha reporta BLEU 43.97 y SemScore 0.82; no son mediciones independientes sobre LOUKSNAPG.
- Existe una discrepancia de licencia que debe resolverse antes de usarlo: el model card identifica CC BY-NC-SA 4.0, mientras los metadatos del Hub consultados durante la auditoría etiquetan el repositorio como cc-by-sa-4.0.
- Aún faltan una revisión inmutable, hashes exactos de todos los archivos, tamaño/recursos, validación de la salida interlineal y adaptador consumidor compatible con la ruta existente.
- Decisión: candidato de investigación; no se descarga, integra ni activa automáticamente. La discrepancia de licencia impide tratarlo como aprobado.

### ilsp/m2m100-1.2B-ag-mg-full-ft — antiguo a moderno griego, no a inglés

- Modelo: https://huggingface.co/ilsp/m2m100-1.2B-ag-mg-full-ft
- Los metadatos consultados lo describen como traducción grc → el, con arquitectura M2M100-1.2B y licencia MIT.
- Decisión: solo corresponde si el destino requerido es griego moderno. No satisface una operación antigua-inglés/español ni se selecciona como sustituto de forma tácita.

## 3. Defecto, consecuencia, corrección y verificación

| Elemento | Resultado |
|---|---|
| Defecto concreto | No hay adaptador consumidor registrado ni un recurso de traducción de frases aprobado, con ID/revisión/hash/licencia verificados y vinculado a la ruta antigua. |
| Consecuencia funcional | La solicitud puede localizar su destino, pero no producir una traducción antigua real. |
| Corrección necesaria | Confirmar dirección lingüística requerida; resolver licencia/formato; fijar revisión inmutable y hashes; implementar un adaptador para el contrato existente sin alterar identidades canónicas ni redirigir al traductor general. |
| Verificación posterior | Ejecutar ejemplos antiguos con traducciones esperadas revisadas por persona competente; comprobar calidad, procedencia, respuesta de la ruta en el candidato exacto y ausencia de fallback. Una prueba de ruta o de lematización no basta. |

## 4. Condiciones para reabrir el dominio

1. Confirmar explícitamente lengua de origen, destino y variedad requerida (por ejemplo, griego koiné/antiguo a inglés).
2. Confirmar licencia de todos los componentes y compatibilidad con la distribución prevista.
3. Fijar IDs/revisiones inmutables y SHA-256 de configuración, tokenizer, índice y todos los pesos.
4. Registrar el adaptador consumidor en la ruta canónica y verificar contrato de entrada/salida.
5. Aprobar un conjunto de traducción funcional con referencias revisadas; registrar errores y métrica, sin equiparar ejecución técnica con calidad.
6. Ejecutar sobre el LOUKSNAPG.md empaquetado exacto, cuyo hash se registre, bajo el presupuesto operativo del runner.
7. Mantener fail-closed si falla identidad, procedencia, ejecución o aceptación semántica.

## 5. Estado persistente

- ancient_translation_route_diagnostic = PASS_ROUTE_IDENTIFIED_FAIL_CLOSED
- ancient_target_adapter = NOT_REGISTERED
- functional_translation_status = BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE
- general_translation_fallback_selected = false
- execution_authorized = false
- ancient_language_translation_is_functionally_certified = false
- global_certification = NOT_GRANTED

Esta auditoría no añade pesos ni convierte fuentes auxiliares en un traductor de producción. El dominio permanece bloqueado hasta que un recurso y su adaptador demuestren la función exigida.
