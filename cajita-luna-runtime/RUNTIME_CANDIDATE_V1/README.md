# Cajita — núcleo Runtime candidato V1

Estado: `RUNTIME_CANDIDATE`. La implementación contiene tres operaciones locales comprobables: integridad SHA-256, estructura JSON y cabecera safetensors. El registro describe 121 recursos originales en 23 grupos. La ejecución funcional de los modelos, paquetes y capacidades de esos grupos permanece `UNVERIFIED` y bloqueada.

El núcleo es infraestructura subordinada a la arquitectura; no redefine su identidad, autoridad, axiomas, bloques, agentes ni comandos. Su validación específica no certifica toda Cajita, no produce LOUKSNA1 y no incorpora OMOT.

## Archivos y contabilidad

- `runtime.py`: operaciones y ciclo de control; usa únicamente biblioteca estándar de Python.
- `registry.json`: rutas relativas a Cajita, hashes, tamaños, grupos, contratos y clasificación de distribución.
- `README.md`: alcance, uso, controles y límites.

El producto entregado no contiene pesos, paquetes copiados, fixtures ni trazas de las pruebas. Al ejecutar una operación, crea su propio directorio `RUNTIME_CANDIDATE_V1/state` dentro de la raíz indicada. Ese estado operativo posterior debe medirse por separado del núcleo inicial.

| Partida | Tratamiento |
|---|---|
| Núcleo | Suma física de los tres archivos entregados; medición y SHA-256 publicados en la evidencia de aceptación |
| Recursos registrados | 128.230.075.138 bytes originales, residentes en Cajita y externos al núcleo |
| Dependencias externas adicionales | Tamaño y cierre `UNVERIFIED`; valor numérico desconocido, no cero |
| Total físico conocido de esta entrega y recursos | Núcleo + recursos registrados; es un límite inferior del conjunto funcional |
| Total funcional completo | `UNVERIFIED` mientras falten dependencias y adaptadores |
| Techo bruto de Cajita | 479.000.000 bytes, decimal; los recursos registrados ya lo exceden |
| Equivalencia funcional / certificación global | `UNVERIFIED` / no concedida |

Un núcleo pequeño no convierte los recursos externos en gratuitos ni demuestra preservación funcional bajo el techo. Las categorías de residencia, distribución y archivo describen ubicación/empaquetado; no declaran recursos opcionales ni autorizan su eliminación. Se conserva la clasificación funcional previa de los 23 grupos.

## Uso

Requiere Python 3.10 o posterior; validación realizada con el intérprete local disponible. Desde esta carpeta:

```text
python -B runtime.py list
python -B runtime.py plan A007
python -B runtime.py run A007 --operation json_structure
python -B runtime.py capability cap-04
python -B runtime.py plan-capability cap-04
python -B runtime.py run-capability cap-04
python -B runtime.py audit-state
python -B runtime.py restore checkpoint-<hash>.json
```

`A007` identifica el recurso registrado `1. Cerebro/config.json`. `cap-04` identifica un grupo, no un archivo. `capability` consulta su contrato; `plan-capability` devuelve un plan determinista bloqueado; `run-capability` registra el intento y deniega activación por ausencia de adaptador o cierre de dependencias. Marcar un adaptador como VALIDATED en datos no crea una implementación: también se bloquea cualquier ejecución de grupo no implementada.

`--root` permite indicar la raíz de recursos; todas las rutas del registro deben quedar contenidas en esa raíz. El registro está fijado por SHA-256 en el código. Cambiarlo exige una nueva revisión de código y evidencia; no se acepta silenciosamente un registro distinto.

## Contratos y selección

Cada grupo expone `id`, `resource_set`, `dependencies`, `adapter_state`, `operability_state`, `activation_rule`, `validation_rule`, `block_reason` y `trace_rule`. Conserva nombre, tamaño y procedencia descriptiva del inventario. Una presencia registrada no demuestra disponibilidad continua ni ejecutabilidad.

Las operaciones se seleccionan sobre un único recurso:

| Operación | Contrato |
|---|---|
| `integrity` | Leer secuencialmente y verificar tamaño, tipo, identidad de archivo y SHA-256; no interpretar su contenido |
| `json_structure` | Verificar integridad y analizar hasta 8 MiB de JSON; rechazar claves duplicadas, números no finitos y formato inválido; devolver solo tipo y cantidad de elementos superiores |
| `safetensors_header` | Verificar integridad del archivo y analizar hasta 8 MiB de cabecera; comprobar tipos admitidos, dimensiones, rangos, continuidad y tamaños; no cargar tensores en un motor |

`auto` elige JSON acotado para un `.json` compatible, cabecera para `.safetensors`, e integridad para el resto. Solo selecciona un recurso y una operación; no activa simultáneamente todos los grupos. La verificación SHA-256 recorre el archivo completo incluso si después solo se interpreta su cabecera. Las dimensiones/dtypes no admitidos provocan rechazo; esa limitación no significa que el modelo original sea inválido.

## Ciclo verificable

La operación sigue PLAN → CHECKPOINT → ACTIVATE → VALIDATE → RELEASE. Ante error sigue FAILURE → RELEASE conservando el último resultado válido. El recurso original se abre únicamente para lectura. El checkpoint permite restaurar estado de control anterior mediante ROLLBACK sin truncar la historia de eventos.

Cada evento incluye secuencia, hash anterior, estado y hash propio. La relectura comprueba cadena, estado derivado y orden de transiciones; una liberación exitosa requiere validación anterior. Escrituras de control usan archivo pendiente, sincronización y reemplazo local; un bloqueo exclusivo impide dos escritores cooperativos. Un estado parcial, bloqueo abandonado o archivo pendiente impide continuar automáticamente y requiere recuperación revisada. La capacidad de restauración no promete reparar archivos fuente externos, que este núcleo nunca modifica.

Se rechazan escapes de ruta, rutas absolutas o ambiguas, enlaces simbólicos, puntos de reanálisis, enlaces duros, hashes alterados, identidades de archivo cambiadas, checkpoints corruptos y cadenas inconsistentes. Las pruebas incluyen una sustitución sintética de identidad durante lectura y metadatos sintéticos de reparse/symlink; también usan un enlace duro real en un fixture.

Los hashes de la cadena detectan inconsistencia y permiten replay; no son firmas de autor ni protección contra un atacante que reescriba coherentemente todos los datos y el código de confianza. La exclusión de escritores es cooperativa. No se certifica resistencia universal frente a cambios concurrentes maliciosos del sistema de archivos. Los límites de 8 MiB del journal y del JSON provocan rechazo, sin truncamiento silencioso.

La implementación no importa paquetes del inventario, no instala dependencias, no deserializa pickle, no ejecuta binarios de recursos ni utiliza red. La certificación independiente y la operatividad global quedan pendientes de sus propios gates.
