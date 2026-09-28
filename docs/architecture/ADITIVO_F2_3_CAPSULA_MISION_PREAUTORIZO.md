# ADITIVO F-2.3 — CÁPSULA DE MISIÓN NOCTURNA SELLABLE, ACTIVACIÓN CONTROLADA Y OPERACIONES EVIDENCIABLES

ID = SYMPHYLAX_R1_PREAUTH_MISSION_CAPSULE_F2_3_CANDIDATE
STATUS = DESIGN_PACKAGE_MATERIALIZED / STATIC_NEGATIVE_TESTS_PASS / SANDBOX_NOT_EXECUTED / G23_HOLD / G24_HOLD
PARENT = docs/architecture/PLAN_INTEGRACION_CERTIFICACION_LUNA_R4_CANDIDATE.md
PREVIOUS = docs/architecture/ADITIVO_F2_2_TRASPASO_AUDITORIA_PREAUTORIZO.md
PACKAGE = docs/architecture/SYMPHYLAX_R1_NIGHT_MISSION_PACKAGE_CANDIDATE.json
VERIFIER = scripts/governance/verify_night_mission_package_candidate.py
STATIC_CI = .github/workflows/verify-night-mission-package-static.yml
RUNTIME_DISPATCH = DISABLED
OWNER_AUTHORIZATION = NOT_RECEIVED
F3_DISK = DENIED_AND_SEPARATE

## 1. Punto exacto retomado

F-2.2 dejó como siguiente entregable un paquete verificable con fuentes exactas, dependencias, DAG de lotes, presupuesto de recursos, controles de consentimiento y posterior prueba sobre réplica aislada. F-2.3 materializa la **parte documental y estática de ese entregable** sin acceder a SYMPHYLAX, al runner self-hosted, al portátil, a PROYECTOS ni a secretos.

La investigación previa no se reinicia. Se utilizan sus referencias y se añaden controles concretos derivados de documentación oficial: NIST SSDF para disciplina de desarrollo seguro; SLSA para procedencia verificable sin reclamar un nivel no demostrado; in-toto para layouts/actores/materiales/productos y evidencia por paso; TUF para resiliencia de actualizaciones y ataques de rollback; Sigstore como patrón opcional de identidad/firmas/transparencia; Ansible para idempotencia y check/diff donde los módulos lo soportan; GitHub para la frontera de seguridad de runners autoalojados; APT Secure para autenticación de repositorios; Hugging Face para evitar cargas de pickle no confiables cuando exista alternativa segura.

Ninguna adopción externa transfiere su certificación a Luna R4. Se comparan mecanismos y se convierten en requisitos verificables locales.

## 2. Paquete de misión materializado

El JSON candidato fija por identidad Git y, cuando existe evidencia disponible, SHA-256/tamaño de:

- autoridad A0 `Louksna.md`;
- derivación A1 `LOUKSNAMEJORADA.md`;
- `PUAC2.md`;
- Skeleton R4 original;
- manifiesto CAS;
- inventario forense de SYMPHYLAX;
- dossier F-2, traspaso F-2.2 y candado inerte.

No se interpreta un branch mutable como identidad suficiente: cada entrada crítica conserva commit/blob y su rol epistémico. A1 permanece referencia derivada y PUAC2 candidato de aseguramiento, sin autoridad o G23/G24 transferidos.

La misión se divide en doce lotes L00–L11. L00 es la barrera de autorización; L01 preflight de solo lectura; L02 checkpoint/evidencia; L03 cierre de fuentes/dependencias sin instalar; L04 base de desarrollo; L05 navegador/compatibilidad universitaria; L06 integración CUSTOSZ/MetaOS/runtime; L07 aplicaciones locales; L08 KDE/UI; L09 runtime semántico; L10 regresión/rollback; L11 informe matinal. Todos salvo L00 están `NOT_EXECUTED`; todos declaran `destructive=false`.

Windows/GPT/EFI/PROYECTOS quedan excluidos por lista explícita y F3-DISK exige una segunda misión.

## 3. De una tarea a una operación certificable por alcance

Cada lote deberá recorrer una transición que no admite saltos:

`DECLARED → PINNED → SIMULATED → SANDBOX_VALIDATED → AUTHORIZED → CHECKPOINTED → EXECUTED → FUNCTIONALLY_VALIDATED → INDEPENDENTLY_VALIDATED → CERTIFIED_FOR_SCOPE → ACTIVE`.

Reglas:

1. `PINNED`: fuente, versión, commit/hash, licencia, dependencia y plataforma identificadas.
2. `SIMULATED`: plan de cambios conocido; operaciones inesperadas o borrados => HOLD.
3. `SANDBOX_VALIDATED`: misma receta ejecutada sobre una réplica suficientemente equivalente, con pruebas positivas, negativas, límite y recuperación.
4. `AUTHORIZED`: consentimiento autenticado y ligado a misión exacta; la palabra literal por sí sola no basta como primitiva técnica.
5. `CHECKPOINTED`: punto de recuperación verificable y evidencia externa al alcance que se va a mutar.
6. `EXECUTED`: operación realizada por el actor autorizado dentro del lote y presupuesto.
7. `FUNCTIONALLY_VALIDATED`: probar función, no solo exit code o paquete presente.
8. `INDEPENDENTLY_VALIDATED`: evidencia repetida/revisada por actor G23 independiente del constructor/ejecutor.
9. `CERTIFIED_FOR_SCOPE`: decisión G24 limitada a objeto, versión, host y alcance probados.
10. `ACTIVE`: solo después de postvalidación; no propaga certificación a otros lotes.

Una ausencia de evidencia mantiene el último estado demostrado; nunca se interpreta como PASS.

## 4. Activación controlada «AUTORIZO»

El objetivo humano se conserva: el servidor termina la preparación y queda esperando una autorización. Para que sea auditable, la autorización futura debe transformarse en un sobre autenticado con al menos: `mission_id`, digest del paquete, commit aprobado, identidad del principal, nonce de un solo uso de >=256 bits, emisión/caducidad, alcance y firma o enlace autenticado equivalente.

Condiciones del diseño:

- TTL máximo candidato: 15 minutos.
- Nonce de un solo uso y rechazo de replay.
- Revocación explícita antes del despacho.
- No guardar claves privadas, tokens o claves BitLocker en Git.
- Un `AUTORIZO` general jamás incluye F3-DISK.
- El primer acto posterior a un sobre válido es L01 de solo lectura. Si identidad, hashes, recursos o mounts difieren, el servidor vuelve a HOLD antes de instalar.
- El adaptador confiable de consentimiento **no está implementado ni auditado todavía**; por eso el candado vigente rechaza incluso la palabra AUTORIZO.

Esto evita que un README, comentario, push, PR, temporizador o texto malicioso se convierta accidentalmente en permiso.

## 5. Presupuesto de recursos y objetivo «una noche»

La cápsula declara un presupuesto provisional, no una garantía: una sola tarea pesada paralela; reserva de 2048 MiB para el escritorio/usuario; techo del trabajador calculado como `min(2048, MemAvailable-2048)`; HOLD si queda por debajo de 768 MiB; cuota CPU candidata 60%; HOLD si raíz tiene menos de 8 GiB libres; cero reboot desatendido.

Estos valores son **hipótesis de ingeniería** y requieren ajuste con la réplica/host. La ventana nocturna exacta continúa sin fijarse. Ninguna predicción se certificará antes de medir duración por lote y reservar margen para pruebas y rollback. Al autorizar, la ficha mostrará ventana exacta y criterio de parada para que el portátil quede disponible al comienzo de la jornada universitaria.

## 6. Resultado de prueba estática F-2.3

La workflow GitHub-hosted `SYMPHYLAX: validar paquete nocturno inerte F2.3` se ejecutó en run **36375968122** sin self-hosted runner, secretos, SYMPHYLAX, CUSTOSZ, PROYECTOS o acceso al host.

Resultado observado:

- paquete estático válido;
- 12 lotes declarados;
- 0 lotes ejecutados;
- 12 pruebas negativas del verificador pasaron;
- `execution_permitted=false`;
- `server_ready=false`;
- `G23=HOLD`, `G24=HOLD`;
- rechazo de falsa autorización, falso ready/certified, G23/G24 falsos, escalada F3-DISK, eliminación del guard FORMAT, nonce débil, lote destructivo y ciclo en DAG.

Esto prueba coherencia de la cápsula y comportamiento fail-closed de su verificador **solo como software estático**. No prueba capacidad del servidor.

## 7. Patrones externos convertidos en controles locales

- **NIST SSDF SP 800-218:** cada lote conserva procedencia, prácticas de protección, verificación y respuesta a fallos.
- **SLSA:** la procedencia será evidencia vinculada a inputs/build, pero no se reclamará SLSA L1/L2/L3 por analogía.
- **in-toto:** cada actor/paso producirá metadata de materiales/productos y se comprobará contra el layout de misión.
- **TUF:** fuentes y actualizaciones deben soportar verificación de integridad/frescura y evitar rollback o repositorio comprometido; en Debian, APT Secure sigue siendo la autoridad práctica de autenticación de repositorios.
- **Sigstore:** puede aportar identidad y transparencia para artefactos si el backend y política se aprueban; no es requisito asumido.
- **Ansible:** es candidato para expresar estado deseado e idempotencia; check mode es simulación y no todos los módulos lo soportan, por lo que no sustituye la réplica real.
- **GitHub Actions:** CI estática permanece en runner hospedado. GitHub advierte que self-hosted no es una VM efímera/limpia garantizada; por ello el runner conectado al entorno del usuario no se usa como sandbox de código no confiable.
- **Hugging Face:** para modelos externos, preferir formatos seguros y tratar pickle como potencial ejecución de código; artefacto de modelo nunca adquiere autoridad arquitectónica por ser descargado.

## 8. Qué falta para poder decir «servidor listo esperando AUTORIZO»

No se cambia el significado de READY para satisfacer una fecha. Faltan:

1. construir y revisar el adaptador de consentimiento autenticado;
2. crear una réplica aislada suficientemente equivalente y autorizada;
3. ejecutar T01–T20 y los doce lotes aplicables en modo sandbox, midiendo tiempo/recursos/rollback;
4. fijar fuentes/versiones definitivas de cada dependencia de R4;
5. revisión independiente G23 del diseño, scripts, resultados y amenazas;
6. decisión G24 sobre el alcance no destructivo;
7. sellar una versión final del paquete con digest y commit exactos.

Solo entonces puede cambiarse `server_ready_waiting_for_authorizo=true`. Aun así, la primera operación después del consentimiento será preflight y cualquier deriva devuelve HOLD. F3-DISK seguirá fuera.

## 9. Estado terminal F-2.3

`RESEARCH_COMPLETE=EVIDENCED`
`DESIGN_PACKAGE_MATERIALIZED=TRUE`
`STATIC_PACKAGE_NEGATIVE_TESTS=12_PASS`
`SANDBOX_VALIDATED=FALSE`
`AUTHENTICATED_CONSENT_ADAPTER=ABSENT_OR_UNVERIFIED`
`G23=HOLD`
`G24=HOLD`
`SERVER_READY_WAITING_FOR_AUTORIZO=FALSE`
`USER_AUTHORIZED=FALSE`
`EXECUTION_PERMITTED=FALSE`
`F3_DISK=DENIED`

F-2.3 fortalece el plan sin convertir investigación o CI en una certificación prestada.
