# F-2.2 — TRASPASO A REVISIÓN INDEPENDIENTE Y CRITERIO REAL DE ESPERA POR «AUTORIZO»

IDENTIDAD = SYMPHYLAX_R1_PREAUTHORIZATION_HANDOFF_F2_2_CANDIDATE
ESTADO = DOCUMENTARY_HANDOFF_PREPARED / RUNTIME_NOT_READY / G23_HOLD / G24_HOLD
AUTORIDAD = Louksna.md
DERIVACIÓN = LOUKSNAMEJORADA.md (consulta, no autoridad nueva)
ORQUESTADOR_DE_MISIÓN = SYMPHYLAX_R1
TRABAJADOR_PRINCIPAL = CUSTOSZ_V7
EJECUCIÓN_Y_RECUPERACIÓN = CUSTOSZ_RUNTIME_V1
GOBERNADOR_OPERACIONAL = MetaOS
ASISTENTE_ESCRITORIO = AUXILIAR_ONLY
FUENTE_NORMATIVA_LOCAL = docs/architecture/PLAN_INTEGRACION_CERTIFICACION_LUNA_R4_CANDIDATE.md
FUENTE_DE_PRUEBAS = docs/architecture/ADITIVO_F2_EVIDENCIA_COMPARADA_Y_PRUEBAS.md
CANDADO_INERTE = docs/architecture/SYMPHYLAX_R1_NIGHT_MISSION_LOCK_CANDIDATE.json
LIMITACIÓN = No es dictamen de validador independiente, credencial, autorización ni instalador.

## 1. Punto exacto de continuación

Ya existe estudio comparado F-2 con referencias NIST SSDF, SLSA v1.2, in-toto, Fedora/openQA, Ansible/Molecule, Google SRE, Debian, restic, Microsoft, Hugging Face y GitHub Actions. El contrato contiene 20 familias T01–T20 **especificadas, no ejecutadas**. Una prueba GitHub-hosted sin acceso al portátil (run 36370225725) confirmó 11 casos negativos del **validador estático**; no ensayó la integración real de SYMPHYLAX/CUSTOSZ/MetaOS ni el mecanismo de consentimiento.

Por consiguiente, la siguiente actividad correcta es **revisión externa del paquete de diseño y preparación verificable de una réplica aislada**, no lanzar una ejecución local ni declarar que el servidor está certificado. Se evita repetir las búsquedas ya documentadas o reiniciar R4.

## 2. Explicación operacional de qué significa «listo»

Separar cinco hitos. El dossier de investigación no certifica los otros cuatro:

| Estado | Condición verificable | Hoy |
|---|---|---|
| RESEARCH_COMPLETE | Fuentes oficiales contrastadas, límites y patrones profesionales enlazados con requisitos medibles | EVIDENCED en F-2; revisión externa pendiente |
| DESIGN_REVIEWABLE | Código de bloqueo revisable, contrato de misión, grafo de dependencias, políticas y criterios de prueba | PARTIAL; faltan puente de consentimiento, lotes y matriz completa |
| SANDBOX_VALIDATED | VM Debian/KDE autorizada, convergencia, pruebas negativas, fallo/rollback, UI y consumo medidos; evidencia reproducible | NOT_EXECUTED |
| HOST_SCOPE_VALIDATED | Preflight real de solo lectura y ensayos reversibles expresamente autorizados; independencia y pruebas G23 específicas | NOT_EXECUTED / G23 HOLD |
| APPROVED_FOR_NONDESTRUCTIVE_MISSION | Dictamen G24 competente por alcance, consentimiento autenticado que vincula hash/commit, ventana, lotes y presupuesto; todos los hard gates PASS | NOT_GRANTED / AUTORIZO NOT_RECEIVED |

«Esperando AUTORIZO» en su sentido operacional exige, como mínimo, diseño de autorización auditado y revisado, ensayos de réplica completos, lotes congelados y política ejecutable que garantice que un evento GitHub o una cadena de texto no puedan instalar nada por sí solos. Si un gate necesita pruebas vivas, deben autorizarse de forma diferenciada antes de presentar la misión nocturna como preparada. Hasta entonces: `PREPARATION_INERT`, no `SERVER_READY`.

## 3. Paquete reproducible exigible a SYMPHYLAX antes de solicitar una misión

Crear, sin tocar el host, un `R4_NIGHT_PREPARATION_BUNDLE` con estos documentos revisables y con hash:

1. **Identidades de fuente:** A0 `Louksna.md`, A1 `LOUKSNAMEJORADA.md`, PUAC2, Skeleton R4, versión de CUSTOSZ, runtime, MetaOS y SYMPHYLAX. Registrar hashes y commits **medidos**; inexistente se representa `UNKNOWN`. Conservación byte-exacta de A0, DOC0001–DOC0022 y estado declarado de las discrepancias axiomatizadas.
2. **Matriz requisito→operación:** una fila por requisito del Skeleton; versión presente, versión propuesta, dependencias y licencia, fuentes oficiales, coste máximo RAM/CPU/disco, prueba de instalación, prueba funcional GUI, plan de reversión, necesidad de privilegios y dependencias del contenedor.
3. **DAG de lotes independientes:** barrera global de escritura, un solo lote mutable por dominio, máximo presupuesto por lote, preflight y punto de restauración realmente comprobable, evidencias almacenadas fuera del alcance de rollback.
4. **Amenazas y controles:** instrucciones maliciosas en repositorios o modelos, contaminación de runner self-hosted, fuentes sin hash, secretos, importación accidental de código remoto de Hugging Face, downgrade silencioso, dependencia cruzada, falsa identidad, replay de autorización y permisos excesivos.
5. **Pruebas reproducibles en réplica:** scripts versionados que no dependan de credenciales ni del disco real, fixtures redacted, IDs T01–T20, resultados reales con ambiente, logs y hashes. Para GUI exigir evidencias visuales de KDE y aplicaciones, no solo que un paquete esté instalado.
6. **Contrato de consentimiento real:** identidad del propietario autenticada por canal de confianza, `mission_id`, hash inmutable de la ficha, commit exacto, lista allowlist, lista denylist, nonce único, vencimiento, revocación, custodia de evidencia y registro de auditoría. Un `AUTORIZO` sin esa vinculación no inicia nada.
7. **Calendario de una noche:** duración observada por lote en la réplica comparable, reserva de tiempo para pruebas/rollback, `deadline` anterior a actividades académicas, política de batería/red/temperatura y presupuesto de CPU/RAM. Duración no medida = NO_CERTIFICABLE.
8. **Prohibiciones expresas:** no borrar Windows, no modificar GPT/EFI, no migrar/formatear PROYECTOS, no reiniciar desatendidamente, no ampliar dominio, no compartir llaves de BitLocker ni secretos en GitHub.

Toda evidencia requiere `evidence_id`, `source_hash`, `actor`, `environment`, `timestamp`, `method`, `result`, `test_id`, `log_hash`, `reviewer` y `rollback_reference`. Ningún campo se declara PASS por ausencia de datos.

## 4. Trabajo del validador independiente G23 y de la autoridad G24

**G23 no puede ser CUSTOSZ, SYMPHYLAX ni el mismo agente que escribió el validador.** Debe revisar al menos: autenticación y replay, integridad de commit/manifiesto, procedencia de paquetes/modelos, aislamiento real del runner, privilegios, inyección de dependencias, denegación de operaciones de disco y recuperación desde fallo. Ejecutar pruebas independientes, conservar salidas originales y emitir un dictamen limitado al alcance efectivamente probado; ausencias => HOLD.

**G24** recibe la documentación G23, revisa competencias, alcance, riesgos residuales y conformidad de las autorizaciones. No puede convertir un PASS estático en autorización para instalar, ni transferir la evaluación no destructiva a una operación de disco.

La referencia SLSA v1.2 documenta pruebas de procedencia y separación entre tracks Source y Build, pero un hash o el uso de GitHub Actions **no acredita ningún nivel** de SLSA (https://slsa.dev/spec/v1.2/). GitHub advierte que los runners autoalojados no garantizan aislamiento efímero; por ello ningún workflow de PR ejecuta código no confiable en el portátil (https://docs.github.com/en/actions/reference/security/secure-use). Para GUI se adopta la idea de openQA sobre VM como prueba reproducible, no una certificación por analogía (https://fedoraproject.org/wiki/OpenQA).

## 5. Separación del expediente F3-DISK

Retirar Windows 11 NO forma parte del permiso nocturno no destructivo. Antes de cualquier intervención futura: identificar por UUID y mapa real dónde están `C:\PROYECTOS`, Debian y EFI; comprobar BitLocker si aplica sin exponer claves; conseguir dos respaldos independientes fuera del dispositivo intervenido y una restauración utilizable ensayada; plan reversible o recuperación física comprobada; competencia del servidor en réplica equivalente; G23/G24 específicos; consentimiento humano H2/H4 separado con mapa de particiones revisado. Si PROYECTOS comparte la partición de Windows, hay que migrarlo y verificarlo antes de borrar dicha partición. Ningún script de este expediente debe ejecutar operaciones de particionado.

## 6. Estado formal para la próxima conversación o auditoría

- `RESEARCH_COMPLETE=TRUE`: F-2 documentado.
- `STATIC_INERT_GUARD_SELF_TEST=11_NEGATIVE_TESTS_PASS`: ámbito exclusivo del código de guardia y manifiesto declarativo, en GitHub-hosted run 36370225725.
- `T01_TO_T20=NOT_EXECUTED` en el ámbito operacional del servidor.
- `AUTHENTICATED_CONSENT_ADAPTER=ABSENT_OR_UNVERIFIED`.
- `SANDBOX_RUNTIME_EVIDENCE=ABSENT`; `HOST_RUNTIME_G23=HOLD`; `HOST_SCOPE_G24=HOLD`.
- `MISSION_SEALED_WITH_EXACT_COMMITS=FALSE`; `AUTORIZO_NOT_RECEIVED`; `INSTALLATION_DISPATCH_ENABLED=FALSE` como norma del nuevo paquete (no garantía acerca de otros flujos preexistentes).
- `F3_DISK=DENIED`, sin cambios físicos a disco.
- **Próximo hito:** revisión del esquema de consentimiento, construcción de lotes con fuentes fijadas y pruebas de réplica expresamente autorizadas, siempre sin disparo remoto sobre el portátil antes de permiso.

## 7. Regla de no regresión documental

Este documento **solo complementa** el plan y el dossier F-2. No reasigna agentes, no sustituye `Louksna.md`, no declara G23/G24, no sobreescribe el Skeleton ni inicia un runner. Cualquier futura versión que modifique el candado debe conservar evidencia del diff, ensayos negativos repetidos y separación entre preflight reversible y F3-DISK.
