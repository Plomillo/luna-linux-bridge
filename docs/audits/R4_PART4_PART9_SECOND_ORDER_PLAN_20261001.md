# LUNA R4 — PLAN DEFINITIVO PART4 → PART9, SEGUNDO ORDEN

STATUS = AUDITED_PLAN_READY_NOT_EXECUTED  
AUTHORITY = Louksna.md  
ASSURANCE = PUAC2.md  
DOCTRINE = EXTEND_DO_NOT_REPLACE  
FAILURE_POSTURE = FAIL_CLOSED  
SOURCE_MASTER_CHECKPOINT = 52d83b97b59fcef4b6e35251d7cc9676d77014ed  
AUDIT_DATE_UTC = 2026-10-01  
AUDIT_BRANCH = audit/r4-part4-part9-second-order-20261001  

## 1. Propósito

Cerrar LUNA R4 desde PART4 hasta PART9 sin reiniciar trabajo ya materializado, usando el estado físico real del host LOUKSNA como fuente observacional, Qwen como razonador de segundo orden en GitHub-hosted runners, Louksna Remote Bridge como plano de telemetría/observación, CUSTOSZ V7/APC como ejecutores gobernados, y G23/G24 como validación independiente/certificación.

Qwen no adquiere autoridad canónica, de ejecución ni de certificación. Su inferencia futura se desplaza fuera del host físico. El modelo local puede permanecer almacenado, pero no debe existir proceso local de inferencia.

## 2. Estado vivo observado

PART1, PART2 y PART3 poseen certificados G24 locales. Maestro y Symphylax están activos. El runner self-hosted está activo. `louksna-live-socket.service` está activo.

Estado de almacenamiento observado:

| Partición | Estado actual | Función |
|---|---|---|
| p1 | vfat, 272629760 B, montada en /boot/efi | EFI |
| p2 | 16777216 B, sin FS | residuo MSR |
| p3 | ext4, 437167223296 B, label LOUKSNA_PROJECTS, UUID e084ec2a-af39-48b5-bb89-db2dc6a98332, desmontada | destino PART4 |
| p4 | NTFS, 700448768 B | residuo Recovery |
| p5 | ext4, 73943322624 B, montada en / | raíz Debian actual |

`~/PROYECTOS` existe actualmente dentro de p5; no es mountpoint de p3.

La evidencia V8 previa demuestra migración y equivalencia de PROYECTOS hasta el borde final: 498092 registros, 436072 archivos, 62016 directorios, 4 symlinks, 200490852057 bytes y fingerprint POSIX `fa50cabb73c9fdb450af4fb3450959672418bd76015239a722d040c1c5603401`. El último HOLD histórico se disparó por `lost+found` como único EXTRA después de la expansión ext4.

Sin embargo, `PART_4_R2/STATE.json` no fue actualizado con esos cambios físicos: todavía declara `ext4_created=false`, `ntfs_shrunk=false`, `projects_migrated_hash_equivalent=false`. El estado material y el estado lógico divergen.

También persiste un `PERMISSION_REQUEST.json` de una misión anterior que exige `two_verified_backups` y `restore_proof`, precondiciones formalmente sustituidas por PART4-R2. Debe preservarse como historia, pero no gobernar la continuación vigente.

## 3. Arquitectura operacional

```text
MAESTRO
  │  orden, estado, gates y handoff
  ▼
OBSERVACIÓN VIVA / REMOTE BRIDGE
  │
  ├── estado físico
  ├── servicios
  ├── storage
  ├── telemetría
  └── resultados
  │
  ▼
GITHUB EVIDENCE SNAPSHOT
  │
  ▼
QWEN — GITHUB HOSTED ONLY
  │
  ├── PUAC.MC.07: causalidad, impactos, alternativas
  └── PUAC.MC.08: self-audit, incertidumbre, escalaciones
  │
  ▼
DETERMINISTIC GUARDS
  │
  ▼
PRE-COMMIT / CHECKPOINT
  │
  ▼
G23/G24 PRE-IRREVERSIBLE CUANDO APLIQUE
  │
  ▼
CUSTOSZ V7 / APC
  │
  ▼
OPERACIÓN MATERIAL EXACTA
  │
  ▼
REMOTE OBSERVE RESULT
  │
  ▼
POST-VALIDATION + NON-REGRESSION
  │
  ▼
G23
  ▼
G24
  ▼
STATE UPDATE DIGEST-BOUND
  ▼
NEXT PART
```

## 4. Regla de segundo orden

Cada propuesta material debe incorporar PUAC.MC.07 y PUAC.MC.08 antes de commit. Debe construir el grafo causal de la acción, distinguir premisas demostradas/no demostradas, calcular impacto directo/indirecto, buscar contraejemplos, registrar incertidumbre y comprobar falsos positivos/falsos negativos metacognitivos.

Pruebas mínimas transversales: T13, T21, T22, T23, T24, T25, T26, T27 y T28.

Qwen produce evidencia auxiliar y propuestas. Los guards deterministas deciden si la propuesta satisface contratos. G23 y G24 permanecen separados.

## 5. S0 — Reconciliación antes de PART4

No ejecutar ninguna nueva mutación del NVMe hasta reconciliar:

```text
STATE_DECLARED
vs
STATE_PHYSICAL
vs
STATE_V8_EVIDENCE
vs
STATE_CERTIFICATION
vs
STATE_AUTHORIZATION
```

S0 debe realizar inspección fresca y read-only de p3, demostrar qué contenido existe en su filesystem ext4 y comprobar PROYECTOS contra el manifiesto certificado. Debe confirmar que p5 sigue siendo raíz válida y que el `~/PROYECTOS` actual pertenece a p5.

El verificador de árbol debe tratar sólo el `lost+found` administrativo de la raíz ext4 como metadata de filesystem, con guardas exactas: path exacto, directorio real, no symlink, raíz del mismo filesystem. Cualquier otro EXTRA continúa siendo HOLD. Deben existir pruebas negativas específicas.

Después se produce un `PART4_RECONCILIATION_RECORD` que preserva el `STATE.json` histórico y añade el estado reconciliado con hashes de la evidencia V8 y de la inspección viva.

El certifier genérico de PART4 debe modificarse para reconocer PART4-R2: las dos copias y restore proof ya no son precondiciones vigentes. En su lugar se verifican H2/H4, freeze G24, scope G23/G24, integridad, equivalencia, final merge y postboot. El permiso histórico obsoleto se marca SUPERSEDED, nunca se borra.

S0 sale solamente con G23/G24 de reconciliación.

## 6. PART4 — Cierre definitivo

PART4 debe continuar desde el estado físico, no repetir V8.

Primero se certifica p3 ext4 y PROYECTOS. Luego se genera un plan exacto para retirar p2/p4, con geometría fresca y G23/G24. Se retiran sólo esos residuos y se revalida p1/p3/p5.

Para el final merge: p3 debe demostrar capacidad para Debian + PROYECTOS + margen. PROYECTOS se coloca en el namespace definitivo de la nueva raíz. La raíz Debian de p5 se copia preservando ACL/xattrs/hardlinks y sin atravesar montajes externos. Se actualizan fstab, initramfs, GRUB y referencias EFI. Antes del reboot: G23/G24.

El primer reboot debe arrancar desde p3 manteniendo p5 intacta. Se comprueba root real, EFI, PROYECTOS, servicios y no-regresión. Sólo entonces G23/G24 autorizan retirar p5. P3 se expande al límite final, se ejecutan e2fsck/resize2fs y una última verificación criptográfica de PROYECTOS.

Salida: EFI + una raíz ext4 principal para Debian y PROYECTOS, PART4_R2_CERTIFIED.

## 7. PART5 — Laboratory

No se acepta package-presence como PASS.

Se debe fijar procedencia/versiones de QEMU, KVM, libvirt y virt-manager; instalar/reutilizar sólo componentes admitidos; comprobar /dev/kvm, grupos/permisos y servicios; registrar imágenes admitidas por hash; cuarentenar cualquier media discrepante; crear una VM desechable, arrancarla, comprobar operación, apagarla y eliminarla; demostrar rollback/no-regresión. Después G23/G24.

## 8. PART6 — Gaming

Cada capacidad Wine, Steam, Proton, Bottles, Lutris, Prism y Waydroid tiene expediente propio: fuente, versión, dependencias, integridad cuando exista hash oficial, prueba de lanzamiento/función, compatibilidad gráfica y rollback. La presencia de un artefacto no satisface el gate. El lote completo requiere no-regresión cruzada y G23/G24.

## 9. PART7 — Study and Devotional

La auditoría viva sólo encontró launchers/icons de ESTUDIO/DEVOCIONAL; eso no prueba la superficie material.

Debe localizarse y clasificarse el corpus real, congelar fuentes por hash, registrar provenance, construir índices reproducibles, aplicar clasificación documental y controles hermenéuticos Louksna. UNKNOWN consecuencial => HOLD. Debe probarse recuperación/consulta y trazabilidad hasta fuente. Después G23/G24.

## 10. PART8 — System

Se cierra status/recursos/updates/backup/recovery/storage/hygiene/version management.

El backup se diseña sobre el layout final de PART4. Debe existir backup verificable y restore proof real. Higiene siempre comienza dry-run y protege explícitamente PROYECTOS, autoridad, checkpoints, evidence, certificates y rollback. La auditoría actual observa rsync, tar y 7z; la selección del mecanismo final depende de cobertura y recuperación demostrada, no del nombre de la herramienta.

## 11. PART9 — Final Integration

Requiere PART1–PART8 certificados y enlazados por digest. Ejecuta matriz global de boot, storage, PROYECTOS, engineering, laboratory, gaming, study/devotional, system/recovery, runner, Symphylax, Maestro, CUSTOSZ/APC, Qwen-hosted y Remote Bridge.

Debe pasar T13/T21/T22/T23/T24/T25/T26/T27/T28, recuperación y no-regresión global. Luego G23 final, G24 final, reboot final autorizado y repetición post-reboot de la matriz crítica.

Sólo después:

```text
GLOBAL_MISSION_STATUS = COMPLETE
```

## 12. Qwen sin RAM local

Estado observado: el GGUF local de 1904339232 bytes existe, pero no hay proceso local de `llama-cli/Qwen`.

La ejecución futura se mueve a `ubuntu-24.04` GitHub-hosted. La binding debe dejar de depender de una ruta/binario local y convertirse en una attestation por entorno: modelo pin + SHA256 + runtime source revision + build provenance + runtime SHA del runner hospedado.

El primer gate de esta ruta es un benchmark alojado en GitHub que mida tiempo, memoria, salida estructurada y reproducibilidad. Hasta entonces Qwen-hosted es CANDIDATE_RUNTIME, no certificado.

## 13. Telemetría y evidencia

`louksna-live-socket.service` está activo. La telemetría de alta frecuencia debe ser efímera/en memoria. No se debe crear un archivo local por cada observación.

Sólo se persiste evidencia en:
- checkpoint;
- pre-commit irreversible;
- post-validation;
- incidente/HOLD;
- G23/G24;
- handoff PARTn→PARTn+1.

GitHub artifacts es el almacén durable preferido para evidencia de misión. El host conserva sólo el mínimo ledger/checkpoint necesario para continuidad y recuperación.

## 14. Automatización

La secuencia automática queda:

```text
S0
→ PART4 G24
→ PART5 G24
→ PART6 G24
→ PART7 G24
→ PART8 G24
→ PART9 FINAL G23/G24
→ FINAL REBOOT
→ POSTBOOT MATRIX
→ COMPLETE
```

No se solicita nueva autorización humana para operaciones que ya estén dentro del alcance explícitamente autorizado de PART4. Una caducidad técnica de lease/APC se renueva sólo conforme al mecanismo de autorización existente; no amplía scope.

Ante UNKNOWN, CONFLICT, scope drift, mismatch, evidencia vencida o gate incompleto: HOLD. No existe retry irreversible idéntico. Se preserva evidencia, Qwen propone alternativas, MC07/MC08 analizan, se elige el delta mínimo, se revalida y recién entonces se reintenta.

## 15. Próximo gate autorizado por este plan

```text
NEXT = S0_RECONCILE_P3_CONTENT_AND_STATE_WITHOUT_NVME_MUTATION
```

El plan no declara PART4 PASS ni emite G23/G24. Prepara la ruta operacional para obtenerlos con evidencia material.
