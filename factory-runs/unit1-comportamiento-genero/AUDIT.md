# Auditoría actualizada — Unidad 1: Comportamiento y género

- Fecha de revisión: 2026-11-22
- Repositorio: `Plomillo/luna-linux-bridge`
- Rama objetivo: `candidate/document-factory-v1-unit2-20261013`
- Fuente normativa: actividad autenticada de Moodle y rúbrica completa, seis criterios / 26,25 puntos.
- Fuente de caso: adjunto exacto de la actividad, 14 páginas; SHA-256 verificado.

## Correcciones respecto del candidato previo
1. Se sustituyó la estructura de ocho páginas por el formato solicitado: seis páginas totales (portada, cuatro páginas de cuerpo y referencias), con tres páginas de desarrollo.
2. Se incorporó la rúbrica analítica completa que sí estaba disponible en la sesión autenticada de Moodle; la evaluación ya no se basa únicamente en el total de 26,25 puntos.
3. Se agregó el nombre del estudiante conocido a la portada y se mantuvieron editables los datos docentes no verificados.
4. Se agregó a referencias la entrada completa de Moscovici (1991), citada en el cuerpo, con páginas 17–37; se alineó el registro de fuente.
5. Se conservó el PDF exacto descargado de Moodle, con hash verificado, y se eliminó la afirmación anterior de que no se había recuperado el adjunto.
6. Se actualizó la nota de procedencia: la pieza es el adjunto oficial de la tarea y su contenido se analiza; su atribución editorial histórica a BUENHOGAR no se presenta como autenticada más allá de lo indicado por la consigna.

## Validación reproducible
- `build.py`: PASS; DOCX y PDF generados.
- `verify.py`: PASS; seis páginas, cuatro páginas de cuerpo, tres páginas de desarrollo, Arial 12/16, interlineado 1,5, márgenes 2,5 cm, rúbrica 26,25 y trazabilidad de citas.
- Document Factory selftest: 12/12 PASS.
- Rubric compiler selftest: PASS.
- El PDF final es de seis páginas A4.

## Límites de certificación
- R1 (entrega a tiempo): pendiente de envío en Moodle.
- R3–R6: alineación y cobertura documentadas; la calificación sustantiva corresponde al docente.
- G23/G24: no ejecutados.
- `CERTIFICATION=NOT_GRANTED`; no se afirma nota máxima garantizada.

El `AUDIT.md` previo y los metadatos de congelación del candidato de ocho páginas se conservan en `history/prior-candidate-8-page-20261122/` como registro histórico supersedido, no como estado vigente.
