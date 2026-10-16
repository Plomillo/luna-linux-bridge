# CUSTOSZV9 / CRFU — estado de implementación candidata

**Estado:** `PROPOSED_UNCERTIFIED_SUCCESSOR`. La CI de construcción demuestra únicamente lo que ejecuta y reporta; no concede G22, G23, G24, admisión canónica, activación ni certificación operativa.

## Baseline V8

El constructor obtiene el baseline desde el archivo binario raíz `CUSTOSZV8.pyz` rastreado por Git, calcula SHA-256 y tamaño, copia los bytes íntegros a `custoszv9/data/CUSTOSZV8.pyz`, verifica el digest y vuelve a medir el baseline después de construir. Extrae solo los miembros `custoszv8/**` del ZIPAPP para que los comandos V8 puedan importarse en el mismo intérprete V9; no lanza un proceso/runtime V8 duplicado. El tamaño de entrada requerido es 99.400 bytes. La identidad con otra copia externa requiere comparar SHA-256; el mismo tamaño por sí solo no demuestra identidad.

## Capacidades CRFU materializadas

- Contrato tipado de tarea y validación de forma/identidad.
- Planificación topológica determinista, presupuesto de alternativas, dependencias sin resolver y ciclos.
- Presupuesto de RAM/disco/concurrencia: las mediciones ausentes o no confiables producen HOLD.
- Antiparálisis con presupuesto finito y rechazo de repetir la misma estrategia en el mismo estado sin evidencia nueva.
- Diario JSONL encadenado por hash, bloqueo de escritores y detección de manipulación.
- Puente de evidencia formal vinculada al digest, alcance, toolchain, supuestos y limitaciones.
- Capa de equivalencia acotada; autoridad, autorización, firma, identidad binaria y certificación no se transportan.
- Registro de checkpoint separado de la prueba de restauración; se valida hash, identidad, dependencias, invariantes y journal.
- Coordinador que requiere verificadores de autorización y adaptadores de operación inyectados de confianza; la referencia de autorización no es una autorización.
- Enrutamiento de comandos V8 desde el mismo intérprete V9.
- Fuentes Agda candidatas y pruebas reproducibles de software.

## Límites explícitos

Las fuentes Agda se incluyen, pero el build actual no ejecuta Agda/Cubical ni demuestra correspondencia entre modelo y código. No se afirma que HoTT/univalencia esté formalmente verificada. Las pruebas locales del paquete son de alcance limitado; la integración de producción V7/Runtime/MetaOS sigue condicionada a las interfaces y pruebas respectivas. El build de software no sustituye G22/G23/G24 independientes ni las firmas Ed25519 separadas exigidas por el documento de cadena de evidencia PUAC2.

`PUAC2.md` en `main` declara `EXTENSION_INDEPENDIENTE_PENDIENTE_ADMISION_FORMAL`, `G23=NO_CONCEDIDA` y `G24=NO_CONCEDIDA`. Los controles C25–C32 permanecen locales y no se presentan como controles canónicos admitidos. El flujo PUAC2 también exige evidencias reales de host, rollback y mTLS; si esos prerrequisitos fallan, la decisión operativa debe quedar en HOLD aunque pase la construcción del artefacto.

## G22/G23/G24

La validación independiente debe reconstruir identidad y resultados desde los artefactos originales, no heredar afirmaciones del productor. G24 debe consumir el mismo commit y digest y verificar identidad de G23 antes de emitir cualquier decisión. La atestación de GitHub Actions/Sigstore puede aportar procedencia, pero no sustituye por sí sola las firmas Ed25519 distintas ni la cadena PUAC2. Faltan la auditoría exacta de aplicabilidad canónica, ejecución formal y el enlace efectivo con las firmas/host PUAC2; en su ausencia, liberación integral = HOLD.
