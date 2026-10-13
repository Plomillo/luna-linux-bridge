# Kestra Open Source — integración candidata para Hydra/Louksna

**Estado:** CANDIDATE_NOT_CERTIFIED  
**Rama de trabajo:** custosz/super-1200-implementation-20261007  
**Autoridad:** Louksna.md · **Doctrina:** EXTEND_DO_NOT_REPLACE · **Política:** append-only / fail-closed

## Qué se añade

Una instalación autoalojada de Kestra Open Source declarada mediante Docker Compose y con credenciales locales. Se usa la imagen completa de Kestra, no la variante slim/no-plugins. Un contenedor de inicialización de un solo uso ajusta los permisos de su volumen; es la única fase que usa UID 0, con solo la capacidad CHOWN, sin red y sin socket Docker. El servidor Kestra de larga duración conserva su usuario no privilegiado.

- Kestra: kestra/kestra:v2.0.3
- PostgreSQL: postgres:18.6-alpine
- UI local: http://127.0.0.1:8080
- Health/management local: http://127.0.0.1:18081/health (authentication required)

### Nota de versión y procedencia

La página oficial de releases del repositorio fuente muestra v2.0.5 publicada el 5 de octubre de 2026. En la revisión del catálogo oficial de Docker Hub se observó la imagen completa con tag exacto v2.0.3; no se pudo establecer con evidencia suficiente que el artefacto de contenedor v2.0.5 estuviera disponible. Por criterio fail-closed, esta incorporación utiliza un tag exacto de imagen observado, en vez de adivinar o usar latest. La actualización a 2.0.5 queda bloqueada hasta verificar el tag de contenedor y su digest.

Fuentes oficiales:
- https://github.com/kestra-io/kestra/releases
- https://github.com/kestra-io/kestra/releases/tag/v2.0.5
- https://hub.docker.com/r/kestra/kestra/tags
- https://kestra.io/docs/oss-vs-paid
- https://kestra.io/docs/installation/docker-compose
- https://kestra.io/docs/scripts/task-runners
- https://kestra.io/docs/administrator-guide/monitoring

## Arranque local

Requisitos: Docker Engine y Docker Compose v2. Ejecuta los comandos desde la raíz clonada del repositorio.

1. Crea credenciales locales sin imprimirlas. En Linux/macOS, desde la raíz del repositorio:

       cd integrations/kestra
       python3 - <<'PY'
       from pathlib import Path
       from secrets import token_hex
       path = Path(".env")
       if path.exists():
           raise SystemExit(".env ya existe; no se sobrescribe.")
       path.write_text(
           "KESTRA_DB_PASSWORD=" + token_hex(32) + "\n"
           "KESTRA_ADMIN_EMAIL=admin@example.com\n"
           "KESTRA_ADMIN_PASSWORD=" + "Kestra-" + token_hex(30) + "A9!" + "\n",
           encoding="utf-8",
       )
       print(".env creado con credenciales aleatorias locales; no se muestran.")
       PY

2. Valida y descarga las imágenes exactas:

       python3 validate.py
       docker compose -f compose.yml config --quiet
       docker compose -f compose.yml pull

3. Inicia y verifica:

       docker compose -f compose.yml up -d --wait --wait-timeout 300
       set -a; . ./.env; set +a
       curl --config <(printf 'user = "%s:%s"' "$KESTRA_ADMIN_EMAIL" "$KESTRA_ADMIN_PASSWORD") --fail --show-error http://127.0.0.1:18081/health

4. Abre http://127.0.0.1:8080 e inicia sesión con las credenciales generadas en .env. El archivo .env está ignorado por Git. No pegues ni subas sus contenidos a issues, PRs, logs o chats.

5. Para detener Kestra conservando los datos:

       docker compose -f compose.yml down

La eliminación de volúmenes borra estado y datos persistentes. No uses docker compose down --volumes como acción rutinaria.

## Prueba funcional automatizada

El workflow `.github/workflows/kestra-oss-smoke.yml` importa `flows/00-smoke-test.yml` mediante la API autenticada de Kestra, ejecuta el flujo y exige que la ejecución llegue al estado terminal `SUCCESS`. El flujo solo emite un mensaje de log y no realiza efectos externos. La ejecución funcional fue verificada en el run `38369065971`; sus evidencias están en el artefacto `kestra-oss-smoke-38369065971`. Cada prueba utiliza una instancia efímera y destruye los contenedores y volúmenes al finalizar. Esto no mantiene Kestra encendido ni equivale a certificar el motor, validar de forma independiente G23 o conceder G24.

La prueba automatizada valida el flujo de humo en CI. Una prueba manual de interacción por la interfaz de Kestra sigue siendo distinta y no está registrada como realizada.

## Límites de seguridad deliberados

- Los puertos UI y management están ligados a loopback. El endpoint de management usa `endpoints.all.basic-auth` y requiere credenciales; el mapeo a 127.0.0.1:18081 no debe cambiarse a 0.0.0.0.
- No se monta /var/run/docker.sock del anfitrión. No se conceden tokens de GitHub, secretos de producción ni conexión automática al repositorio.
- No hay sincronización GitOps ni importación automática de flujos en un despliegue persistente. La única importación automatizada autorizada en esta fase es el flujo de humo log-only dentro del CI efímero. No hay autorreparación, commit, push, merge ni promoción a main desde Kestra.
- Los scripts con el runner Process se ejecutan como procesos locales con los permisos y el entorno del worker; no tienen aislamiento de contenedor. Por eso el validador bloquea flujos de scripting en esta fase. La ejecución de código confiable en un runner dedicado y aislado es una siguiente fase, no una garantía de esta instalación.
- Docker Compose configura persistencia para Kestra y PostgreSQL. Esto no constituye backup probado ni recuperación ante desastre.
- Las credenciales de .env se protegen frente a commit accidental, pero no frente a otros usuarios o procesos con acceso al anfitrión.
- El CI inicia una instancia efímera en GitHub Actions, registra sus imágenes resueltas y su salud, y la destruye al finalizar. Eso valida un arranque de prueba; no instala un servicio permanente en GitHub ni en tu equipo.

## Evidencia y puertas

El workflow `.github/workflows/kestra-oss-smoke.yml` valida la configuración, arranca Kestra/PostgreSQL, comprueba salud autenticada, importa y ejecuta el flujo log-only, conserva evidencias no secretas y destruye el entorno temporal. La última comprobación funcional registrada es el run `38369065971`; el artefacto `11798671287` contiene las evidencias y está retenido hasta el 12 de noviembre de 2026. Las credenciales de CI son aleatorias, efímeras y no se incluyen en el artefacto.

El workflow de Kestra se ejecuta automáticamente ante cambios relevantes en esta rama; no está configurado como servicio permanente ni como ejecución nocturna. GitHub Actions solo admite eventos programados desde la rama predeterminada, por lo que no se ha añadido un `schedule` que aparentaría funcionar desde esta rama candidata. `main` no se ha modificado.

La prueba de humo no habilita ejecución arbitraria de scripts, no implica validación independiente G23 ni certificación G24. La integración sigue `CANDIDATE_NOT_CERTIFIED`; activación y promoción continúan prohibidas hasta que se cumplan y autoricen las puertas correspondientes.

## Rollback

La configuración se añade como un conjunto aislado de archivos; no sustituye los componentes existentes ni modifica Louksna.md, PUAC2.md o los ejecutores actuales. Si la incorporación debe retirarse, revierte el commit específico de integración en esta misma rama después de revisar el diff. Los datos persistentes se administran por separado y deben preservarse o destruirse mediante una decisión explícita.
