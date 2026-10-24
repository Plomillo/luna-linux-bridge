# Calibre Slim — integración en Cajita de Luna

**Dominio:** D05 — Inteligencia documental  
**Estado:** binario incorporado físicamente en el árbol de runtime; candidato todavía no certificado.  
**Versión base:** Calibre oficial v9.17.0.

## Ruta interna

Directorio: `cajita-luna-runtime/5. Inteligencia documental/Conversión documental/Calibre Slim/`

- Lanzador con validación de alcance: `calibre-slim-convert.py`
- Perfil: `profile.json`
- Fijación de procedencia: `source-lock.json`
- Referencia verificable del artefacto: `ARTIFACT_REFERENCE.json`
- Destino previsto del binario: `calibre-slim-overlay.tar.xz`
- Tras extraer el overlay, se espera `source/calibre/customize/builtins.py`.

## Alcance público

Se admiten entradas PDF, EPUB y TXT; las salidas públicas se limitan a PDF y EPUB. Las cuatro conversiones requeridas son PDF→EPUB, EPUB→PDF, TXT→PDF y TXT→EPUB. HTML se rechaza como entrada pública, aunque Calibre lo conserva como dependencia interna de la conversión TXT. OCR, paquetes de idiomas, interfaz gráfica, catálogos, tiendas, gestión de dispositivos y otros formatos quedan fuera de alcance.

## Límite de tamaño y dependencia externa

El artefacto del overlay pesa **58.180 bytes (0,05818 MB decimal)** y su SHA-256 esperado es `dc1518eccd24d0bb6a294918381d9d42fa24df8b05026d1f173dadbd6e70977b`. La referencia apunta al artefacto de CI identificado en `ARTIFACT_REFERENCE.json`.

**El archivo ya está físicamente en esta carpeta de runtime.** El lanzador verifica tamaño y SHA-256, extrae el overlay de forma segura la primera vez y falla cerrado ante discrepancias. Una vez materializado, se requiere además el runtime oficial de Calibre v9.17.0 para Linux x86-64 y sus dependencias Qt/WebEngine, fuera del overlay. No se afirma que Calibre completo quepa en 16 MB.

## Evidencia y puerta pendiente

CI: ejecución `40057448243`, resultado `success`, con 6/6 canaries del overlay ejecutadas con un runtime oficial externo. Esa evidencia valida el artefacto ensayado en CI, no prueba todavía la materialización en Cajita, la reconstrucción `.macrodown`, la validación independiente ni la certificación. La siguiente puerta exige copiar el archivo exacto a la ruta prevista, verificar tamaño/hash, regenerar el manifiesto y el paquete, y repetir las conversiones desde la ruta interna.
