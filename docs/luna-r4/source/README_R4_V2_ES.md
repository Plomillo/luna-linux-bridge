# LOUKSNA — R4 diferencial V2: ejecución real desde Konsole

ESTADO ACTUAL: PRECOMMIT ACOTADO SUPERADO; paquetes y R4 aún NO instalados. El primer lanzador R4_DIFFERENTIAL_DEPLOY.sh no debe utilizarse: contenía el defecto '--no-download' con archivos .deb locales, diagnosticado mediante simulación APT código 100. Los cuatro auxiliares V2 y el nuevo lanzador se crearon en archivos nuevos; ambos juegos de hashes (M3 original y delta V2) y las pruebas de sintaxis han pasado. 19 paquetes nuevos, cero actualizaciones, cero retiradas en simulación combinada; 3 corresponden a Chromium y 16 a Java/CMake/Ninja y dependencias. El análisis de los paquetes descargados vincula índices Debian firmados con SHA256 y versión exacta de cada .deb.

## Instrucción única de instalación

1. Abre **Konsole dentro de tu sesión habitual de KDE Plasma**. No ejecutes como root ni cierres otras aplicaciones a la fuerza.
2. Copia y pega exactamente este comando (una línea):

```bash
bash "$HOME/LOUKSNA_MAESTRO_20260925/MISSION3_OPERATIVE/R4_DIFFERENTIAL_DEPLOY_V2.sh"
```

3. El lanzador verifica integridad de los 17 archivos de M3 y de los 5 archivos nuevos de V2, después comprueba hashes de las fuentes, que PROYECTOS siga montado solo lectura y que el enlace de tu carpeta personal apunte al original. Exige terminal local y sesión gráfica. Si alguna comprobación falla, no se ejecutan cambios.
4. El instalador llama a sudo cuando se requiere permiso de administrador. En el indicador `[sudo] contraseña para diegoignacionorambuenamiranda:` introduce **tu contraseña de inicio de sesión de Debian** y pulsa Enter. Cuando escribas, NO verás caracteres, asteriscos ni puntos. Esto es normal. Nunca entregues la contraseña a ChatGPT, a Codex, al plugin Remote Desktop Commander ni a ningún archivo de registro. El instalador no la lee ni la guarda.
5. Instala solo las dependencias de desarrollo ausentes desde los archivos .deb ya congelados y cotejados con los índices Debian; en una segunda fase descarga únicamente los tres paquetes Chromium seleccionados de fuentes oficiales, vuelve a comprobar firma e índices y aplica la instalación. Ningún paquete existente se reinstala por rutina y el instalador usa `--no-remove` para impedir retiradas inesperadas.
6. Después verifica versiones, integridad dpkg y comandos funcionales; activa el esquema nativo Luna R4, accesos de proyectos y navegador predeterminado en tu cuenta KDE, guardando una copia íntegra de los archivos de configuración que modifica. Lanza Chromium con `chrome://sandbox` y el sitio de ChatGPT para que puedas comprobar visualmente el sandbox y la autenticación. No entregues credenciales a terceros.
7. **Firefox no se elimina en este lanzamiento**: antes es obligatorio comprobar Chromium en sesión gráfica, el sandbox activo, el navegador predeterminado y que ChatGPT funciona; después se realizará una operación independiente y auditada que purgará solo los paquetes Firefox realmente instalados tras comprobar su simulación y preservará `~/.mozilla` hasta una autorización separada. R4 gráfica completa y panel nativo siguen sujetos a su evaluación visual.
8. Si se produce un error, **no repitas ciegamente** el instalador. Localiza el directorio más reciente en `MISSION3_OPERATIVE/live_runs/`. Dentro hay `apt_update.log`, `apt_install.log` y recibos de instalación o activación. Una instalación parcial debe evaluarse antes de retomar; ninguna prueba fallida puede convertirse en PASS por continuar una segunda vez. En caso de conflicto de la configuración gráfica, la copia exacta de los archivos de usuario y el mecanismo de rollback están en el subdirectorio `browser/user_backup` de la ejecución.
9. Este lanzador NO toca el volumen NTFS que contiene PROYECTOS, NO elimina Windows, NO cambia particiones/EFI, NO purga Firefox automáticamente y **NO reinicia**. R4 nativo parcial NO equivale a certificación de todo el entorno. G23/G24 de retirada de Windows permanecen pendientes hasta su evidencia real.

Puntos de control independientes registrados antes de sudo: `R4_V2_PRECOMMIT_RESULT.json`, `M3_BROWSER_DOWNLOAD_20260926T012845Z/closure/APT_CLOSURE.json`, `dev_verified/R4_DEV_CLOSURE.json`, `DELIVERABLES_M3.sha256` y `R4_V2_DELTA.sha256`. Los metadatos RAW de los tres enlaces OpenGL ya están recuperados y su relectura independiente pasó en `M3_CHECKPOINT_OPENGL/REPARSE_TARGETS_RECOVERED.json`.

**REINICIO:** solo Diego decidirá después de que Windows y sus restos se hayan retirado realmente, PROYECTOS conserve sus propiedades exigidas, R4 esté operativo y G23/G24 generales estén completos. Ningún script de este lote lo ejecutará.
