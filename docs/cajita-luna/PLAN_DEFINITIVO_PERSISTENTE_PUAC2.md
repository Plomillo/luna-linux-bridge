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

**Instante de medición:** `2026-10-22T06:25:23Z`.

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

El sistema de archivos tenía `63367270400` bytes disponibles en la medición. Ese espacio libre sirve sólo para evaluar picos transitorios; no eleva ni reemplaza el techo de distribución.

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


## 7. Automatización ejecutable de G23/G24 — enmienda de endurecimiento

Esta sección concreta el plano de automatización. Es aditiva; no altera la autoridad de \`Louksna.md\`, la línea base protegida ni los cinco resultados de cuantización congelados.

### Controladores

- \`scripts/cajita_luna_governed_preflight.py\`: inventario de bytes, recursos, alcance y preflight de cambios; no transforma motores.
- \`scripts/cajita_luna_puac2_gates.py\`: prepara la evidencia G23, firma el recibo independiente, comprueba la firma de G23, emite una decisión G24 o \`HOLD\`, persiste los recibos de manera append-only y verifica de nuevo el árbol físico.
- \`.github/workflows/cajita-luna-governed-preflight.yml\`: compila los controladores y ejecuta sus pruebas automatizadas. Su éxito certifica los controles del código, no el producto Cajita.
- \`.github/workflows/cajita-luna-puac2-g23-g24.yml\`: workflow confiable de despacho manual-controlado, con G23 en el host autorizado, G24 en un runner distinto y persistencia/lectura final de vuelta en el host de Cajita. No se ejecuta desde un pull request ni distribuye los archivos/modelos/perfil de Cajita como artefactos de Actions.

### Cadena automática

1. Tras terminar una transformación con CUSTOSZ V9, el controlador vuelve a medir y sólo permite el siguiente paso si preflight, inventarios y pruebas pasan.
2. Una vez que el conjunto final ya es funcional y el manifiesto de preparación está cerrado, \`dispatch-g23-g24\` vuelve a ejecutar el preflight G23, recalcula SHA-256 del sujeto y solicita el workflow confiable de \`main\`. No despacha si faltan manifests, quedan puertas abiertas, la raíz tiene errores, el tamaño previsto no cabe o el hash recibido no coincide.
3. G23 valida el estado actual y firma con la identidad de validación independiente. Una falta de evidencia produce un recibo \`HOLD\`; firmar ese recibo no convierte la validación fallida en aprobación.
4. G24 valida la firma de G23, la identidad distinta, el candidato/hash exactos, los digests de evidencia y todos los predicados G01–G24. Produce un certificado firmado sólo si todos pasan; de otro modo firma \`HOLD\`.
5. El host persiste los recibos y el manifiesto en \`.cajita-optimization-candidates/evidence/\` sin sobrescribir registros existentes. El controlador vuelve a comprobar el árbol con esos bytes incluidos, más sidecars y el informe de decisión.
6. El estado final sólo es \`RELEASED_AND_CERTIFIED\` si la verificación posterior a la persistencia devuelve \`PASS\` y mide el árbol completo en \`<= 479000000\` bytes. En todos los demás casos el resultado es \`BLOCKED\` o \`HOLD\`.

### Interfaz de operación autorizada

Preflight de sólo lectura:

\`\`\`bash
python3 scripts/cajita_luna_governed_preflight.py preflight --root "$CAJITA_LUNA_ROOT" --no-persist
\`\`\`

Comprobación de evidencia G23 sin despacho:

\`\`\`bash
python3 scripts/cajita_luna_puac2_gates.py prepare-g23 \\
  --root "$CAJITA_LUNA_ROOT" \\
  --candidate-commit "$CANDIDATE_COMMIT_40_HEX" \\
  --expected-subject-sha256 "$SUBJECT_SHA256" \\
  --validator-id "$CAJITA_G23_VALIDATOR_ID" \\
  --producer-id CUSTOSZ_V9 \\
  --output "$RUNNER_TEMP/G23_UNSIGNED.json"
\`\`\`

Despacho a G23/G24 sólo después de tener PASS real para preflight final y evidencia funcional:

\`\`\`bash
python3 scripts/cajita_luna_puac2_gates.py dispatch-g23-g24 \\
  --root "$CAJITA_LUNA_ROOT" \\
  --candidate-commit "$CANDIDATE_COMMIT_40_HEX" \\
  --expected-subject-sha256 "$SUBJECT_SHA256" \\
  --repo Plomillo/luna-linux-bridge \\
  --workflow .github/workflows/cajita-luna-puac2-g23-g24.yml \\
  --ref main
\`\`\`

La llamada de despacho no modifica contenido y no hace cuantización; sólo lanza el workflow de certificación si la comprobación previa pasa. El flujo requiere identidad/configuración de confianza provisionadas. Claves privadas separadas (G23 y G24) se guardan únicamente en GitHub Actions Secrets; identificadores y claves públicas van en variables de Actions. No se registran secretos, contraseñas, cookies ni datos de sesión en los informes.

Variables requeridas para la automatización confiable:
- \`CAJITA_LUNA_ROOT\`: ruta absoluta al árbol físico autorizado en el runner self-hosted.
- \`CAJITA_G23_VALIDATOR_ID\`, \`CAJITA_G24_CERTIFIER_ID\`: identidades inequívocas y distintas.
- Secretos \`CAJITA_G23_SIGNING_PRIVATE_KEY_PEM\` y \`CAJITA_G24_SIGNING_PRIVATE_KEY_PEM\`, almacenados en ámbitos separados de sus jobs.
- Variables públicas \`CAJITA_G23_PUBLIC_KEY_PEM\` y \`CAJITA_G24_PUBLIC_KEY_PEM\`; los fingerprints resultantes deben ser distintos.
- CLI \`gh\` autenticado únicamente con permisos mínimos para despachar el workflow.
- Runner host autorizado con etiquetas \`self-hosted, linux, x64, luna-aux\`, accesible a la ruta local real de Cajita. La ausencia del runner o de su raíz configurada bloquea la certificación, no la degrada a una validación del contenido subido a GitHub.

### Evidencia independiente adicional y preservación

\`.cajita-optimization-candidates/evidence/INDEPENDENT_FUNCTIONAL_TESTS.json\` debe certificar una repetición de pruebas por una identidad/ejecutor diferente de CUSTOSZ V9 y enlazar por SHA-256 el plan de pruebas, informe de resultado y manifiesto de ejecución. Debe cubrir seis dominios y los catorce componentes pendientes. No reemplaza G23: es una entrada de evidencia que G23 vuelve a verificar.

El manifiesto de congelación de V9 identifica por ruta, tamaño y hash todos los archivos incluidos en los cinco alcances protegidos y vincula evidencia de cuantización de V9. El registro histórico se reconcilia en otro artefacto, sin reescritura del registro original. Ambas condiciones se verifican automáticamente antes de certificar.

El único gate G23/G24 utilizado para Cajita es \`scripts/cajita_luna_puac2_gates.py\` y su workflow dedicado. El gate \`scripts/puac2_mtls_gate.py\` es específico del puente remoto/mTLS; no es prueba de funcionalidad de Cajita y no se debe reutilizar como su autoridad certificadora.

### Estado de esta enmienda

Esta actualización persiste el diseño y el código de control en la rama de revisión. La ejecución funcional de la Cajita, la provisión real de identidades/llaves/runner, la viabilidad del límite de bytes y el certificado G23/G24 siguen pendientes. Que la CI pase las pruebas de controlador no cambia esos estados.


## 8. Contrato verificable para los 22 dominios auxiliares

Los 22 dominios se usan como herramientas externas a la distribución Cajita. No se copian sus repositorios, módulos, dependencias, pruebas ni cachés a la distribución final. La autorización es por capacidad específica, no por nombre genérico del dominio.

### Fuente versionada

- Repositorio de ayuda: \`Plomillo/luna-linux-bridge\`.
- Registro autoritativo de capacidades: \`implementation/super1200/domains/D01.json\` a \`D22.json\`.
- Fuente de cada capacidad: su \`implementation_artifact\` declarado en el manifiesto versionado.
- Prueba específica: su \`test_artifact\` declarado en el mismo manifiesto.
- Fijación: \`repository_commit\` inmutable de 40 caracteres hexadecimales, registrado en \`OPTIMIZATION_PLAN_V9.json\`. Todos los hashes se verifican contra ese commit, no contra la rama móvil en el momento de certificar.
- Alcance de cada dominio: la tabla de rangos D01–D22 ya definida en el repositorio. Una capacidad fuera del rango del dominio es causa de rechazo.

### Manifiestos que debe producir el ejecutor

Dentro del árbol Cajita, y por tanto contabilizados en los bytes finales:

- \`.cajita-optimization-candidates/evidence/DOMAIN_TOOL_VALIDATION_V9.json\`, esquema \`CAJITA_DOMAIN_TOOL_VALIDATION_V9/1.0\`. Contiene exactamente los 22 dominios, el repositorio y commit fijados, \`status=PASS\` sólo si toda la matriz pasa y un SHA-256 del informe de prueba por dominio.
- Un informe por dominio en la ruta \`test_report_path\` declarada en el manifiesto, esquema \`CAJITA_DOMAIN_TEST_REPORT_V9/1.0\`, enlazado por hash al informe global. Cada informe contiene exactamente las capacidades enrutadas a ese dominio y el resultado por capacidad: identificador, nombre canónico, rutas de implementación/test, SHA-256 de ambas fuentes, estado/código de salida de la prueba, ruta y SHA-256 de la salida de prueba y \`route_evidence_sha256\`.
- \`OPTIMIZATION_PLAN_V9.json\` contiene un bloque \`domain_routing\` de esquema \`CAJITA_V9_DOMAIN_ROUTING/1.0\`. Para cada uno de los 14 componentes pendientes, \`operations[].domain_routes\` identifica uno o más dominios, los IDs de capacidad concretos, la justificación y \`route_evidence_sha256\`. Cada uno de los 22 dominios debe figurar como \`USED\` con una relación trazable a componentes y capacidades.
- \`DOMAIN_TOOL_VALIDATION_V9.json\` se incluye en la cadena de hashes G23/G24 como \`domain_tool_validation_sha256\`; el test report por dominio se verifica de nuevo a partir de esos hashes en G23.

### Predicados de aceptación automáticos

1. Exactamente D01–D22, sin duplicados, omisiones ni dominios externos.
2. Cada manifiesto Dxx, implementación y fichero de prueba coincide byte a byte por SHA-256 con el commit fijado.
3. Cada capability ID está en el intervalo correcto y figura en el manifiesto Dxx con nombre canónico coincidente.
4. Las capacidades declaradas en la ruta superior, las asignadas a componentes y las presentes en el informe de prueba por dominio deben coincidir exactamente; se rechazan capacidades no enrutadas o resultados extra.
5. Cada prueba tiene \`status=PASS\`, \`exit_code=0\`, salidas guardadas por hash y evidencia de ruta única. Una capacidad usada por varios componentes sólo puede compartir el mismo digest de evidencia de ruta si el manifiesto demuestra esa relación; las colisiones se rechazan.
6. G23 repite el cotejo de manifests, implementaciones, pruebas y hashes sobre la fuente fijada. G24 no firma \`CERTIFIED\` si falta el hash del informe global o si G23 no pasa.
7. El resultado es \`BLOCKED/HOLD\` si no existen informes o si no se puede acceder al commit de origen. No se completan los manifiestos con hashes inventados ni se resuelve un dominio por inferencia.
8. Ninguna de las pruebas de los dominios auxiliares puede modificar el payload congelado de Cajita ni su perfil Edge. Las salidas de prueba se limitan a informes pequeños y medibles; cualquier salida voluminosa se rechaza o se evita antes de ejecutarla.

La automatización de este contrato se realiza en \`validate_domain_routing()\`, invocada por el preflight de optimización y repetida por G23 a través del mismo validador de plan. El éxito de una prueba unitaria del controlador no sustituye los 22 informes reales.

### Estado del contrato

El validador está implementado en la rama de PR como condición obligatoria. Los 22 informes de ejecución real, el routing manifest completo y su evidencia aún deben generarse y cotejarse por el ejecutor autorizado CUSTOSZ V9. Por eso no debe interpretarse como prueba de que los 22 dominios ya ejecutaron con éxito trabajo sobre Cajita.


## 9. Última medición física confirmada

La lectura de sólo lectura más reciente quedó registrada como \`docs/cajita-luna/MEASUREMENTS_20261022T062523Z.json\`, medida a \`2026-10-22T06:25:23Z\`. El tamaño total permanece en \`1656649690\` bytes; el uso del disco disponible para temporales cambió respecto de la lectura anterior, así que el nuevo valor registrado es \`63367270400\` bytes libres. Las seis carpetas de dominio y ambos elementos de raíz medidos siguen sumando exactamente el total publicado en el JSON.

La lectura volvió a comprobar el SHA-256 del archivo Edge, que coincide con su sidecar. También volvió a comparar el inventario legado: 121 registros, \`128230075138\` bytes originales declarados, 47 rutas ausentes y 6 discrepancias de tamaño. No aparecieron los manifiestos de congelación, reconciliación, plan, prueba de los dominios ni validación funcional; G23/G24 siguen sin emitirse para Cajita.

**Decisión por evidencia:** no se ha hecho ninguna transformación física durante esta actualización de plan/controladores. Cajita continúa bloqueada por el exceso exacto de \`1177649690\` bytes, por la incompatibilidad del archivo Edge con el techo global en su representación actual y por los manifiestos/evidencias operativas ausentes.


## 10. Arranque local secuencial persistente (append-only)

El controlador `scripts/cajita_luna_sequential_startup.py` implementa el arranque local de este plan. Preserva el orden B1→B2→B3→B4→B5→B6→B7 y falla cerrado: si un bloque queda en HOLD/FAIL, los posteriores se registran como `NOT_STARTED_PREDECESSOR_HOLD`. La telemetría y el ledger SHA-256 encadenado se guardan fuera de Cajita, dentro del directorio de jobs de CUSTOS. La ejecución no escribe manifiestos, recibos ni logs dentro del árbol de Cajita.

La política de recursos solicita 1 GiB para el árbol de procesos del controlador, limita el espacio virtual del controlador a 384 MiB y el de un hijo secuencial a 640 MiB, y supervisa el RSS sumado del proceso y sus descendientes. No se ejecuta paralelismo de transformaciones. La prueba unitaria del controlador cubre el orden estricto, rechazo de operaciones cuando CUSTOS V9 no está autorizado, tope de RAM declarado y detección de manipulación del ledger.

### Evidencia del primer arranque local

Run ID `20261022T071427355820Z`; commit de `main` utilizado: `b88cc56aeb81930230babd700d426c84046ed9a8`. El controlador registró `SUCCESS_TELEMETRY_CONFIRMED` en 1,69 s y la cadena de eventos pasó su verificación SHA-256. B1 pasó tras inventariar 136 entradas y calcular hashes de los cinco ámbitos congelados y del archivo Edge. B2 quedó en HOLD: `FROZEN_V9_OUTPUTS_MANIFEST_MISSING` y `REGISTRY_RECONCILIATION_MANIFEST_MISSING`; el registro legado presenta 47 rutas ausentes y 6 discrepancias de tamaño. Por orden estricto, B3–B7 se registraron `NOT_STARTED_PREDECESSOR_HOLD`.

Los 22 manifiestos D01–D22 estaban presentes y sus JSON se pudieron analizar, pero esto no demuestra que hayan ejecutado tareas sobre Cajita. El paquete local CUSTOSZ V9 informó `active_authorized=false`, `certification=NOT_GRANTED`; su autoprueba pasó 12 comprobaciones, pero devolvió `authorization_granted=false`. Por ello el controlador no lanzó el trabajador de transformación. La telemetría midió Cajita en `1656649690` bytes, techo `479000000`, exceso `1177649690`; el archivo Edge ocupa `951395079` bytes y su SHA-256 observado fue `9b6be254db05b410dbb8966f861c3b64ff7d74a56a267f6218ff3c108c9d4e6b`.

Este resultado certifica únicamente que el controlador se inició, midió y conservó evidencia local verificable. **No certifica el inicio de la misión CUSTOS, la viabilidad del límite, el funcionamiento final ni G23/G24.** No se modificaron los artefactos de Cajita.
