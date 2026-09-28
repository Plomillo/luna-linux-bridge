# ADITIVO F-2 — EVIDENCIA EXTERNA, COMPARACIÓN DE ARQUITECTURAS Y ENSAYOS DE ADMISIÓN

ID = SYMPHYLAX_R1_RESEARCH_ASSURANCE_ADDENDUM_F2_CANDIDATE
STATUS = RESEARCH_DOCUMENTED / DESIGN_NOT_INDEPENDENTLY_VALIDATED
PARENT = docs/architecture/PLAN_INTEGRACION_CERTIFICACION_LUNA_R4_CANDIDATE.md
DOCTRINE = EXTEND_DO_NOT_REPLACE; APPEND_ONLY; FAIL_CLOSED
SUBJECT = Preparatoria documental para instalación nocturna reversible R4
OWNER_TRIGGER = AUTORIZO_VINCULADO_A_FICHA_EXACTA
DESTRUCTIVE_SCOPE = DENIED_UNDER_GENERAL_AUTORIZO
RUNTIME_ACTIVATION = FALSE
HOST_ACTION_BEFORE_AUTHORIZATION = FORBIDDEN

## 1. Alcance y frontera epistémica

Este es un **aditivo investigativo y un contrato de pruebas**: no es un certificado del servidor, un informe de pruebas realizadas ni permiso para instalar. El plazo de 20 minutos se refiere al esfuerzo preparatorio de investigación, contraste y publicación documental. No se utiliza para fingir que se han materializado, probado o validado independientemente programas complejos; la verificación operacional requiere mediciones y evidencia reales.

**Objetivo operativo:** antes de solicitar AUTORIZO, disponer de plan, fuentes contrastadas, matriz de controles, scripts sometidos a revisión, hipótesis identificadas, ficha de misión acotada y disparador *inerte*. Tras autorización exacta, SYMPHYLAX ejecuta solo preflight de solo lectura y ensayos reversibles **dentro del permiso**; si faltan G23/G24 aplicables al host, detiene antes de instalar. Solo una nueva autorización expresa, diferenciada y posterior al respaldo/restauración certificables permitirá tramitar F3-DISK. La capacitación de CUSTOSZ no constituye G23 independiente, y un LLM no reemplaza un validador independiente ni una autoridad certificadora competente.

## 2. Investigación contrastada: patrones reproducibles, no certificados prestados

**R-01 — NIST SSDF SP 800-218 v1.1, FINAL (2022), edición española NIST (2025).** Marco institucional de preparación de la organización, protección del software, producción segura y respuesta a vulnerabilidades. Aplicar: política de versiones/fuentes, amenazas de binarios y dependencias, revisión separada y gestión de incidencias. La revisión v1.2 publicada en diciembre de 2025 sigue siendo *draft* según el índice NIST consultado; no usarla como norma final ni declarar «cumplimiento NIST» por citarla.
- https://csrc.nist.gov/projects/ssdf/publications
- https://www.nist.gov/publications/secure-software-development-framework-ssdf-version-11-recommendations-mitigating-risk-0

**R-02 — SLSA v1.2 APROBADO: tracks Source y Build.** Atestar qué código/fuente, quién y qué plataforma produjo cada paquete, preservando digests y firma verificable cuando el constructor permita hacerlo. Comprobar la pareja firmante-constructor; no atribuir SLSA Build L2/L3 por un SHA-256, una acción autoalojada o un JSON sin plataforma atestadora confiable. Exigir una ficha de procedencia por lote y artefacto, con niveles demostrados o `UNCLAIMED`.
- https://slsa.dev/spec/v1.2/
- https://slsa.dev/spec/v1.2/build-track-basics
- https://slsa.dev/spec/v1.2/source-requirements

**R-03 — in-toto, investigación arbitrada USENIX Security 2019.** Cadena firmada de materiales, actor autorizado, operaciones esperadas, productos y atestación. Adaptar a operaciones CUSTOSZ: cada lote publica un link firmado/verificable y el auditor reconstruye la secuencia. El artículo demuestra el mecanismo y lo evalúa frente a compromisos de cadena de suministro; no certifica automáticamente el diseño propio de SYMPHYLAX.
- https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias
- https://in-toto.io/docs/what-is-in-toto/

**R-04 — Fedora + openQA (uso documentado por el proyecto Fedora).** Caso funcional de validación automatizada de instalación completa, arranque, escritorio y GUI mediante máquinas virtuales, entradas de teclado/ratón y comprobación de salidas visuales. Trasladar el patrón a una réplica Debian 13 + KDE que ejercite Projects Center, lanzadores, UI, fondos, audio/red y recuperación. Fedora declara utilizar openQA en validaciones de lanzamiento y actualizaciones; esto **no equivale** a que R4 haya ejecutado openQA ni a una certificación heredable.
- https://fedoraproject.org/wiki/OpenQA
- https://github.com/os-autoinst/openQA
- https://github.com/os-autoinst/openQA/blob/master/docs/GettingStarted.md

**R-05 — Ansible check/diff + Molecule.** Patrón de instalación declarativa, convergencia e idempotencia sometida a ensayos sobre VMs aisladas. Ejecutar `--check --diff` como señal preliminar **solo cuando todos los módulos relevantes soporten check**; Ansible advierte que check no cubre ciertos condicionales/resultados registrados. En Molecule: `create→converge→idempotence→verify→destroy` cuando la versión/configuración del harness lo permita. No afirmar que una simple simulación certifica efectos reales.
- https://docs.ansible.com/projects/ansible-core/stable-2.22/playbook_guide/playbooks_checkmode.html
- https://github.com/ansible/molecule/

**R-06 — Google SRE, Canarying Releases y Configuration Design.** Aplicar ensayo incremental, métricas y rollback por lote. Si la salud del entorno baja, detener o revertir la última operación antes de afectar al resto; especificar `SLO_STUDY_AVAILABILITY` y deadline nocturno. No adoptar porcentajes de tráfico de servicios web como si fueran equivalentes al estado monousuario del portátil; la analogía válida es minimizar el radio del cambio y observarlo antes de progresar.
- https://sre.google/workbook/canarying-releases/
- https://sre.google/workbook/configuration-design/

**R-07 — NIST SP 800-34 Rev.1; Debian installer y Microsoft BitLocker.** Copias verificadas y ensayo de recuperación son una capacidad distinta de rollback de aplicación. En F3-DISK, medir RPO/RTO objetivo después de inventario, ubicar físicamente PROYECTOS, preservar Debian/EFI, comprobar disponibilidad de cualquier clave BitLocker **sin divulgarla**. Debian advierte de la pérdida de datos al elegir particionado automático/alterar particiones y exige confirmación humana. Nada de ello autoriza manipular el disco ahora.
- https://www.nist.gov/publications/contingency-planning-guide-federal-information-systems-including-updates-through
- https://d-i.debian.org/manual/en.amd64/ch06s03.html
- https://support.microsoft.com/es-ES/Windows/Security/Encryption/find-your-bitlocker-recovery-key
- https://restic.readthedocs.io/en/latest/050_restore.html

**R-08 — Hugging Face Hub y model cards.** Cada modelo candidato al runtime se evalúa separadamente: `repo_id`, revisión por SHA de commit, archivos exactos/ETag-digest cuando disponible, licencia y restricciones de modelo, `README.md`/model card, evaluaciones propias y presupuesto local de memoria. Preferir `safetensors` a formatos que deserialicen código Python; prohibir `trust_remote_code` sin auditoría y autorización específica. Un modelo descargado o descrito no se registra como motor operativo ni altera automáticamente Louksna.
- https://huggingface.co/docs/huggingface_hub/en/guides/download
- https://huggingface.co/docs/hub/model-cards
- https://huggingface.co/docs/hub/model-release-checklist

**R-09 — GitHub Actions: riesgos de runners self-hosted y límites reales de entornos.** Un runner persistente con acceso al portátil no es aislamiento de seguridad; ningún script no confiable de PR debe ejecutarse en él. `workflow_dispatch` manual requiere workflow en rama por defecto; no se instala allí automáticamente. En repo privado, no dar por supuesto que `required reviewers` o atestaciones nativas están disponibles bajo cualquier plan: verificar elegibilidad en la cuenta. Si no está soportado, exigir **validador externo independiente**, no aprobación simulada.
- https://docs.github.com/en/actions/reference/security/secure-use
- https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows

## 3. Traducción de casos reales a controles del servidor

| Caso | Prueba real de la fuente | Control trasladable a R4 | NO implica |
|---|---|---|---|
| Fedora/openQA | Uso documentado de pruebas de instalación GUI de SO | VM Debian/KDE + captura de consola/pantalla + trazas de arranque + pruebas de UI | Que SYMPHYLAX ya haya pasado GUI o BIOS/EFI reales |
| Ansible/Molecule | Herramientas efectivas de check/idempotencia/verificación | Lotes inmutables, convergencia repetida y escenarios negativos | Equivalencia entre `--check` y ejecución real |
| Google SRE | Prácticas profesionales publicadas de rollout/rollback | Lotes pequeños observables y aceptación escalonada | Cero fallos o finalización garantizada |
| SLSA 1.2/in-toto | Especificaciones de procedencia y artículo arbitrado | Cadena `fuente→construcción→paquete→instalación→prueba` verificable | Acreditación SLSA/G23/G24 por mera referencia |
| Hugging Face Hub | Herramientas de versiones/model cards | Modelos fijados por commit, licencias, formatos seguros y medición local | Disponibilidad de un motor por descargar pesos |
| NIST/Restic/Debian/Microsoft | Normas y manuales de continuidad, restauración y disco | Dos copias independientes más ensayo de restauración antes de F3-DISK | Protección física infalible o permiso de particionado |

## 4. Contrato de admisión verificable — familias T01–T20

Cada ensayo debe generar `test_id, test_version, host_id_pseudonymous, environment_hash, source_commit, binary_hash, expected, observed, evidence_sha256, actor, timestamp_utc, status, isolation_scope, rollback_reference`; `PASS` sin evidencia original recuperable es `UNVERIFIED`.

| ID | Criterio de ensayo | Resultado requerido para avance |
|---|---|---|
| T01 | Verificar identidad, hash/bytes y autoridad A0/A1; detectar alteración | Sustitución o contradicción ⇒ DENY |
| T02 | Matriz Skeleton completa con estados reales y unknown explícitos | No omitir un requisito ni inventar capacidad |
| T03 | Resolver grafo de dependencias, licencias y fuentes oficiales fijadas | Cero dependencia crítica UNKNOWN al lanzar su lote |
| T04 | Validar manifiesto de misión y contrato de consentimiento malformados | Malformado/ausente ⇒ DENY |
| T05 | Cambiar un carácter del plan, commit, digests o lote aprobado | Hash/binding desigual ⇒ DENY |
| T06 | AUTORIZO fuera de ficha, de otro usuario, vencido o repetido | DENY + evidencia; nonce de un solo uso y revocación reales |
| T07 | Inyectar operación de formateo, EFI, Windows o PROYECTOS en misión R4 | DENY antes de adquirir privilegios |
| T08 | PR/push/cron/intención de agente malicioso sin AUTORIZO válido | Ningún acceso al runner/host por ese evento |
| T09 | Ejecutar revisión de secretos, permisos mínimos y aislamiento de runner | Sin secretos del portátil en runners de PR |
| T10 | Simular lote de paquetes con versiones fijadas y diff seguro | Sin eliminación o downgrade fuera del ámbito |
| T11 | VM Debian13/KDE: convergencia y segunda ejecución idempotente | Segunda ejecución sin cambios no previstos |
| T12 | VM: prueba de apagón/red/paquete roto y recuperación | Abort/rollback/restauración reproducibles |
| T13 | VM: arranque, login, periféricos virtuales y pruebas UI | PASS condicionado a la réplica; hardware real aún pendiente |
| T14 | Pruebas CUSTOSZ↔Runtime↔MetaOS↔SYMPHYLAX | Trazas con límites, roles, causalidad y decisiones |
| T15 | Inducir carga de CPU/RAM/disco y deadline | ABORT/HOLD sin perjudicar sesión académica |
| T16 | CAS: diferenciar objeto descargado, hash validado, remoto y runtime | Nunca equiparar las cuatro condiciones |
| T17 | Ensayo de restauración de datos protegidos en destino independiente | Restauración probada para F3-DISK, no solo hash de backup |
| T18 | Simular mapa GPT/EFI/NTFS/BitLocker en réplica | Bloquear si PROYECTOS solapa volumen a borrar |
| T19 | Validador G23 distinto del constructor/ejecutor y alcance firmado | Si no existe actor independiente ⇒ HOLD |
| T20 | Autoridad G24, consentimiento humano y postvalidación | Si G23/H2/H4 aplicables faltan ⇒ DENY |

La fase F1 necesita solo los ensayos aplicables de alcance **no destructivo**; T17/T18 y H2/H4 se reservan a la futura F3-DISK. La selección exacta y las exclusiones requieren justificación por alcance. Ninguna familia se marca `PASS` mientras no exista evidencia original y review independiente cuando aplique.

## 5. Paquete de misión sellado y tiempos medidos

El diseño del paquete `MISSION_R4_NIGHT` contendrá `mission_id`, `version`, `owner_pseudonymous`, `plan_commit`, `plan_sha256`, `skeleton_sha256`, `A0_sha256`, `A1_sha256`, `PUAC2_sha256`, `model_registry_by_pinned_commit`, `CAS_manifest_sha256`, `CUSTOSZ_runtime_sha256`, `MetaOS_sha256`, `authorized_lots`, `forbidden_capabilities`, `prerequisite_evidence`, `G23_G24_scope`, `resource_limits`, `deadline_utc`, `checkpoint_id`, `restore_test_id`, `abort_conditions` y `provenance_root`. Los campos sin valor probado serán `null` o `UNKNOWN`, jamás valores ficticios.

Calendario de ejecución nocturna **derivado de ensayos de tiempo**, no promesa apriorística:
- Preflight y reconciliación del manifiesto antes de cualquier mutación; ante discrepancia, HOLD.
- Misiones pequeñas y ordenadas por DAG, máximo una transacción mutable por dominio y un bloqueo de escritura global por host.
- Reservar margen para recuperación y postvalidación. No llenar el 100 % de la noche de instalaciones: establecer deadline anterior a la primera actividad universitaria confirmada.
- La noche acaba con informe completo incluso si quedan pendientes. Solo un SLO medido y evidenciado puede usarse para pronosticar la factibilidad; tiempo UNKNOWN ⇒ objetivo nocturno NO_CERTIFICABLE.

## 6. Operación con dos barreras independientes

**Barrera A: PREPARACIÓN (sin operación del servidor).** Documentos, especificación de pruebas, matriz de dependencias, código revisable e investigación pública. Si existe infraestructura de CI GitHub-hosted estrictamente aislada y autorizada, pruebas estáticas allí son distintas del servidor SYMPHYLAX. Prohibido usar credenciales del portátil o montar PROYECTOS en esa CI.

**Barrera B: AUTORIZO para UNA misión NO DESTRUCTIVA.** El propietario ve una ficha con identidad, hash/commit exacto, operaciones incluidas/excluidas, límite de tiempo, presupuesto RAM/CPU, estado G23/G24 y riesgos conocidos. La intención escrita se enlaza mediante mecanismo real de autenticación, nonce único, caducidad, revocación y log firmado a esa ficha, **no por coincidencia literal de la palabra**. Si no hay un mecanismo implementado y auditado, el servidor debe permanecer INERTE aun cuando exista esta documentación.

**Barrera C: F3-DISK separada.** Una ficha distinta con geometría real, dos copias físicas independientes y restauración probada, G23/G24 competentes por dispositivo y autorización humana H2/H4. Esta barrera permanece DENY hasta el evento futuro. Ni Barrera B ni la finalización R4 incluyen derecho a borrar Windows.

## 7. Matriz de estado de preparación publicable

| Propiedad | Evidencia actual | Estado |
|---|---|---|
| Arquitectura mejorada completa | GitHub PR #4, 11.542.631 bytes, SHA-256 archivado | SOURCE_HASH_VERIFIED, no equivalencia semántica G23 |
| Skeleton R4 | PR #3, original 24.964 bytes | SPECIFIED_NOT_CERTIFIED |
| PUAC2 | main, versión 2.0.0-CANDIDATE | G23/G24 NO_CONCEDIDAS |
| SYMPHYLAX R1 | PR #1, inventario forense de 11.746 archivos | INVENTORY_EVIDENCED, capacidad de instalar NO_DEMOSTRADA |
| Contenedor semántico | PR #2, 252/252 SHA-256 pass en una ejecución anterior | 248 objetos GitHub pendientes; runtime NO_DEMOSTRADO |
| Misión nocturna firmada/ejecutable | No existe evidencia de integración real con servidor/host | HOLD |
| Backups independientes PROYECTOS y restauración | No se ha presentado un expediente de dos medios y restauración | HOLD_F3_DISK |
| AUTORIZO ligado criptográficamente a ficha | No existe consentimiento autenticado de esa misión | NOT_RECEIVED |
| G23/G24 del alcance de instalación | No constan dictámenes de validadores independientes | HOLD |

**Prohibición de falsa certificación:** `SPECIFIED` y `STATIC_VALIDATED` no implican `INDEPENDENTLY_VALIDATED`, `CERTIFIED` o `ACTIVE`. El informe final debe declarar directamente qué se verificó y qué quedó pendiente, sin trasladar sellos de casos externos ni de otros alcances.

## 8. Riesgos dominantes que el servidor debe modelar explícitamente

RISK-01 pérdida de PROYECTOS por confundir carpeta con partición; RISK-02 runner self-hosted no aislado/secretos; RISK-03 flujos PR/README como autorizaciones fraudulentas; RISK-04 incongruencia del contenedor CAS entre hash local, remoto e integración; RISK-05 insuficiencia de RAM/espacio y afectación a estudios; RISK-06 falla de recuperación por backup no ensayado; RISK-07 activación de modelos/documentos no confiables como scripts/autoridad; RISK-08 certificación otorgada por mismo actor que construye/ejecuta; RISK-09 falsa garantía de plazo por duración no medida; RISK-10 dependencia de servicio externo no disponible en la ventana.

Cada riesgo debe tener amenaza, mitigación verificable, prueba negativa, detector, condición de parada, responsable y evidencia de cierre. Riesgo crítico no mitigado => HOLD.
