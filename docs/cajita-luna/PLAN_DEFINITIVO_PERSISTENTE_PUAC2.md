# PLAN DEFINITIVO PERSISTENTE — CAJITA DE LUNA / PUAC2

**Estado:** ESPECIFICACIÓN DE CONTROL PERSISTENTE; EJECUCIÓN Y CERTIFICACIÓN NO CONCEDIDAS  
**Fecha de actualización física de referencia:** 2026-10-22  
**Autoridad superior:** `Louksna.md`  
**Gobernanza:** PUAC2 + G01–G24; `EXTEND_DO_NOT_REPLACE`; `APPEND_ONLY`; `FAIL_CLOSED`  
**Límite de distribución final:** `479000000` bytes decimales, exactos  
**Ejecutor de las transformaciones:** CUSTOSZ V9  
**Uso de los 22 dominios:** herramientas de análisis, planificación y validación; no se empaquetan dentro de Cajita.

## 0. Invariantes obligatorios

1. `Louksna.md` mantiene la autoridad canónica. Este plan y los scripts quedan subordinados a ella y a PUAC2; no pueden transferir autoridad, redefinir identidad, certificar Louksna ni propagar una certificación de Cajita a otro artefacto.
2. La operación se limita a optimización gobernada de la Cajita existente. No se crea una segunda Cajita, una distribución paralela ni una copia completa de trabajo fuera del árbol autorizado.
3. Se mantienen el orden y la identidad de los seis dominios: `1. Cerebro`, `2. Orquestación`, `3. Transcripción`, `4. Traductor Inteligente`, `5. Inteligencia documental`, `6. Sistema Inteligente`.
4. Se respetan los resultados de cuantización material ya obtenidos por CUSTOSZ V9. Los cinco ámbitos protegidos —Cerebro, Transcripción, Traducción general, Inteligencia documental y Análisis Avanzado— no se vuelven a cuantizar, reemplazar, podar, mover ni alterar. Sobre ellos se permiten únicamente lecturas de integridad y pruebas que no escriban sobre los originales.
5. Los 22 dominios del repositorio son dependencias auxiliares de trabajo. Se acepta una capacidad sólo tras comprobar su implementación, versión, contrato I/O, pruebas, procedencia y límites. La presencia de un nombre en un manifiesto no demuestra ejecutabilidad.
6. Edge y su perfil permanecen dentro del árbol de Cajita y se incluyen en todos los cálculos. Cookies, datos de sesión/autenticación, almacenamiento local, IndexedDB, preferencias y extensiones requeridos para la operación no se consideran caché descartable. Cualquier eliminación de caché regenerable exige clasificación expresa, evidencia de regeneración y prueba de que no rompe el perfil. No se permite registrar secretos, cookies ni contenido sensible en el informe.
7. No se acepta una reducción estimada sin base medible. Se calcula primero la huella final proyectada, el pico temporal, el espacio de recuperación, la RAM y el cierre de dependencias. Si el plan no cabe, no se inicia la transformación.
8. Toda mutación autorizada debe respetar la transacción `REQUEST → INTENT → VALIDATION → EVIDENCE → PROPOSAL → PRE-COMMIT → CHECKPOINT → COMMIT → POST-VALIDATION → UPDATE → ACTIVE`. En fallo: `FAIL → ABORT → RESTORE_CHECKPOINT → VERIFY_RESTORATION → RECORD_FAILURE → AUDIT`.
9. Los registros, manifiestos, checkpoints y certificados residentes dentro de Cajita forman parte de sus bytes finales. No se omiten del límite por estar ocultos o por ser “temporales”. La reserva para evidencia final debe definirse y contabilizarse antes de transformar.
10. No se declara funcionalidad, validación independiente ni certificación por configuración, existencia de código, firma declarada o ejecución de una sola prueba.

## 1. Estado físico de partida medido

Medición de sólo lectura sobre el árbol existente:
`/home/diegoignacionorambuenamiranda/PROYECTOS/1. PROYECTOS PRIORITARIOS/1. PROYECTO LUNA/2. Cajita de Luna`

**Instante de medición:** `2026-10-22T05:22:19Z`.

| Ruta raíz | Bytes medidos |
|---|---:|
| `1. Cerebro` | 176492920 |
| `2. Orquestación` | 1033158688 |
| `3. Transcripción` | 39528193 |
| `4. Traductor Inteligente` | 26889840 |
| `5. Inteligencia documental` | 21659313 |
| `6. Sistema Inteligente` | 358787008 |
| `RUNTIME_CANDIDATE_V1` | 128586 |
| `CajitadeLuna.md` | 5142 |
| `_ARCHIVO_CANDIDATOS_NO_SELECCIONADOS` y `.cajita-optimization-candidates` | 0 bytes de archivos |
| **Árbol completo medido** | **1656649690** |
| **Techo final** | **479000000** |
| **Reducción mínima matemática respecto del estado medido** | **1177649690** |

El valor anterior es una fotografía de medición, no un resultado de optimización. Cada ejecución volverá a inventariar todo el árbol, incluidos los ficheros ocultos, sidecars, resultados de pruebas y certificados. La suma se vuelve a calcular después de cada transacción y al final.

**Edge:** el archivo `2. Orquestación/Orquestador/EdgeBackup_20260907_170357_d18dac86743a/EdgeBackup_20260907_170357_d18dac86743a.7z` mide `951395079` bytes. Su SHA-256 observado el mismo día es `9b6be254db05b410dbb8966f861c3b64ff7d74a56a267f6218ff3c108c9d4e6b`. El archivo por sí solo supera el techo completo en `472395079` bytes, sin contar los sidecars. Esta es una incompatibilidad de tamaño demostrada con la representación actual, no una razón para eliminar el perfil. El plan sólo puede avanzar si CUSTOSZ presenta una estrategia cuantificada que conserve los datos operativos obligatorios y demuestre una salida final válida. Si no existe una estrategia probada, el estado será `BLOCKED`.

El sistema de archivos tenía `63679909888` bytes disponibles en la medición. Ese espacio libre sirve sólo para evaluar picos transitorios; no eleva ni reemplaza el techo de distribución.

## 2. Inventario legado y reconciliación de V9

El registro original `RUNTIME_CANDIDATE_V1/registry.json` contiene 121 artefactos con un tamaño original declarado agregado de `128230075138` bytes. La comparación de sólo lectura contra el árbol actual encontró **47 rutas ausentes y 6 discrepancias de tamaño**. Entre los ejemplos están los fragmentos de Cerebro que ya no aparecen con su ruta original y un modelo de Transcripción cuyo tamaño registrado no coincide con el archivo que reside hoy. Esos datos históricos no autorizan a restaurar ni a modificar resultados de V9.

Se debe añadir, sin reescribir el registro original, `RUNTIME_CANDIDATE_V1/registry_reconciliation.json`, con una correspondencia por cada discrepancia. Cada registro debe contener identificador de origen, ruta y tamaño originales, disposición explícita, ruta actual si existe, bytes y SHA-256 actuales, hash de la evidencia de ejecución V9 y prueba de dependencias/regenerabilidad cuando proceda. Disposiciones posibles: `V9_REPLACED`, `RESTORED`, `REGENERABLE_CACHE`, `NON_RESIDENT_PROVEN_UNNECESSARY`. No se admite `UNRESOLVED`. Una ruta ausente o cambio de tamaño no se resuelve por conjetura.

Se requiere además `.cajita-optimization-candidates/FROZEN_OUTPUTS_V9.json`, con inventario hash-verificable de todos los archivos que integran los cinco ámbitos protegidos y referencia de evidencia V9. No se fabricarán sus hashes ni se marcará una cuantización como ejecutada desde este controlador.

## 3. Los siete bloques de trabajo endurecidos

### Bloque 1 — Congelación y línea base

Automatizar la lectura de identidad, ruta, tamaño, SHA-256, relación con el artefacto de origen y evidencia V9 de los cinco ámbitos protegidos. Guardar una línea base inmutable y versionada. Comparar la línea base antes y después de cada operación.

**Gate:** `G01`, `G02`, `G04`, `G05`, `G19`, `G20`. Un hash cambiado bloquea el trabajo, no activa una reparación automática del contenido congelado.

### Bloque 2 — Inventario íntegro y reconciliación

Escanear recursivamente el árbol, incluidos directorios ocultos y auxiliares. Detectar rutas escapadas, symlinks/hardlinks no autorizados, colisiones de identidad, cambios de tamaño, archivos desconocidos y dependencias que el registro no cubre. Mantener el inventario original y añadir la reconciliación V9.

**Gate:** `G01`, `G02`, `G05`, `G16`, `G19`, `G20`. Inventario incompleto = `HOLD`.

### Bloque 3 — Presupuesto exacto de bytes y recursos

Antes de autorizar cada transformación, calcular: bytes actuales de toda Cajita; tamaño de cada ámbito de operación; bytes fijos que no se modificarán; cota superior del resultado por operación; reserva de evidencia/certificación; pico de temporales; bytes para rollback; RAM disponible; espacio real de disco; cierre de dependencias. Las operaciones son secuenciales (`MAX_PARALLEL_OPERATIONS=1`) salvo que una prueba independiente autorice explícitamente un modo distinto.

La cota final se calcula como:

`FINAL_UPPER_BOUND = CURRENT_TREE_BYTES - SUM(CURRENT_BYTES_OF_NON_OVERLAPPING_TARGET_SCOPES) + SUM(OUTPUT_UPPER_BOUNDS) + FINAL_EVIDENCE_RESERVE`

El plan pasa el gate sólo si esa cota es `<= 479000000`, el pico temporal y el rollback caben en el almacenamiento disponible y el pico de RAM cabe en la memoria real. No se permiten reducciones deduplicadas, dependencias externas gratuitas ni exclusiones de archivos sin prueba.

**Gate:** `G05`, `G06`, `G19`, `G20`, `G21`, `G22`. Imposibilidad matemática o recursos insuficientes = aborto antes de escribir un candidato.

### Bloque 4 — Optimización de los pendientes por medio de 22 dominios

CUSTOSZ V9 elige los métodos por evidencia y tipo de artefacto; no por una jerarquía de prioridad entre pendientes. El manifiesto de plan debe enumerar, una vez cada uno, los siguientes componentes:

- Orquestador; Multi + Interdisciplinar; Confesión Eclesial Reformada.
- Hermenéutica H-G; traducción de lenguas antiguas.
- Testing; Runtime Android/Windows; Portabilidad base; Motor protocolar; Migración y Persistencia; Consola; Cognitive CI-CD; Archivado Detección; Anti-Alucinaciones.

El alcance del trabajo de Orquestación incluye una estrategia específica para preservar la utilidad operativa del perfil Edge. Los resultados congelados de V9 quedan excluidos de los ámbitos de escritura. Cada operación necesita evidencia cuantitativa que fundamente su cota, contrato de entradas/salidas, técnica, dependencias, pruebas y rollback. Se admiten operaciones de streaming sólo cuando tienen una recuperación verificable. No se crean copias completas de Cajita ni se distribuyen los 22 dominios dentro de ella.

**Gate:** `G03`, `G06`–`G18`, `G21`, `G22`. Cualquier cambio fuera del ámbito autorizado detiene la transacción.

### Bloque 5 — Validación funcional y de calidad

Probar cada dominio, no solamente la presencia de sus archivos:
- ejecución real de modelos y adaptadores; errores; interfaz I/O; dependencias instaladas y sus versiones;
- traducción general, hermenéutica H-G y lenguas antiguas con corpus y criterios de evaluación separados;
- transcripción con muestras conocidas y medidas reproducibles;
- operaciones documentales y salida de documentos reales;
- Orquestación multiagente, CLIs requeridas, aislamiento entre dominios, timeouts, manejo de fallos y recuperación;
- runtime Android/Linux/Windows, portabilidad, persistencia/migración y acceso a servicios;
- Edge: integridad del archivo/perfil, apertura en el runtime objetivo, preservación de la sesión/autenticación, almacenamiento local y prueba de navegación aprobada sin exponer valores secretos;
- análisis de alucinaciones, falsos positivos/negativos, resultados contradictorios, límites de confianza y abstención;
- regresión funcional y de rendimiento antes/después, uso máximo de RAM, tiempo, latencia y fallos.

Cada test debe señalar el artefacto exacto por hash, la versión del runtime, la fixture/corpus por hash, resultado, métricas, log y rollback. Una prueba de estructura, un hash correcto o un `NotImplementedError` no demuestra operatividad.

**Gate:** `G03`, `G06`–`G18`, `G20`–`G22`. Los dominios no demostrados permanecen `UNVERIFIED`.

### Bloque 6 — Transacciones, rollback y no regresión

Para cada cambio: comparar hash del origen; validar el manifiesto de autorización; calcular picos; establecer checkpoint; verificar restauración previa; realizar una única transformación; ejecutar pruebas locales; comparar artefactos protegidos; ejecutar pruebas cruzadas; confirmar que se conserva el registro de evidencia. Un fallo cancela la operación y restaura el checkpoint. El rollback se prueba de verdad, no se infiere de la existencia de un archivo.

**Gate:** `G19`, `G20`, `G21`, `G22`. No se aceptan reemplazos silenciosos, estados parciales, certificados antiguos vinculados a un hash distinto ni borrado de evidencia de un intento fallido.

### Bloque 7 — Automatización de PUAC2, G23 y G24

Se automatizan las transiciones y decisiones, pero se mantienen identidades independientes:
1. La automatización normaliza el candidato y construye un paquete de evidencias vinculado a los hashes exactos.
2. El validador G23 recibe el artefacto/evidencia como datos, ejecuta o comprueba las pruebas independientes en un entorno de privilegios mínimos y sin secretos del usuario, vuelve a comprobar G01–G22 y firma su resultado con su identidad autorizada.
3. G24, como proceso separado, verifica criptográficamente la identidad y firma de G23, el mismo sujeto/hash, el cierre completo de las 24 puertas, la autorización, la línea base protegida, la evidencia de rollback y la ausencia de razones abiertas. Firma el certificado o emite `HOLD`.
4. Un verificador final vuelve a medir los bytes del árbol y comprueba que certificado, recibos y logs caben dentro del límite. Si el tamaño final supera el techo, no se emite liberación.
5. Los informes fallidos se preservan. El pipeline no puede crear su propio G23/G24 válido, asignarse una identidad independiente ni convertir una certificación de paquete CUSTOSZ V9 en certificación integral de Cajita o Louksna.

La salida final esperada es un artefacto `CAJITA_G24_CERTIFICATE.json` firmado y vinculado al sujeto exacto, más los recibos G23/G24 y su cadena PUAC2. G23 y G24 no se consideran satisfechos por una bandera booleana o por la conclusión de tests unitarios del script.

**Gate:** todos `G01–G24` en `PASS`, todos con evidencia verificable, `G23` independiente, `G24` criptográficamente válido, no regresión global aprobada y rollback probado. En cualquier otro caso: `NOT_CERTIFIED`.

## 4. Automatización obligatoria y persistencia

Los artefactos previstos y sus ubicaciones dentro de la Cajita (sus bytes computan en el total final):

- `.cajita-optimization-candidates/FROZEN_OUTPUTS_V9.json`: inventario de congelación/hash.
- `RUNTIME_CANDIDATE_V1/registry_reconciliation.json`: reconciliación aditiva del registro histórico.
- `.cajita-optimization-candidates/OPTIMIZATION_PLAN_V9.json`: plan de 14 componentes, incluido el plan específico Edge; cotas de tamaño y recursos.
- `.cajita-optimization-candidates/FUNCTIONAL_VALIDATION_V9.json`: pruebas funcionales por dominio.
- `.cajita-optimization-candidates/evidence/`: evidencia append-only, logs saneados, informes G01–G22, recibos firmados G23/G24 y certificado final.
- `scripts/cajita_luna_governed_preflight.py`: inventario, presupuesto, validación de manifiestos, preflight y verificación PUAC2.
- `tests/test_cajita_luna_governed_preflight.py`: pruebas automatizadas de controles y fallos.
- `.github/workflows/cajita-luna-governed-preflight.yml`: pruebas de regresión del controlador en CI. Esta CI prueba el controlador; por sí sola no certifica la Cajita física.

Los trabajos deben ser repetibles e idempotentes; los informes son append-only y tienen identificador UTC, hash, herramienta/versión y razón de decisión. La ausencia de runtime real, de prueba, de recibo independiente o de identidad de confianza es un bloqueo visible. El ejecutor no debe pedir aprobación reiteradamente para controles que ya estén determinados en el manifiesto autorizado, pero tampoco puede ampliar ese manifiesto ni autoautorizar cambios.

## 5. Criterios de liberación

Sólo se permite `RELEASED_AND_CERTIFIED` cuando simultáneamente:
- el árbol final completo —incluidos metadatos, auxiliares, recibos y sidecars— mide como máximo `479000000` bytes enteros;
- cada dominio está operacional y las pruebas funcionales/generales pasan;
- los cinco ámbitos protegidos coinciden con los hashes de congelación de V9;
- las discrepancias del registro histórico están reconciliadas con evidencia;
- el perfil Edge conserva datos de sesión requeridos y supera pruebas de restauración/navegación;
- las 24 puertas G01–G24 y PUAC2 pasan, G23 y G24 tienen identidades/firmas distintas y el certificado se vincula al sujeto exacto;
- no existen bloqueadores de procedencia, seguridad, regresión, dependencias ni rollback;
- la última medición posterior al certificado sigue bajo el límite.

## 6. Estado honesto a 2026-10-22

`PHYSICAL_INVENTORY = 1656649690_BYTES`  
`GLOBAL_CAP = 479000000_BYTES`  
`CURRENT_OVERAGE = 1177649690_BYTES`  
`EDGE_ARCHIVE = 951395079_BYTES`  
`EDGE_ARCHIVE_OVER_CAP_ALONE = 472395079_BYTES`  
`LEGACY_REGISTRY = 121_ARTIFACTS / 128230075138_DECLARED_BYTES`  
`LEGACY_RECONCILIATION = 47_MISSING_PATHS / 6_SIZE_MISMATCHES`  
`FROZEN_OUTPUTS_MANIFEST = NOT_FOUND_AT_MEASUREMENT`  
`RECONCILIATION_MANIFEST = NOT_FOUND_AT_MEASUREMENT`  
`FUNCTIONAL_CERTIFICATION = NOT_GRANTED`  
`G23 = NOT_RUN_FOR_CAJITA`  
`G24 = NOT_ISSUED_FOR_CAJITA`

Por estos bloqueos, el plan persistente queda especificado, pero **la Cajita no está todavía lista ni certificada**. El controlador debe devolver `BLOCKED` mientras falten el plan medible, el inventario de congelación, la reconciliación, las pruebas operativas o una estrategia Edge cuantificada. No puede declarar éxito por redactar este documento ni por superar sus propias pruebas unitarias.
