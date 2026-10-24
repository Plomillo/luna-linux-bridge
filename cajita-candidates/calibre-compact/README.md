# Cajita · Calibre Compact Candidate V1

Estado: **CANDIDATO EXPERIMENTAL; NO CERTIFICADO**.

Este candidato conserva el motor oficial de conversión de Calibre y construye un paquete Linux x86-64 reducido, orientado exclusivamente a generar PDF/EPUB y convertir documentos hacia esos dos formatos. La interfaz pública es una envoltura CLI propia; el motor sigue siendo `ebook-convert` del upstream.

## Funciones admitidas

- PDF → EPUB.
- EPUB → PDF.
- Creación de EPUB desde HTML, TXT/Markdown, DOCX, ODT o RTF.
- Creación de PDF desde EPUB, HTML, TXT/Markdown, DOCX, ODT o RTF.
- Entradas adicionales PDF y EPUB para las conversiones bidireccionales.
- Hash SHA-256, tamaño, versión del motor y resultado de cada operación en un registro JSONL append-only.
- Salida temporal validada antes de reemplazar el destino; fallo de conversión o evidencia impide declarar éxito.

## Poda

La distribución deja fuera la GUI de biblioteca, visor y editor, el servidor de contenido, la descarga de noticias y recetas, los comandos de dispositivos, el generador/descargador de metadatos, manuales, iconografía de interfaz, complementos de conversión ajenos a la lista de formatos admitidos, traducciones no inglesas/españolas y la infraestructura de texto a voz (Piper/espeak).

Se retienen expresamente el trabajador `calibre-parallel`, el motor de conversión, el recurso interno `resources/default_tweaks.py`, el mapa MIME, Qt WebEngine y sus dependencias de renderizado. La ejecución de pruebas detectó que eliminar el trabajador o el recurso de ajustes rompe el motor; ambos están protegidos por comprobaciones del constructor.

No se borra código fuente solo por parecer innecesario. El código Python empaquetado en el runtime congelado se conserva en esta versión para evitar una reconstrucción invasiva del upstream. Este candidato poda funciones y recursos de distribución; **no afirma haber eliminado todos los bugs de Calibre**. Un arreglo upstream solo se añadirá tras un fallo reproducible y una prueba de regresión.

## Procedencia y plataforma

Calibre 9.17.0 oficial Linux x86-64:
https://download.calibre-ebook.com/9.17.0/calibre-9.17.0-x86_64.txz

El constructor obtiene y comprueba el SHA-512 publicado por el proyecto antes de extraer o podar. Conserva las licencias y la procedencia del paquete. La prueba de PDF necesita al menos `libegl1` y `libgl1` del sistema; por tanto, este paquete aún no se considera un runtime Linux totalmente autónomo.

## Tamaño y empaquetado

El paquete final se distribuye como un único `.tar.xz` comprimido. Cajita debe registrar ese archivo como un solo payload y extraerlo en disco bajo demanda; no debe distribuir a la vez el archivo comprimido y la copia expandida. El tamaño expandido se registra aparte como requisito de espacio temporal/disco, no se confunde con el tamaño del artefacto comprimido.

La inclusión en Macrodown no es automática: el gate final debe sumar el tamaño exacto del paquete comprimido y sus metadatos al resto del payload de Cajita y volver a validar el límite global de 470.000.000 bytes. El artefacto de prueba por sí solo no concede certificación.

## Pruebas

El workflow comprueba el SHA-512 upstream, compila y ejecuta pruebas de política, pruna el paquete, y realiza conversiones reales HTML→EPUB, HTML→PDF, EPUB→PDF y PDF→EPUB. Comprueba el contenedor EPUB, la salida PDF y la conservación de texto y acentos en el fixture español. También comprueba que se rechace una salida no permitida como MOBI.

La prueba sintética es un gate inicial, no una evaluación de calidad en libros reales. Los PDF escaneados, de varias columnas, tablas complejas y documentos con fuentes incrustadas requieren un corpus de aceptación independiente.
