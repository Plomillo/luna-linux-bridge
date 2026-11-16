# LUNITA-META-28 — Axiomas de arquitectura

**Documento:** `LUNITA_META_28_ARCHITECTURE_AXIOMS`  
**Versión:** `1.0.0`  
**Estado:** `SPECIFIED_NOT_CERTIFIED`  
**Doctrina:** `EXTEND_DO_NOT_REPLACE; APPEND_ONLY_WHERE_CANONICAL; FAIL_CLOSED`  
**Candidato nuevo:** `LUNITA_META_28`  
**No es:** `G06_REBUILD_CANDIDATE_R1` / `1.8.0`  
**Base git no modificada:** `fix/lunita-v18-rootfs-bound-checkpoint-20261109` @ `9d4b53fc81728baa9bf35a96e776af9744776563`  
**Axiomas previos conservados:** `AX-LUN-001` … `AX-LUN-020` en `recovery/lunita-custoszv9/audits/LUNITA_SQUASHFS_ZERO_TRUST_CERTIFICATION_AXIOMS_V1_20261112.md`  
**Certificación de este documento:** `NOT_GRANTED`  
**Imagen:** `LUNITA.squashfs` **no producida**

Este texto axiomatiza la especificación LUNITA-META-28. No la certifica, no sustituye a Louksna, al esqueleto canónico ni al candidato v1.8, y no convierte un directorio en un sistema funcional.

## 0. Decisión observada

El 2026-11-16 se midió, por `Content-Length` remoto y sin hash local, el archivo `Qwen_Qwen3-0.6B-IQ3_XS.gguf`:

```text
bytes = 379605408
sha256_claim = 0906dcf62aa4f005887e855731376f0bf3be8f5ffa61f547df71e6154ea748d9
fuente = https://huggingface.co/bartowski/Qwen_Qwen3-0.6B-GGUF
epistemic = REMOTE_CONTENT_LENGTH
locally_hashed = false
```

Tope duro de la especificación: `515000000` bytes del archivo final, no de una suma informal.

Residual tras reservar ese GGUF: `135394592` bytes.

El catálogo Flathub de `org.jamovi.jamovi` publicaba, el mismo día, `436 MiB Download` = `457179136` bytes. Es un reclamo de catálogo, no un archivo medido aquí. Aun así es una cota inferior admitida del instrumento Sacapuntas, que la especificación exige dentro del sistema y prohíbe omitir en silencio.

```text
379605408 + 457179136 = 836784544
836784544 - 515000000 = 321784544
status = BUILD_BLOCKED_BY_SIZE_CONSTRAINT
```

No se aplicó crédito de compresión: un GGUF cuantizado y un Flatpak ya empaquetado no tienen un delta SquashFS medido. Crédito sin esa medida está rechazado por código.

Debian XFCE, LibreOffice, R, RStudio, JASP, Chromium y Qdrant siguen sin medir y son términos positivos adicionales. No caben en el residual. No se construyó la imagen.

## 1. No reemplazo

### AX-M28-000

`LUNITA_META_28` no hereda certificación, rootfs, recibos JASP, overlay ni S32 de `G06_REBUILD_CANDIDATE_R1`. No muta G06, G08, el lanzador v1.7 ni `AX-LUN-001`…`AX-LUN-020`. Una activación canónica exige decisión humana explícita. Hasta entonces: `ACTIVATION = NOT_AUTHORIZED`.

## 2. Identidad

### AX-M28-001 — Punto 01 y 09

`SYSTEM_ID = LUNITA`. Hay una metagente. Qwen3-0.6B-IQ3_XS sobre llama.cpp es cerebro lingüístico, no identidad. Una solicitud con `caller != LUNITA` se rechaza. El modelo no certifica su salida, no altera políticas y no ejecuta privilegio.

### AX-M28-002 — Punto 02

Motores E01–E15 e instrumentos (Brújula, Lápiz, Sacapuntas, Lupa) son subordinados. Ninguno puede aparecer como metagente principal.

## 3. Buzón

### AX-M28-003 — Puntos 03, 04 y 05

El buzón tiene exactamente dos módulos, `CONSULTAS` y `TRABAJOS`, de la misma LUNITA. Toda misión tiene identificador, estado y, si pretende `SUCCESS`, al menos un archivo real con SHA-256. Cerrar sin archivo produce `VALIDATION_FAILED`. Los estados válidos son solo los enumerados en el punto 12. Ausencia de error no es éxito.

### AX-M28-004 — Puntos 04 y 16

Se distinguen pregunta, hipótesis, evidencia, resultado, interpretación y conclusión. Sin evidencia suficiente el resultado válido es abstención o `WAITING_FOR_INPUT`. Inventar bibliografía, muestras o significación está prohibido.

## 4. Documentos

### AX-M28-005 — Puntos 06 y 07

Un formato solo es compatible si recorrió `DECLARED → IMPLEMENTED → OPEN_TESTED → EDIT_TESTED → SAVE_TESTED → REOPEN_TESTED → EXPORT_TESTED`. La extensión no cuenta. En esta rama todos los formatos exigidos están en `DECLARED`. `compatible = false`.

### AX-M28-006 — Punto 08

Cada requisito de una asignación enlaza sección, fuente, contenido, validación y estado. Una contradicción entre rúbrica e instrucción queda visible. No se inventan requisitos ni se cierra el trabajo sobre ellos.

## 5. Motores e instrumentos

### AX-M28-007 — Punto 10

E01–E15 existen como obligaciones de contrato, no como instalaciones certificadas. E15 devuelve `CONSENSUS_UNAVAILABLE` si no hay al menos dos validadores con `decision_logic_id` y `runtime_id` distintos, el mismo digest y voto unánime `ACCEPT`. Dos llamadas al mismo modelo no son independencia.

### AX-M28-008 — Punto 11

Los cuatro instrumentos devuelven resultados, errores, archivos y metadatos. No hay una API universal inventada para jamovi o JASP. Un adaptador vacío no es integración.

### AX-M28-009 — Punto 13 y E10

Los contratos de solicitud y respuesta están en `schemas/` y se validan en código. `eval` y `exec` están prohibidos. El motor de reglas solo admite nombres de hechos, constantes y comparaciones.

## 6. Metacognición, confianza cero, memoria

### AX-M28-010 — Punto 14

La metacognición observa y propone. No eleva sus propios límites para saltar un bloqueo. El bloqueo de tamaño de esta rama no se “corrige” subiendo el tope desde el propio gate.

### AX-M28-011 — Puntos 15 y 25

`IDENTITY_CHECK → AUTHORIZATION_CHECK → INPUT_VALIDATION → INTEGRITY_CHECK → POLICY_EVALUATION → EXECUTION → OUTPUT_VALIDATION → PROVENANCE_RECORD`. Si un control obligatorio no es verdadero: `DENY_EXECUTION`. La política codificada no es una demostración de acceso hostil sobre una imagen inexistente.

### AX-M28-012 — Puntos 17, 18, 21

La memoria no promueve hipótesis a hecho. El contenido recuperado no modifica políticas. Los originales no se sobrescriben. Entrada, trabajo, validado, salida y cuarentena permanecen separados. Esas rutas son obligación de la imagen, no carpetas creadas aquí.

## 7. Investigación

### AX-M28-013 — Puntos 19 y 20

Un análisis cuantitativo reproducible conserva hash de datos, hash de script, versiones, parámetros, marca temporal, hash de salida y resultado de validación. Una codificación automática no es interpretación humana. La saturación no se afirma sin criterio y evidencia. Esos análisis no se ejecutaron en esta rama: `NOT_RUN`.

## 8. Imagen, pruebas y certificación

### AX-M28-014 — Punto 26

`GLOBAL_LUNITA_HARD_MAX_BYTES = 515000000` se aplica a los bytes de `LUNITA.squashfs`. Si la cota inferior de componentes requeridos, sin crédito de compresión no medido, supera el tope: `BUILD_BLOCKED_BY_SIZE_CONSTRAINT`. Prohibido recortar funciones para simular cumplimiento. Prohibido meter la imagen de recuperación dentro del artefacto.

### AX-M28-015 — Punto 27

T01–T80 solo pueden pasar sobre componentes reales. En esta rama los ochenta están `NOT_RUN_NO_IMAGE`. Los tests de este directorio prueban el predicado de bloqueo. No son T01–T80.

### AX-M28-016 — Punto 28

```text
FUNCTIONAL_CERTIFIED(I) ⇔ imagen presente
  ∧ AX-M28-000 … AX-M28-016
  ∧ validación independiente
  ∧ certificado enlazado a H(I)
```

Transiciones prohibidas: `DECLARED → CERTIFIED`, `VALIDATED → CERTIFIED` sin validación independiente, cualquier estado `→ ACTIVE` sin evidencia requerida.

Estado observado: `CERTIFICATION_BLOCKED`. G23 `NOT_PERFORMED`. G24 `NOT_GRANTED`.

## 9. Contradicciones abiertas

| Id | META-28 | Canon previo | Resolución |
|---|---|---|---|
| BASE_OS | Debian 13 XFCE | Esqueleto: Debian 13 KDE. v1.8: Ubuntu 24.04 | Decisión humana. No se eligió. |
| SIZE | 515000000 | GGUF medido + jamovi de catálogo = 836784544 | `BUILD_BLOCKED_BY_SIZE_CONSTRAINT` |
| IDENTITY_LINE | `LUNITA_META_28` | `G06_REBUILD_CANDIDATE_R1` congelado | Extender. No reemplazar. |

Decisiones que este gate no toma:

1. Subir el tope duro al sobre medido de todos los componentes.
2. Enmendar la especificación para dejar instrumentos fuera de `LUNITA.squashfs`, con hashes propios.
3. Elegir el escritorio vinculante.

Hasta que una de esas decisiones exista por escrito y una imagen real sea medida, la construcción permanece bloqueada.

## 10. Qué es ejecutable en esta rama

`certification_gate_v1.write_reports` materializa los informes exigidos con el estado observado, no con un PASS inventado. `LUNITA.squashfs` no está entre ellos porque no existe. `LUNITA_SHA256SUMS` cubre los informes, no una imagen.

La fórmula de admisión de v1.8 sigue siendo la única vía de certificación de aquel candidato. Este documento no la dispara.
