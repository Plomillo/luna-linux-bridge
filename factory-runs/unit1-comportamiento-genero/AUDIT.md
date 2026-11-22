# Auditoría del trabajo — Unidad 1: Comportamiento y género

- Fecha: 2026-11-22
- Repositorio: `Plomillo/luna-linux-bridge`
- Rama de trabajo: `candidate/document-factory-v1-unit2-20261013`
- Workflow: `.github/workflows/document-factory-unit1-run.yml`
- Run definitivo: https://github.com/Plomillo/luna-linux-bridge/actions/runs/45077299372
- Resultado del run definitivo: `success`
- Artifact de GitHub Actions: `unidad1-comportamiento-genero-documentos` (artifact ID `14774774951`)
- Commit de entradas final: `8c056ed2857e8f43015ddd3ec57b0cbd43cde8a8`

## Resultado de construcción y validación

| Control | Resultado |
|---|---|
| DOCX | PASS |
| PDF | PASS |
| PPTX | PASS |
| XLSX | PASS |
| Conteo de cuerpo | PASS — 1.078 palabras; rango del perfil 1.050–1.650 |
| Fuentes verificadas | PASS — 8 fuentes; mínimo configurado 7 |
| Formato Word | APLICADO — Arial 12 texto, Arial 16 títulos, 1,5 interlineado, márgenes 2,5 cm, párrafos justificados y títulos centrados |
| Paginación del cuerpo | PASS — 4 páginas entre Introducción y Conclusión |
| PDF total | 8 páginas — portada, cuerpo y referencias |
| Congelación del candidato | PASS — `frozen=true` |

Archivos finales:
- `deliverables/latest/Trabajo1_DiegoIgnacioNorambuenaMiranda.docx`
- `deliverables/latest/Trabajo1_DiegoIgnacioNorambuenaMiranda.pdf`
- `deliverables/latest/report-source.md`
- `deliverables/latest/evidence/validation.json`
- `deliverables/latest/evidence/formatting.json`
- `deliverables/latest/evidence/self-audit.json`
- `deliverables/latest/FROZEN_CANDIDATE.json`
- `deliverables/latest/CANDIDATE_DIGEST.txt`
- `deliverables/latest/STATUS.txt`

Digest del candidato congelado:
`991fdfbb0bbc99dbb17bdff54740fb9961190efc1ffa22ba7ee69b8861db2558`

SHA-256 del DOCX:
`5f1ff304234dc744f7ee5e360eb65b5620fbf76aec756e9d05d3ab21d7392e29`

SHA-256 del PDF:
`8aedbdb71e6bc694fe0f9c41eeade15b0990e5560e9d817aa875820079b92239`

## Estado epistemológico y límites de certificación

`first_order_validation=PASS`

`metacognitive_self_audit=PASS_WITH_ESCALATION`

`G23=NOT_EXECUTED`

`G24=NOT_EXECUTED`

`CERTIFICATION=NOT_GRANTED`

El auto-audit conserva dos asuntos no resueltos: (1) juicio humano/independiente sobre la rúbrica y (2) conflicto documental relativo a la procedencia de la pieza. La rúbrica analítica de 26,25 puntos no fue incluida en el material recibido; el perfil conserva solo el puntaje total y no inventa criterios ni ponderaciones. Por ello, el trabajo satisface las instrucciones explícitas auditables, pero no se afirma una nota máxima garantizada ni certificación académica.

## Fuente «Guía de la buena esposa»

No se encontró en los archivos accesibles un PDF original facilitado por UNIACC ni un ejemplar autenticado de BUENHOGAR de 1953. Por esa razón, no se ha incorporado al repositorio un binario rotulado engañosamente como original. En cambio, se añadió:

`sources/GUIA_DE_LA_BUENA_ESPOSA_SOURCE.md`

Esa ficha enlaza una copia pública de Académie de Poitiers y registra que la fecha impresa «Año 1953» no autentica por sí sola su procedencia. También resume la verificación de Maldita.es: la versión de once reglas circuló en la apertura de *Las Aparicio* (2010) y no se halló esa lista en los manuales de economía doméstica consultados por esa investigación. El ensayo distingue expresamente el análisis del contenido de la atribución histórica controvertida.

## Integridad del repositorio

Se creó un directorio nuevo `factory-runs/unit1-comportamiento-genero/` y un workflow específico para esta actividad. No se editaron los archivos canónicos de `document-factory/`, los trabajos preexistentes de otras unidades ni la rama `main`. Los intentos de validación que fallaron por paginación quedaron registrados en GitHub Actions; el último run pasó las compuertas fail-closed y es el único utilizado para los entregables finales.
