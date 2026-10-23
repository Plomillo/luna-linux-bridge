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

El perfil tipográfico independiente con PyMuPDF contabilizó 4.519.610 caracteres y 897.446 palabras en los spans del PDF. Encontró 28.831 spans numéricos aislados en `Clearface-Heavy` a 10 pt, otros 1.173 en `Clearface-Regular-SC700` a 10,2 pt y 1.033 spans numéricos grandes de 26 pt. Son candidatos de estructura, **no recuentos certificados de versículos/capítulos**. El perfil encontró siete líneas que coinciden exactamente con nombres de libros y ningún bloque completo que coincida exactamente con un nombre de libro. Por tanto, hace falta un parser basado en estructura/estilo y validación de cobertura; una división por expresiones regulares sobre el texto plano no es suficiente.

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

## 9. Reconciliación tipográfica posterior — 2026-10-23

La primera cifra del 86,96 % correspondía únicamente a comparar los números de capítulo de tamaño grande contra los 1.189 capítulos del canon protestante habitual; no era evidencia de 155 capítulos ausentes. Una segunda pasada separó el estilo grande de las variantes tipográficas:

- **1.034/1.034 marcadores de capítulo en tipografía grande** coinciden en orden con los capítulos que el PDF representa con ese estilo.
- **Salmos:** se detectaron 150 marcadores de capítulo en estilo `Clearface-Heavy-SC700`, tamaño 10,2 pt. La secuencia obtenida cubre los números 1–150 sin duplicados ni huecos.
- **Cinco libros de un capítulo** no presentan el marcador grande esperado y deben identificarse por el límite del libro: Abdías, Filemón, 2 Juan, 3 Juan y Judas.

La reconciliación tipográfica, por tanto, explica el total estructural de 1.189 capítulos como **1.034 marcadores grandes + 150 marcadores de Salmos + 5 capítulos únicos representados por el límite del libro**. Esta comprobación cierra el diagnóstico de numeración de capítulos; **no certifica todavía la extracción de los versículos** ni la correspondencia exacta de cada fragmento de texto con su referencia. El siguiente gate continúa siendo construir el libro BTX y validar íntegramente sus libros, capítulos, versículos, contenido, consultas e índices antes de autorizar cualquier sustitución.


## 9. Addendum: compact BTX SQLite candidate — 2026-10-23 23:36 UTC

**Source:** successful structural-candidate run https://github.com/Plomillo/luna-linux-bridge/actions/runs/40040512871, branch commit \`c83b2a0d708a711bf98329a176d06cc205e7e818\`.

The CI build produced a **temporary, non-promoted** SQLite candidate with:

| Check | Result |
|---|---:|
| Candidate DB size | 6,750,208 bytes |
| Candidate DB SHA-256 | \`fdb4a43776a06e76cf772242bc8c802970b2b55c9544cd03826aa8453bc993e0\` |
| Books | 66 |
| Chapter records | 1,189 |
| Nonempty verse rows | 29,883 |
| Duplicate verse-reference keys | 0 |
| Duplicate source-marker events after the canon cutoff | 0 |
| Main-Scripture cutoff | PDF page 1,298 |
| Post-canon pages excluded from Scripture parsing | 62 |
| Normalized text-stream round trip | PASS — 3,862,059 characters each side |
| Representative reference lookups | 13/13 PASS |
| Transient FTS5 search probe | PASS across 29,883 verse rows |
| FTS5 bundled into core database | NO |
| Structural candidate gate | PASS |
| Independent certification | NOT GRANTED |
| Source deletion/replacement | DENIED |

The source-marker audit finds 36 reference numbers without an explicit verse-marker span in the corresponding source range, across 24 chapters. They are recorded in the database table \`source_reference_gaps\` with status \`NO_EXPLICIT_VERSE_MARKER_FOUND_IN_SOURCE_RANGE\`. The builder does not synthesize verse text for those references. John 8:1 is among these gaps; the opening span for John 8:1–11 is not present as separate verse markers in this PDF extraction. This is evidence of unmarked/source-specific reference positions, **not proof that the missing textual variants or editorial notes have been independently reconstructed**.

The database is deliberately **reference-indexed in its core distribution form** (book → chapter → verse). FTS5 is tested transiently in memory, but the full FTS index is not bundled: the prior persisted-FTS variant was 15,421,440 bytes and, if substituted for the 6,949,245-byte source archive, would take the gross Cajita payload from 464,307,422 to approximately 472,779,617 bytes, breaching the exact 470,000,000-byte limit. The compact core candidate is 6,750,208 bytes; simple substitution would yield an arithmetic projection of 464,108,385 bytes before regenerating the runtime manifest and measuring all changed metadata. This projection is not a release-size certificate.

**Scope limit:** the candidate reconstructs the main Scripture body text. Editorial footnotes, cross-references, headings and other apparatus are not separately indexed or independently validated in this pass. The candidate's own builder round-trip is not a substitute for independent source-to-record content validation. Therefore this structural pass cannot be promoted to PUAC G23/G24 certification.

## 10. Orquestador — active-state reconciliation

The current \`CajitadeLuna.md\` on \`main\` (SHA \`cd7c4301be32cf8ed3d098621b2056e718c02845\`) states that routing for 14 commands and 21 targets is still \`PLAN_ONLY\`. The command routing registry is not operational dispatch proof.

The Orquestador directory contains packages for Agno, Deep Agents, LangChain Core and Playwright, but registry entries A043–A046 remain \`UNVERIFIED\` and \`REGISTERED_REFERENCE_NOT_BUNDLED\`. The presence of a wheel/source archive does not establish a dependency closure, a working consumer adapter or an end-to-end route. The eight CLI domains in \`punto.json\` remain \`ADAPTER_PENDING\`, dependencies \`UNRESOLVED_UNTIL_INVENTORY\`, and mutations denied until a versioned action contract is registered. The absolute, machine-specific \`cli_spec.path\` in that manifest remains a portability defect. Existing CLI Python modules are chiefly read-only binary/version probes, not proof of install/update/self-repair/rollback functions.

The current \`CajitadeLuna.md\` also contains two same-day status descriptions that should be reconciled additively, not by erasing historical evidence: the integration audit near its lines 129–149 says the expanded assets are not available in original formats at distribution paths and \`runtime_path_repair\` remains pending, while the later deployment section near lines 186–206 says the ten assets were extracted into persistent runtime directories and their hashes/trees validated. The later section still says native execution tests and manifest regeneration are pending. A dated active-state reconciliation should name the checked commit, directory tree, exact runtime manifest state and verification artifacts before any activation is authorized.

## 11. Governance event — branch correction

During work on the separate structural validator, one file-add call omitted the branch argument and temporarily created \`tools/btx-audit/validate_btx_sqlite_candidate.py\` on \`main\`. I then removed that file through a compensating commit and recreated it on \`audit/btx-book-census-20261023\`. No runtime source, \`CajitadeLuna.md\`, BTX archive, PDF or Parquet corpus was changed by that incident. The validator is now subject to the same draft PR and fail-closed checks; this event is recorded rather than silently omitted.

## 12. Current decision

\`BTX_BOOK_CORE_CANDIDATE = STRUCTURAL_PASS_PENDING_INDEPENDENT_VALIDATION\`  
\`FTS5_CORE_BUNDLED = FALSE\`  
\`CERTIFICATION = NOT_GRANTED\`  
\`SOURCE_DELETION = DENIED\`  
\`SOURCE_REPLACEMENT_IN_MAIN = DENIED\`

The working database remains a temporary CI candidate. The original BTX \`.7z\` and its embedded PDF remain intact in the repository. The draft PR must not be merged as a certified runtime replacement until the separate validator, reproducibility check, source-content verification, manifest regeneration, hard-cap check, independent validation and rollback test all pass.
