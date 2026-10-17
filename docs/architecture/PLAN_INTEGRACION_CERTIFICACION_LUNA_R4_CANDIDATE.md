# PLAN CANDIDATO — CONTINUIDAD, INSTALACIÓN Y CERTIFICACIÓN DE LUNA R4

**Estado:** PROPUESTA OPERACIONAL / NO CERTIFICADO / NO AUTORIZA EJECUCIÓN DE CAMBIOS EN EL HOST  
**Fecha de formulación:** 2026-09-27 (Chile); referencias de GitHub fechadas en UTC cuando corresponda.  
**Rama documental:** `staging/architecture-louksnamejorada-20260927`.  
**Autoridad:** `Louksna.md`. **Derivación de consulta:** `LOUKSNAMEJORADA.md`.  
**Doctrina:** EXTEND_DO_NOT_REPLACE; APPEND_ONLY_WHERE_CANONICAL; FAIL_CLOSED; NO_SILENT_OPERATIONS.  
**Propósito:** terminar de implementar las capacidades de R4 aún ausentes y producir pruebas separadas de implementación, no regresión, validación independiente y eventual certificación. Este plan no es certificación ni reemplaza decisiones humanas.

## Enmienda de gobernanza — responsabilidad del servidor y frontera de disco

**Decisión del propietario:** SYMPHYLAX R1 es el responsable operacional de la continuación de R4. No es un mero repositorio de evidencias ni debe delegar en el asistente o Remote Desktop Commander las misiones para las que fue concebido. Bajo la autoridad de Louksna y el gobierno de MetaOS, el servidor planifica, coordina, supervisa y verifica; CUSTOSZ V7 es el trabajador ejecutor autorizado, con CUSTOSZ_RUNTIME_V1 para límites temporales, checkpoints y recuperación. Las capacidades cognitivas y metacognitivas (arquitecturas A0/A1, Meta 2, contenedor semántico, PUAC2) son entradas gobernadas y versionadas; no prueban por sí mismas que SYMPHYLAX o CUSTOSZ puedan ejecutar una misión real.

**Precondición fuerte:** antes de que el servidor instale aplicaciones por lotes debe completar una validación independiente G23 y una decisión G24 **limitadas al alcance de instalación no destructiva**, basadas en pruebas reales, negativas, recuperación y observabilidad. Antes de cualquier intervención sobre particiones o retirada de Windows debe superar además una evaluación separada **para el alcance destructivo concreto**. La acreditación de un alcance no se hereda por otros dominios. Ningún actor se autocertifica. El propietario conserva la autorización humana de operaciones irreversibles.

**Activo prioritario:** `C:\PROYECTOS`; protección de datos comprobable, sin prometer riesgo físico cero. Si comparte partición NTFS con Windows, no se puede borrar esa partición para «quitar Windows» sin migrar primero los datos protegidos y demostrar recuperación desde copias independientes. La integridad del Debian operativo y las particiones EFI/arranque también es condición técnica de éxito. El plan debe exigir preservación explícita de `PROYECTOS`, sin conservar Windows como objetivo final.

**Condición de uso cotidiano:** ventanas de ejecución controladas, presupuesto CPU/RAM/disco/red y prioridad para la estabilidad del escritorio y los estudios universitarios del propietario. El servidor no debe ocupar la máquina de modo que interrumpa el trabajo académico; tareas largas, si hay recursos, se realizan en el servidor y se sincronizan solo en checkpoints verificados.

## A. Fuentes congeladas y estado actualmente sustentado

| Recurso | Identidad y evidencia verificadas | Estado admisible |
|---|---|---|
| A0 — Louksna.md | `main/Louksna.md`, 11.536.067 bytes, SHA-256 `5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9`, Git blob `1a399ab7494d6df5582436819eee557083e753ed` | Referencia de autoridad; no modificar para esta operación |
| A1 — LOUKSNAMEJORADA.md | Esta rama, 11.542.631 bytes, 304.498 líneas, SHA-256 `2114188988126aa7a9650c131526c9d7c54ad351db315635569a317114f4eb51`, Git blob `8cdefe026de748bf924f14a9b6efc6308079c2c2`, run `36367210934` | EVIDENCIADA como copia byte-exacta; validación semántica global y certificación operacional NO demostradas |
| PUAC2.md | `main/PUAC2.md`, versión `2.0.0-CANDIDATE`, blob `da3b216888c86e588685d384c34dd3c481414b22` | Extensión independiente pendiente de admisión; G23/G24 no concedidas |
| Skeleton R4 | PR #3; 24.964 bytes, 832 líneas, SHA-256 `fb9fad37994e684ad54b1ffc2762660eebcb8e41bd9c4ba685ffac55217d5b0f` | Contrato de necesidades; `SPECIFIED_NOT_CERTIFIED` |
| SYMPHYLAX R1 | PR #1; inventario solo lectura, run `36352624122`: 11.746 archivos regulares con SHA-256, 193 entradas sensibles excluidas y 12 symlinks no seguidos | Inventario de alcance evidenciado; runtime operacional, G23 y G24 pendientes |
| Contenedor semántico | PR #2; run `36357166014`: 252/252 SHA-256 PASS sobre 327.745.213 bytes; se interrumpió tras detectar worktree sucio | HASH_VERIFIED en aquella ejecución; solo 4 objetos registrados en la rama GitHub; 248 pendientes de transferencia |

Los hashes declarados en Skeleton para CUSTOSZ V7, runtime, MetaOS y manifiesto semántico son **objetivos de cotejo**, no pruebas de disponibilidad o ejecución actual. Los estados históricos de documentos no se trasladan automáticamente a esta nueva versión o plataforma.

## B. Responsabilidades y separación de autoridad

- **Louksna.md:** autoridad arquitectónica vigente; controla identidades, invariantes, gobernanza y autorización; no se reescribe por esta misión.
- **LOUKSNAMEJORADA.md:** derivación mejorada disponible para consulta, refinamiento y comparación; su incorporación como autoridad requiere procedimiento separado y las puertas correspondientes.
- **MetaOS:** gobernador propuesto del host y de la orquestación; debe demostrar versión, hash, permisos, fronteras y supervisión efectivas.
- **CUSTOSZ V7:** trabajador autorizado para descubrimiento, adquisición, instalación en lotes previamente autorizados, diagnósticos, pruebas y rollback; no se sustituye silenciosamente por Desktop Commander, el runner o el asistente.
- **CUSTOSZ_RUNTIME_V1:** control de tiempo, ejecución material, puntos de recuperación y persistencia, sujeto a prueba real.
- **SYMPHYLAX R1:** servidor/puente para coordinación, continuidad, CI y transporte de evidencia. Su inventario no demuestra que pueda realizar todas las operaciones del host; probar cada permiso/capacidad antes de ampliarlo.
- **PUAC2:** candidato de aseguramiento operativo y cognitivo (causal, lógico, empírico, filológico, metacognitivo, seguridad, auditoría), con controles y ensayos trazables; no es sustituto de G23/G24.
- **G23:** evaluador independiente del ejecutor/constructor, competente para el alcance probado.
- **G24:** autoridad certificadora competente que examina evidencia G23, alcance, autorización humana y riesgos residuales.

## C. Secuencia cerrada de implementación

### F0 — Congelación y diagnóstico diferencial: requisito previo a cambios

1. Conservar A0 byte-exacto; incorporar A1 y Skeleton como **referencias** con commit, hash, versión y estado epistémico propio.
2. Leer inventario SYMPHYLAX, estado de CUSTOSZ V7, MetaOS, runtime, contenedor y R4 instalado. Verificar **presencia real, hash del binario, ejecutabilidad y pruebas funcionales** por separado.
3. Generar una matriz de discrepancias para cada requisito del Skeleton: `SPECIFIED / ACQUIRED / HASH_VERIFIED / MATERIALIZED / INSTALLED / CONFIGURED / FUNCTIONALLY_VALIDATED / INDEPENDENTLY_VALIDATED / CERTIFIED / ACTIVE`. Para cada fila, añadir `actual_state`, evidencia, dependency_ids, riesgo, coste de RAM/disco, responsable y rollback.
4. Congelar snapshot no destructivo del estado de Debian, KDE, particiones, montajes y aplicaciones. El volumen original PROYECTOS permanece protegido; sin formatear, desmontar, purgar ni mover sin autorización explícita.
5. Identificar contradicciones sin normalización silenciosa. En particular, la derivación A1 distingue el censo estricto de **11.708 definiciones distintas** y **706 huecos** del conteo histórico basado en tokens de **11.757** y **657 huecos**. No inventar 49 definiciones ni modificar AX hasta auditoría independiente.
6. Registrar la preparación del servidor: runner self-hosted, versiones de herramientas, permisos, aislamiento, almacenamiento temporal y disponibilidad de recuperación; no suponer competencia por estar en línea.

**Gate F0:** manifiestos firmados o hasheados, lista de ausencias y contradicciones, inventario host, checkpoint comprobable, fuente canónica preservada. Si falta alguno, bloquear cambios materiales.

### F1 — Certificar capacidad operacional del servidor ANTES de encargarle la instalación

1. Identificar el binario y configuración efectivos de SYMPHYLAX R1, CUSTOSZ V7, CUSTOSZ_RUNTIME_V1, MetaOS y, donde corresponda, Meta 2 y el contenedor semántico. Cotejar su versión, fuente, permisos, hash, plataforma, dependencias, recursos y límite de autoridad. Las referencias A0/A1 orientan la operación, no transfieren autoridad.
2. Levantar una **matriz de competencias verificadas del servidor**: inventariar hardware/software; resolver dependencias; adquirir y verificar fuentes oficiales; simular instalación; instrumentar un checkout aislado; instalar/configurar paquetes en entorno de prueba; comprobar KDE/UI y aplicaciones; monitorizar CPU/RAM; checkpoint; rollback; recuperación de fallo; protección de PROYECTOS; gestión de ventanas temporales; generación y custodia de evidencia; diagnóstico autónomo sin destruir datos.
3. Ejecutar una misión trazable de extremo a extremo, primero inocua, luego de instalación en sandbox: SYMPHYLAX recibe y planifica, MetaOS autoriza, CUSTOSZ ejecuta, runtime controla recursos y checkpoint, servidor evalúa resultados y redacta evidencia; inyectar fallos para exigir abortar, restaurar y comprobar restauración.
4. Distinguir resultados: `AVAILABLE`, `TESTED`, `FUNCTIONALLY_VALIDATED`, `INDEPENDENTLY_VALIDATED`, `CERTIFIED_FOR_SCOPE`. No aceptar un inventario, un script, una salida autodeclarada o un hash como evidencia de competencia profesional integral.
5. Exigir G23 **independiente del constructor y ejecutor** y dictamen G24 competente para un alcance delimitado de **instalación reversible no destructiva**. Si no hay validador independiente disponible, `HOLD`, sin certificación ni instalación autónoma. Registrar limitaciones explícitas.
6. Remote Desktop Commander es AUXILIAR_ONLY para observación o transporte bajo permiso, no ejecutor sustituto. El servidor mantiene el presupuesto de recursos y no invade horarios de estudio ni interrumpe cargas académicas.

**Gate F1 PRE-INSTALL:** trazas, matriz de competencias, pruebas positivas/negativas/límites, recuperación ensayada, aislamiento entre dominios, G23 independiente y G24 aplicables al **alcance no destructivo**. Falta de evidencia, permisos insuficientes, inestabilidad del host o `EXECUTOR=UNBOUND` => `HOLD`.

### F2 — Contenedor semántico: conservar avance y completar transporte aparte

1. No repetir automáticamente las 252 descargas. Verificar antes si el caché/objeto original SHA-256 sigue presente, con la misma versión y en una fuente autorizada.
2. Resolver el bloqueo de worktree sucio **mediante checkout nuevo y aislado**, preservando los cambios no relacionados; no usar `git clean -fdx` sobre el trabajo del usuario.
3. Completar los 248 objetos CAS restantes mediante Git LFS cuando el usuario autorice retomar esta rama; cotejar 252/252 **desde el destino remoto**, con manifiesto de tamaños y SHA-256.
4. Independientemente, probar indexación, recuperación, relaciones, metacognición, consistencia de contexto, persistencia y recuperación local. `OBJECTS_UPLOADED` no significa `SEMANTIC_RUNTIME_ACTIVE`.

**Gate F2:** identidad exacta de los 252 objetos verificada desde GitHub **para el cierre del transporte**; contrato de consulta y recuperación validado por separado **para el cierre funcional**. F2 no impide empezar inventario e interfaz de F3 si la tarea es independiente.

### F3 — Instalación diferencial R4 dirigida por SYMPHYLAX, ejecutada por CUSTOSZ

**Responsable de misión:** SYMPHYLAX R1, únicamente después de F1. **Trabajador de ejecución:** CUSTOSZ V7. **Gobernador:** MetaOS bajo Louksna. **Control de ejecución:** CUSTOSZ_RUNTIME_V1. **Asistente/Desktop:** auxiliares sin delegación del trabajo principal.

1. El servidor compara requisitos completos del Skeleton con el sistema instalado. No reinstala Debian ni repite herramientas funcionales. Cada ausencia recibe ID, dependencias, riesgo, prueba, coste, responsable, ventana temporal, checkpoint y recuperación.
2. El servidor genera y propone lotes ordenados: seguridad/firmware/almacenamiento → Node/Python/Git/7-Zip/OpenJDK/C++23/Mojo → navegador y compatibilidad universitaria → Projects Center/CUSTOSZ local → KDE/UI y referencias visuales → Devocional/backend local → juegos/virtualización/higiene.
3. Antes de cada lote, SYMPHYLAX exige simulación de paquetes, fuente oficial y licencias, fijación de versión/hash disponible, conflicto de dependencias, prueba de protección de PROYECTOS, consumo de RAM/CPU y checkpoint. MetaOS autoriza el alcance; CUSTOSZ ejecuta **solo ese lote** y el runtime vigila límites y rollback.
4. SYMPHYLAX conserva evidencia inmutable fuera del ámbito que pueda revertirse, ordena pruebas funcionales/repetición negativa y verifica no regresión. Fallo => abortar, restaurar checkpoint, comprobar restauración, informar con diagnóstico y detener avance de ese dominio.
5. Las aplicaciones propias (Projects Center, Devocional, gestor de versiones, Hygiene, integración semántica) exigen pruebas funcionales reales; instalar dependencias no constituye entrega de una aplicación. Para KDE se contrasta el diseño, fondo, accesibilidad, navegación y referencias UI, no solo el inicio de sesión.
6. Aplicar planificación respetuosa de la universidad: trabajo pesado preferentemente en servidor; límites configurables de recursos y tiempo en portátil; sin reinicios desatendidos, sin afectar documentos/clases ni quitar conectividad esencial.
7. **Exclusión de este alcance:** borrar Windows, alterar GPT/EFI/particiones, formatear, mover PROYECTOS o purgar recursos de otro dominio. Su expediente separado es F3-DISK, no una subrutina de F3.

**Gate F3:** cada lote muestra `INSTALLED`, `FUNCTIONALLY_VALIDATED`, evidencia de seguridad de datos y no regresión, bajo la competencia por alcance concedida en F1; sin atribución automática de G23/G24 al producto completo.

### F3-DISK — Protección de PROYECTOS y eventual retirada de Windows 11 (fase separada)

**Estado inicial obligatorio: `DENY_DESTRUCTIVE_ACTION`.** El objetivo futuro es retirar Windows 11 conservando los datos de PROYECTOS y el arranque funcional de Debian. No comenzar esta fase hasta la madurez y estabilización de SYMPHYLAX/CUSTOSZ y la autorización humana puntual. La regla H2 del Skeleton sigue vigente: particionado físico MANUAL por el usuario, asistido por un plan del servidor, salvo futura modificación expresa y formal de esa regla.

1. **Geometría de solo lectura:** el servidor inventaría discos físicos, seriales/WWN si disponibles, GPT, UUID/PARTUUID, sistemas de archivos, volúmenes, uso real, montaje, EFI, GRUB/bootloader, Debian y ubicación física exacta de PROYECTOS. Confirmar si el antiguo `C:\PROYECTOS` se encuentra en la misma partición de Windows. No usar la letra C: como identificador Linux estable.
2. **Cifrado y acceso:** detectar BitLocker u otro cifrado. Si existe, comprobar con el propietario que tiene una clave de recuperación accesible y comprobada **sin imprimirla ni subirla a GitHub**. Fallo de desbloqueo o duda de localización => abortar.
3. **Congelación lógica:** interrumpir escrituras sobre la fuente protegida durante la captura consistente, inventariar cada ruta y metadatos, crear hashes y un manifiesto de exclusiones justificadas. No asumir que un atributo de solo lectura equivale a una instantánea consistente de NTFS; confirmar que el método empleado permite recuperación completa.
4. **Redundancia real:** preparar al menos dos copias independientes cifradas de PROYECTOS en soportes físicos o ubicaciones de fallo independientes, ninguna almacenada exclusivamente en el mismo disco que será particionado. Conservar originales hasta verificar por lectura íntegra tamaños/hashes y realizar restauraciones de muestra **y un ensayo de restauración utilizable en destino aislado**. Disponer, cuando corresponda, de imagen de disco/volumen y un medio de rescate que realmente arranque. Una copia en GitHub o CAS no reemplaza por defecto el respaldo integral de PROYECTOS.
5. **Análisis destructivo del servidor:** SYMPHYLAX debe generar un mapa exacto de segmentos a CONSERVAR/MIGRAR/ELIMINAR, comandos propuestos sin ejecutar, prueba en réplica o disco virtual de geometría equivalente, prueba de arranque y acceso a PROYECTOS desde Debian, prueba de restauración y plan de contingencia. Si PROYECTOS comparte partición con Windows, migrar primero a volumen de datos separado y conservar copias verificadas; NUNCA formatear esa partición suponiendo que la carpeta quedará a salvo.
6. **Gate independiente para alcance destructivo:** G23 evalúa por separado la competencia efectiva de SYMPHYLAX/CUSTOSZ para ese dispositivo, esa tabla de particiones, ese mapa y ese método de restauración; G24 solo puede certificar/autorizar dentro de sus competencias y del alcance probado. Debe constar evidencia de arranque Debian/EFI preservado, copias probadas, riesgos residuales y ruta de recuperación.
7. **Autorización humana H2/H4:** presentar al propietario el plano exacto del disco, tamaños/UUID de destinos, qué desaparece, qué se conserva, evidencias de restauración, margen de riesgo y momento de indisponibilidad; solicitar consentimiento explícito inmediatamente antes del evento. El usuario realiza el particionado físico manual conforme al Skeleton. El servidor puede inspeccionar y verificar antes y después, pero no adquirir permisos ilimitados para borrar discos automáticamente.
8. **Postoperación:** verificar hashes del conjunto recuperado, disponibilidad de PROYECTOS, arranque limpio y estable de Debian/KDE, EFI funcional, acceso a universidad, recuperación de emergencia y no regresión de R4. Conservar evidencia fuera del disco intervenido. Eliminar imágenes y respaldos temporales solo mediante expediente de retención autorizado, nunca por limpieza automática.

**Gate F3-DISK:** `SOURCE_FROZEN_AND_ACCESSIBLE` + `INDEPENDENT_BACKUPS_VERIFIED` + `RESTORE_PROVEN` + `DISK_MAP_REVIEWED` + `DEBIAN_BOOT_PROTECTED` + `SERVER_DESTRUCTIVE_SCOPE_INDEPENDENTLY_VALIDATED` + `G24_DECISION` + `HUMAN_H2_H4_APPROVAL`. Si cualquiera es desconocido, `HOLD` y mantener Windows temporalmente. No afirmar «riesgo cero» ni prometer rollback de particiones sin respaldo restaurable probado.

### F4 — Aseguramiento y validación independiente por objeto

1. Verificar invariantes arquitectónicos A0/A1: B1–B134, cuatro agentes, 14 comandos, E01–E15, CFE001–CFE074, documentos congelados y prohibición de reasignación silenciosa. Aclarar antes de certificar el censo axiomatizado sin mutar el histórico.
2. Ejecutar ensayos PUAC2 del ámbito correspondiente: positivos, negativos, límites, fallos, causalidad, procedencia, estado epistémico, permisos, reproducibilidad, regresión, restauración y coherencia documental. La existencia de 28 clases o 16 invariantes en una especificación no demuestra que todas las pruebas hayan pasado en el host.
3. Validar independientemente los objetos por alcance: A1 documental, contenedor CAS, CUSTOSZ y runtime, MetaOS, SYMPHYLAX, aplicaciones R4 y su integración. **No propagar** un PASS entre objetos o versiones.
4. G23 emite dictamen firmado con actores independientes, fuentes, entorno, alcance, artefactos, hashes, pruebas repetibles y contradicciones resueltas o abiertas.
5. G24 decide únicamente el objeto y las propiedades respaldadas por G23 y la autoridad competente, con aceptación de riesgos y autorización humana donde corresponda.

**Gate F4:** ninguna transición `VALIDATED→CERTIFIED` sin G23; ninguna transición `CERTIFIED→ACTIVE` sin autorización, despliegue controlado y postvalidación.

### F5 — Liberación y continuidad

1. Crear paquete de lanzamiento con manifiestos cerrados, fuente y binarios fijados, instrucciones de reconstrucción, hashes, licencias, pruebas, inventario de datos protegidos, cambios operacionales y checkpoint de vuelta.
2. Activar por dominios solo después de completar sus gates. Someter a ensayo de continuidad apagado/reinicio y restauración cuando exista autorización humana explícita.
3. Establecer monitoreo de regresión, cambios upstream y deriva de referencias, con notificación únicamente ante cambios accionables. Cada actualización es una nueva propuesta con nuevos hashes y su propia cadena de evidencias.

## D. Contrato mínimo de evidencia y prohibiciones

Toda operación consecuencial debe emitir `operation_id, actor, authority, source_commit, source_sha256, target, dependency_graph, permission, timestamp, input_hash, output_hash, expected_result, actual_result, functional_tests, negative_tests, checkpoint, rollback_pointer, recovery_test, G23_actor, G23_result, G24_actor, G24_result, scope, epistemic_state`.

`UNKNOWN`, conflicto de hashes, contaminación entre dominios, ausencia de permisos, falla de rollback o evaluación independiente incompleta => `FAIL_CLOSED` y conservación del último estado válido.

**Restricciones globales:** A1 no reemplaza A0; PUAC2 no se autoautoriza; servidor no se transforma en autoridad canónica; el límite de 479.000.000 bytes aplica al artefacto operacional de Luna especificado en el programa maestro, **no al tamaño total del sistema operativo Debian instalado**. Si la restricción global del artefacto no es verificable, no declarar cumplimiento.

## E. Próximo hito autorizado

**F0 → F1 PRE-INSTALL:** el servidor SYMPHYLAX ejecuta inventario diferencial del host respecto del Skeleton e identifica CUSTOSZ V7, MetaOS, runtime, arquitectura normal/mejorada, Meta 2 y contenedor semántico sin asumir que las declaraciones sean ejecutables. Su siguiente obligación es demostrar capacidad de instalación reversible en un entorno aislado con pruebas de error/rollback, seguida de G23 independiente y dictamen G24 **para ese alcance**. Solo entonces SYMPHYLAX coordina y CUSTOSZ ejecuta F3; no delegar la instalación al asistente ni a Desktop Commander. **F3-DISK se pospone** hasta completar protección comprobada y dos copias independientes restaurables de PROYECTOS, validar la capacidad destructiva por separado y obtener autorización humana H2/H4; Windows 11 no es un requisito que deba conservarse después de esa transición segura. Las cargas de trabajo preservan disponibilidad del portátil para estudios universitarios. La transferencia CAS pendiente puede completarse en paralelo, sin equiparar transporte con ejecución local.

---

## ADITIVO F-1 — PREPARACIÓN CERRADA Y DISPARO EXPLÍCITO AUTORIZO

ADITIVO_ID = SYMPHYLAX_R1_READINESS_AUTHORIZATION_20260927  
STATUS = SPECIFIED_PENDING_IMPLEMENTATION_AND_VERIFICATION  
CHANGE_DOCTRINE = EXTEND_DO_NOT_REPLACE  
APPEND_ONLY = TRUE; FAIL_CLOSED = TRUE; NO_SILENT_OPERATIONS = TRUE  
RESPONSABLE_OPERACIONAL = SYMPHYLAX_R1  
TRABAJADOR = CUSTOSZ_V7  
EJECUCIÓN_CONTROLADA = CUSTOSZ_RUNTIME_V1  
GOBERNADOR = MetaOS; AUTORIDAD_ARQUITECTÓNICA = Louksna.md  
PUAC2_STATUS = CANDIDATE_WITHOUT_G23_G24  
ENTRY_STATE = PREPARATION_INERT  
EXECUTION_GATE = EXPLICIT_USER_AUTORIZO_BOUND_TO_ONE_MISSION  
DESTRUCTIVE_ACTIONS = DENIED_UNDER_GENERAL_AUTORIZO  

### F-1.0 — Regla de alcance y no activación

Este aditivo se suma a F0–F5 y F3-DISK: no sustituye ni reenumera etapas anteriores. Una aprobación para investigar o preparar NO permite instalar, modificar el host, subir datos privados ni iniciar trabajos en el runner self-hosted. Tampoco convierte la disponibilidad de documentación, código, hashes o corpus en competencia operacional verificada.

Antes de AUTORIZO, se permite preparar documentación, fuente, manifiestos, dependencias y pruebas estáticas en GitHub; se permiten simulaciones **únicamente en infraestructura aislada expresamente autorizada** que no monte discos del usuario, no posea credenciales del host ni acceda a PROYECTOS. Si no está claro el aislamiento, no se realiza siquiera la simulación. No se programará cron, systemd timer, workflow de push, PR o schedule que active la instalación. La rama documental no es ejecutable por el simple hecho de existir.

**Conflicto epistemológico que no se oculta:** no se puede certificar en vivo la capacidad de SYMPHYLAX sobre el portátil sin ejecutar pruebas en ese servidor. Por tanto, antes de AUTORIZO pueden quedar certificados, por una autoridad competente e independiente, el **diseño del procedimiento** y los ensayos **en un entorno aislado**, si efectivamente se realizaron; pero la capacidad operacional sobre el host sigue PENDING hasta que exista una autorización diferenciada para pruebas locales o se ejecuten los prechecks iniciales del propio AUTORIZO. Está prohibido presentar PREPARED o STATIC_VALIDATED como SERVER_OPERATIONALLY_CERTIFIED.

### F-1.1 — Investigación y cierre de dependencias, sin tocar la estación

SYMPHYLAX es el responsable futuro del ciclo completo. En la preparación documental se construye, para cada requisito del Skeleton y de las arquitecturas A0/A1, una fila con: identificación; criticidad; requisito verificable; estado previo basado en evidencia; programa/binario propuesto; proveedor oficial; versión fija; firma/hash disponible; licencia; plataforma Debian 13/KDE; recursos de CPU/RAM/disco; dependencias declaradas; interfaz con MetaOS/CUSTOSZ/runtime; datos afectados; prueba positiva, negativa y de regresión; checkpoint; restauración; responsable; duración medida o UNKNOWN; y ventana prevista.

La investigación separa (a) conocimiento referencial de Louksna/A1, Meta 2 y contenedor semántico, (b) capacidades realmente materializadas y (c) permisos de ejecución efectivos. Si un objeto CAS falta en GitHub, se señala sin bloquear artificialmente tareas independientes. Está prohibido inventar implementaciones, normalizar axiomas conflictivos o tratar un índice del corpus como motor ejecutable.

Producto obligatorio: matriz de requisitos del Skeleton frente a instalación actual, grafo de dependencias sin ciclos no resueltos, BOM/SBOM provisional, rutas de descarga oficial y plan de ensayo reproducible. Los datos que solo pueden obtenerse del host permanecen UNKNOWN antes del permiso para observarlo.

### F-1.2 — Paquete de misión sellado y reproducible

Preparar en GitHub un expediente de misión con:
- Identidad exacta del propietario y del ámbito, sin publicar identificadores privados, tokens ni material sensible.
- Git commit exacto de la propuesta, SHA-256 de la especificación, manifiesto de entradas y artefactos, conjunto de lotes autorizables, dependencias, fuente/versión/hashes y árbol de datos excluidos.
- Plan de instalación idempotente en lotes, simulación sin efectos cuando esté soportada, políticas de actualización, pruebas funcionales y condiciones de detención.
- Presupuesto de memoria, CPU, disco y red y una ventana nocturna con deadline; ante insuficiencia de recursos o exceso de tiempo, preservar Debian usable para clases y entregar pendientes en vez de forzar una ejecución.
- Evidencia externa a los directorios reversibles, cifrada cuando incluya información privada, con políticas de retención; accesos de solo lectura a arquitectura y corpus salvo autorización más estricta.
- Checkpoints válidos para la operación real: pruebas de restauración de los mismos tipos de archivos y estados; nunca equiparar un commit Git con una imagen de disco o rollback de paquetes.
- Permisos mínimos por lote, destinos expresamente permitidos, bloqueo de ejecución transversal entre dominios y prohibición global de particionar, formatear, borrar Windows, cambiar EFI o mover PROYECTOS bajo este paquete.
- Contrato de observabilidad: log append-only protegido, run_id, operation_id, timestamps UTC, actor, entrada/salida SHA-256, causa, autorización, comandos con parámetros saneados, exit_code, prueba, recursos, checkpoint, rollback, resultado y siguiente estado epistémico.

Proponer artefactos versionados para misión y autorización; **no incluir credenciales** en PR, commit, artefactos descargables o logs. Cualquier ejecutable debe demostrar que contrasta los campos contra el commit y hash aprobados; un texto AUTORIZO encontrado en README, commit, issue o salida de un agente no es una autorización válida.

### F-1.3 — Evidencia y evaluación independiente anterior al disparo

A. Validación documental/estática: esquema de manifiesto, parser de autorización, cobertura de requisitos, matriz de permisos, revisión de dependencias y licencias, análisis de secretos, reglas de no degradación, idempotencia y capacidad de abortar.

B. Ensayos en sandbox independiente **cuando estén expresamente autorizados**: instalación desde fuentes fijadas sobre réplica Debian 13/KDE, pruebas de aplicación e interfaz, errores de red/almacenamiento, falta de recursos, fallos entre operaciones, restauración, límite de tiempo y trazas completas. No dar por ensayado lo no ejecutado. El servidor real requiere validación posterior en su entorno.

C. Revisión de seguridad de GitHub: no ejecutar código arbitrario de PR en runners self-hosted con acceso a recursos persistentes; fijar commit de workflow y acciones externas; permisos mínimos de GITHUB_TOKEN; ejecución de una sola misión; no utilizar secretos de producción en ensayos. Las protecciones de entornos/revisores y las atestaciones nativas tienen restricciones según el plan de GitHub en repositorios privados: **verificar elegibilidad real antes de incorporarlas a un gate** y, si no existen, utilizar un comprobador externo e independiente de autorización, no simular una aprobación de GitHub.

D. G23 independiente y G24 competente pueden emitir dictamen **sobre el diseño y la réplica probada**, con estado y alcance exactos. Su existencia no habilita el equipo real. Si nadie independiente ha ejecutado la evaluación, registrar G23 = HOLD. Está prohibida la autocertificación del servidor, del asistente y de CUSTOSZ.

E. Dos informes diferentes: READINESS_DESIGN (especificación y código listos para revisión) y READINESS_RUNTIME (solo después de ensayo material). Nunca mezclar los resultados.

**Gate PRE-AUTORIZO:** expediente de diseño completo, hipótesis y supuestos etiquetados, scripts revisados y sin activación, ensayos independientes de réplica completados o claramente HOLD, conjunto exacto de operaciones congelado, riesgos residuales y fuente de recuperación declarados. El estado PREPARED no equivale a CERTIFIED.

### F-1.4 — Estado de espera y semántica de AUTORIZO

Estado inicial y tras publicar este plan: WAITING_FOR_EXPLICIT_AUTHORIZATION. No hay timer de arranque ni conexión que interprete PR merge, push, aprobación automatizada o mensaje de tercero como permiso.

El propietario recibe una **ficha de decisión** con mission_id, versión/hash/commit, lista exhaustiva de lotes y prohibiciones, duración prevista basada en mediciones, recursos mínimos, respaldos, pruebas y riesgos. El vocablo **AUTORIZO** constituye intención humana únicamente cuando está **vinculado a esa ficha exacta** y al alcance específico. La ejecución deberá implementar identificación verificable del propietario, alcance, caducidad, nonce de un solo uso y revocación; la simple coincidencia de cadena no puede activar acciones. No pedir ni almacenar la prueba de identidad en documentación pública. Revalidar el token/consentimiento justo antes de entrar en cada frontera de efectos.

Si la intención expresada es solo AUTORIZO para instalación reversible R4, **NO** autoriza F3-DISK. La operación destructiva requiere una **segunda ficha y una segunda autorización expresa** posteriores a copia/restauración probadas, evaluación independiente por dispositivo y revisión humana del plano de particiones. El particionado físico H2 sigue siendo manual por el usuario según el Skeleton.

**Gate de activación:** AUTHENTICATED_USER + EXACT_MISSION_BINDING + UNEXPIRED_SINGLE_USE_AUTHORIZATION + G23/G24_APPLICABLE_OR_HOLD_FOR_LIVE_VERIFICATION + NO_FORBIDDEN_OPERATIONS. Cualquier falta: DENY_WITH_AUDIT.

### F-1.5 — Secuencia de la noche después del consentimiento válido

Solo después de AUTORIZO y exclusivamente para la ficha consentida:
1. SYMPHYLAX recibe una única misión, establece lock por host y lote, constata que no hay otra misión viva, revalida commit/hash, dependencias y autorización; CUSTOSZ y runtime están subordinados a MetaOS.
2. Ejecuta el preflight real de solo lectura en host: montaje y salud de PROYECTOS, espacio y energía, sesión de usuario/clases, compatibilidad del hardware, versiones, disponibilidad del runtime, respaldo/checkpoints y presupuesto temporal. Cambios respecto del expediente congelado => HOLD y nuevo consentimiento.
3. Ejecuta **pruebas vivas mínimas y reversibles autorizadas** del controlador, aislamiento, observabilidad, fallo simulado y restauración. Si G23/G24 para el alcance real no estaban previamente concedidas, **no empezar la instalación hasta obtenerlas**; no presumir que puedan concederse automáticamente durante la noche.
4. SYMPHYLAX coordina los lotes F3, CUSTOSZ los ejecuta, CUSTOSZ_RUNTIME_V1 controla recursos y rollback, MetaOS autoriza cada frontera, y una comprobación posterior evita propagación de fallos. El servidor conserva trazas fuera del ámbito modificable y redacta evidencia de cada lote.
5. Ante error, cancelación, desconexión, inconsistencias o vencimiento de ventana: detener nuevas operaciones, completar o revertir únicamente la transacción en curso cuando sea seguro, verificar restauración, conservar PROYECTOS y dejar el escritorio disponible. No hacer rollback destructivo sin demostrar recuperación.
6. Al término: informe nocturno con lotes instalados y funcionalmente validados, pruebas fallidas, hashes, cambios, uso de recursos, checkpoint y pendientes. Un objetivo de una noche es un **SLO condicionado a tiempo medido**, no una garantía absoluta de finalización.

El disparador no debe iniciar la misión en GitHub Actions mientras solo exista en una rama documental. Según la documentación oficial, un workflow_dispatch manual debe existir en la rama por defecto antes de poder lanzarse con el botón de GitHub. Su futura incorporación a main requiere revisión expresa, política de identidad efectiva y pruebas del bloqueo; no se hará como efecto lateral de este aditivo.

### F-1.6 — Investigación de las fronteras destructivas, con autorización independiente posterior

La retirada de Windows sigue siendo F3-DISK. Pre-AUTORIZO solo puede elaborarse el procedimiento **teórico y documental** de geometría, medios de rescate, inventario de datos y pruebas en réplicas, sin mapear el disco real si no hay permiso de lectura. Tras consentimiento de diagnóstico, SYMPHYLAX deberá comprobar UUID/PARTUUID, EFI, BitLocker si existe, ubicación exacta de PROYECTOS, número de copias independientes y restauración real antes de solicitar autorización destructiva.

**Nunca** prometer seguridad física absoluta ni presentar un check SHA-256 como sustituto de dos respaldos independientes y restauración probada. La documentación oficial de Debian considera intrínsecamente peligroso modificar particiones existentes y exige respaldo antes de reparticionar.

### F-1.7 — Condición de parada y estado publicable

El proyecto está **READY_FOR_OWNER_DECISION** únicamente cuando se presenta un paquete de diseño verificable, fuentes y dependencias fijadas, matriz de permisos y prohibiciones, pruebas y dictámenes efectivamente realizados (con sus huecos), preflight real planificado, ventana nocturna viable y un disparador validado por revisión **sin ejecutar**. Si la verificación del disparador no es posible sin el host, declarar READY_DESIGN_ONLY, no READY_RUNTIME.

**Estado actual del aditivo al incorporarlo al PR:** DOCUMENTATION_PREPARED / SERVER_OPERATIONAL_READINESS_UNVERIFIED / G23_G24_NOT_GRANTED_FOR_NIGHT_RUN / AUTORIZO_NOT_RECEIVED / NO_HOST_ACTION. Ninguna instrucción de este documento modifica los permisos del servidor ni arma automáticamente el futuro flujo.

### F-1.8 — Fuentes primarias de ingeniería para reproducir la investigación

- GitHub Actions, evento manual workflow_dispatch (solo activable como workflow presente en rama por defecto): https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- GitHub Actions, seguridad de runners autohospedados y aislamiento: https://docs.github.com/en/actions/reference/security/secure-use
- GitHub Actions, reglas de entornos y límites para repositorios privados: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- GitHub Actions, limitación de concurrencia: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
- GitHub Actions, condiciones de atestaciones nativas en repositorios privados: https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations
- Debian, precauciones ante cambios de partición y respaldos: https://www.debian.org/releases/stable/amd64/ch03s05.en.html
- systemd, cuotas de memoria y CPU para ejecutar de forma controlada: https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html

---

## ADITIVO F-2 — INVESTIGACIÓN EXTERNA Y CONTRATO DE ENSAYOS

**Alcance:** endurecimiento trazable del plan precedente, sin sustituir F0–F5, F3-DISK ni F-1 y sin convertir fuentes externas en autoridad canónica. El dossier íntegro [ADITIVO_F2_EVIDENCIA_COMPARADA_Y_PRUEBAS.md](ADITIVO_F2_EVIDENCIA_COMPARADA_Y_PRUEBAS.md) y el candado declarativo [SYMPHYLAX_R1_NIGHT_MISSION_LOCK_CANDIDATE.json](SYMPHYLAX_R1_NIGHT_MISSION_LOCK_CANDIDATE.json) forman parte de este mismo expediente del PR #4.

**Estudio profesional contrastado:** NIST SSDF v1.1 *final* y NIST 800-34, SLSA v1.2 *aprobado*, artículo arbitrado in-toto (USENIX Security 2019), Fedora/openQA sobre instalaciones completas y GUI, Ansible/Molecule para idempotencia, Google SRE para cambios progresivos y rollback, Debian/Microsoft/restic para recuperación y cifrado, Hugging Face para modelos fijados por revisión/model cards y GitHub para riesgos de runners autoalojados. Cada fuente se registra en el dossier con enlace primario, aplicación a R4 y una prohibición de inferir que el éxito externo certifica nuestro servidor.

**Criterio antidecorativo:** por cada control externo debe existir una implementación verificable y un ensayo positivo, negativo o de recuperación ligado a evidencia original. El dossier define T01–T20 con identidad de fuente, manifiesto de misión y consentimiento, aislamiento, idempotencia, instalación simulada/real, UI visual, restauración, controles de recursos, prueba de precedencia G23/G24 y barrera F3-DISK. Los 20 ensayos están **especificados, NO ejecutados**; ningún PASS es transferible desde las herramientas citadas.

**Plazo:** el objetivo de **20 minutos** aplica únicamente a investigación, contrastación de fuentes, redacción del aditivo y preparación documental. No convierte la revisión en certificación ni permite falsificar pruebas operacionales. El objetivo separado de completar la instalación **durante una noche** exige duraciones medidas, dependencias fijadas, competencia efectiva SYMPHYLAX/CUSTOSZ y reserva temporal para rollback y disponibilidad universitaria.

**Puesta en espera segura:** el registro declarativo permanece `PREPARATION_INERT`, `user_authorized=false`, `automation_armed=false`, `server_operations_authorized=false`. No se ha habilitado workflow de instalación, cron ni servicio que responda a coincidencias del texto AUTORIZO. La futura autorización requiere una ficha de misión concreta, identidad verificada, commit/hash fijados, nonce, caducidad, revocación y validador de permisos efectivo. Un mensaje, PR o merge por sí solos no son suficiente autenticación. Si la cuenta GitHub privada no ofrece la política de entornos requerida, no se simula ese control.

**Separación de resultados:** investigación terminada `RESEARCH_DOCUMENTED` ≠ paquete compilado `DESIGN_READY` ≠ pruebas de réplica `SANDBOX_VALIDATED` ≠ servidor/host `RUNTIME_VALIDATED` ≠ G23 independiente ≠ G24 competente ≠ permiso humano ≠ `ACTIVE`. El primer uso tras una autorización válida inicia solamente un preflight de lectura y ensayos reversibles expresamente consentidos; si G23/G24 de alcance real siguen pendientes, no instalar. La eliminación de Windows y todo cambio GPT/EFI permanecen bloqueados bajo esta autorización general y requieren F3-DISK con autorización H2/H4 distinta.


## ADITIVO F-2.1 — Evidencia de guardia estática sin acceso al host

Se incorporó `scripts/governance/verify_symp_inert_candidate.py` como verificador **puramente estático** de `SYMPHYLAX_R1_NIGHT_MISSION_LOCK_CANDIDATE.json`. El programa no contiene rutas de instalación, autorización, SSH, subprocess, formateo o ejecución remota: únicamente lee el JSON, comprueba invariantes de `PREPARATION_INERT`, el bloqueo destructivo, veinte ensayos en `NOT_EXECUTED` y la ausencia de credenciales/identidad de autorización. Su supuesto adaptador de autorización responde siempre `DENIED` hasta implementar y auditar un adaptador real.

La workflow `.github/workflows/verify-symphylax-inert-static.yml` usa exclusivamente **GitHub-hosted `ubuntu-latest`**, token con `contents: read`, checkout fijado por SHA y ninguna credencial/servicio del portátil; no ejecuta SYMPHYLAX, CUSTOSZ, MetaOS ni el runner self-hosted. En la [ejecución 36370225725](https://github.com/Plomillo/luna-linux-bridge/actions/runs/36370225725), **11 ensayos negativos de bloqueo pasaron** y el manifiesto de 20 familias quedó confirmado como no ejecutado: `execution_permitted=false`, `host_executions=0`, `g23=false`, `g24=false`. Esta prueba documenta una propiedad local del código candidato; **no es** revisión independiente de seguridad integral, ni acredita que el futuro puente de autenticación o el servidor estén preparados.

Siguiente evidencia exigida: revisión externa del adaptador criptográfico de consentimiento y de la matriz de permisos, pruebas de integración sobre réplica aislada expresamente autorizada, preparación de los lotes con versiones fijadas y validación G23/G24 circunscrita al ámbito que efectivamente se haya ensayado. Hasta entonces: `DESIGN_RESEARCH_COMPLETE`; `INERT_LOCK_STATIC_TEST=PASS`; `SERVER_PREPARED_TO_EXECUTE=NOT_ESTABLISHED`; `AUTORIZO_NOT_RECEIVED`.


## ADITIVO F-2.2 — TRASPASO DE EVIDENCIA Y ESTADO VERAZ PRE-AUTORIZO

El [expediente F-2.2](ADITIVO_F2_2_TRASPASO_AUDITORIA_PREAUTORIZO.md) continúa a partir de F-2.1 sin reiniciar investigación ni interpretar las once pruebas negativas estáticas como ensayos del servidor. Formaliza cinco estados independientes (`RESEARCH_COMPLETE`, `DESIGN_REVIEWABLE`, `SANDBOX_VALIDATED`, `HOST_SCOPE_VALIDATED`, `APPROVED_FOR_NONDESTRUCTIVE_MISSION`) y asigna evidencia y bloqueos a cada uno. El siguiente entregable es el paquete de misión verificable con fuentes exactas, dependencias, DAG de lotes, presupuesto de recursos, controles de identidad/consentimiento y pruebas de réplica expresamente autorizadas.

**Observación actual de los gates:** investigación documentada; guardia inerte estática probada exclusivamente en CI GitHub-hosted; T01–T20 operacionales `NOT_EXECUTED`; puente de consentimiento `ABSENT_OR_UNVERIFIED`; G23/G24 de servidor/host `HOLD`; AUTORIZO `NOT_RECEIVED`; F3-DISK `DENIED`. **No atribuir `SERVER_READY` por el archivo JSON, un PASS de CI o un mensaje escrito.** El paquete no instala código ni modifica la máquina. La eventual eliminación de Windows exige expediente y autorización independientes después de copias externas y recuperación probada de PROYECTOS. 

**Criterio de cierre del objetivo de 20 minutos:** publicación del estudio y del contrato de pruebas; no prueba de madurez del servidor. El objetivo de instalación nocturna se acepta únicamente con mediciones sobre réplica equivalente, margen de rollback, límites para disponibilidad académica y validaciones G23/G24 aplicables.


## ADITIVO F-2.3 — CÁPSULA DE MISIÓN PRE-AUTORIZO

El expediente [F-2.3](ADITIVO_F2_3_CAPSULA_MISION_PREAUTORIZO.md) materializa el siguiente entregable de F-2.2 sin modificar el host: `SYMPHYLAX_R1_NIGHT_MISSION_PACKAGE_CANDIDATE.json`, un paquete inerte con inputs fijados por commit/blob, 12 lotes L00–L11 en DAG, presupuesto provisional de recursos, contrato de evidencia, autorización de un solo uso y exclusión absoluta de F3-DISK del permiso general.

La operación se formaliza como `DECLARED → PINNED → SIMULATED → SANDBOX_VALIDATED → AUTHORIZED → CHECKPOINTED → EXECUTED → FUNCTIONALLY_VALIDATED → INDEPENDENTLY_VALIDATED → CERTIFIED_FOR_SCOPE → ACTIVE`; ausencia de evidencia no permite saltos. El paquete mantiene `user_authorized=false`, `automation_armed=false`, `dispatch_enabled=false`, `live_server_ready=false` y `execution_permitted=false`.

La workflow GitHub-hosted [36375968122](https://github.com/Plomillo/luna-linux-bridge/actions/runs/36375968122) ejecutó el verificador estático F-2.3: 12 pruebas negativas pasaron, 12 lotes declarados, 0 ejecutados, sin self-hosted runner ni acceso a SYMPHYLAX/LOUKSNA/PROYECTOS. Este PASS acredita coherencia estática y fail-closed local del paquete; no es G23, G24, sandbox funcional ni certificación del servidor.

**Patrones endurecidos:** NIST SSDF (disciplina SDLC/evidencia), SLSA (procedencia sin reclamar nivel), in-toto (layout, actores, materiales/productos), TUF (resiliencia de updates), Sigstore (opción de firma/identidad a revisar), APT Secure (autenticación Debian), Ansible (idempotencia y check/diff con límites), GitHub Actions (self-hosted no asumido como sandbox) y Hugging Face (carga segura de modelos). Son referencias de diseño, no certificados transferibles.

**Estado después de F-2.3:** `RESEARCH_COMPLETE=EVIDENCED`; `DESIGN_PACKAGE_MATERIALIZED=TRUE`; `STATIC_PACKAGE_NEGATIVE_TESTS=12_PASS`; `SANDBOX_VALIDATED=FALSE`; `AUTHENTICATED_CONSENT_ADAPTER=ABSENT_OR_UNVERIFIED`; `G23=HOLD`; `G24=HOLD`; `SERVER_READY_WAITING_FOR_AUTORIZO=FALSE`; `AUTORIZO=NOT_RECEIVED`; `F3_DISK=DENIED`.

**Próximo hito F-2.4:** diseñar/revisar el adaptador de consentimiento autenticado y la réplica aislada, fijar las fuentes/versiones definitivas de los lotes y ejecutar T01–T20 + benchmarks de duración/recursos en sandbox autorizado. Solo evidencia real de esos ensayos y revisión independiente podrá convertir el paquete en candidato a `SERVER_READY_WAITING_FOR_AUTORIZO`.
