# CUSTOSZV9 / CRFU — estado y alcance de la candidatura

**Estado del artefacto:** `PROPOSED_UNCERTIFIED_SUCCESSOR`. El CI de construcción demuestra solo el subámbito que ejecuta y documenta. No concede G22, G23 o G24 canónicos, admisión formal de PUAC2, activación, autorización operacional ni certificación integral.

## Preservación del baseline V8

El constructor lee el archivo binario raíz `CUSTOSZV8.pyz` rastreado por Git, calcula SHA-256 y tamaño, copia los bytes exactos a `custoszv9/data/CUSTOSZV8.pyz` y vuelve a verificar su identidad. Extrae los miembros `custoszv8/**` para mantener los comandos heredados disponibles dentro del mismo intérprete V9, sin arrancar un segundo runtime V8. El baseline registrado es de 99.400 bytes y SHA-256 `e0b5866a75d606fe04a246806192a77f35c3509e9b6c31b7ee13b84713b1f60c`; el builder no modifica el archivo fuente.

El paquete de construcción debe comprobar el archivo concreto recibido contra ese baseline. Igualdad de tamaño por sí sola no demuestra identidad.

## Capacidades CRFU implementadas y pruebas

- Contrato tipado de tareas y verificación de identificadores, plazos y presupuestos.
- Planificador topológico determinista, acotado por el máximo de alternativas y fail-closed ante ciclos, dependencias ausentes, capacidades insuficientes o efectos no admisibles.
- Sondeo medido de RAM, disco y CPU; medida desconocida o no confiable produce `HOLD`.
- Antiparálisis: repetición de una estrategia en el mismo estado sin evidencia nueva se bloquea; los reintentos están limitados por clase de idempotencia.
- Cola persistente SQLite dirigida por eventos, transiciones de estado controladas, reanudación por condición, deadlines y cadena de hashes verificable.
- Journal de evidencia JSONL con hash chaining, bloqueo de escritores y detección de alteraciones.
- Validadores PUAC2 de claims y unidades tipadas, estados epistémicos, timestamps de eventos separados, grafo causal acíclico, AuthorityBinding, RecoveryPlan, métricas separadas de cobertura documental y operacional, cardinalidades T01–T28 e INV-01–INV-16 y cierre de incidentes separado de reactivación.
- C25–C32 como controles locales: cada evaluación exige digest y commit exactos, payload hash, referencias a evidencia y un evaluador distinto del productor. Sus identificadores no se presentan como controles canónicos admitidos.
- Constructor ZIPAPP reproducible, comandos V8 heredados y pruebas de integridad del paquete.

## Cadena automática G22/G23/G24

La propuesta de flujo de confianza separa la generación de evidencia, la validación y la firma para que el candidato no reciba claves privadas:

1. **G22 — precomprobación acotada de baseline y pruebas.** Recalcula digest, tamaño, preservación byte-exacta, vínculo del commit, reproducibilidad y evidencia del conjunto de pruebas. Los límites del ZIP y las entradas duplicadas también se comprueban. El registro mantiene `status=HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN`; `tested_scope_result=PASS` solo significa que este subámbito acotado pasó.
2. **G23 — validación independiente.** Un runner aislado ejecuta las cinco comprobaciones previstas (versión, estado CRFU, selftest CRFU, selftest V8 y estado V8) sin heredar secretos ni tokens en el entorno del proceso candidato. Los resultados vinculan el mismo commit, digest, tamaño, registro G22 y SHA de la raíz de confianza. El informe distingue el resultado del subámbito de G23 canónico.
3. **Firma G23 en un job distinto.** El job que obtiene `PUAC2_G23_SIGNING_PRIVATE_KEY_PEM` no ejecuta el candidato; verifica la consistencia del informe, vuelve a calcular las identidades y firma el payload canónico con Ed25519. La clave pública `PUAC2_G23_PUBLIC_KEY_PEM` y la identidad `PUAC2_G23_VALIDATOR_ID` deben corresponder.
4. **G24 — verificación independiente y decisión firmada.** G24 verifica la firma Ed25519 de G23, su huella de clave, la identidad del firmante, el digest del payload, commit, package SHA-256 y relación con G22. Comprueba además que los resultados de las cinco comprobaciones concuerden con el estado reportado. G24 firma su propia decisión con una clave distinta. La decisión actual es deliberadamente `HOLD` para la liberación integral, incluso si las pruebas del subámbito pasan.
5. **Sigstore/GitHub artifact attestation.** G24 también produce una atestación de procedencia del archivo de decisión firmado. Esa atestación respalda la procedencia de GitHub Actions; no reemplaza las firmas Ed25519 de G23/G24, la aplicabilidad canónica ni la autorización operacional.
6. **Evidencia persistente.** Los reportes G22, G23 unsigned/signed y el G24 firmado se conservan como artefactos separados vinculados al SHA exacto.

El secreto de G23 solo se utiliza en el job de firma separado, después de terminar la ejecución de código candidato. G24 nunca ejecuta el ZIPAPP. Los jobs de firma exigen:
- Variables de Actions: `PUAC2_G23_VALIDATOR_ID`, `PUAC2_G23_PUBLIC_KEY_PEM`, `PUAC2_G24_CERTIFIER_ID`, `PUAC2_G24_PUBLIC_KEY_PEM`.
- Secrets de Actions: `PUAC2_G23_SIGNING_PRIVATE_KEY_PEM`, `PUAC2_G24_SIGNING_PRIVATE_KEY_PEM`.

El código verifica que las claves públicas correspondan a sus respectivas privadas y que las claves/identidades de G23 y G24 no coincidan. Si falta una variable, clave o evidencia, la firma no se concede y la liberación queda bloqueada. El paquete ZIPAPP no requiere `cryptography` en su ejecución ordinaria; `cryptography==50.0.2` está fijado en los jobs de CI que prueban o ejecutan las operaciones Ed25519.

## PUAC2: límites que siguen pendientes

El archivo `PUAC2.md` en `main` declara `EXTENSION_INDEPENDIENTE_PENDIENTE_ADMISION_FORMAL`, `G23=NO_CONCEDIDA` y `G24=NO_CONCEDIDA`. PUAC.C25–C32 conservan identidad local y nunca sustituyen G23/G24. Por ello el dictamen integral mantiene explícitamente:
- `G01–G24` completos: `HOLD` hasta la matriz normativa canónica y toda evidencia de cada gate aplicable.
- `PUAC.C25–C32`: `HOLD_NOT_CANONICALLY_ADMITTED` hasta evidencia completa y admisión autorizada.
- Fuentes formales: los hashes/tamaños de los ocho módulos Agda base se registran en el manifiesto, pero **sus archivos no se incluyen en el ZIPAPP operativo**. Permanecen como fuentes del repositorio para la cadena formal independiente. El constructor de la aplicación no ejecuta Agda/Cubical y no afirma correspondencia modelo–implementación; cualquier resultado formal debe provenir de la ejecución independiente ligada al commit y al manifiesto exactos.
- Uso operacional: pruebas reales del host mTLS, restauración/rollback y la autorización operacional siguen pendientes hasta que el flujo host real aporte sus reportes verificables.

Las pruebas de unidad, compilación, ZIPAPP y reproducibilidad no acreditan por sí solas comportamiento de producción ni certificación externa.

## Condición de confianza del workflow

`.github/workflows/custoszv9-independent-g22-g23-g24.yml` usa `workflow_run` y debe existir en la rama predeterminada para que su raíz de confianza sea la versión confiable de GitHub Actions. Mientras solo esté en esta rama/PR, no se afirma que la cadena protegida se haya ejecutado. Además, el repositorio no tiene actualmente rulesets/required checks efectivos visibles desde la integración utilizada; por tanto, un job verde no se debe confundir con enforcement obligatorio para merge o release.

**Conclusión de estado:** el candidato V9 se construye y prueba automáticamente; la cadena de firmas Ed25519 está implementada y es sometida a tests criptográficos; la decisión integral permanece firmada como `HOLD` hasta demostrar los requisitos canónicos, formales y operacionales restantes.

## Certificación independiente del paquete ZIPAPP

La raíz confiable ahora está desplegada en la rama por defecto y escucha solo builds de tipo `push` en la rama de candidatura. Para cada nuevo build, ejecuta G22 y G23 en jobs separados y verifica las atestaciones OIDC/Sigstore con una etapa G24 separada. La evidencia se liga al commit, al SHA-256 y tamaño exactos del paquete, al hash del registro G22/G23, al baseline V8 y al contrato de alcance embebido.

El certificado de software de alcance declarado puede emitirse únicamente si:
- G22 confirma estructura e integridad ZIP, baseline V8 byte-exacto, igualdad byte-exacta de los documentos de autoridad comparables y del contrato de alcance, informe de pruebas y reconstrucción reproducible.
- Los cinco comandos independientes G23 pasan sobre el paquete exacto, con salidas hasheadas y sin variables de secreto ni claves privadas.
- GitHub verifica la atestación OIDC/Sigstore de G23 y, después, la atestación del certificado G24.

La emisión tiene dos resultados distintos: `CERTIFIED_FOR_DECLARED_STANDALONE_SOFTWARE_SCOPE` para el paquete exacto, si la cadena pasa, y `HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN` para certificación canónica integral. No hay transferencia automática entre esos estados.

Fuera del alcance quedan la comparación byte-exacta con `LUNACORE_final_formalized_v25.md` (ese baseline no está disponible en el repositorio), la admisión canónica de PUAC.C25–C32, la demostración formal Agda/Cubical/HoTT y la autorización operacional. No se realizan pruebas contra servicios remotos, mTLS ni rollback de producción en este flujo.

Estado de esta edición documental: prepara la ejecución de un nuevo build por `push`; no constituye por sí misma evidencia G22/G23/G24 ni un certificado emitido.

