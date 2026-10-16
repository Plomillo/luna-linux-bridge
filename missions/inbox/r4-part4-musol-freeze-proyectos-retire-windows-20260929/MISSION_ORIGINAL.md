# MISIÓN DE PROPUESTA — PART4 / CONGELAR PROYECTOS Y RETIRAR WINDOWS 11

STATUS_REQUESTED = PROPOSAL_ONLY
MUTATION_AUTHORIZED = FALSE
DESTRUCTIVE_EXECUTION_AUTHORIZED = FALSE

## Autoridad y participantes

- AUTHORITY = Louksna.md
- GOVERNOR = MetaOS
- SUPERVISOR = SYMPHYLAX_R1
- WORKER = CUSTOSZ_V7
- MASTER_CONTEXT = LUNA R4 PART_4
- TRANSPORT/EVIDENCE = GitHub Mission Mailbox

## Decisión humana de diseño

El usuario establece como objetivo operativo:

1. La carpeta exacta `/media/diegoignacionorambuenamiranda/Windows/PROYECTOS` debe convertirse en el único alcance preservado de la partición Windows.
2. PROYECTOS debe ser congelado, blindado, inventariado, verificado, certificado y protegido antes de cualquier operación destructiva.
3. Ningún archivo, subdirectorio, identidad, contenido o metadato necesario de PROYECTOS puede perderse por la retirada de Windows.
4. Una vez que PROYECTOS disponga de protección y evidencia suficiente conforme a Louksna/Maestro, Windows 11 y todo lo que permanezca fuera de PROYECTOS en la partición Windows puede ser retirado.
5. La retirada debe ser trazable, auditable, gobernable, determinista en lo técnicamente posible, con prevalidación, checkpoint, evidencia de alcance, postvalidación y rollback/recovery cuando aplique.
6. No tocar EFI, GPT, Debian/Linux ni otras particiones.
7. No ejecutar todavía el borrado. Primero devolver una propuesta de plan para autorización humana.

## Idea MUSOL comunicada

Tratar esta estrategia como la “idea MUSOL” para esta misión:
`FREEZE(PROYECTOS) -> PROTECT -> VERIFY -> CERTIFY -> REMOVE_WINDOWS_OUTSIDE_PROYECTOS -> POST_VALIDATE`.

El nombre no concede autoridad adicional ni modifica identidades canónicas.

## Estado relevante ya demostrado

- PROYECTOS está montado RW de forma persistente sobre `/dev/nvme0n1p3`.
- La deduplicación autorizada de PART4 cerró posteriormente en PASS sin errores residuales.
- Los cuatro PermissionError residuales fueron corregidos de forma hash-verificada y acotada.
- Maestro continúa exigiendo los gates formales:
  - `two_verified_backups`
  - `restore_proof`
  - `destructive_scope_prevalidated`
- No se permite falsificar esos gates ni propagarlos por declaración.

## Entregable requerido de CUSTOSZ + gobierno

Responder con un PLAN PROPUESTO, no con ejecución, que especifique como mínimo:

- estado exacto que debe congelarse;
- inventario/hashes/manifiesto necesarios para blindar PROYECTOS;
- qué constituye Backup 1 y Backup 2 bajo el gate actual;
- dónde pueden materializarse de forma realista con el almacenamiento disponible;
- prueba de restauración exigible y criterio binario PASS/HOLD;
- prueba de exclusión que demuestre que el borrado jamás atraviesa PROYECTOS;
- alcance exacto de lo que se eliminaría de Windows;
- tratamiento de NTFS, atributos, permisos, symlinks/reparse points y mounts anidados;
- checkpoint y rollback/recovery;
- evidencia previa y posterior;
- validación independiente G23 y certificación G24;
- orden de ejecución recomendado;
- autorizaciones humanas concretas que todavía deban solicitarse;
- condiciones de ABORT/HOLD;
- estimación de espacio liberable basada sólo en evidencia;
- cómo dejar PART4 listo para continuar a PART5 después de la retirada.

## Restricciones absolutas

- PROYECTOS = NO DELETE / NO RENAME / NO SUBSTITUTE / NO SILENT MUTATION.
- `8. Vida personal y Ocio` continúa bajo las restricciones históricas mientras siga dentro de PROYECTOS.
- NO borrar Windows todavía.
- NO ampliar alcance por inferencia.
- NO marcar backups, restore proof, G23 o G24 como PASS sin evidencia material.
- NO certificación propia.
- FAIL_CLOSED = TRUE.
- NO_SILENT_OPERATIONS = TRUE.

## Pregunta terminal

Presentar la propuesta gobernada para que el usuario pueda responder con una autorización explícita y única de ejecución si la acepta.
