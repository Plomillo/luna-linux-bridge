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
| Cerebro | `1. Cerebro/model.safetensors` | 148.477.400 |
| Transcripción | `3. Transcripción/model.safetensors` | 34.877.948 |
| Traductor Inteligente | `4. Traductor Inteligente/Traducción general/model.safetensors` | 20.256.147 |
| Inteligencia documental | `5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_weights.bin` | 13.483.380 |
| Sistema Inteligente | `6. Sistema Inteligente/Análisis Avanzado/model.safetensors` | 52.950.152 |
| Sistema Inteligente | `6. Sistema Inteligente/Anti-Alucinaciones/model.onnx` | 110.516.001 |
| **Total de seis archivos de modelo/pesos** | | **380.561.028** |

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
