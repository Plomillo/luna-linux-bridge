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

## Código fuente íntegro del subsistema CLI — embebido en CajitadeLuna.md

Este bloque contiene una copia literal, ligada por ruta y SHA de blob Git, de la infraestructura operativa que también se conserva como archivos ejecutables en el runtime. Se incorpora aquí para que CajitadeLuna.md no sea solo una referencia descriptiva. La ubicación operativa sigue siendo `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/`; `CLIS.txt` permanece eliminado. La especificación no certifica por sí sola que todos los proveedores estén instalados.

Commit de origen leído: `3424c96aebfa215a4f090e85e4e7089221ba18bc`.

### `punto.json`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/punto.json`  
Blob SHA de Git: `b08ba089ccf8e646ecf7e582c066cd6a8d9dfd4a`  
Longitud en bytes/characters devuelta por el repositorio: 6295

````json
{
  "authority": "Louksna.md",
  "certification": "NOT_GRANTED",
  "cli_extension_framework": {
    "role": "EXTENSIBLE_INFRASTRUCTURE_NOT_NINTH_CLI"
  },
  "cli_spec": {
    "migration_status": "IMPLEMENTED_MODULAR_INFRASTRUCTURE_LEGACY_TEXT_REMOVED",
    "legacy_git_path": "cajita-luna-runtime/2. Orquestación/Orquestador/CLIS.txt",
    "legacy_git_blob_sha": "146afab4ef88e659cba5b94c2e989f7106fdd1e4",
    "replacement_contract_path": "CLIs/cli_contract.json",
    "replacement_registry_path": "CLIs/cli_registry.py",
    "replacement_manager_path": "CLIs/cli_manager.py",
    "policy": "TEXT_SPEC_MIGRATED_TO_VERSIONED_MODULAR_IMPLEMENTATION; HOST_PROVIDER_INSTALLATION_IS_TRACKED_SEPARATELY"
  },
  "created_at_utc": "2026-10-17T20:36:25Z",
  "doctrine": "EXTEND_DO_NOT_REPLACE",
  "domain_order": [
    "CLI_MOJO",
    "CLI_CPP23_TOOLCHAIN",
    "CLI_CLAUDE_CODE",
    "CLI_PYTHON",
    "CLI_GITHUB",
    "CLI_GEMINI",
    "CLI_GROK",
    "CLI_HUGGING_FACE"
  ],
  "domains": [
    {
      "allowed_default_effects": [
        "DISCOVER",
        "VERSION_PROBE",
        "DIAGNOSE"
      ],
      "dependencies": "UNRESOLVED_UNTIL_INVENTORY",
      "executable_probe": {
        "argv": [
          "--version"
        ],
        "binary": "mojo"
      },
      "id": "CLI_MOJO",
      "initial_state": "HOST_AUDIT_PENDING",
      "module": "CLIs/cli_mojo.py",
      "mutations": "DENY_UNTIL_VERSIONED_ACTION_CONTRACT"
    },
    {
      "allowed_default_effects": [
        "DISCOVER",
        "VERSION_PROBE",
        "DIAGNOSE"
      ],
      "dependencies": "UNRESOLVED_UNTIL_INVENTORY",
      "executable_probe": {
        "argv": [
          "--version"
        ],
        "binary": "g++"
      },
      "id": "CLI_CPP23_TOOLCHAIN",
      "initial_state": "HOST_AUDIT_PENDING",
      "module": "CLIs/cli_cpp23_toolchain.py",
      "mutations": "DENY_UNTIL_VERSIONED_ACTION_CONTRACT"
    },
    {
      "allowed_default_effects": [
        "DISCOVER",
        "VERSION_PROBE",
        "DIAGNOSE"
      ],
      "dependencies": "UNRESOLVED_UNTIL_INVENTORY",
      "executable_probe": {
        "argv": [
          "--version"
        ],
        "binary": "claude"
      },
      "id": "CLI_CLAUDE_CODE",
      "initial_state": "HOST_AUDIT_PENDING",
      "module": "CLIs/cli_claude_code.py",
      "mutations": "DENY_UNTIL_VERSIONED_ACTION_CONTRACT"
    },
    {
      "allowed_default_effects": [
        "DISCOVER",
        "VERSION_PROBE",
        "DIAGNOSE"
      ],
      "dependencies": "UNRESOLVED_UNTIL_INVENTORY",
      "executable_probe": {
        "argv": [
          "--version"
        ],
        "binary": "python3"
      },
      "id": "CLI_PYTHON",
      "initial_state": "HOST_AUDIT_PENDING",
      "module": "CLIs/cli_python.py",
      "mutations": "DENY_UNTIL_VERSIONED_ACTION_CONTRACT"
    },
    {
      "allowed_default_effects": [
        "DISCOVER",
        "VERSION_PROBE",
        "DIAGNOSE"
      ],
      "dependencies": "UNRESOLVED_UNTIL_INVENTORY",
      "executable_probe": {
        "binary": "gh",
        "argv": [
          "--version"
        ],
        "support_binary": "git",
        "support_is_not_substitute": true
      },
      "id": "CLI_GITHUB",
      "initial_state": "HOST_AUDIT_PENDING",
      "module": "CLIs/cli_github.py",
      "mutations": "DENY_UNTIL_VERSIONED_ACTION_CONTRACT"
    },
    {
      "allowed_default_effects": [
        "DISCOVER",
        "VERSION_PROBE",
        "DIAGNOSE"
      ],
      "dependencies": "UNRESOLVED_UNTIL_INVENTORY",
      "executable_probe": {
        "argv": [
          "--version"
        ],
        "binary": "gemini"
      },
      "id": "CLI_GEMINI",
      "initial_state": "HOST_AUDIT_PENDING",
      "module": "CLIs/cli_gemini.py",
      "mutations": "DENY_UNTIL_VERSIONED_ACTION_CONTRACT"
    },
    {
      "allowed_default_effects": [
        "DISCOVER",
        "VERSION_PROBE",
        "DIAGNOSE"
      ],
      "dependencies": "UNRESOLVED_UNTIL_INVENTORY",
      "executable_probe": {
        "binary": "grok",
        "argv": [
          "--version"
        ],
        "provider_package": "@xai-official/grok",
        "official_source": "https://x.ai/cli/install.sh",
        "execution_only_after_official_installation_identity_verification": true
      },
      "id": "CLI_GROK",
      "initial_state": "HOST_AUDIT_PENDING",
      "module": "CLIs/cli_grok.py",
      "mutations": "DENY_UNTIL_VERSIONED_ACTION_CONTRACT"
    },
    {
      "allowed_default_effects": [
        "DISCOVER",
        "VERSION_PROBE",
        "DIAGNOSE"
      ],
      "dependencies": "UNRESOLVED_UNTIL_INVENTORY",
      "executable_probe": {
        "binary": "hf",
        "argv": [
          "--help"
        ],
        "legacy_discovery_only": "huggingface-cli"
      },
      "id": "CLI_HUGGING_FACE",
      "initial_state": "HOST_AUDIT_PENDING",
      "module": "CLIs/cli_hugging_face.py",
      "mutations": "DENY_UNTIL_VERSIONED_ACTION_CONTRACT"
    }
  ],
  "role": "DECLARATIVE_ENTRYPOINT_NOT_MONOLITHIC_IMPLEMENTATION",
  "schema": "CUSTOSZ_ORCHESTRATOR_MANIFEST/1.0",
  "security": {
    "checkpoint_before_mutation": true,
    "credential_values_never_logged": true,
    "fail_closed_for_unauthorized_mutation": true,
    "independent_validation_required": true,
    "install_update_requires_explicit_versioned_plan": true,
    "no_silent_path_or_shell_mutation": true,
    "official_hash_signature_used_when_published": true,
    "read_only_discovery_before_changes": true,
    "rollback_and_post_validation_required": true
  },
  "shared_runtime_policy": {
    "evidence_jsonl_hash_chain": true,
    "idempotent": true,
    "max_concurrency": 1,
    "subprocess_shell": false,
    "timeout_seconds_default": 30
  },
  "cli_subsystem": {
    "contract": "CLIs/cli_contract.json",
    "registry": "CLIs/cli_registry.py",
    "manager": "CLIs/cli_manager.py",
    "test_path": "CLIs/tests/test_cli_registry.py",
    "host_audit_workflow": ".github/workflows/cajita-cli-host-audit.yml",
    "default_mode": "READ_ONLY_AUDIT_AND_PLAN",
    "install_requires": [
      "EXACT_VERSION_PIN",
      "OFFICIAL_SOURCE_AND_INTEGRITY",
      "PRE_MUTATION_CHECKPOINT",
      "ROLLBACK",
      "POST_VALIDATION",
      "EXACT_PLAN_SHA256_APPROVAL"
    ],
    "certification": "NOT_GRANTED"
  }
}
````

### `cli_contract.json`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/cli_contract.json`  
Blob SHA de Git: `d32da89a22a6e569a94619fac28ddc0c7562b5e9`  
Longitud en bytes/characters devuelta por el repositorio: 4477

````json
{
  "schema": "CAJITA_CLI_INFRASTRUCTURE_CONTRACT/1.0",
  "authority": "Louksna.md",
  "doctrine": "EXTEND_DO_NOT_REPLACE",
  "legacy_specification": {
    "path": "cajita-luna-runtime/2. Orquestación/Orquestador/CLIS.txt",
    "git_blob_sha": "146afab4ef88e659cba5b94c2e989f7106fdd1e4",
    "migration_status": "MIGRATED_TO_MODULAR_CONTRACT"
  },
  "domain_order": [
    "CLI_MOJO",
    "CLI_CPP23_TOOLCHAIN",
    "CLI_CLAUDE_CODE",
    "CLI_PYTHON",
    "CLI_GITHUB",
    "CLI_GEMINI",
    "CLI_GROK",
    "CLI_HUGGING_FACE"
  ],
  "governance": {
    "default_mode": "READ_ONLY_AUDIT_AND_PLAN",
    "allowed_default_effects": [
      "DISCOVER",
      "VERSION_PROBE",
      "DIAGNOSE"
    ],
    "install_requires": [
      "EXACT_VERSION_PIN",
      "OFFICIAL_SOURCE",
      "SOURCE_INTEGRITY",
      "EXPLICIT_PLAN_SHA256_APPROVAL",
      "PRE_MUTATION_CHECKPOINT",
      "ROLLBACK_PLAN",
      "POST_VALIDATION",
      "STRUCTURED_EVIDENCE"
    ],
    "shell": false,
    "implicit_sudo": false,
    "secret_logging": false,
    "cross_domain_mutation": false,
    "fail_closed": true,
    "certification_propagation": false,
    "extension_framework": "CLI_EXTENSION_FRAMEWORK"
  },
  "domains": [
    {
      "id": "CLI_MOJO",
      "provider": "Modular",
      "module": "cli_mojo.py",
      "package": "mojo",
      "binary": "mojo",
      "official_sources": [
        "https://docs.modular.com/mojo/manual/install",
        "https://mojolang.static.modular.com/install/"
      ],
      "status": "PIN_REQUIRED"
    },
    {
      "id": "CLI_CPP23_TOOLCHAIN",
      "provider": "GNU/LLVM, CMake, Ninja",
      "module": "cli_cpp23_toolchain.py",
      "package": "system toolchain",
      "binary": "g++ or clang++ plus cmake and ninja",
      "official_sources": [
        "https://gcc.gnu.org/",
        "https://clang.llvm.org/",
        "https://cmake.org/",
        "https://ninja-build.org/"
      ],
      "status": "VERSIONED_PLATFORM_PLAN_REQUIRED"
    },
    {
      "id": "CLI_CLAUDE_CODE",
      "provider": "Anthropic",
      "module": "cli_claude_code.py",
      "package": "@anthropic-ai/claude-code",
      "binary": "claude",
      "official_sources": [
        "https://docs.anthropic.com/en/docs/claude-code/getting-started"
      ],
      "status": "PIN_REQUIRED"
    },
    {
      "id": "CLI_PYTHON",
      "provider": "Python / OS distribution",
      "module": "cli_python.py",
      "package": "python3",
      "binary": "python3",
      "official_sources": [
        "https://docs.python.org/3/using/unix.html"
      ],
      "status": "HOST_AUDIT_ONLY_DO_NOT_REPLACE_SYSTEM_PYTHON"
    },
    {
      "id": "CLI_GITHUB",
      "provider": "GitHub CLI maintainers",
      "module": "cli_github.py",
      "package": "gh",
      "binary": "gh",
      "official_sources": [
        "https://cli.github.com/",
        "https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
      ],
      "status": "PIN_AND_INTEGRITY_REQUIRED"
    },
    {
      "id": "CLI_GEMINI",
      "provider": "Google",
      "module": "cli_gemini.py",
      "package": "@google/gemini-cli",
      "binary": "gemini",
      "official_sources": [
        "https://geminicli.com/docs/get-started/installation/"
      ],
      "status": "PIN_REQUIRED"
    },
    {
      "id": "CLI_GROK",
      "provider": "xAI",
      "module": "cli_grok.py",
      "package": "@xai-official/grok",
      "binary": "grok",
      "official_sources": [
        "https://x.ai/cli/install.sh",
        "https://docs.x.ai/build/overview"
      ],
      "status": "OFFICIAL_DISTRIBUTION_IDENTIFIED_PIN_REQUIRED"
    },
    {
      "id": "CLI_HUGGING_FACE",
      "provider": "Hugging Face",
      "module": "cli_hugging_face.py",
      "package": "huggingface_hub",
      "binary": "hf",
      "official_sources": [
        "https://huggingface.co/docs/huggingface_hub/guides/cli"
      ],
      "status": "PIN_REQUIRED"
    }
  ],
  "extension": {
    "id": "CLI_EXTENSION_FRAMEWORK",
    "role": "EXTENSIBLE_CONTRACT_NOT_NINTH_CLI",
    "required_fields": [
      "canonical_id",
      "official_source",
      "version_pin",
      "package",
      "binary",
      "dependencies",
      "health_check",
      "integrity",
      "rollback",
      "provenance",
      "independent_validation"
    ],
    "activation": [
      "DISCOVER",
      "REGISTER",
      "RESOLVE",
      "EVIDENCE",
      "VALIDATE",
      "INDEPENDENT_VALIDATE",
      "CERTIFY",
      "ACTIVATE"
    ]
  }
}
````

### `cli_manager.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/cli_manager.py`  
Blob SHA de Git: `0fe88a61f69ab5978ae53962941faa97adfcf97d`  
Longitud en bytes/characters devuelta por el repositorio: 13436

````python
from __future__ import annotations
import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parent
ORCHESTRATOR=ROOT.parent
sys.path.insert(0,str(ROOT))
import cli_registry
CONTRACT=ROOT/"cli_contract.json"
MANIFEST=ORCHESTRATOR/"punto.json"
SENSITIVE=re.compile(r"(token|password|passwd|secret|api[_-]?key|authorization|credential)",re.I)
INSTALL_TOOLS={"npm","uv","pipx","apt-get","dnf"}
def utc(): return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def digest(data): return hashlib.sha256(data).hexdigest()
def read_json(path):
    obj=json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj,dict): raise ValueError("JSON_ROOT_NOT_OBJECT")
    return obj
def atomic_write(path,obj):
    path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    tmp.replace(path)
def build_plan():
    contract=read_json(CONTRACT); actions=[]
    for d in contract["domains"]:
        if d.get("id")=="CLI_PYTHON":
            status="AUDIT_ONLY_NO_INSTALL_MUTATION"
        elif not d.get("version_pin"):
            status="BLOCKED_VERSION_PIN_REQUIRED"
        elif d.get("status","").startswith("BLOCKED"):
            status="BLOCKED_OFFICIAL_SOURCE_UNVERIFIED"
        else:
            status="BLOCKED_SOURCE_INTEGRITY_EVIDENCE_REQUIRED"
        actions.append({"domain_id":d["id"],"package":d.get("package"),"version_pin":d.get("version_pin"),"status":status,"mutations_authorized":False})
    return {"schema":"CAJITA_CLI_INSTALL_PLAN/1.0","created_at_utc":utc(),"contract_sha256":digest(CONTRACT.read_bytes()),"manifest_sha256":digest(MANIFEST.read_bytes()),"domain_order":contract["domain_order"],"status":"BLOCKED_FAIL_CLOSED","actions":actions,"commands":[],"no_mutations":True,"reason":"No vendor install is run without exact contract pins, source-integrity evidence, rollback steps and an approved exact plan SHA-256.","certification":"NOT_GRANTED"}
def validate_argv(step,domain,rollback=False):
    if not isinstance(step,dict) or not isinstance(step.get("argv"),list) or not step["argv"] or any(not isinstance(x,str) or not x for x in step["argv"]):
        raise ValueError("INSTALL_STEP_ARGV_INVALID:"+domain)
    argv=step["argv"]; exe=pathlib.Path(argv[0]).name; args=argv[1:]
    if exe not in INSTALL_TOOLS: raise ValueError("INSTALL_EXECUTABLE_NOT_ALLOWLISTED:"+exe)
    if any(SENSITIVE.search(x) for x in argv): raise ValueError("POSSIBLE_SECRET_IN_ARGV_DENIED:"+domain)
    if any(x in {"upgrade","dist-upgrade","purge","autoremove","autoclean","clean"} for x in args):
        raise ValueError("DESTRUCTIVE_PACKAGE_OPERATION_DENIED")
    if exe=="npm":
        allowed={"install","uninstall"}
        if not args or args[0] not in ({"uninstall"} if rollback else {"install"}): raise ValueError("NPM_OPERATION_NOT_ALLOWLISTED")
        if "--global" not in args or "--prefix" not in args: raise ValueError("NPM_INSTALL_MUST_USE_EXPLICIT_USER_PREFIX")
        package_args=[x for x in args if not x.startswith("-") and x not in allowed]
        if not package_args: raise ValueError("NPM_PACKAGE_REQUIRED")
        if not rollback and not any(re.search(r"@(?:[0-9]+\.){1,2}[0-9]+",x) for x in package_args):
            raise ValueError("NPM_EXACT_VERSION_PIN_REQUIRED")
    elif exe=="uv":
        expected=["tool","uninstall"] if rollback else ["tool","install"]
        if len(args)<2 or args[:2]!=expected: raise ValueError("UV_OPERATION_NOT_ALLOWLISTED")
        if not rollback and not any(re.search(r"==[^=]+$",x) for x in args): raise ValueError("UV_EXACT_VERSION_PIN_REQUIRED")
    elif exe=="pipx":
        expected="uninstall" if rollback else "install"
        if not args or args[0]!=expected: raise ValueError("PIPX_OPERATION_NOT_ALLOWLISTED")
        if not rollback and not any(re.search(r"==[^=]+$",x) for x in args): raise ValueError("PIPX_EXACT_VERSION_PIN_REQUIRED")
    elif exe=="apt-get":
        required="remove" if rollback else "install"
        if required not in args or (not rollback and not any(re.search(r"=[^=]+$",x) for x in args if not x.startswith("-"))):
            raise ValueError("APT_EXACT_VERSIONED_OPERATION_REQUIRED")
        if any(x in {"-y","--yes"} for x in args) is False: raise ValueError("APT_INTERACTIVE_OR_UNCONFIRMED_OPERATION_DENIED")
    elif exe=="dnf":
        required="remove" if rollback else "install"
        if required not in args or (not rollback and not any(re.search(r"=[^=]+$",x) for x in args if not x.startswith("-"))):
            raise ValueError("DNF_EXACT_VERSIONED_OPERATION_REQUIRED")
        if "-y" not in args and "--assumeyes" not in args: raise ValueError("DNF_INTERACTIVE_OR_UNCONFIRMED_OPERATION_DENIED")
    return argv
def verify_source_evidence(action,domain,version_pin,plan_dir,contract_domain):
    evidence=action.get("source_evidence")
    if not isinstance(evidence,dict): raise ValueError("SOURCE_INTEGRITY_EVIDENCE_REQUIRED:"+domain)
    raw_path=evidence.get("path")
    if not raw_path: raise ValueError("SOURCE_EVIDENCE_PATH_REQUIRED:"+domain)
    p=(plan_dir/raw_path).resolve(strict=True)
    try: p.relative_to(plan_dir.resolve())
    except ValueError: raise ValueError("SOURCE_EVIDENCE_PATH_ESCAPE:"+domain)
    raw=p.read_bytes()
    if digest(raw).lower()!=str(evidence.get("sha256","")).lower(): raise ValueError("SOURCE_EVIDENCE_HASH_MISMATCH:"+domain)
    doc=json.loads(raw.decode("utf-8"))
    official_source=evidence.get("official_source")
    if official_source not in contract_domain.get("official_sources",[]): raise ValueError("OFFICIAL_SOURCE_BINDING_MISMATCH:"+domain)
    if doc.get("official_source")!=official_source or doc.get("version_pin")!=version_pin or doc.get("source_integrity_status")!="PASS":
        raise ValueError("SOURCE_INTEGRITY_EVIDENCE_NOT_PASS:"+domain)
    if not re.fullmatch(r"[0-9a-fA-F]{64}",str(doc.get("artifact_sha256",""))): raise ValueError("SOURCE_ARTIFACT_SHA256_MISSING:"+domain)
    return {"path":str(p),"sha256":digest(raw),"artifact_sha256":doc["artifact_sha256"],"official_source":official_source,"version_pin":version_pin}
def verify_plan(path,approved):
    path=pathlib.Path(path).resolve(strict=True)
    raw=path.read_bytes()
    if not approved or digest(raw).lower()!=approved.lower(): raise ValueError("PLAN_SHA256_APPROVAL_MISMATCH")
    plan=json.loads(raw.decode("utf-8"))
    if plan.get("schema")!="CAJITA_CLI_INSTALL_PLAN/1.0" or plan.get("status")!="READY_TO_APPLY": raise ValueError("INSTALL_PLAN_NOT_READY_FAIL_CLOSED")
    if plan.get("no_mutations") is True: raise ValueError("READ_ONLY_PLAN_CANNOT_BE_APPLIED")
    if plan.get("contract_sha256")!=digest(CONTRACT.read_bytes()) or plan.get("manifest_sha256")!=digest(MANIFEST.read_bytes()): raise ValueError("INPUT_CHANGED_SINCE_PLAN")
    c=read_json(CONTRACT); cmap={d["id"]:d for d in c["domains"]}
    if plan.get("domain_order")!=c["domain_order"]: raise ValueError("INSTALL_PLAN_DOMAIN_ORDER_INVALID")
    actions=plan.get("actions")
    if not isinstance(actions,list) or not actions: raise ValueError("INSTALL_PLAN_HAS_NO_ACTIONS")
    seen=set(); validated=[]
    for action in actions:
        domain=action.get("domain_id")
        if domain not in cmap or domain in seen: raise ValueError("UNKNOWN_OR_DUPLICATE_DOMAIN:"+str(domain))
        seen.add(domain); d=cmap[domain]; pin=action.get("version_pin")
        if not pin or pin!=d.get("version_pin"): raise ValueError("VERSION_PIN_MISMATCH:"+domain)
        if action.get("mutations_authorized") is not True: raise ValueError("MUTATION_NOT_AUTHORIZED_IN_PLAN:"+domain)
        if not d.get("official_sources") or d.get("status","").startswith("BLOCKED"): raise ValueError("OFFICIAL_DISTRIBUTION_UNVERIFIED:"+domain)
        evidence=verify_source_evidence(action,domain,pin,path.parent,d)
        steps=action.get("steps"); rollback=action.get("rollback_steps")
        if not isinstance(steps,list) or not steps or not isinstance(rollback,list) or not rollback: raise ValueError("INSTALL_STEPS_OR_ROLLBACK_MISSING:"+domain)
        step_args=[validate_argv(x,domain,False) for x in steps]
        rollback_args=[validate_argv(x,domain,True) for x in rollback]
        validated.append((domain,steps,rollback,evidence))
    return plan,validated
def run_step(step,domain,rollback=False):
    argv=validate_argv(step,domain,rollback); started=time.monotonic()
    proc=subprocess.run(argv,shell=False,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=min(900,max(1,int(step.get("timeout_seconds",300)))),check=False)
    return {"executable":pathlib.Path(argv[0]).name,"argv_sha256":digest(json.dumps(argv,separators=(",",":")).encode()),"returncode":proc.returncode,"elapsed_seconds":round(time.monotonic()-started,3),"stdout_sha256":digest((proc.stdout or "").encode()),"stderr_sha256":digest((proc.stderr or "").encode()),"stdout_bytes":len((proc.stdout or "").encode()),"stderr_bytes":len((proc.stderr or "").encode()),"status":"PASS" if proc.returncode==0 else "FAIL"}
def probe_one(domain):
    contract=read_json(CONTRACT)
    d=next(x for x in contract["domains"] if x["id"]==domain)
    module=(ROOT/d["module"]).resolve()
    module.relative_to(ROOT.resolve())
    spec=__import__("importlib.util",fromlist=["spec_from_file_location"]).spec_from_file_location("cajita_"+domain.lower(),module)
    if spec is None or spec.loader is None: raise RuntimeError("PROBE_MODULE_UNAVAILABLE")
    mod=__import__("importlib.util",fromlist=["module_from_spec"]).module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.probe()
def apply_plan(path,approved,evidence_root=None):
    plan,actions=verify_plan(path,approved)
    before=cli_registry.run_registry()
    base=pathlib.Path(evidence_root or pathlib.Path.home()/".local/state/cajita-cli/checkpoints").resolve()
    base.mkdir(parents=True,exist_ok=True)
    operation=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+approved[:12]
    checkpoint=base/operation; checkpoint.mkdir(exist_ok=False)
    atomic_write(checkpoint/"before.json",before)
    action_results=[]; overall_ok=True
    for domain,steps,rollback_steps,evidence in actions:
        before_row=next((x for x in before["results"] if x.get("domain_id")==domain),{})
        step_results=[]; failed=False
        for step in steps:
            row=run_step(step,domain,False); step_results.append(row)
            if row["status"]!="PASS": failed=True; break
        post=None
        if not failed:
            post=probe_one(domain)
            if post.get("status")!="AVAILABLE": failed=True
        rollback_results=[]; rollback_verified=None
        if failed:
            overall_ok=False
            for step in reversed(rollback_steps):
                row=run_step(step,domain,True); rollback_results.append(row)
            after_rollback=probe_one(domain)
            rollback_verified=(all(x["status"]=="PASS" for x in rollback_results) and after_rollback.get("status")==before_row.get("status"))
            step_results.append({"post_install_status":None if post is None else post.get("status"),"status":"FAIL"})
        action_results.append({"domain_id":domain,"source_evidence":evidence,"status":"FAIL_ROLLED_BACK" if failed and rollback_verified else ("FAIL_ROLLBACK_UNVERIFIED" if failed else "PASS"),"steps":step_results,"rollback_steps":rollback_results,"rollback_verified":rollback_verified})
        if failed: break
    receipt={"schema":"CAJITA_CLI_INSTALL_EXECUTION/1.0","operation_id":operation,"created_at_utc":utc(),"plan_sha256":approved,"checkpoint_path":str(checkpoint),"pre_install_audit_sha256":digest(json.dumps(before,sort_keys=True).encode()),"status":"PASS" if overall_ok else "FAIL_ROLLBACK_ATTEMPTED","actions":action_results,"certification":"NOT_GRANTED"}
    atomic_write(checkpoint/"execution.json",receipt)
    return receipt
def main():
    p=argparse.ArgumentParser(description="Cajita CLI governance manager; audit/plan is read-only, installs require an approved immutable plan.")
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("audit"); a.add_argument("--output",type=pathlib.Path)
    b=sub.add_parser("plan"); b.add_argument("--output",type=pathlib.Path)
    c=sub.add_parser("apply-plan"); c.add_argument("--plan",required=True); c.add_argument("--approve-sha256",required=True); c.add_argument("--evidence-dir",type=pathlib.Path)
    x=p.parse_args()
    if x.command=="audit":
        result=cli_registry.run_registry(); result["manager"]={"status":"IMPLEMENTED","mode":"READ_ONLY_AUDIT","side_effects":False}
    elif x.command=="plan": result=build_plan()
    else:
        try: result=apply_plan(x.plan,x.approve_sha256,x.evidence_dir)
        except Exception as e: result={"status":"DENIED_FAIL_CLOSED","reason":str(e)[:700],"mutations_performed":False,"certification":"NOT_GRANTED"}
    if x.output: atomic_write(x.output,result)
    print(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False))
    return 0 if (x.command=="plan" or (x.command=="audit" and result.get("infrastructure_status")=="PASS") or result.get("status")=="PASS") else 2
if __name__=="__main__": raise SystemExit(main())
````

### `cli_registry.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/cli_registry.py`  
Blob SHA de Git: `89ebf3f2841f93ffb94c0c577f77872ccbb7948d`  
Longitud en bytes/characters devuelta por el repositorio: 5907

````python
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, pathlib, sys
from datetime import datetime, timezone
ROOT=pathlib.Path(__file__).resolve().parent
ORCHESTRATOR=ROOT.parent
sys.path.insert(0,str(ROOT))
ORDER=["CLI_MOJO","CLI_CPP23_TOOLCHAIN","CLI_CLAUDE_CODE","CLI_PYTHON","CLI_GITHUB","CLI_GEMINI","CLI_GROK","CLI_HUGGING_FACE"]
def utc(): return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read_json(p):
    v=json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError("JSON_ROOT_NOT_OBJECT")
    return v
def load_inputs(manifest_path=None,contract_path=None):
    mp=pathlib.Path(manifest_path or ORCHESTRATOR/"punto.json")
    cp=pathlib.Path(contract_path or ROOT/"cli_contract.json")
    m=read_json(mp); c=read_json(cp)
    if m.get("domain_order")!=ORDER or c.get("domain_order")!=ORDER: raise ValueError("DOMAIN_ORDER_MISMATCH")
    if m.get("role")!="DECLARATIVE_ENTRYPOINT_NOT_MONOLITHIC_IMPLEMENTATION": raise ValueError("MANIFEST_ROLE_INVALID")
    if len(m.get("domains",[]))!=8 or [x.get("id") for x in m["domains"]]!=ORDER: raise ValueError("MANIFEST_DOMAIN_COUNT_OR_ORDER_INVALID")
    if [x.get("id") for x in c.get("domains",[])]!=ORDER: raise ValueError("CONTRACT_DOMAIN_COUNT_OR_ORDER_INVALID")
    if any(m["domains"][i].get("module","").split("/")[-1]!=c["domains"][i].get("module") for i in range(8)): raise ValueError("MODULE_BINDING_MISMATCH")
    return mp,cp,m,c
def selftest(manifest_path=None,contract_path=None):
    mp,cp,m,c=load_inputs(manifest_path,contract_path)
    missing=[]
    for d in c["domains"]:
        p=(ROOT/pathlib.Path(d["module"]).name).resolve()
        try: p.relative_to(ROOT.resolve())
        except ValueError: missing.append({"id":d["id"],"status":"MODULE_PATH_ESCAPE"}); continue
        if not p.is_file(): missing.append({"id":d["id"],"status":"MODULE_ABSENT"})
    legacy_absent = not (ORCHESTRATOR/"CLIS.txt").exists()
    return {"schema":"CAJITA_CLI_INFRASTRUCTURE_SELFTEST/1.0","status":"PASS" if not missing and legacy_absent else "FAIL","domain_count":8,"unique_domain_count":len(set(ORDER)),"contract_present":cp.is_file(),"manifest_present":mp.is_file(),"all_adapters_present":not missing,"missing_adapters":missing,"legacy_spec_git_blob_sha":c.get("legacy_specification",{}).get("git_blob_sha"),"legacy_spec_absent_after_migration":legacy_absent,"side_effects":False,"certification":"NOT_GRANTED"}
def run_registry(manifest_path=None,contract_path=None):
    mp,cp,m,c=load_inputs(manifest_path,contract_path)
    cmap={d["id"]:d for d in c["domains"]}; rows=[]
    for d in m["domains"]:
        p=(ROOT/pathlib.Path(d["module"]).name).resolve()
        try: p.relative_to(ROOT.resolve())
        except ValueError: rows.append({"domain_id":d["id"],"status":"MODULE_PATH_ESCAPE"}); continue
        if not p.is_file(): rows.append({"domain_id":d["id"],"status":"ADAPTER_ABSENT"}); continue
        try:
            spec=importlib.util.spec_from_file_location("cajita_"+d["id"].lower(),p)
            if spec is None or spec.loader is None: raise ImportError("MODULE_LOADER_UNAVAILABLE")
            mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            row=mod.probe(); row["official_sources"]=cmap[d["id"]].get("official_sources",[]); row["installation_policy_status"]=cmap[d["id"]].get("status"); rows.append(row)
        except Exception as e: rows.append({"domain_id":d["id"],"status":"PROBE_ERROR","error_type":type(e).__name__,"reason":str(e)[:400]})
    infrastructure="PASS" if len(rows)==8 and all(r.get("status") not in {"PROBE_ERROR","ADAPTER_ABSENT","MODULE_PATH_ESCAPE"} for r in rows) else "FAIL"
    counts={}
    for r in rows: counts[r.get("status","UNKNOWN")]=counts.get(r.get("status","UNKNOWN"),0)+1
    available=sum(1 for r in rows if r.get("status")=="AVAILABLE")
    return {"schema":"CAJITA_CLI_HOST_AUDIT/1.0","captured_at_utc":utc(),"repository":"Plomillo/luna-linux-bridge","source_commit":os.getenv("GITHUB_SHA"),"runtime_relative_path":"2. Orquestación/Orquestador/CLIs","manifest_sha256":sha(mp),"contract_sha256":sha(cp),"legacy_specification":{"path":"2. Orquestación/Orquestador/CLIS.txt","git_blob_sha":c.get("legacy_specification",{}).get("git_blob_sha"),"working_tree_present":(ORCHESTRATOR/"CLIS.txt").exists()},"domain_order":ORDER,"domain_count":len(rows),"available_domain_count":available,"status_counts":counts,"infrastructure_status":infrastructure,"provider_host_readiness":"ALL_REQUIRED_PROBES_PASS" if available==8 else "PARTIAL","results":rows,"read_only":True,"mutations_performed":False,"shell_invoked":False,"credential_values_logged":False,"certification":"NOT_GRANTED"}
def write(path,value):
    p=pathlib.Path(path); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+".tmp"); t.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8"); t.replace(p)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--manifest",type=pathlib.Path,default=ORCHESTRATOR/"punto.json"); ap.add_argument("--contract",type=pathlib.Path,default=ROOT/"cli_contract.json"); ap.add_argument("--output",type=pathlib.Path); ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    try: result=selftest(a.manifest,a.contract) if a.self_test else run_registry(a.manifest,a.contract)
    except Exception as e: result={"status":"ERROR","infrastructure_status":"FAIL","reason":str(e)[:700],"certification":"NOT_GRANTED"}
    if a.output: write(a.output,result)
    print(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False))
    return 0 if (result.get("status")=="PASS" if a.self_test else result.get("infrastructure_status")=="PASS") else 2
if __name__=="__main__": raise SystemExit(main())
````

### `common.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/common.py`  
Blob SHA de Git: `2329b8034b7ac3fdaf0b13b444b71ba6ee11360b`  
Longitud en bytes/characters devuelta por el repositorio: 2505

````python
from __future__ import annotations
import hashlib, os, shutil, subprocess, time
from pathlib import Path

def sha256_file(path):
    h=hashlib.sha256()
    try:
        with Path(path).open("rb") as f:
            for block in iter(lambda:f.read(1024*1024), b""): h.update(block)
        return h.hexdigest()
    except OSError: return None

def probe_version(binary, argv, timeout_seconds=20, input_text=None):
    env=os.environ.copy()
    resolved=shutil.which(binary, path=env.get("PATH"))
    if not resolved:
        return {"binary":binary,"argv":list(argv),"status":"ABSENT","reason":"EXECUTABLE_NOT_FOUND","shell":False,"mutations_performed":False}
    started=time.monotonic()
    kwargs={"stdout":subprocess.PIPE,"stderr":subprocess.PIPE,"text":True,"timeout":max(1,min(int(timeout_seconds),60)),"shell":False,"env":env,"check":False}
    kwargs["stdin"]=subprocess.DEVNULL if input_text is None else None
    if input_text is not None: kwargs["input"]=input_text
    try:
        p=subprocess.run([resolved,*list(argv)],**kwargs)
        return {"binary":binary,"resolved_path":resolved,"binary_sha256":sha256_file(resolved),"argv":list(argv),"returncode":p.returncode,"status":"PASS" if p.returncode==0 else "NONZERO_EXIT","stdout":(p.stdout or "")[:1200],"stderr":(p.stderr or "")[:800],"elapsed_seconds":round(time.monotonic()-started,3),"shell":False,"mutations_performed":False}
    except subprocess.TimeoutExpired:
        return {"binary":binary,"resolved_path":resolved,"argv":list(argv),"status":"TIMEOUT","elapsed_seconds":round(time.monotonic()-started,3),"shell":False,"mutations_performed":False}
    except OSError as e:
        return {"binary":binary,"resolved_path":resolved,"argv":list(argv),"status":"EXECUTION_ERROR","error_type":type(e).__name__,"shell":False,"mutations_performed":False}

def probe_domain(domain_id,candidates,official_source_verified=True):
    rows=[]
    for binary,argv,required in candidates:
        row=probe_version(binary,argv); row["required"]=bool(required); rows.append(row)
    required=[r for r in rows if r.get("required")]
    if not official_source_verified: status="BLOCKED_OFFICIAL_DISTRIBUTION_UNVERIFIED"
    elif required and all(r["status"]=="PASS" for r in required): status="AVAILABLE"
    elif any(r["status"] not in {"ABSENT"} for r in rows): status="PARTIAL"
    else: status="ABSENT"
    return {"domain_id":domain_id,"status":status,"probes":rows,"read_only":True,"mutations_performed":False,"certification":"NOT_GRANTED"}
````

### `cli_mojo.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/cli_mojo.py`  
Blob SHA de Git: `e683593c8af04fafd285029c2dbc465f9f0f4cba`  
Longitud en bytes/characters devuelta por el repositorio: 154

````python
from common import probe_domain
DOMAIN_ID="CLI_MOJO"
CANDIDATES=[("mojo",["--version"],True)]
def probe(): return probe_domain(DOMAIN_ID,CANDIDATES,True)
````

### `cli_cpp23_toolchain.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/cli_cpp23_toolchain.py`  
Blob SHA de Git: `20e407f1499d211f681d02cff49e98e2e4428c5d`  
Longitud en bytes/characters devuelta por el repositorio: 952

````python
from common import probe_version
DOMAIN_ID="CLI_CPP23_TOOLCHAIN"
def probe():
    compilers=[probe_version(x,["--version"]) for x in ("g++","clang++")]
    cmake=probe_version("cmake",["--version"]); ninja=probe_version("ninja",["--version"])
    source="#include <version>\nint main() { return 0; }\n"
    tests=[probe_version(x,["-std=c++23","-x","c++","-fsyntax-only","-"],30,source) for x in ("g++","clang++")]
    accepted=[x["binary"] for x in tests if x["status"]=="PASS"]
    status="AVAILABLE" if accepted and cmake["status"]=="PASS" and ninja["status"]=="PASS" else ("PARTIAL" if any(x["status"]!="ABSENT" for x in compilers+[cmake,ninja]) else "ABSENT")
    return {"domain_id":DOMAIN_ID,"status":status,"probes":compilers+[cmake,ninja],
            "cxx23_smoke":{"status":"PASS" if accepted else "FAIL","accepted_compilers":accepted,"results":tests},
            "read_only":True,"mutations_performed":False,"certification":"NOT_GRANTED"}
````

### `cli_claude_code.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/cli_claude_code.py`  
Blob SHA de Git: `94b774358e86a5f100b15b311afcb5e9875e2be1`  
Longitud en bytes/characters devuelta por el repositorio: 163

````python
from common import probe_domain
DOMAIN_ID="CLI_CLAUDE_CODE"
CANDIDATES=[("claude",["--version"],True)]
def probe(): return probe_domain(DOMAIN_ID,CANDIDATES,True)
````

### `cli_python.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/cli_python.py`  
Blob SHA de Git: `4b236bfbebe2f6cea6ec88518e9713ba401d919a`  
Longitud en bytes/characters devuelta por el repositorio: 219

````python
from common import probe_domain
DOMAIN_ID="CLI_PYTHON"
CANDIDATES=[("python3",["--version"],True),("python",["--version"],False),("pip3",["--version"],False)]
def probe(): return probe_domain(DOMAIN_ID,CANDIDATES,True)
````

### `cli_github.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/cli_github.py`  
Blob SHA de Git: `0bd08d760e886b05c004d4d9e2e527560f262859`  
Longitud en bytes/characters devuelta por el repositorio: 257

````python
from common import probe_domain
DOMAIN_ID="CLI_GITHUB"
# git is auxiliary and cannot substitute for the required GitHub CLI (gh).
CANDIDATES=[("gh",["--version"],True),("git",["--version"],False)]
def probe(): return probe_domain(DOMAIN_ID,CANDIDATES,True)
````

### `cli_gemini.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/cli_gemini.py`  
Blob SHA de Git: `126c1925db73ad1a3d9436b2d1e501aad4056c7d`  
Longitud en bytes/characters devuelta por el repositorio: 158

````python
from common import probe_domain
DOMAIN_ID="CLI_GEMINI"
CANDIDATES=[("gemini",["--version"],True)]
def probe(): return probe_domain(DOMAIN_ID,CANDIDATES,True)
````

### `cli_grok.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/cli_grok.py`  
Blob SHA de Git: `9b4b01fb71308d5c5e3c757abe0908ee59310ce7`  
Longitud en bytes/characters devuelta por el repositorio: 620

````python
from __future__ import annotations
import shutil
DOMAIN_ID="CLI_GROK"
def probe():
    # First-party distribution is documented by xAI as @xai-official/grok; only report
    # presence here. Never execute an interactive agent in an inventory probe.
    path=shutil.which("grok")
    return {"domain_id":DOMAIN_ID,"status":"PRESENT_REQUIRES_VERSION_PROBE" if path else "ABSENT",
            "binary_path":path,"official_package":"@xai-official/grok","official_source":"https://x.ai/cli/install.sh",
            "candidate_binary_executed":False,"read_only":True,"mutations_performed":False,"certification":"NOT_GRANTED"}
````

### `cli_hugging_face.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/cli_hugging_face.py`  
Blob SHA de Git: `10e12f5dfa65a00b29a88452b4d6a1058c1a13ca`  
Longitud en bytes/characters devuelta por el repositorio: 276

````python
from common import probe_domain
DOMAIN_ID="CLI_HUGGING_FACE"
# hf is the official CLI name; legacy huggingface-cli is not a substitute for hf.
CANDIDATES=[("hf",["--help"],True),("huggingface-cli",["--help"],False)]
def probe(): return probe_domain(DOMAIN_ID,CANDIDATES,True)
````

### `test_cli_registry.py`

Ruta canónica: `cajita-luna-runtime/2. Orquestación/Orquestador/CLIs/tests/test_cli_registry.py`  
Blob SHA de Git: `a4e9b5240c9f93147380543211c7938fbcbf638d`  
Longitud en bytes/characters devuelta por el repositorio: 4978

````python
import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))
import common
import cli_registry
import cli_manager

class CLIModuleTests(unittest.TestCase):
    def test_missing_binary_is_absent_without_mutation(self):
        result = common.probe_version("definitely-not-installed-cajita-cli-test", ["--version"])
        self.assertEqual(result["status"], "ABSENT")
        self.assertFalse(result["shell"])
        self.assertFalse(result["mutations_performed"])

    def test_probe_invokes_direct_argv_without_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            exe = pathlib.Path(temp) / "fixture-cli"
            exe.write_text("#!/usr/bin/env python3\nprint('fixture 1.0')\n", encoding="utf-8")
            exe.chmod(0o750)
            old_path = os.environ.get("PATH", "")
            with patch.dict(os.environ, {"PATH": temp + os.pathsep + old_path}, clear=False):
                with patch("common.subprocess.run", wraps=common.subprocess.run) as runner:
                    result = common.probe_version("fixture-cli", ["--version"])
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["shell"])
            self.assertIn("fixture 1.0", result["stdout"])
            args, kwargs = runner.call_args
            self.assertEqual(args[0], [str(exe), "--version"])
            self.assertIs(kwargs["shell"], False)

    def test_contract_and_manifest_keep_the_eight_canonical_domains(self):
        _mp, _cp, manifest, contract = cli_registry.load_inputs()
        expected = ["CLI_MOJO", "CLI_CPP23_TOOLCHAIN", "CLI_CLAUDE_CODE", "CLI_PYTHON",
                    "CLI_GITHUB", "CLI_GEMINI", "CLI_GROK", "CLI_HUGGING_FACE"]
        self.assertEqual(manifest["domain_order"], expected)
        self.assertEqual(contract["domain_order"], expected)
        self.assertEqual([d["id"] for d in contract["domains"]], expected)

    def test_all_eight_modular_adapters_are_present(self):
        result = cli_registry.selftest()
        self.assertEqual(result["status"], "PASS", result)
        self.assertTrue(result["all_adapters_present"])
        self.assertTrue(result["legacy_spec_absent_after_migration"])
        self.assertEqual(result["domain_count"], 8)

    def test_git_does_not_substitute_for_github_cli(self):
        import cli_github
        with patch("common.probe_version", side_effect=[
            {"binary": "gh", "status": "ABSENT"},
            {"binary": "git", "status": "PASS"}
        ]):
            result = cli_github.probe()
        self.assertNotEqual(result["status"], "AVAILABLE")

    def test_grok_audit_does_not_execute_a_candidate_binary(self):
        import cli_grok
        with patch("shutil.which", return_value="/usr/local/bin/grok"), patch("subprocess.run") as run:
            result = cli_grok.probe()
        self.assertFalse(result["candidate_binary_executed"])
        run.assert_not_called()

    def test_read_only_registry_separates_infrastructure_from_provider_state(self):
        result = cli_registry.run_registry()
        self.assertEqual(result["infrastructure_status"], "PASS", result)
        self.assertEqual(result["domain_count"], 8)
        self.assertFalse(result["mutations_performed"])
        self.assertEqual(result["certification"], "NOT_GRANTED")

    def test_install_plan_does_not_mutate_without_version_pins(self):
        result = cli_manager.build_plan()
        self.assertEqual(result["schema"], "CAJITA_CLI_INSTALL_PLAN/1.0")
        self.assertEqual(result["status"], "BLOCKED_FAIL_CLOSED")
        self.assertEqual(result["commands"], [])
        self.assertTrue(result["no_mutations"])
        statuses = {x["domain_id"]: x["status"] for x in result["actions"]}
        self.assertEqual(statuses["CLI_MOJO"], "BLOCKED_VERSION_PIN_REQUIRED")
        self.assertEqual(statuses["CLI_PYTHON"], "AUDIT_ONLY_NO_INSTALL_MUTATION")

    def test_install_command_allowlist_requires_pinned_package_and_correct_uv_syntax(self):
        self.assertEqual(cli_manager.validate_argv({"argv": ["uv", "tool", "install", "demo==1.2.3"]}, "CLI_MOJO"), ["uv", "tool", "install", "demo==1.2.3"])
        with self.assertRaisesRegex(ValueError, "UV_OPERATION_NOT_ALLOWLISTED"):
            cli_manager.validate_argv({"argv": ["uv", "uninstall", "demo"]}, "CLI_MOJO", rollback=False)

    def test_apply_plan_rejects_wrong_plan_sha_before_any_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            plan_path = pathlib.Path(temp) / "plan.json"
            plan_path.write_text(json.dumps(cli_manager.build_plan()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "PLAN_SHA256_APPROVAL_MISMATCH"):
                cli_manager.apply_plan(plan_path, "0" * 64)

if __name__ == "__main__":
    unittest.main(verbosity=2)
````

## Candidato aditivo de conversión documental — Calibre Slim (2026-10-24)

**Asignación canónica:** D05 — Inteligencia documental.  
**Ruta interna prevista:** `cajita-luna-runtime/5. Inteligencia documental/Conversión documental/Calibre Slim/`  
**Lanzador registrado:** `calibre-slim-convert.py`  
**Entradas públicas:** PDF, EPUB y TXT. **Salidas públicas:** PDF y EPUB.  
**Conversiones requeridas:** PDF→EPUB, EPUB→PDF, TXT→PDF y TXT→EPUB. OCR, paquetes de idiomas, GUI y formatos adicionales quedan excluidos.

El overlay de Calibre v9.17.0 tiene tamaño de referencia de **58.180 bytes (0,05818 MB decimal)** y SHA-256 `dc1518eccd24d0bb6a294918381d9d42fa24df8b05026d1f173dadbd6e70977b`. Su evidencia CI está en [ejecución 40057448243](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40057448243), artefacto [12545698477](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40057448243/artifacts/12545698477).

**Materialización física: PASS.** El archivo `calibre-slim-overlay.tar.xz` está presente en la ruta interna del árbol `main`; el tamaño y SHA-256 se verificaron tras copiarlo desde el artefacto de CI. El lanzador verifica otra vez esos valores y extrae el overlay de forma segura en el primer uso. La incorporación física está verificada: el binario está en `main`, sus bytes y SHA-256 coinciden con el artefacto ensayado, y la reconstrucción del paquete `.macrodown` pasó en CI. El candidato permanece sin certificación independiente. El overlay no contiene el runtime nativo oficial ni las dependencias Qt/WebEngine; por tanto, los 58 KB no representan una instalación independiente de Calibre.


---

## Política de fabricación V10: módulos materializados y distribución conjunta

Esta sección es aditiva; se preserva el documento histórico y se aplica a esta fabricación para resolver el empaquetado durante la construcción, no durante cada ejecución.

- Cada archivo ZIP o 7Z del runtime se valida y extrae durante la fabricación. Solo se elimina el contenedor después de la prueba de integridad y la verificación de colisiones. Se conserva una copia de rollback fuera del runtime distribuible.
- Se eliminan todos los archivos cuyo nombre comienza por README, sin distinguir mayúsculas. Sus rutas, tamaños y SHA-256 quedan registrados en el manifiesto de fabricación.
- Cada paquete extraído queda identificado como módulo mediante CAJITA_MODULE.json y module_registry.json. La materialización no autoriza a dar por conectado un consumidor: adaptador, smoke nativo y medición de recursos siguen siendo pruebas separadas.
- Los seis artefactos de pesos deben mantener exactamente tamaño y SHA-256. No se reemplazan modelos ni motores por motivos de tamaño.
- El árbol de trabajo materializado tiene un techo de fabricación separado de 1500000000 bytes. La puerta de distribución conjunta mide el archivo .macrodown más Louksna1.md, con máximo decimal exacto de 470000000 bytes. El techo del árbol de trabajo no amplía el presupuesto del producto final.
- La ejecución sigue siendo secuencial y bajo demanda. La autorización de una tarea no equivale a autorización de efectos ajenos a ella.
- El sistema antiparálisis mantiene un diario persistente encadenado por SHA-256, limita a tres las observaciones idénticas sin progreso y pasa a HOLD_CONSCIOUS al agotarlas. No realiza reintentos automáticos con efectos desconocidos ni sin idempotencia y checkpoint verificado.
- Ningún estado de certificación se hereda automáticamente. La certificación integral exige evidencia independiente G23 y una decisión G24 separada.

Estado de fabricación: 28 contenedores ZIP/7Z retirados tras extracción; 125 README retirados; 28 módulos de ruta registrados. La validación funcional completa y la certificación global permanecen pendientes de sus gates independientes.


---

## Política de fabricación V10: módulos materializados y distribución conjunta

Esta sección es aditiva; se preserva el documento histórico y se aplica a esta fabricación para resolver el empaquetado durante la construcción, no durante cada ejecución.

- Cada archivo ZIP o 7Z del runtime se valida y extrae durante la fabricación. Solo se elimina el contenedor después de la prueba de integridad y la verificación de colisiones. Se conserva una copia de rollback fuera del runtime distribuible.
- Se eliminan todos los archivos cuyo nombre comienza por README, sin distinguir mayúsculas. Sus rutas, tamaños y SHA-256 quedan registrados en el manifiesto de fabricación.
- Cada paquete extraído queda identificado como módulo mediante CAJITA_MODULE.json y module_registry.json. La materialización no autoriza a dar por conectado un consumidor: adaptador, smoke nativo y medición de recursos siguen siendo pruebas separadas.
- Los seis artefactos de pesos deben mantener exactamente tamaño y SHA-256. No se reemplazan modelos ni motores por motivos de tamaño.
- El árbol de trabajo materializado tiene un techo de fabricación separado de 1500000000 bytes. La puerta de distribución conjunta mide el archivo .macrodown más Louksna1.md, con máximo decimal exacto de 470000000 bytes. El techo del árbol de trabajo no amplía el presupuesto del producto final.
- La ejecución sigue siendo secuencial y bajo demanda. La autorización de una tarea no equivale a autorización de efectos ajenos a ella.
- El sistema antiparálisis mantiene un diario persistente encadenado por SHA-256, limita a tres las observaciones idénticas sin progreso y pasa a HOLD_CONSCIOUS al agotarlas. No realiza reintentos automáticos con efectos desconocidos ni sin idempotencia y checkpoint verificado.
- Ningún estado de certificación se hereda automáticamente. La certificación integral exige evidencia independiente G23 y una decisión G24 separada.

Estado de fabricación: 28 contenedores ZIP/7Z retirados tras extracción; 125 README retirados; 28 módulos de ruta registrados. La validación funcional completa y la certificación global permanecen pendientes de sus gates independientes.


---

## Política de fabricación V10: módulos materializados y distribución conjunta

Esta sección es aditiva; se preserva el documento histórico y se aplica a esta fabricación para resolver el empaquetado durante la construcción, no durante cada ejecución.

- Cada archivo ZIP o 7Z del runtime se valida y extrae durante la fabricación. Solo se elimina el contenedor después de la prueba de integridad y la verificación de colisiones. Se conserva una copia de rollback fuera del runtime distribuible.
- Se eliminan todos los archivos cuyo nombre comienza por README, sin distinguir mayúsculas. Sus rutas, tamaños y SHA-256 quedan registrados en el manifiesto de fabricación.
- Cada paquete extraído queda identificado como módulo mediante CAJITA_MODULE.json y module_registry.json. La materialización no autoriza a dar por conectado un consumidor: adaptador, smoke nativo y medición de recursos siguen siendo pruebas separadas.
- Los seis artefactos de pesos deben mantener exactamente tamaño y SHA-256. No se reemplazan modelos ni motores por motivos de tamaño.
- El árbol de trabajo materializado tiene un techo de fabricación separado de 1500000000 bytes. La puerta de distribución conjunta mide el archivo .macrodown más Louksna1.md, con máximo decimal exacto de 470000000 bytes. El techo del árbol de trabajo no amplía el presupuesto del producto final.
- La ejecución sigue siendo secuencial y bajo demanda. La autorización de una tarea no equivale a autorización de efectos ajenos a ella.
- El sistema antiparálisis mantiene un diario persistente encadenado por SHA-256, limita a tres las observaciones idénticas sin progreso y pasa a HOLD_CONSCIOUS al agotarlas. No realiza reintentos automáticos con efectos desconocidos ni sin idempotencia y checkpoint verificado.
- Ningún estado de certificación se hereda automáticamente. La certificación integral exige evidencia independiente G23 y una decisión G24 separada.

Estado de fabricación: 28 contenedores ZIP/7Z retirados tras extracción; 125 README retirados; 28 módulos de ruta registrados. La validación funcional completa y la certificación global permanecen pendientes de sus gates independientes.


---

## Política de fabricación V10: módulos materializados y distribución conjunta

Esta sección es aditiva; se preserva el documento histórico y se aplica a esta fabricación para resolver el empaquetado durante la construcción, no durante cada ejecución.

- Cada archivo ZIP o 7Z del runtime se valida y extrae durante la fabricación. Solo se elimina el contenedor después de la prueba de integridad y la verificación de colisiones. Se conserva una copia de rollback fuera del runtime distribuible.
- Se eliminan todos los archivos cuyo nombre comienza por README, sin distinguir mayúsculas. Sus rutas, tamaños y SHA-256 quedan registrados en el manifiesto de fabricación.
- Cada paquete extraído queda identificado como módulo mediante CAJITA_MODULE.json y module_registry.json. La materialización no autoriza a dar por conectado un consumidor: adaptador, smoke nativo y medición de recursos siguen siendo pruebas separadas.
- Los seis artefactos de pesos deben mantener exactamente tamaño y SHA-256. No se reemplazan modelos ni motores por motivos de tamaño.
- El árbol de trabajo materializado tiene un techo de fabricación separado de 1500000000 bytes. La puerta de distribución conjunta mide el archivo .macrodown más Louksna1.md, con máximo decimal exacto de 470000000 bytes. El techo del árbol de trabajo no amplía el presupuesto del producto final.
- La ejecución sigue siendo secuencial y bajo demanda. La autorización de una tarea no equivale a autorización de efectos ajenos a ella.
- El sistema antiparálisis mantiene un diario persistente encadenado por SHA-256, limita a tres las observaciones idénticas sin progreso y pasa a HOLD_CONSCIOUS al agotarlas. No realiza reintentos automáticos con efectos desconocidos ni sin idempotencia y checkpoint verificado.
- Ningún estado de certificación se hereda automáticamente. La certificación integral exige evidencia independiente G23 y una decisión G24 separada.

Estado de fabricación: 28 contenedores ZIP/7Z retirados tras extracción; 125 README retirados; 28 módulos de ruta registrados. La validación funcional completa y la certificación global permanecen pendientes de sus gates independientes.


---

## Política de fabricación V10: módulos materializados y distribución conjunta

Esta sección es aditiva; se preserva el documento histórico y se aplica a esta fabricación para resolver el empaquetado durante la construcción, no durante cada ejecución.

- Cada archivo ZIP o 7Z del runtime se valida y extrae durante la fabricación. Solo se elimina el contenedor después de la prueba de integridad y la verificación de colisiones. Se conserva una copia de rollback fuera del runtime distribuible.
- Se eliminan todos los archivos cuyo nombre comienza por README, sin distinguir mayúsculas. Sus rutas, tamaños y SHA-256 quedan registrados en el manifiesto de fabricación.
- Cada paquete extraído queda identificado como módulo mediante CAJITA_MODULE.json y module_registry.json. La materialización no autoriza a dar por conectado un consumidor: adaptador, smoke nativo y medición de recursos siguen siendo pruebas separadas.
- Los seis artefactos de pesos deben mantener exactamente tamaño y SHA-256. No se reemplazan modelos ni motores por motivos de tamaño.
- El árbol de trabajo materializado tiene un techo de fabricación separado de 1500000000 bytes. La puerta de distribución conjunta mide el archivo .macrodown más Louksna1.md, con máximo decimal exacto de 470000000 bytes. El techo del árbol de trabajo no amplía el presupuesto del producto final.
- La ejecución sigue siendo secuencial y bajo demanda. La autorización de una tarea no equivale a autorización de efectos ajenos a ella.
- El sistema antiparálisis mantiene un diario persistente encadenado por SHA-256, limita a tres las observaciones idénticas sin progreso y pasa a HOLD_CONSCIOUS al agotarlas. No realiza reintentos automáticos con efectos desconocidos ni sin idempotencia y checkpoint verificado.
- Ningún estado de certificación se hereda automáticamente. La certificación integral exige evidencia independiente G23 y una decisión G24 separada.

Estado de fabricación: 28 contenedores ZIP/7Z retirados tras extracción; 125 README retirados; 28 módulos de ruta registrados. La validación funcional completa y la certificación global permanecen pendientes de sus gates independientes.


---

## Política de fabricación V10: módulos materializados y distribución conjunta

Esta sección es aditiva; se preserva el documento histórico y se aplica a esta fabricación para resolver el empaquetado durante la construcción, no durante cada ejecución.

- Cada archivo ZIP o 7Z del runtime se valida y extrae durante la fabricación. Solo se elimina el contenedor después de la prueba de integridad y la verificación de colisiones. Se conserva una copia de rollback fuera del runtime distribuible.
- Se eliminan todos los archivos cuyo nombre comienza por README, sin distinguir mayúsculas. Sus rutas, tamaños y SHA-256 quedan registrados en el manifiesto de fabricación.
- Cada paquete extraído queda identificado como módulo mediante CAJITA_MODULE.json y module_registry.json. La materialización no autoriza a dar por conectado un consumidor: adaptador, smoke nativo y medición de recursos siguen siendo pruebas separadas.
- Los seis artefactos de pesos deben mantener exactamente tamaño y SHA-256. No se reemplazan modelos ni motores por motivos de tamaño.
- El árbol de trabajo materializado tiene un techo de fabricación separado de 1500000000 bytes. La puerta de distribución conjunta mide el archivo .macrodown más Louksna1.md, con máximo decimal exacto de 470000000 bytes. El techo del árbol de trabajo no amplía el presupuesto del producto final.
- La ejecución sigue siendo secuencial y bajo demanda. La autorización de una tarea no equivale a autorización de efectos ajenos a ella.
- El sistema antiparálisis mantiene un diario persistente encadenado por SHA-256, limita a tres las observaciones idénticas sin progreso y pasa a HOLD_CONSCIOUS al agotarlas. No realiza reintentos automáticos con efectos desconocidos ni sin idempotencia y checkpoint verificado.
- Ningún estado de certificación se hereda automáticamente. La certificación integral exige evidencia independiente G23 y una decisión G24 separada.

Estado de fabricación: 28 contenedores ZIP/7Z retirados tras extracción; 125 README retirados; 28 módulos de ruta registrados. La validación funcional completa y la certificación global permanecen pendientes de sus gates independientes.


---

## Política de fabricación V10: módulos materializados y distribución conjunta

Esta sección es aditiva; se preserva el documento histórico y se aplica a esta fabricación para resolver el empaquetado durante la construcción, no durante cada ejecución.

- Cada archivo ZIP o 7Z del runtime se valida y extrae durante la fabricación. Solo se elimina el contenedor después de la prueba de integridad y la verificación de colisiones. Se conserva una copia de rollback fuera del runtime distribuible.
- Se eliminan todos los archivos cuyo nombre comienza por README, sin distinguir mayúsculas. Sus rutas, tamaños y SHA-256 quedan registrados en el manifiesto de fabricación.
- Cada paquete extraído queda identificado como módulo mediante CAJITA_MODULE.json y module_registry.json. La materialización no autoriza a dar por conectado un consumidor: adaptador, smoke nativo y medición de recursos siguen siendo pruebas separadas.
- Los seis artefactos de pesos deben mantener exactamente tamaño y SHA-256. No se reemplazan modelos ni motores por motivos de tamaño.
- El árbol de trabajo materializado tiene un techo de fabricación separado de 1500000000 bytes. La puerta de distribución conjunta mide el archivo .macrodown más Louksna1.md, con máximo decimal exacto de 470000000 bytes. El techo del árbol de trabajo no amplía el presupuesto del producto final.
- La ejecución sigue siendo secuencial y bajo demanda. La autorización de una tarea no equivale a autorización de efectos ajenos a ella.
- El sistema antiparálisis mantiene un diario persistente encadenado por SHA-256, limita a tres las observaciones idénticas sin progreso y pasa a HOLD_CONSCIOUS al agotarlas. No realiza reintentos automáticos con efectos desconocidos ni sin idempotencia y checkpoint verificado.
- Ningún estado de certificación se hereda automáticamente. La certificación integral exige evidencia independiente G23 y una decisión G24 separada.

Estado de fabricación: 28 contenedores ZIP/7Z retirados tras extracción; 125 README retirados; 28 módulos de ruta registrados. La validación funcional completa y la certificación global permanecen pendientes de sus gates independientes.


---

## Política de fabricación V10: módulos materializados y distribución conjunta

Esta sección es aditiva; se preserva el documento histórico y se aplica a esta fabricación para resolver el empaquetado durante la construcción, no durante cada ejecución.

- Cada archivo ZIP o 7Z del runtime se valida y extrae durante la fabricación. Solo se elimina el contenedor después de la prueba de integridad y la verificación de colisiones. Se conserva una copia de rollback fuera del runtime distribuible.
- Se eliminan todos los archivos cuyo nombre comienza por README, sin distinguir mayúsculas. Sus rutas, tamaños y SHA-256 quedan registrados en el manifiesto de fabricación.
- Cada paquete extraído queda identificado como módulo mediante CAJITA_MODULE.json y module_registry.json. La materialización no autoriza a dar por conectado un consumidor: adaptador, smoke nativo y medición de recursos siguen siendo pruebas separadas.
- Los seis artefactos de pesos deben mantener exactamente tamaño y SHA-256. No se reemplazan modelos ni motores por motivos de tamaño.
- El árbol de trabajo materializado tiene un techo de fabricación separado de 1500000000 bytes. La puerta de distribución conjunta mide el archivo .macrodown más Louksna1.md, con máximo decimal exacto de 470000000 bytes. El techo del árbol de trabajo no amplía el presupuesto del producto final.
- La ejecución sigue siendo secuencial y bajo demanda. La autorización de una tarea no equivale a autorización de efectos ajenos a ella.
- El sistema antiparálisis mantiene un diario persistente encadenado por SHA-256, limita a tres las observaciones idénticas sin progreso y pasa a HOLD_CONSCIOUS al agotarlas. No realiza reintentos automáticos con efectos desconocidos ni sin idempotencia y checkpoint verificado.
- Ningún estado de certificación se hereda automáticamente. La certificación integral exige evidencia independiente G23 y una decisión G24 separada.

Estado de fabricación: 28 contenedores ZIP/7Z retirados tras extracción; 125 README retirados; 28 módulos de ruta registrados. La validación funcional completa y la certificación global permanecen pendientes de sus gates independientes.
