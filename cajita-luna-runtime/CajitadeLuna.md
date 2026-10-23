# Cajita de Luna — Runtime reproducible V9

**Formato de distribución:** `CAJITA_RUNTIME_MACRODOWN/1.0`, archivo contenedor ZIP determinista con extensión `.macrodown`.
**Límite bruto:** 479.000.000 bytes (decimal, exacto).
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
- **Puerta bruta del paquete:** BLOQUEADA. El payload anterior registrado era 476.525.572 bytes. Los diez activos suman 286.535.330 bytes; la proyección asciende a 763.060.902 bytes antes del crecimiento del manifiesto regenerado, es decir, **284.060.902 bytes por encima** del máximo de 479.000.000. `reproduce_macrodown.py` denegará el build mientras se mantenga este exceso.
- **Estado del artefacto distribuible:** NO RECONSTRUIDO ni certificado con estos activos. No se actualiza el manifiesto anterior para fingir una inclusión ya empaquetada. La regeneración debe producir un manifiesto nuevo desde el árbol efectivo y pasar de nuevo ambas comprobaciones de límite.

## Alcance, entorno y evidencia

El registro `BUILD_PROVENANCE.json` fija las fuentes, el commit externo auxiliar y las pruebas observadas para el candidato V9 anterior. El registro aditivo de integración de activos está en `EXTERNALIZED_ASSET_PLACEMENT.json`; no sustituye la procedencia histórica. Los 22 manifiestos `D01.json`–`D22.json` del repositorio auxiliar se usan solo como información externa; no forman parte del paquete Cajita.

La prueba estructural y la integridad de los seis hashes de modelos son gates de contenido, no pruebas de equivalencia de calidad. D04 superó una generación de traducción mínima; D05 pasó la verificación de carga de su modelo. Las pruebas anteriores del candidato V4 dieron PASS para D01, D02, D03 y D06; D04 y D05 presentaban fallos que se han corregido en el candidato V9, con los límites de prueba descritos en el registro de procedencia. Equivalencia de calidad, validación independiente y certificación integral siguen sin establecerse.

**Estado de publicación:** las ubicaciones de los diez activos y este inventario documental están en GitHub. El artefacto distribuible `.macrodown` no se ha reconstruido ni publicado con estos activos; la puerta de límite bruto continúa bloqueada, como se documenta arriba.
