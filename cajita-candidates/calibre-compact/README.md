# Cajita · Calibre Compact Candidate V1

Estado: **CANDIDATO EXPERIMENTAL; NO CERTIFICADO**.

Este candidato conserva el motor oficial de conversión de Calibre y construye una distribución Linux x86-64 restringida a generar PDF y EPUB, con entradas PDF, EPUB, HTML, TXT/Markdown, DOCX, ODT y RTF. La interfaz pública es una envoltura CLI propia; el motor sigue siendo ebook-convert del upstream.

## Objetivo

- PDF → EPUB.
- EPUB → PDF.
- Crear EPUB desde HTML, TXT/Markdown, DOCX, ODT o RTF.
- Crear PDF desde EPUB, HTML, TXT/Markdown, DOCX, ODT o RTF.
- Mantener la conversión PDF/EPUB de Calibre, sus dependencias nativas y sus recursos de renderizado necesarios.
- Eliminar recursos no necesarios para este ámbito: colecciones de recetas/noticias, manuales y ayudas de GUI, recursos de servidor y editor, localizaciones distintas de inglés/español, iconografía de interfaz y módulos de conversión de formatos ajenos a la lista blanca.
- Auditar el hash/tamaño de entrada y salida, el estado de la conversión y la versión del motor.
- Detener la construcción si falla cualquiera de las pruebas positivas, las validaciones de archivo o la política de formatos.

## Procedencia

Se fija Calibre 9.17.0, descarga oficial Linux x86-64: https://download.calibre-ebook.com/9.17.0/calibre-9.17.0-x86_64.txz. El constructor verifica SHA-512 contra el fichero lateral publicado en https://calibre-ebook.com/signatures/ antes de extraer o podar.

La copia de Calibre continúa sujeta a GPL-3.0 y conserva los ficheros de licencia/procedencia presentes en el paquete oficial. Este candidato no sustituye ni modifica la autoridad de Louksna; es infraestructura técnica subordinada.

## Poda y límites

La poda es una operación de empaquetado sobre una copia temporal aislada, no sobre el sistema del usuario. El script registra cada archivo eliminado (ruta relativa, tamaño, SHA-256 y regla de poda). Conserva los archivos de licencia y no elimina código de conversión fuera de la lista explícita. La lista blanca actual conserva entradas PDF, EPUB, HTML, TXT/Markdown, DOCX, ODT y RTF, salidas PDF/EPUB y el formato OEB interno.

No se eliminan indiscriminadamente fuentes tipográficas, datos Unicode, MIME, componentes Qt/WebEngine, bibliotecas nativas ni recursos que puedan ser necesarios para renderizar libros. Se conservan el paquete de idioma inglés de Qt WebEngine y los recursos españoles si el paquete los incluye.

## Pruebas exigidas

1. ebook-convert --version.
2. HTML → EPUB; EPUB → PDF; PDF → EPUB; HTML → PDF.
3. Integridad ZIP/OCF de EPUB, mimetype como primera entrada sin compresión y existencia de META-INF/container.xml.
4. Cabecera %PDF- en el PDF y extracción de texto para comprobar contenido español.
5. Rechazo de extensiones de entrada/salida fuera de la lista blanca.
6. Inspección de tamaño bruto, tamaño comprimido, hashes y archivos retirados.
7. Captura de evidencia reproducible como artefacto de GitHub Actions.

## Qué no se proclama

- No se proclama equivalencia funcional con toda la distribución oficial de Calibre.
- No se proclama que se hayan encontrado o reparado todos los errores del upstream. No se incorporan parches especulativos sin un fallo reproducible y una prueba de regresión.
- No se proclama compatibilidad con Windows o Android: esta construcción se dirige a Linux x86-64.
- No se declara aprobado para incluirse en Macrodown hasta medir el candidato real, verificar calidad funcional e integrar el tamaño global sin romper el límite duro de Cajita.
- La prueba de humo cubre fixtures sintéticos; la calidad de PDF reales complejos y escaneados necesita un corpus de aceptación separado.

## Ejecución

El workflow Calibre Compact Candidate descarga, verifica, extrae, poda, ejecuta las pruebas y publica el paquete y un JSON de evidencia. El ZIP/artefacto no se incorpora automáticamente a cajita-luna-runtime; primero hay que evaluar su tamaño final y su calidad contra el presupuesto global.
