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


## Incidente de automatización y corrección — 2026-11-23

### Fallo inicial (run `45090536290`)
- Resultado: `failure` en `Validate profile and build with Document Factory`.
- Causa raíz: `profile.json` declaraba etapas genéricas `INGEST`, `BUILD`, `VALIDATE` y `SELF_AUDIT`, mientras `factory.py` consumía `BUILD_DOCX`, `BUILD_PPTX` y `BUILD_PDF`.
- Defecto de control: `validate_profile` validaba únicamente las etapas presentes y no exigía las claves que el constructor indexaba directamente. Por eso declaró válido un perfil incompatible.
- Responsabilidad: defecto de integración y validación introducido en la configuración del flujo; no fue un fallo espontáneo de GitHub Actions.

### Segundo defecto detectado tras el primer rerun
- El run `45090975862` terminó técnicamente en `success`, pero el artefacto descargado tenía ocho páginas.
- Causa raíz: el workflow compilaba `workspace/source/report.md`, una copia anterior, en vez de `source/report.md`, fuente canónica corregida. Además, el gate medía la distancia entre encabezados, pero no exigía `total_pages == 6`; el documento podía desbordarse en páginas adicionales y pasar.
- Se descartó ese artefacto como no conforme. Su `success` de CI no se considera validación documental suficiente.

### Remediación aplicada
1. El perfil declara explícitamente `BUILD_DOCX`, `BUILD_PPTX` y `BUILD_PDF`; `validate_profile` falla cerrado si falta cualquiera o si su definición es inválida.
2. `selftest.py` incorpora prueba positiva del perfil de Unidad 1 y prueba negativa de ausencia de `BUILD_DOCX`.
3. El workflow usa `source/report.md` como fuente canónica y ejecuta `build.py` + `verify.py` antes de congelar el candidato.
4. `verify.py` impone seis páginas exactas, mapa de contenido por página, cuatro páginas de cuerpo, tres de desarrollo, formato Arial 12/16, interlineado 1,5, márgenes de 2,5 cm, integridad de la fuente y trazabilidad de citas.
5. El workflow preserva evidencia separada del constructor y de la verificación documental.

### Verificación local reproducible de la corrección
- Document Factory selftest: 13/13 PASS.
- Perfil Unidad 1: PASS; ausencia de `BUILD_DOCX`: rechazo esperado.
- `build.py`: PASS; seis páginas; 1.242 palabras de cuerpo; rúbrica 6 criterios / 26,25 puntos; ledger 10 fuentes verificadas.
- `verify.py`: PASS; 6 páginas totales, 4 de cuerpo, 3 de desarrollo; Arial 12/16; 1,5; márgenes 2,5 cm; cobertura de reglas 1–11, «Extra» e imagen final.
- Flujo completo local (factory build → build.py → verify.py → validación → self-audit → freeze): PASS.
- G23/G24 no se ejecutaron; certificación académica no concedida; envío a Moodle pendiente.

La ejecución de GitHub Actions debe repetirse sobre este flujo corregido y verificarse antes de declarar la automatización remota conforme.


### Ajuste de portabilidad del verificador DOCX
- En el runner Ubuntu, LibreOffice produjo el estilo de sangría francesa con un identificador OOXML distinto al que expone la instalación local.
- El verificador ya no depende de un `styleId` localizado; inspecciona las propiedades OOXML y exige que exista un estilo con `w:ind/@w:hanging=720`.
- La comprobación sigue siendo estructural y no relaja el requisito APA de sangría francesa.


### Corrección de referencia de archivo en el workflow
- La ejecución `45091731863` completó la construcción y `verify.py` (seis páginas, formato y contenido PASS), pero se detuvo al copiar el DOCX por una diferencia tipográfica en el nombre del archivo (`Norabuena` frente al nombre de artefacto existente `Norambuena`).
- Se alineó la ruta de origen con el nombre que realmente produce `build.py`; no afecta el contenido del documento ni su identidad en portada.
