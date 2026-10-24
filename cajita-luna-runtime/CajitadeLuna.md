# Cajita de Luna — Runtime reproducible V9

**Formato de distribución:** `CAJITA_RUNTIME_MACRODOWN/1.0`, archivo contenedor ZIP determinista con extensión `.macrodown`.
**Límite bruto operativo vigente:** 470.000.000 bytes (decimal, exacto).
**Orden canónico de rutas:** Cerebro → Orquestación → Transcripción → Traductor Inteligente → Inteligencia documental → Sistema Inteligente.

## Dominios y route_type

| route_type | ID | directorio relativo |
|---|---|---|
| `cerebro` | D01_CEREBRO | `1. Cerebro/` |
| `orquestacion` | D02_ORQUESTACION | `2. Orquestación/` |
| `transcripcion` | D03_TRANSCRIPCION | `3. Transcripción/` |
| `traductor_inteligente` | D04_TRADUCTOR_INTELIGENTE | `4. Traductor Inteligente/` |
| `inteligencia_documental` | D05_INTELIGENCIA_DOCUMENTAL | `5. Inteligencia documental/` |
| `sistema_inteligente` | D06_SISTEMA_INTELIGENTE | `6. Sistema Inteligente/` |

Los seis directorios contienen cada uno su adaptador y los recursos cuantizados de su candidato. El runtime `cajita_runtime.py` ofrece enrutamiento por dominio, autoprueba de estructura, auditoría SHA-256 de pesos y smoke por ruta.

## Routing de los 14 comandos y asignación por subdominio

El registro ejecutable de asignaciones es `command_subdomain_routing.json`. Conserva las catorce órdenes canónicas y sus bindings de agente/motores E01–E15, y añade destinos concretos por subdominio, compatibilidad de motores por destino y los diez activos de infraestructura con versión, ruta, tamaño y SHA-256.

El árbol de enrutamiento tiene seis dominios, 21 destinos registrados, 19 subdominios explícitos y quince motores canónicos enlazados a los destinos. Sistema Inteligente conserva sus once subdominios; Traductor Inteligente conserva sus tres; Orquestación tiene tres; Inteligencia documental tiene dos. Los subdominios se seleccionan por orden canónico e intención de la tarea, con ejecución secuencial y carga bajo demanda.

Los activos `.7z` son paquetes de soporte, no ejecutables directos. Antes de invocarlos se requiere extracción bajo demanda, verificación SHA-256, adaptador real de consumidor, smoke nativo y medición de recursos. El router conserva `PLAN_ONLY` y deniega ejecución si esas dependencias/evidencias no están disponibles. Una asignación registrada no equivale a prueba de funcionamiento.

La identidad de comando es estricta. Solo se aceptan las catorce grafías canónicas y los cinco aliases explícitos registrados en el contrato; no se normalizan arbitrariamente todas las mayúsculas/minúsculas. La tabla de auditoría se conserva en `../docs/cajita-luna/LOUKSNA_14_COMMAND_SUBDOMAIN_AUDIT_20261023.md`.

## Construcción reproducible

El generador es `reproduce_macrodown.py`; no necesita acceso a GitHub ni a la red. Enumera de forma recursiva los archivos regulares del directorio de runtime y calcula el manifiesto con tamaño y SHA-256. El build debe ejecutarse después de reconciliar el presupuesto bruto; el script deniega la construcción si se supera el límite.

Desde la raíz extraída de este paquete:

```bash
python3 -B reproduce_macrodown.py --output ../CAJITA_LUNA_RUNTIME_V9.macrodown
python3 -B cajita_runtime.py status
python3 -B cajita_runtime.py selftest
python3 -B cajita_runtime.py audit-weights
python3 -B cajita_runtime.py smoke --domain 1
python3 -B cajita_runtime.py smoke --domain 2
python3 -B cajita_runtime.py smoke --domain 3
python3 -B cajita_runtime.py smoke --domain 4
python3 -B cajita_runtime.py smoke --domain 5
python3 -B cajita_runtime.py smoke --domain 6
```

D05 ejecuta el verificador de carga del candidato cuantizado; la generación OCR completa requiere una evaluación funcional posterior. Las dependencias de Python del host se declaran en `REQUIREMENTS.runtime.lock`; no se incluyen instalaciones gigantes del framework dentro del límite de payload.

## Activos cuantizados inventariados

| Dominio | Activo | Bytes |
|---|---|---:|
| Cerebro | `1. Cerebro/model.safetensors` | 40.489.120 |
| Transcripción | `3. Transcripción/model.safetensors` | 10.399.882 |
| Traductor Inteligente | `4. Traductor Inteligente/Traducción general/model.safetensors` | 11.720.882 |
| Inteligencia documental | `5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_weights.bin` | 13.483.380 |
| Sistema Inteligente | `6. Sistema Inteligente/Análisis Avanzado/model.safetensors` | 14.956.240 |
| Sistema Inteligente | `6. Sistema Inteligente/Anti-Alucinaciones/model.onnx` | 110.516.001 |
| **Total de seis archivos de modelo/pesos** | | **201.565.505** |

## Integración de activos recuperados — registro aditivo

**Registro:** `CAJITA_LUNA_RUNTIME_V9_ASSET_INTEGRATION_20261023`  
**Árbol auditado:** `main`, commit `5bcb6fedd1860a2943df6c1d7f54623170218510`.  
**Registro estructurado:** [EXTERNALIZED_ASSET_PLACEMENT.json](EXTERNALIZED_ASSET_PLACEMENT.json).  
**Regla de integración:** conservar los dominios y rutas canónicas; identificar cada artefacto por ruta, versión, tamaño y SHA-256; no equiparar presencia física con prueba funcional ni certificación.

Los diez archivos siguientes están presentes físicamente bajo sus rutas internas de dominio. Sus blobs del destino son idénticos a los blobs recuperados en staging y sus tamaños coinciden con el inventario. La clasificación de procedencia se preserva: siete son coincidencias exactas del registro de externalización y tres son candidatos oficiales que difieren del hash o tamaño registrado originalmente.

| Orden de dominio | ID | Ruta interna relativa a `cajita-luna-runtime/` | Versión | Bytes | SHA-256 | Relación con registro original |
|---|---|---|---|---:|---|---|
| D02 — Orquestación | `APACHE_JENA_6_2_0` | `2. Orquestación/Multi + Interdisciplinar/apache-jena-6.2.0.tar.gz` | 6.2.0 | 23.986.647 | `14c12ef4aa2f0078a473be4b10b015e0e0b85e767d6867e8581679de8fec3f6e` | Coincidencia exacta |
| D02 — Orquestación | `PLAYWRIGHT_1_63_0_SOURCE` | `2. Orquestación/Orquestador/playwright-1.63.0.tar.gz` | v1.63.0 | 40.525.667 | `bc3d50b5a6c51cd401b2b4a71514be75ffd91223e129abcee51b8913746e4c6d` | Coincidencia exacta |
| D06 — Sistema Inteligente | `ONNX_RUNTIME_1_29_0_CP311` | `6. Sistema Inteligente/Anti-Alucinaciones/onnxruntime-1.29.0-cp311-cp311-manylinux_2_28_x86_64.whl` | 1.29.0 | 23.113.193 | `85f8e8406c52658735fe5c7fbfd3ebaa1ed340768324f6252e4274e374580a23` | Candidato oficial PyPI; hash/tamaño distintos del registro original |
| D06 — Sistema Inteligente | `DAGGER_0_21_8_LINUX_AMD64` | `6. Sistema Inteligente/Cognitive CI - CD/dagger_v0.21.8_linux_amd64.tar.gz` | v0.21.8 | 21.927.634 | `53e226c7da8fb75171e58c35759d736d961ce8b3a12db0baa7b7107954fccc5a` | Coincidencia exacta |
| D06 — Sistema Inteligente | `OPA_STATIC_LINUX_AMD64_CANDIDATE` | `6. Sistema Inteligente/Cognitive CI - CD/opa_linux_amd64_static` | v1.21.3 | 64.185.579 | `add7c9dcf56e1ce1538426a6ee595ea1cc7ee830bbedd4c23219825b02b19a79` | Candidato oficial OPA; versión no fijada en el registro original y hash/tamaño distintos |
| D06 — Sistema Inteligente | `RQLITE_10_2_7_LINUX_AMD64` | `6. Sistema Inteligente/Migración y Persistencia/rqlite-v10.2.7-linux-amd64.tar.gz` | v10.2.7 | 17.600.273 | `0b4e8ffbbacc84e421c49915bbd82cc67ac6488e22d4ce58b678fc1219c6a38a` | Coincidencia exacta |
| D06 — Sistema Inteligente | `SQLITE_SOURCE_3_53_4` | `6. Sistema Inteligente/Migración y Persistencia/sqlite-src-3530400.zip` | 3.53.4 | 14.557.315 | `d18fa15aec74d8c17e1463f861095adc01b5ad190256acb4f91d22f0368d232b` | Coincidencia exacta |
| D06 — Sistema Inteligente | `CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE` | `6. Sistema Inteligente/Portabilidad base/cmake-4.4.3-windows-x86_64.zip` | 4.4.3 | 54.408.599 | `4d52ebab7193a698651639ed80d8d04fd903358843572cf44c7fd234cb7c26ab` | Paquete oficial base de Kitware; no es el artefacto `.optimized.zip` del registro original |
| D06 — Sistema Inteligente | `AVALONIA_12_1_1_NUGET` | `6. Sistema Inteligente/Runtime Android Windows/avalonia.12.1.1.nupkg` | 12.1.1 | 10.112.805 | `193bf6ae8b90293acb72bca8a1d62e8e46b460a48527f5f1f18f629073d9d77d` | Coincidencia exacta |
| D06 — Sistema Inteligente | `TAURI_2_11_5_SOURCE_ZIP` | `6. Sistema Inteligente/Runtime Android Windows/tauri-tauri-v2.11.5.zip` | tauri-v2.11.5 | 16.117.618 | `a85eb38b0ffc7b37b5c2eadbd637dc1206fb7f719bfe5b3ceca37ad5dac42cdd` | Coincidencia exacta |
| **Total de diez archivos recuperados** | | | | **286.535.330** | | **7 exactos + 3 candidatos oficiales alternativos** |

### Control de integración y puerta de publicación

- **Presencia en el árbol fuente:** PASS, 10/10 rutas encontradas.
- **Tamaño Git frente al inventario:** PASS, 10/10 coinciden.
- **Identidad del blob destino frente al archivo de staging:** PASS, 10/10 idénticos.
- **Integridad criptográfica:** el registro estructurado conserva los SHA-256 de los artefactos. Para los tres candidatos alternativos, el hash identifica el candidato oficial recuperado y no acredita identidad con el artefacto externalizado original.
- **Integración funcional:** NO VERIFICADA. La colocación física no equivale a instalación, enlace con adaptadores, pruebas de ejecución ni certificación de los motores.
- **Inclusión en el manifiesto de distribución previo:** NO. `MACRODOWN_MANIFEST.json` corresponde al snapshot anterior y no debe reinterpretarse como si ya enumerara estos diez archivos.
- **Puerta bruta del paquete:** pendiente de reconciliación y reconstrucción. La auditoría completa del árbol, diferenciando los punteros Git LFS de sus objetos declarados, queda registrada en `../docs/cajita-luna/CAJITA_FORENSIC_PAYLOAD_AUDIT_20261023.json`. No se deben tomar las cifras del manifiesto estático anterior como inventario del árbol actual.
- **Estado del artefacto distribuible:** NO RECONSTRUIDO ni certificado con estos activos. No se actualiza el manifiesto anterior para fingir una inclusión ya empaquetada. La regeneración debe producir un manifiesto nuevo desde el árbol efectivo y pasar de nuevo ambas comprobaciones de límite.

## Auditoría forense pre-cuantización — 2026-10-23

**Informe forense completo:** [CAJITA_FORENSIC_PAYLOAD_AUDIT_20261023.json](../docs/cajita-luna/CAJITA_FORENSIC_PAYLOAD_AUDIT_20261023.json). El informe vive fuera de `cajita-luna-runtime/` para no añadir su propio inventario al payload distribuible.

El inventario del árbol `main` del commit base `91b1c89543511d171de83f20a46012f51f7c97a9` registró 144 archivos de entrada al generador, excluyendo el manifiesto estático que el generador reemplaza. La vista de blobs Git suma 504.063.305 bytes, pero contiene dos punteros Git LFS de 134 bytes. Sus OID SHA-256 y tamaños declarados coinciden con el manifiesto de pesos (148.477.400 y 110.516.001 bytes); el cuerpo actual de los dos objetos LFS no se descargó de nuevo durante esta auditoría. Con ambos objetos materializados conforme a sus declaraciones, la suma calculada de archivos de entrada es 763.056.438 bytes antes del manifiesto generado.

El manifiesto estático existente enumera 132 archivos, mientras que el árbol actual tiene 144 entradas de archivo destinadas al generador: hay 12 archivos no enumerados y cuatro divergencias visibles frente al snapshot antiguo. Dos divergencias son los punteros LFS; las otras corresponden a este documento y a `cajita_runtime.py`, modificados después de generarse aquel manifiesto. Por tanto, debe regenerarse a partir del árbol definitivo después de la optimización del payload, no corregirse manualmente con cifras supuestas.

**Clasificación para la auditoría de masa:** los diez activos recuperados son archivos de software (binarios, wheels, paquetes o archivos de código fuente), no tensores de pesos de modelos; la cuantización estadística de pesos no es la operación aplicable a esos diez artefactos. La reducción de sus bytes, si procede, se evalúa por tipo de artefacto y contenido incluido. Los seis elementos de `weights_manifest.json` suman 380.561.028 bytes declarados; la cuantización y la calidad no se dan por aprobadas únicamente por su etiqueta o por un smoke test.

**Alertas de evidencia que se conservan para priorizar el trabajo de peso:** el registro de Cerebro informa error relativo de Frobenius 0,998336 y un smoke runtime fallido; el informe de Qwen3 informa 0,996409 y deja el gate de calidad sin ejecutar/sin aprobar. El runtime de traducción solo tiene una prueba mínima con salida `te te te te`, y la generación completa de Docling no quedó completada. Son límites de evidencia relevantes para decidir qué pesos deben optimizarse, no certificaciones.

La auditoría no cuantizó, reemplazó ni eliminó binarios y no regeneró el manifiesto de distribución. La distinción entre inventario físico, contenido LFS materializado, peso de archivo y evidencia de calidad queda trazada en el informe enlazado.

## Alcance, entorno y evidencia

El registro `BUILD_PROVENANCE.json` fija las fuentes, el commit externo auxiliar y las pruebas observadas para el candidato V9 anterior. El registro aditivo de integración de activos está en `EXTERNALIZED_ASSET_PLACEMENT.json`; no sustituye la procedencia histórica. Los 22 manifiestos `D01.json`–`D22.json` del repositorio auxiliar se usan solo como información externa; no forman parte del paquete Cajita.

La prueba estructural y la integridad de los seis hashes de modelos son gates de contenido, no pruebas de equivalencia de calidad. D04 superó una generación de traducción mínima; D05 pasó la verificación de carga de su modelo. Las pruebas anteriores del candidato V4 dieron PASS para D01, D02, D03 y D06; D04 y D05 presentaban fallos que se han corregido en el candidato V9, con los límites de prueba descritos en el registro de procedencia. Equivalencia de calidad, validación independiente y certificación integral siguen sin establecerse.

**Estado de publicación:** las ubicaciones de los diez activos y este inventario documental están en GitHub. El artefacto distribuible `.macrodown` no se ha reconstruido ni publicado con estos activos; la puerta de límite bruto continúa bloqueada, como se documenta arriba.


## Compactación de los diez activos nuevos — 2026-10-23

Se ejecutó una pasada de compactación máxima de los diez activos incorporados, priorizando reducción de bytes. Los contenedores LZMA2/7z solo sustituyen al original cuando disminuyen estrictamente el tamaño; los originales recuperados continúan preservados en externalized-assets-staging para rollback. Los binarios ELF elegibles de Dagger, OPA y rqlite se sometieron a UPX con comprobación del empaquetado y ronda exacta de descompresión SHA-256. La relación entre ruta lógica y contenedor comprimido queda registrada en EXTERNALIZED_ASSET_PLACEMENT.json.

La reparación de rutas de extracción/consumo queda pendiente para la siguiente fase. No se modificaron los seis artefactos de peso/modelo preexistentes. La proyección usa los tamaños LFS declarados y excluye el manifiesto estático obsoleto; el constructor deberá regenerar el manifiesto tras la reparación y volver a comprobar el límite de 470.000.000 bytes. Certificación no otorgada.

Informe de evidencia: ../docs/cajita-luna/CAJITA_NEW_ENGINE_COMPACTION_20261023.json.


## Auditoría de integración funcional de los diez activos — 2026-10-23

**Referencia auditada:** rama `main`, commit de referencia `edf9f39cc5a65f338595775894a1526f5a99cb57`.
**Evidencia primaria:** [EXTERNALIZED_ASSET_PLACEMENT.json](EXTERNALIZED_ASSET_PLACEMENT.json), [CAJITA_NEW_ENGINE_COMPACTION_20261023.json](../docs/cajita-luna/CAJITA_NEW_ENGINE_COMPACTION_20261023.json) y [CAJITA_NEW_ENGINE_QUANTIZATION_20261023.json](../docs/cajita-luna/CAJITA_NEW_ENGINE_QUANTIZATION_20261023.json).

#### Resultado

- **Diez activos inventariados:** sí.
- **Diez artefactos disponibles en el árbol de runtime en sus formatos originales:** no. Las diez rutas de runtime apuntan a contenedores `.7z`; las copias fuente conservadas en `externalized-assets-staging/` están fuera del árbol de runtime.
- **Diez activos incluidos en `MACRODOWN_MANIFEST.json`:** no. El manifiesto estático previo enumera 132 archivos y los diez campos `included_in_current_macrodown_manifest` permanecen en `false`.
- **Integración funcional de los consumidores/rutas:** no verificada; `runtime_path_repair` sigue pendiente. Presencia del contenedor, prueba de integridad del contenedor y funcionamiento de la herramienta son controles distintos.
- **Cuantización de redes neuronales contenidas en esos diez paquetes:** no produjo ninguna reducción validada que permita cerrar el déficit. El escaneo halló solo tres ONNX de demostración dentro de ONNX Runtime; cero candidatos quedaron más pequeños y validados.
- **Puerta de tamaño:** bloqueada. La proyección bruta de entradas es `641.773.963` bytes frente a `470.000.000`; el exceso es `171.773.963` bytes, antes del crecimiento del manifiesto generado.

#### Decisión de control

`INTEGRATION_STATUS = BLOCKED_GLOBAL_SIZE_CAP`

No se declara que los diez activos estén funcionalmente integrados. No se deben descomprimir/copiarlos todos al árbol distribuible ni reconstruir/publicar el paquete hasta rebajar y volver a medir el payload global, preservando los seis artefactos de pesos existentes y validando cualquier optimización con pruebas funcionales. Hacerlo antes dejaría el paquete por encima del límite de tamaño. La extracción diferida a un entorno de instalación separado es una estrategia distinta y no equivale a incluir los diez artefactos expandidos en el `.macrodown`.

Este bloque registra el estado real de la auditoría actual; no sustituye ni borra los registros históricos de compactación.
## Catálogo canónico de los diez motores y componentes de infraestructura

Este catálogo incorpora los diez activos al mapa operativo de `CajitadeLuna.md` y los agrupa según el orden canónico de dominios de la Cajita. Se conserva el orden de los seis dominios: `1. Cerebro` → `2. Orquestación` → `3. Transcripción` → `4. Traductor Inteligente` → `5. Inteligencia documental` → `6. Sistema Inteligente`. Estos diez activos pertenecen a los dominios 2 y 6; no se inventan entradas para los dominios 1, 3, 4 o 5.

Los términos «motor» y «activo» se utilizan aquí para los componentes de infraestructura del runtime. No todos son modelos neuronales: Jena, Playwright, ONNX Runtime, Dagger, OPA, rqlite, SQLite, CMake, Avalonia y Tauri cumplen funciones distintas y no deben tratarse como pesos cuantizables equivalentes.

### Dominio 2 — Orquestación

| Orden | ID canónico del activo | Función prevista en Cajita | Directorio de materialización dentro del runtime | Paquete de origen registrado |
|---:|---|---|---|---|
| 01 | `APACHE_JENA_6_2_0` | Infraestructura RDF/OWL, grafos y consultas semánticas para los flujos interdisciplinarios. | `2. Orquestación/Multi + Interdisciplinar/APACHE_JENA_6_2_0/` | `apache-jena-6.2.0.tar.gz.7z` |
| 02 | `PLAYWRIGHT_1_63_0_SOURCE` | Automatización de navegador y pruebas end-to-end controladas del orquestador. | `2. Orquestación/Orquestador/PLAYWRIGHT_1_63_0_SOURCE/` | `playwright-1.63.0.tar.gz.7z` |

### Dominio 6 — Sistema Inteligente

| Orden | ID canónico del activo | Función prevista en Cajita | Directorio de materialización dentro del runtime | Paquete de origen registrado |
|---:|---|---|---|---|
| 03 | `ONNX_RUNTIME_1_29_0_CP311` | Runtime de inferencia ONNX para Linux x86-64 y CPython 3.11, ubicado bajo Anti-Alucinaciones para los consumidores compatibles. | `6. Sistema Inteligente/Anti-Alucinaciones/ONNX_RUNTIME_1_29_0_CP311/` | `onnxruntime-1.29.0-cp311-cp311-manylinux_2_28_x86_64.whl.7z` |
| 04 | `DAGGER_0_21_8_LINUX_AMD64` | Motor de ejecución de pipelines CI/CD reproducibles en Linux amd64 para Cognitive CI/CD. | `6. Sistema Inteligente/Cognitive CI - CD/DAGGER_0_21_8_LINUX_AMD64/` | `dagger_v0.21.8_linux_amd64.tar.gz.7z` |
| 05 | `OPA_STATIC_LINUX_AMD64_CANDIDATE` | Evaluación local de políticas como puerta de autorización/validación en Cognitive CI/CD. | `6. Sistema Inteligente/Cognitive CI - CD/OPA_STATIC_LINUX_AMD64_CANDIDATE/` | `opa_linux_amd64_static.7z` |
| 06 | `RQLITE_10_2_7_LINUX_AMD64` | Persistencia SQL replicada y servicio de base de datos distribuida. | `6. Sistema Inteligente/Migración y Persistencia/RQLITE_10_2_7_LINUX_AMD64/` | `rqlite-v10.2.7-linux-amd64.tar.gz.7z` |
| 07 | `SQLITE_SOURCE_3_53_4` | Fuentes del motor SQLite para compilación, integración y validación de persistencia embebida. | `6. Sistema Inteligente/Migración y Persistencia/SQLITE_SOURCE_3_53_4/` | `sqlite-src-3530400.zip.7z` |
| 08 | `CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE` | Herramienta de configuración/construcción para la base de portabilidad Windows x64. El ejecutable Windows no se declara ejecutable en Linux. | `6. Sistema Inteligente/Portabilidad base/CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE/` | `cmake-4.4.3-windows-x86_64.zip.7z` |
| 09 | `AVALONIA_12_1_1_NUGET` | Paquete NuGet de interfaz/runtime .NET para el dominio Runtime Android/Windows, sujeto a compatibilidad del consumidor .NET. | `6. Sistema Inteligente/Runtime Android Windows/AVALONIA_12_1_1_NUGET/` | `avalonia.12.1.1.nupkg.7z` |
| 10 | `TAURI_2_11_5_SOURCE_ZIP` | Fuentes del framework Rust/Tauri para el runtime de escritorio multiplataforma. | `6. Sistema Inteligente/Runtime Android Windows/TAURI_2_11_5_SOURCE_ZIP/` | `tauri-tauri-v2.11.5.zip.7z` |

### Contrato de materialización y validación

1. Cada activo debe quedar expandido en el directorio indicado, con sus nombres, subdirectorios y bytes de origen preservados; los diez `.7z` no cuentan por sí solos como integración del motor.
2. La automatización verifica tamaño y SHA-256 del contenedor, integridad 7z, recuento de miembros, tipo de contenido esperado y hash del árbol copiado. Los contenedores optimizados se conservan fuera del árbol de runtime como rollback.
3. La expansión no autoriza por sí sola la inclusión en `MACRODOWN_MANIFEST.json`, la reconstrucción del paquete, la cuantización de componentes que no sean modelos neuronales ni la certificación funcional. Las pruebas nativas de ejecución y el rebalanceo del límite global de `470.000.000` bytes son puertas separadas.
4. El estado realmente materializado se determina mediante `docs/cajita-luna/CAJITA_TEN_ASSET_EXPANSION_20261023.json` y la sección generada `Despliegue materializado de los diez activos`; este catálogo fija la asignación arquitectónica de carpetas y no sustituye esas evidencias.

**Regla de orden:** no reordenar los seis dominios ni mover un activo entre dominios sin cambio explícito y trazable de su asignación. Se preservan los seis artefactos de peso/modelo preexistentes y se mantiene el estado de certificación en `NOT_GRANTED` hasta superar las validaciones independientes pertinentes.


## Despliegue materializado de los diez activos — 2026-10-23

Se extrajeron los diez contenedores internos y su contenido real quedó materializado bajo el árbol persistente de Cajita. Los contenedores optimizados se conservaron como copias de rollback fuera del árbol de distribución. Se validaron SHA-256 y tamaños de los contenedores, integridad 7z, número de miembros, tipos de payload esperados y la ronda de copia del árbol expandido. Los seis hashes de los artefactos de peso/modelo preexistentes permanecen idénticos. Las pruebas de ejecución de los ejecutables nativos no forman parte de esta pasada y se mantienen explícitamente como pendientes.

| Activo | Ruta expandida en runtime | Archivos/objetos | Bytes expandidos | Validación |
|---|---|---:|---:|---|
| APACHE_JENA_6_2_0 | `cajita-luna-runtime/2. Orquestación/Multi + Interdisciplinar/APACHE_JENA_6_2_0` | 251 | 27,295,036 | PASS |
| PLAYWRIGHT_1_63_0_SOURCE | `cajita-luna-runtime/2. Orquestación/Orquestador/PLAYWRIGHT_1_63_0_SOURCE` | 3093 | 68,493,538 | PASS |
| ONNX_RUNTIME_1_29_0_CP311 | `cajita-luna-runtime/6. Sistema Inteligente/Anti-Alucinaciones/ONNX_RUNTIME_1_29_0_CP311` | 322 | 62,736,574 | PASS |
| DAGGER_0_21_8_LINUX_AMD64 | `cajita-luna-runtime/6. Sistema Inteligente/Cognitive CI - CD/DAGGER_0_21_8_LINUX_AMD64` | 2 | 15,382,954 | PASS |
| OPA_STATIC_LINUX_AMD64_CANDIDATE | `cajita-luna-runtime/6. Sistema Inteligente/Cognitive CI - CD/OPA_STATIC_LINUX_AMD64_CANDIDATE` | 1 | 25,271,120 | PASS |
| RQLITE_10_2_7_LINUX_AMD64 | `cajita-luna-runtime/6. Sistema Inteligente/Migración y Persistencia/RQLITE_10_2_7_LINUX_AMD64` | 3 | 12,970,604 | PASS |
| SQLITE_SOURCE_3_53_4 | `cajita-luna-runtime/6. Sistema Inteligente/Migración y Persistencia/SQLITE_SOURCE_3_53_4` | 2208 | 111,974,369 | PASS |
| CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE | `cajita-luna-runtime/6. Sistema Inteligente/Portabilidad base/CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE` | 8819 | 143,281,458 | PASS |
| AVALONIA_12_1_1_NUGET | `cajita-luna-runtime/6. Sistema Inteligente/Runtime Android Windows/AVALONIA_12_1_1_NUGET` | 121 | 35,926,924 | PASS |
| TAURI_2_11_5_SOURCE_ZIP | `cajita-luna-runtime/6. Sistema Inteligente/Runtime Android Windows/TAURI_2_11_5_SOURCE_ZIP` | 1058 | 21,729,836 | PASS |

El manifiesto estático de distribución no se declara actualizado ni certificado. La expansión deja pendiente el rebalanceo del tamaño global y la fase de cuantización/optimización; la reconstrucción debe ejecutarse solo tras reducir el payload a un máximo de `470.000.000` bytes.

Informe: `../docs/cajita-luna/CAJITA_TEN_ASSET_EXPANSION_20261023.json`.


## Rebalanceo físico del payload — 2026-10-23

**Operación aplicada:** los diez árboles expandidos (15.877 archivos; 525.037.706 bytes de blobs Git) se sustituyen en las rutas de runtime por sus diez contenedores LZMA2/7z verificados. Las copias fuente y los contenedores de reversión se conservan fuera del payload, en `externalized-assets-staging/`; no se cambia la identidad/versionado de los diez componentes. El orden de los seis dominios permanece intacto. La restauración del formato original se realiza desde los contenedores con verificación SHA-256 contra el registro de colocación.

**Reducción medida de esta operación:** 525.037.706 bytes de árboles expandidos eliminados del payload + 165.250.049 bytes de contenedores añadidos = reducción neta de 359.787.657 bytes en la representación Git del runtime. Esta cifra no equivale al tamaño bruto final distribuible porque los dos objetos Git LFS de modelos se contabilizan por su tamaño declarado, no por los punteros de 134 bytes.

**Puerta de tamaño global:** sigue bloqueada hasta cuantizar y validar los pesos neuronales. La proyección previa con objetos LFS materializados era 641.773.963 bytes; por tanto, la siguiente reducción requerida es de al menos 171.773.964 bytes más el crecimiento del manifiesto. Los diez componentes de infraestructura no se someten a cuantización de tensores. Los seis archivos de modelo/pesos no se sustituyen automáticamente ni se declaran equivalentes: sus candidatos cuantizados requieren comparación de calidad, hashes, pruebas por dominio, validación independiente y rollback. El límite bruto de 470.000.000 bytes sigue siendo un hard gate; no se construye ni publica un paquete que lo exceda.

**Certificación:** NOT_GRANTED. La compactación física no prueba por sí sola la integración funcional ni la equivalencia de calidad.


## Rebalanceo de peso cuantizado — 2026-10-23

La pasada actúa sobre los factores INT8 de bajo rango de los cuatro motores que usan model.safetensors y ensaya cuantización INT8 dinámica del ONNX. Un candidato solo se promueve si reduce bytes y el smoke de salida conserva la firma funcional determinista observada antes de la transformación. Los artefactos originales quedan recuperables en el historial Git; el informe registra hashes, tamaños y rollback.

| Motor | Ruta | Estado | Bytes originales | Bytes candidatos/activos |
|---|---|---|---:|---:|
| W01_CEREBRO | `1. Cerebro/model.safetensors` | PROMOTED_Q4_BLOCKWISE | 148477400 | 116856296 |
| W02_TRANSCRIPTION | `3. Transcripción/model.safetensors` | PROMOTED_Q4_BLOCKWISE | 34877948 | 21579806 |
| W03_TRANSLATION | `4. Traductor Inteligente/Traducción general/model.safetensors` | PROMOTED_Q4_BLOCKWISE | 20256147 | 14765381 |
| W05_QWEN3 | `6. Sistema Inteligente/Análisis Avanzado/model.safetensors` | PROMOTED_Q4_BLOCKWISE | 52950152 | 28687808 |
| W06_ONNX | `6. Sistema Inteligente/Anti-Alucinaciones/model.onnx` | CANDIDATE_NOT_SMALLER | 110516001 | 110581945 |

El control de tamaño suma los archivos reales del runtime, excluye únicamente el manifiesto de distribución que el constructor regenera y compara con el techo decimal de 470.000.000 bytes. Este control de tamaño no equivale por sí solo a certificación integral de calidad.


## Segunda pasada de INT4 para tensores flotantes — 2026-10-23

Se empaquetaron tensores de precisión restantes en bloques INT4 con escala por bloque, manteniendo el mismo modelo lógico y restaurando el dtype original al cargar. Los candidatos se promueven solo si reducen el tamaño total (modelo más sidecar) y la prueba de arranque/generación sigue pasando. La firma de salida se registra separadamente; equivalencia de calidad y certificación no quedan establecidas.

| Motor | Estado | Tensores empaquetados | Bytes originales elegibles | Bytes netos ahorrados |
|---|---|---:|---:|---:|
| W01_CEREBRO | PROMOTED_FLOAT_Q4_BLOCKWISE | 72 | 79626240 | 58439856 |
| W02_TRANSCRIPTION | PROMOTED_FLOAT_Q4_BLOCKWISE | 2 | 4986880 | 3660882 |
| W03_TRANSLATION | NO_LARGE_FLOAT_TENSORS_TO_PACK | 0 | 0 | 0 |
| W05_QWEN3 | NO_LARGE_FLOAT_TENSORS_TO_PACK | 0 | 0 | 0 |


## Segunda pasada de empaquetado de factores a 2 bits — 2026-10-23

Los factores de bajo rango que ya estaban empaquetados en INT4 se recodificaron como enteros afines sin signo de 2 bits por bloque, con mínimos y pasos FP32 por grupo. Cada candidato se admite únicamente si reduce el total modelo+sidecar y la prueba de arranque/generación sigue pasando. La comparación de firma se registra, pero no equivale a equivalencia de calidad ni certificación.

| Motor | Estado | Tensores factores | Bytes del modelo previos | Bytes candidatos/activos | Bytes netos ahorrados |
|---|---|---:|---:|---:|---:|
| W01_CEREBRO | PROMOTED_Q2_BLOCKWISE | 508 | 58391640 | 40489120 | 17826826 |
| W02_TRANSCRIPTION | PROMOTED_Q2_BLOCKWISE | 472 | 17918086 | 10399882 | 7445404 |
| W03_TRANSLATION | PROMOTED_Q2_BLOCKWISE | 1682 | 14765381 | 11720882 | 2771797 |
| W05_QWEN3 | PROMOTED_Q2_BLOCKWISE | 564 | 28687808 | 14956240 | 13647850 |


## Sustitución operativa BTX por SQLite — 2026-10-23

El recurso BTX del runtime se ha sustituido por la candidata SQLite en la ruta equivalente del dominio Orquestación. El PDF empaquetado en el antiguo contenedor .7z ya no está en la ruta de runtime.

- Recurso activo: 2. Orquestación/Confesión Eclesial Reformada/Biblia Textual BTX -- Biblia Textual BTX -- ( WeLib.org ).sqlite3
- Tamaño: 6.750.208 bytes.
- SHA-256: fdb4a43776a06e76cf772242bc8c802970b2b55c9544cd03826aa8453bc993e0.
- Fuente original preservada para rollback fuera del runtime: externalized-assets-staging/2-Orquestacion/BTX/Biblia_Textual_BTX_original_rollback.7z
- Construcción de origen: GitHub Actions run 40041740047, artefacto 12539134323.
- Estado: RUNTIME_SUBSTITUTION=APPLIED_UNCERTIFIED; STRUCTURAL_VALIDATION=PASS; BYTE_REPRODUCIBILITY=PASS; SOURCE_TO_VERSE_CONTENT_EQUIVALENCE=NOT_INDEPENDENTLY_VALIDATED; EDITORIAL_APPARATUS=NOT_INCLUDED_OR_CERTIFIED; CERTIFICATION=NOT_GRANTED; OPERABILITY=UNVERIFIED.

Esta sustitución cambia el formato de almacenamiento del recurso; no declara certificación integral del texto bíblico ni equivalencia versículo por versículo. La entrada A029 conserva los hashes, tamaños, procedencia y estado pendiente. El archivo original se retiene únicamente para recuperación.


## Auditoría integral del inventario y subsistema CLI — 2026-10-24

**Fuente de verdad:** árbol de Git y manifiesto Macrodown regenerado durante la construcción reproducible. Presencia de archivo, instalación de proveedor, operatividad y certificación se registran como estados diferentes.

### Subsistema CLI

La infraestructura modular se mantiene en `2. Orquestación/Orquestador/CLIs/`: `cli_contract.json`, `cli_registry.py`, `cli_manager.py`, `common.py`, los ocho adaptadores y las pruebas. `punto.json` es el punto de entrada declarativo. El documento anterior `CLIS.txt` se migra a este contrato, no se interpreta como prueba de que estén instaladas las ocho herramientas proveedoras.

El modo predeterminado es de solo lectura. La instalación de proveedores requiere versión exacta fijada, fuente oficial y comprobación de integridad, plan versionado con SHA-256 explícitamente aprobado, checkpoint previo, rollback, prueba posterior y evidencia estructurada. No hay uso implícito de shell, privilegios, tokens ni actualizaciones. Python se audita pero no se sustituye como runtime del sistema. La autenticación de cada proveedor es un control aparte y sus secretos nunca se registran.

El workflow `.github/workflows/cajita-cli-host-audit.yml` hace una auditoría de solo lectura del runner Linux `luna-aux` y preserva el resultado JSON como artefacto de GitHub Actions. Separa la coherencia de la infraestructura (`infrastructure_status`) del estado real de los proveedores (`provider_host_readiness`). La infraestructura no se declara certificada por existir el código.

### Inventario completo del runtime

La construcción reproducible regenera `MACRODOWN_MANIFEST.json` con ruta, tamaño, SHA-256, dominio y tipo de compresión para cada archivo distribuido. El informe generado `docs/cajita-luna/CAJITA_INVENTORY_AUDIT_20261024.json` añade el propio manifiesto al inventario final, reconcilia rutas añadidas/retiradas/modificadas, separa los seis dominios canónicos del soporte de raíz y registra tamaño bruto, tamaño empaquetado y hash del artefacto construido. El workflow debe guardar en Git el manifiesto regenerado y el informe.

Dominios, en orden inmutable:
1. `1. Cerebro`
2. `2. Orquestación`
3. `3. Transcripción`
4. `4. Traductor Inteligente`
5. `5. Inteligencia documental`
6. `6. Sistema Inteligente`

### Pendientes preservados

- BTX está almacenada como SQLite en el runtime y el archivo original se conserva fuera para rollback. La equivalencia versículo por versículo y el aparato editorial no están validados de forma independiente; certificación integral no concedida.
- Los 121 registros externos de `RUNTIME_CANDIDATE_V1/registry.json` declaran operatividad y dependencias `UNVERIFIED`. Son referencias externas, no bytes incluidos automáticamente en el paquete Macrodown.
- El workflow de expansión de diez componentes registró el fallo `DESTINATION_EXISTS_FAIL_CLOSED:APACHE_JENA_6_2_0`. Su reintento no debe depender de una edición documental ni interpretarse como integración funcional. Ejecución nativa, cableado y rollback de ese flujo siguen separados.
- Equivalencia de calidad de los modelos, verificación independiente y certificación integral siguen pendientes de las pruebas registradas por dominio.
- Cada build debe medir el contenido real con objetos Git LFS materializados y comprobar el límite duro de `470.000.000` bytes. Ningún número histórico sustituye la medición del build actual.

**Estado de esta sección:** inventario trazable y actualización continua prevista; certificación integral `NOT_GRANTED`.


## Estado reconciliado de inventario y CLI — evidencia final 2026-10-24

Esta adenda registra el estado posterior a la sustitución BTX, la instalación del subsistema CLI y la reconstrucción reproducible de Macrodown. Las menciones anteriores a “manifiesto no regenerado” y “paquete no reconstruido” describen un estado histórico anterior a esta adenda; no describen el artefacto validado abajo. Se conservan para trazabilidad, sin que prevalezcan sobre esta evidencia posterior.

### Distribución actual comprobada en GitHub

- Inventario distribuido: 151 archivos más MACRODOWN_MANIFEST.json = 152 miembros en el paquete.
- Payload bruto sin manifiesto: 464.090.916 bytes.
- Payload bruto incluido manifiesto: 464.130.593 bytes.
- Archivo Macrodown reproducible: 412.237.160 bytes.
- Límite duro: 470.000.000 bytes. Puertas de tamaño bruto y de archivo: PASS.
- SHA-256 del artefacto Macrodown: 9fc7dedde0076524d1f1c98bb353521cc914de5217d4fb18e1b276ddc401b580.
- MACRODOWN_MANIFEST.json está regenerado y versionado con el mismo inventario que fue incrustado en el archivo construido.

Inventario individual completo, tamaños, SHA-256, clasificación por dominio y comparación de rutas con la versión previa: docs/cajita-luna/CAJITA_INVENTORY_AUDIT_20261024.json. Manifiesto de contenido: MACRODOWN_MANIFEST.json. Evidencia de build: docs/cajita-luna/CAJITA_MACRODOWN_BUILD_20261023.json.

### Subsistema CLIs

La infraestructura en 2. Orquestación/Orquestador/CLIs/ contiene el contrato de dominios, registro de sondas, gestor de operaciones, utilidades comunes, ocho adaptadores y pruebas. punto.json está vinculado a esos módulos y conserva el orden canónico de los ocho dominios. CLIS.txt fue retirado de esta ruta después de migrar su especificación al contrato modular; su SHA histórico se conserva como procedencia. Las pruebas de CI de la infraestructura pasaron (compilación sintáctica y nueve pruebas de regresión).

Auditoría de solo lectura del host Linux registrado (runner luna-aux), capturada el 2026-10-24 a las 00:57:32 UTC:

| Dominio | Estado observado | Evidencia resumida |
|---|---|---|
| CLI_MOJO | AVAILABLE | Mojo 1.1.0 |
| CLI_CPP23_TOOLCHAIN | AVAILABLE | g++ 14.2.0, smoke C++23 PASS; CMake 3.31.6; Ninja 1.12.1; clang++ ausente pero opcional |
| CLI_CLAUDE_CODE | ABSENT | No se encontró claude |
| CLI_PYTHON | AVAILABLE | Python 3.13.5; pip 25.1.1 |
| CLI_GITHUB | AVAILABLE | GitHub CLI 2.46.0; Git 2.47.3 como soporte |
| CLI_GEMINI | ABSENT | No se encontró gemini |
| CLI_GROK | ABSENT | No se encontró grok |
| CLI_HUGGING_FACE | ABSENT | No se encontraron hf ni huggingface-cli |

Resultado de la infraestructura: PASS. Disponibilidad de proveedores en el host: PARTIAL (4/8). La auditoría no instaló ni actualizó proveedores ni modificó PATH. La instalación de los cuatro ausentes permanece bloqueada hasta definir pines de versión exactos, verificar procedencia e integridad, crear checkpoint y rollback, y aprobar el plan versionado mediante su SHA-256. Por ello no se declara que los ocho proveedores estén instalados o certificados.

Evidencia registrada: docs/cajita-luna/CAJITA_CLI_HOST_AUDIT_20261024.json. Artefacto original de ejecución: cajita-cli-host-audit-40047411263.

### Pendientes funcionales y de gobernanza

1. **BTX en SQLite:** archivo activo 2. Orquestación/Confesión Eclesial Reformada/Biblia Textual BTX -- Biblia Textual BTX -- ( WeLib.org ).sqlite3, 6.750.208 bytes, SHA-256 fdb4a43776a06e76cf772242bc8c802970b2b55c9544cd03826aa8453bc993e0. La ruta del antiguo archivo PDF/7z está ausente del inventario de distribución y su original se conserva fuera del runtime para rollback. La equivalencia versículo por versículo y el aparato editorial no han recibido validación independiente: certificación no concedida.
2. **Registro de recursos externos:** 121 referencias siguen con dependencias y operatividad UNVERIFIED. No se deben tratar como parte de los 151 archivos que sí contiene el paquete, ni como dependencias ya resueltas.
3. **Diez activos de infraestructura:** el intento previo de expansión fue abortado de forma fail-closed por DESTINATION_EXISTS_FAIL_CLOSED:APACHE_JENA_6_2_0. La colocación/compresión verificada no constituye prueba de ejecución nativa ni cableado funcional integral.
4. **Calidad de modelos:** siguen sin establecerse equivalencia de calidad e independencia de validación para el conjunto completo. El PASS del límite de tamaño no equivale a certificación integral.

**Estado final de la evidencia disponible:** inventario de distribución actualizado y reproducible; infraestructura CLI modular presente y probada; presencia real de proveedores auditada parcialmente; gates funcionales independientes aún pendientes; CERTIFICATION=NOT_GRANTED.
