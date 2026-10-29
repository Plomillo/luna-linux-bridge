# LOUKSNAPG — auditoría forense de traducción de lenguas antiguas

Fecha de observación: 2026-10-29 UTC. Rama examinada: `louksnapg/phase4-resume-20261028`.

## Decisión ejecutiva

`D04_TRADUCCION_LENGUAS_ANTIGUAS` existe como subdominio declarado y el planificador tiene reglas de intención para griego koiné/griego bíblico, latín, hebreo, arameo, siríaco, Vulgata y Septuaginta. Sin embargo, **no hay prueba de una operación real de traducción de lenguas antiguas**. El módulo es actualmente código fuente del compilador Foma; no incluye un transductor de traducción compilado, un léxico operacional ni un adaptador consumidor registrado. El dominio permanece bloqueado para la certificación.

## 1. Defecto concreto y evidencia

- Target: `D04_TRADUCCION_LENGUAS_ANTIGUAS`.
- Módulo: `cajita-luna-runtime/4. Traductor Inteligente/Traducción de lenguas antiguas`.
- Descriptor del módulo: `schema=CAJITA_CANONICAL_TARGET_MODULE/1.0`, `consumer_adapter_registration.status=NOT_REGISTERED`, `native_smoke=REQUIRED`, `functional_state=MODULE_REGISTERED_ADAPTER_AND_NATIVE_SMOKE_REQUIRED`, `certification=NOT_GRANTED`.
- Descriptor Git: `target_id=D04_TRADUCCION_LENGUAS_ANTIGUAS`, árbol declarado de 72 archivos y 797.405 bytes; hash de árbol declarado `ccc2d8db85945f0864bb3bb26bd67737332d7cdccdfe034dc5b6607947ed6a26`.
- Archivo fuente original del compilador dentro del módulo: `4. Traductor Inteligente/Traducción de lenguas antiguas/foma-master.zip`, 225.343 bytes, SHA-256 `93d2a4eeb811f4bc3fbe584a35385f1aae07908ef42d2893693eabd354db1e74`.
- La inspección de 87 rutas del subárbol encontró cero artefactos con extensiones de transductor compilado `.fst`, `.hfst`, `.hfstol`, `.ol`, `.att` o `.dict`. Hay código de compilador C y archivos `.foma` de ejemplo/test, incluidos ejemplos de finés y hixkaryana; no son un recurso de traducción para las lenguas asignadas.
- La tabla de rutas asigna de forma explícita `D04_TRADUCCION_LENGUAS_ANTIGUAS` y elimina `D04_TRADUCCION_GENERAL` cuando coincide la intención de lenguas antiguas. El planificador informa el adaptador del target como `NOT_REGISTERED` y mantiene `execution_authorized=false`.

La verificación del árbol fue una consulta GET de solo lectura a la API Git de la rama; no descargó ni compiló el módulo en la PC.

## 2. Consecuencia funcional

La configuración puede seleccionar correctamente el subdominio, pero no tiene consumidor ejecutable que convierta la entrada lingüística en una traducción. La presencia del compilador Foma, sus tests o la ruta declarada no acredita traducción. Usar `D04_TRADUCCION_GENERAL` como fallback ocultaría el defecto y violaría la separación de dominios.

## 3. Corrección necesaria

1. Aclarar el par de idiomas que el proyecto debe certificar primero, porque los artefactos existentes enumeran varias familias lingüísticas pero no fijan un par operativo de origen/destino.
2. Obtener o construir un léxico/transductor adecuado para ese par con procedencia, licencia, revisión y hashes verificables. No utilizar los ejemplos genéricos de Foma como si fueran un léxico.
3. Registrar un adaptador consumidor independiente para `D04_TRADUCCION_LENGUAS_ANTIGUAS`; mantener `D04_TRADUCCION_GENERAL` fuera de esa operación.
4. Añadir un conjunto de entradas conocidas con referencias de traducción, incluidos acentos/variantes ortográficas que formen parte del alcance.

No se incorporó un diccionario ficticio ni se descargó otro modelo grande, y no se reasignaron los motores canónicos.

## 4. Verificación posterior requerida

La corrección sólo se cerrará cuando una tarea de traducción se ejecute en el runtime exacto de `LOUKSNAPG.md`, la entrada transite por el target antiguo y devuelva la traducción esperada; el informe debe enlazar SHA del paquete, transductor, adaptador, entrada y salida. También debe comprobar que una entrada desconocida falla explícitamente y no recurre al traductor general.

Se añadió al harness G24 una prueba de ruta que ejecuta `cajita_router.py plan` con una petición de griego koiné y verifica el target seleccionado, la exclusión del traductor general, el adaptador ausente y el bloqueo fail-closed. Esa prueba sólo es diagnóstica: **no certifica la función de traducción**. El resultado real de este probe está pendiente de la ejecución hospedada `40794248442` y no se declara pasado hasta leer su evidencia.

## Estado de las cuatro obligaciones

| Obligación | Estado |
|---|---|
| Defecto concreto | Confirmado: falta adaptador consumidor y transductor/léxico |
| Consecuencia funcional | Confirmada: no hay operación E2E ejecutable para certificar |
| Corrección | Especificada; requiere un par lingüístico objetivo y un recurso adecuado |
| Verificación posterior | Harness de ruta agregado; prueba de ejecución pendiente y función sin reparar |

`CERTIFICATION=D04_TRADUCCION_LENGUAS_ANTIGUAS:NOT_GRANTED`
