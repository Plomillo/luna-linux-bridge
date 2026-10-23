# Auditoría de enrutamiento de los 14 comandos hacia dominios y subdominios de Cajita

**Registro:** `LOUKSNA_14_COMMAND_SUBDOMAIN_ROUTING_20261023`  
**Estado:** `ROUTING_MAP_REGISTERED_EXECUTION_REMAINS_FAIL_CLOSED`  
**Fuente de bindings canónicos:** `LOUKSNAMEJORADA.md`, secciones 13, 25, 27–35.  
**Registry implementable:** `cajita-luna-runtime/command_subdomain_routing.json`  
**Router consumidor:** `cajita-luna-runtime/cajita_router.py`

## Alcance y regla de preservación

La auditoría conserva las 14 identidades de comando, los cuatro agentes, las matrices de motores E01–E15, la criticidad y la presencia obligatoria de Luna en cada ruta. La modificación es aditiva: enlaza los perfiles de comando existentes con destinos concretos del runtime y añade clasificación de intención por subdominio. No cambia la autoridad de Louksna ni propaga certificación.

El fichero de origen consultado en el proyecto expone el registro canónico y la matriz de rutas. El hash criptográfico de los bytes originales de ese adjunto no se computó durante esta pasada; no se declara verificación de hash de la fuente.

## Resultado de inventario

- **6 dominios** mantienen su orden canónico: Cerebro → Orquestación → Transcripción → Traductor Inteligente → Inteligencia documental → Sistema Inteligente.
- **21 destinos de routing:** 2 raíces de dominio sin subdivisión declarada en este registro y 19 subdominios explícitos.
- **Distribución de subdominios:** Orquestación = 3; Traductor Inteligente = 3; Inteligencia documental = 2; Sistema Inteligente = 11.
- **15 motores canónicos E01–E15** tienen una matriz de compatibilidad por cada uno de los 21 destinos.
- **10 activos de infraestructura** tienen ruta, versión, tamaño, SHA-256 y destino(s) declarados.

## Matriz de los 14 comandos

Los motores listados por la matriz canónica permanecen en el registro activo del router; las asignaciones siguientes añaden los destinos de Cajita. Las reglas de intención pueden añadir subdominios según el trabajo solicitado. Solo se activa el conjunto mínimo relevante y de forma secuencial.

| ID | Comando canónico | Destinos iniciales |
|---|---|---|
| HELP | `/help` | Motor Protocolar; Testing |
| PT | `/play PT` | Cerebro; Análisis Avanzado; Testing |
| PA | `/play PA` | Multi + Interdisciplinar; Análisis Avanzado; Motor Protocolar; Cognitive CI-CD; Testing |
| DCI | `/play DCI` | Multi + Interdisciplinar; Hermenéutica H-G; Análisis Avanzado; Anti-Alucinaciones |
| DCIL | `/play DCIL` | Multi + Interdisciplinar; Hermenéutica H-G; Análisis Avanzado; Anti-Alucinaciones |
| TRAD | `/play traductor` | Traducción general; selección por intención/pareja lingüística |
| E | `/play e` | Hermenéutica H-G; Anti-Alucinaciones |
| EMA | `/play ema` | Hermenéutica H-G; Multi + Interdisciplinar; Análisis Avanzado; Anti-Alucinaciones; Testing |
| P | `/play p` | Orquestador; Motor Protocolar; Cognitive CI-CD; Testing |
| C | `/play c` | Multi + Interdisciplinar; Archivado Deteccion; Análisis Avanzado |
| CP | `/play cp` | Multi + Interdisciplinar; Análisis Avanzado; Anti-Alucinaciones |
| MA | `/play MA` | Cerebro; Multi + Interdisciplinar; expansión adicional bajo demanda |
| H | `/play H` | Hermenéutica H-G; Confesión Eclesial Reformada; Anti-Alucinaciones |
| AE | `/play AE` | Orquestador; Análisis Avanzado; Motor Protocolar; Cognitive CI-CD; Testing |

### Reglas de intención que refinan el destino

- Audio, voz a texto o Whisper → Transcripción.
- PDF, OCR o extracción documental → Docling.
- EPUB, biblioteca digital o gestión de libros electrónicos → Calibre.
- Latín, hebreo, griego koiné/bíblico, arameo, siríaco, Vulgata, Septuaginta o idioma original → Hermenéutica H-G + Traducción de lenguas antiguas; se retira Traducción general de esa selección.
- Traducción general → Traducción general.
- Biblia, teología reformada, confesión o catecismo → Confesión Eclesial Reformada + Hermenéutica H-G.
- RDF/OWL, grafos u ontologías → Multi + Interdisciplinar.
- Citas, contraste de fuentes, trazabilidad o control de alucinaciones → Anti-Alucinaciones.
- Razonamiento, análisis, auditoría o formalización → Análisis Avanzado.
- ZIP/7z/RAR, inventarios o detección de formato → Archivado Deteccion.
- Workflow, GitHub Actions, build o despliegue → Cognitive CI-CD.
- Terminal, shell o CLI → Consola.
- Memoria gobernada/persistente → Memoria Gobernada.
- SQLite, rqlite, esquema o migración de datos → Migración y Persistencia.
- Protocolos, OPA, política y autorizaciones → Motor Protocolar.
- CMake, compilación, Windows x64 o portabilidad → Portabilidad base.
- Android, aplicación de escritorio, Avalonia o Tauri → Runtime Android Windows.
- Pruebas, smoke o no-regresión → Testing; Playwright se mapea como activo de soporte tanto a Orquestador como a Testing.

## Asignación de los diez activos compactados

Los archivos son contenedores `.7z` y no se tratan como ejecutables directos. Las asignaciones representan relación funcional y de consumo prevista, no prueba de ejecución del binario.

| Activo | Destino(s) | Versión | Tamaño del contenedor |
|---|---|---:|---:|
| `APACHE_JENA_6_2_0` | Multi + Interdisciplinar | 6.2.0 | 23.103.199 B |
| `PLAYWRIGHT_1_63_0_SOURCE` | Orquestador; Testing | 1.63.0 | 32.133.546 B |
| `ONNX_RUNTIME_1_29_0_CP311` | Anti-Alucinaciones | 1.29.0 | 10.219.873 B |
| `DAGGER_0_21_8_LINUX_AMD64` | Cognitive CI-CD | 0.21.8 | 15.377.436 B |
| `OPA_STATIC_LINUX_AMD64_CANDIDATE` | Cognitive CI-CD; Motor Protocolar | 1.21.3 | 25.273.630 B |
| `RQLITE_10_2_7_LINUX_AMD64` | Migración y Persistencia; Memoria Gobernada | 10.2.7 | 12.962.199 B |
| `SQLITE_SOURCE_3_53_4` | Migración y Persistencia; Memoria Gobernada | 3.53.4 | 7.954.439 B |
| `CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE` | Portabilidad base | 4.4.3 | 21.310.484 B |
| `AVALONIA_12_1_1_NUGET` | Runtime Android Windows | 12.1.1 | 3.836.434 B |
| `TAURI_2_11_5_SOURCE_ZIP` | Runtime Android Windows | 2.11.5 | 13.078.809 B |

## Puerta de ejecución

La ruta de ejecución **permanece bloqueada intencionalmente**. El router puede producir un plan con destinos, motores compatibles y activos requeridos, pero no afirma que ejecuta todavía los trabajos de cada subdominio. Antes de activar una ruta real faltan, según corresponda:

1. extracción bajo demanda del contenedor de soporte;
2. verificación SHA-256 y de integridad del contenido expandido;
3. registro de un adaptador de consumidor real por subdominio;
4. prueba nativa/end-to-end pertinente;
5. medición de RSS pico, latencia y descarga de recursos;
6. prueba de fallo, traza, rollback y validación independiente.

La entrada al registro no equivale a instalación/ejecución. Los activos de infraestructura siguen dentro del runtime compactado; no se altera su tamaño por declarar su destino.

## Identidad exacta de comandos y aliases

El router acepta exactamente los 14 comandos canónicos y cinco aliases explícitos del contrato del proyecto:

- `/play E` → `/play e`
- `/play EMA` → `/play ema`
- `/play P` → `/play p`
- `/play C` → `/play c`
- `/play CP` → `/play cp`

No se aplica una conversión general de mayúsculas/minúsculas. Por ejemplo, `/PLAY EMA` no se acepta implícitamente. Un comando desconocido o una grafía no autorizada conduce a `FAIL_CLOSED`.

## Invariantes de aceptación de la matriz

- 14 comandos únicos y con perfil de destino.
- Luna primero en todas las rutas canónicas.
- E01–E15 preservados como IDs canónicos y asignados funcionalmente a cada uno de los 21 destinos.
- 19 subdominios explícitos, incluidos los 11 de Sistema Inteligente.
- 10/10 activos de soporte con destino, hash, tamaño y versión.
- Orden canónico de seis dominios preservado.
- Selección por demanda, secuencial y sin activar la caja completa por defecto.
- Sin autorización de ejecución cuando falta el adaptador, perfil de recursos o evidencia obligatoria.

**Certificación del runtime y equivalencia funcional:** `NOT_GRANTED`. Este documento certifica el alcance y la forma de la matriz de enrutamiento, no la ejecución integral de todos los motores.
