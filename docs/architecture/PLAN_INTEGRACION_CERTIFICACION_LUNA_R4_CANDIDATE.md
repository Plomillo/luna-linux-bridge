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
