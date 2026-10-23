# Auditoría forense de Orquestador y Biblia Textual BTX — 2026-10-23

**Estado:** `AUDIT_PASS_SOURCE_INTACT_CONVERSION_NOT_CERTIFIED`  
**Autoridad:** `Louksna.md`  
**Rama de trabajo:** `audit/btx-book-census-20261023`  
**PR de auditoría:** https://github.com/Plomillo/luna-linux-bridge/pull/96

## 1. Resultado ejecutivo

No se ha encontrado una representación estructurada identificada como Biblia Textual BTX lista para sustituir su PDF. El archivo `data.parquet` ya presente sí tiene un esquema por libro/capítulo/versículo, pero su README lo identifica como **Reina-Valera 1909**, con 66 libros y 30.997 filas. No debe renombrarse ni reutilizarse como BTX.

El contenedor BTX original está íntegro y contiene un PDF con una capa de texto sustancial. Eso hace viable continuar con una conversión; no prueba que las referencias se hayan segmentado correctamente ni que la conversión exista.

**No se ha borrado, modificado ni reemplazado el archivo BTX original ni el PDF que contiene. No se declara certificación del libro estructurado.**

## 2. Evidencia del archivo BTX

Ruta fuente:
`cajita-luna-runtime/2. Orquestación/Confesión Eclesial Reformada/Biblia Textual BTX -- Biblia Textual BTX -- ( WeLib.org ).7z`

| Comprobación | Resultado observado |
|---|---|
| Contenedor `.7z` | 6.949.245 bytes |
| SHA-256 esperado y observado del contenedor | `be5ec9ee6153a5573a8e491e2f96ea0a4e94c9c6c023d3cb43abd6807f040b36` — coincide |
| Prueba de integridad 7z | PASS |
| Miembros | 1 PDF |
| PDF interno | 8.078.938 bytes |
| SHA-256 observado del PDF interno | `30dc19d8bc0905b311a185726583cb55d0907d97cdcf015e971cf46ff33d3acd` |
| Páginas | 1.360 |
| Páginas con texto extraíble por `pdftotext -layout` | 1.356 |
| Caracteres extraídos | 6.810.867 |
| Palabras extraídas | 896.214 |
| Nombres de libros detectados en modo texto | 64/66 por `-layout`; 65/66 por `-raw` |
| Conversión BTX a libro consultable | NO REALIZADA / NO CERTIFICADA |

La diferencia en los nombres detectados y la ausencia de encabezados de libro claramente aislados en la primera pasada impiden usar el recuento textual como prueba de cobertura completa. Los diagnósticos de formato no publican el contenido de los versículos.

## 3. El conjunto estructurado existente no es BTX

El README contiguo a `data.parquet` declara:

- Traducción: Reina-Valera 1909.
- Formato: Parquet con compresión Zstandard.
- Filas: 30.997.
- Libros: 66.
- Campos: traducción, idioma, número/nombre/abreviatura del libro, capítulo, número de versículo, sufijo, ID de versículo y texto.

Por tanto, es un corpus estructurado y útil como ejemplo de diseño de datos, pero **no constituye evidencia del contenido de BTX** y no puede sustituirlo.

## 4. Estado de la capacidad Confesión Eclesial Reformada

El registro `RUNTIME_CANDIDATE_V1/registry.json` relaciona los recursos A029–A032 con la capacidad `cap-05`, pero mantiene:

- `operability = UNVERIFIED`;
- cierre de dependencias sin verificar;
- `BLOCK_EXECUTION_UNTIL_ADAPTER_AND_DEPENDENCIES_VALIDATED`.

La mera presencia del PDF, del Parquet y del ZIP de CLIPS no equivale a un lector BTX operativo. No se encontró evidencia de una prueba de consulta BTX por referencia, cobertura íntegra de capítulos/versículos o validación independiente del corpus.

## 5. Auditoría de Orquestador

En `2. Orquestación/Orquestador` se encontraron:

- `punto.json`, manifiesto declarativo;
- `CLIS.txt`, especificación de las ocho capacidades CLI;
- módulos Python por CLI y un registro de sondeo;
- ruedas de Agno, Deep Agents y LangChain Core;
- paquete fuente de Playwright.

Hallazgos:

1. `punto.json` mantiene `certification = NOT_GRANTED` y marca los dominios como `ADAPTER_PENDING`; las dependencias figuran como sin resolver hasta completar el inventario.
2. Los módulos CLI individuales encontrados actúan principalmente como sondeos de disponibilidad/versión. No demuestran por sí mismos la instalación, actualización, autorreparación o rollback descritos en `CLIS.txt`.
3. El campo `cli_spec.path` de `punto.json` apunta a una ruta absoluta específica del entorno del autor y no es portable.
4. Los paquetes de LangChain Core, Deep Agents y Agno aparecen físicamente en el directorio, pero el mapa de routing declara explícitamente solo Playwright como activo de soporte para Orquestador. No hay evidencia suficiente aquí de que los otros paquetes tengan contrato de dependencias, adaptador integrado y pruebas end-to-end.
5. El mapa de 14 comandos continúa en `PLAN_ONLY_UNTIL_TASK_ADAPTERS_AND_RESOURCE_EVIDENCE_PASS`; el despacho efectivo a todos los subdominios no está certificado.

Conclusión: la capa está parcialmente materializada y dispone de artefactos útiles, pero no debe describirse como un orquestador completo y certificado.

## 6. Límites de tamaño

La última evidencia disponible del build declara:

- bruto con manifiesto: 464.307.422 bytes;
- límite operativo exacto: 470.000.000 bytes;
- margen bruto aritmético restante: 5.692.578 bytes.

La base BTX candidata, sus índices y metadatos deberán contabilizarse en el payload completo. El margen no es una autorización para superar el límite ni para degradar calidad o trazabilidad.

## 7. Puerta de aceptación para construir el libro BTX

La conversión debe generar una base consultable —preferentemente SQLite con tablas normalizadas e índice de texto completo— con al menos:

- catálogo canónico de libros y aliases de referencia;
- capítulos y versículos con IDs deterministas;
- índice por libro/capítulo/versículo y búsqueda textual;
- procedencia, hashes del origen y versión del convertidor;
- control separado para notas y material editorial que exista en la fuente.

Antes de aceptar o sustituir el PDF deben pasar, como mínimo:

1. extracción segura e íntegra y coincidencia de hash;
2. reconocimiento de todos los libros del corpus;
3. validación de capítulos y referencias de versículos, sin duplicados ni huecos no explicados;
4. pruebas de consulta para referencias iniciales, intermedias y finales de cada libro;
5. comparación de contenido extraído contra los segmentos de origen, con discrepancias registradas;
6. pruebas de búsqueda textual y round-trip de serialización;
7. hash reproducible de salida y medida real de bytes;
8. validación independiente y prueba de rollback.

Si una puerta no pasa, el resultado debe marcarse `NOT_CERTIFIED`, conservar el original y no reemplazar el recurso en runtime.

## 8. Estado final de esta pasada

- Auditoría automatizada de solo lectura: PASS.
- Integridad del contenedor BTX: PASS.
- Capa textual aprovechable: PASS.
- Identificación de dataset existente como Reina-Valera 1909: PASS.
- Libro BTX normalizado generado: NO.
- Equivalencia de todas las referencias/versículos: NO VERIFICADA.
- Certificación funcional BTX: NOT GRANTED.
- Eliminación o sustitución del original: DENIED.

Esta pasada añade evidencia y herramientas de inspección en una rama separada. No altera `CajitadeLuna.md`, la autoridad canónica, el archivo BTX, el PDF contenido ni el Parquet existente.
