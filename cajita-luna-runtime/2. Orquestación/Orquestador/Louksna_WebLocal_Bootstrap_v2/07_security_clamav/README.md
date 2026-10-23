# ClamAV 1.5.4 — seguridad local Linux

Componente de seguridad para la futura integración con Louksna/Cajita.

## Perfil seleccionado
- Plataforma: Linux x86_64.
- Versión: ClamAV 1.5.4.

## Paquetes oficiales
- RPM x86_64: clamav-1.5.4.linux.x86_64.rpm — 43.2 MB publicados.
- DEB x86_64: clamav-1.5.4.linux.x86_64.deb — 101.0 MB publicados.
- Fuente: clamav-1.5.4.tar.gz — 60.8 MB publicados.

Fuente oficial: https://www.clamav.net/downloads
Release oficial: https://github.com/Cisco-Talos/clamav/releases/tag/clamav-1.5.4

## Flujo previsto
1. Descargar el paquete Linux apropiado.
2. Verificar integridad/autenticidad antes de instalar.
3. Instalar ClamAV.
4. Actualizar firmas con `freshclam`.
5. Escanear descargas en cuarentena con `clamscan` o `clamdscan`.
6. Integrar el resultado en la política de liberación de Louksna.

Este bootstrap no contiene credenciales, cookies, sesiones ni secretos.
