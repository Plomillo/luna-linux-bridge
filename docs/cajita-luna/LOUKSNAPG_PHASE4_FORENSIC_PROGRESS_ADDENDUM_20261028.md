# LOUKSNAPG — adenda de verificación de continuidad

- Fecha: 2026-10-28 UTC.
- Rama: `louksnapg/phase4-resume-20261028`.
- Commit candidato auditado por la ejecución más reciente: `ffbf9093eba715f080be130a9d40e4c2fbe13f9a`.
- Estado de certificación integral: `NOT_GRANTED`.
- Propósito: añadir evidencia sobre la corrección del presupuesto de memoria de CI, sus pruebas y la reauditoría de los bloqueos. No modifica las conclusiones funcionales de los modelos.

## Corrección del presupuesto de recursos y verificación posterior

La primera versión de la prueba nueva encontró dos defectos de implementación del propio control: una ruta de importación de test incorrecta y, después, una expresión regular doblemente escapada al leer `MemTotal`. Ambos se corrigieron en los commits `262debb7f3c124091388efdecc3097b2accc572e`, `a1822c8c05ccfaabd3ace775076e4027e9986f19` y `ffbf9093eba715f080be130a9d40e4c2fbe13f9a`. La prueba también cubre el caso en que un override excede la capacidad segura física: queda limitado al 75 % del menor límite entre memoria del runner y cgroup.

La ejecución de GitHub Actions [40780809929](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40780809929) confirma:
- compilación de los scripts de continuación: PASS;
- siete pruebas unitarias del control de recursos: PASS;
- la admisión de fase 4 se ejecuta con éxito técnico, pero su decisión funcional sigue siendo `BLOCKED_FAIL_CLOSED`;
- fase 5, 6 y 7: OMITIDAS por la dependencia de reparación no superada;
- fase 8: bloqueada con `G23_EVIDENCE_MISSING`, `G24_EVIDENCE_MISSING`, `PHASE4_REPAIR_GATE_NOT_PASSED`, `PHASE5_TARGETED_RETEST_NOT_PASSED`, `PHASE6_INTEGRATION_NOT_PASSED`, `PHASE7_GLOBAL_RELEASE_READINESS_NOT_ESTABLISHED` y `PHASE7_INDEPENDENT_VALIDATION_NOT_PASSED`;
- fase 9: registra el bloqueo y termina con código no cero mientras falte cualquier gate obligatorio.

La conclusión de la ejecución sigue siendo `GLOBAL_CERTIFICATION=NOT_GRANTED`. El resultado verde de las pruebas unitarias valida el control de recursos, no la calidad de los modelos.

## Reauditoría del traductor de lenguas antiguas

En la versión candidata, el manifiesto de nivel superior declara `consumer_adapter_registration.status=NOT_REGISTERED` y `native_smoke=REQUIRED`. La búsqueda de árbol del repositorio encontró, fuera de los fuentes del compilador Foma, sólo los manifiestos `CAJITA_MODULE.json` de los dos niveles. Los archivos Foma encontrados son el código fuente del compilador y sus pruebas de compilación; no se halló un autómata de traducción compilado, un léxico de lenguas antiguas ni un recurso equivalente listo para servir como modelo.

No se fabricó un diccionario, no se eligió un idioma por suposición y no se registró un adaptador fingido. La corrección real requiere identificar la lengua o lenguas concretas del módulo, localizar el léxico/transductor licenciado y registrar un adaptador que se pruebe con un caso conocido de extremo a extremo.

## Kestra y CUSTOSZ 9

Kestra sigue activo como servicio, con un proceso limitado a un hilo, pero la API de administración local rechazó con HTTP 401 incluso la consulta autenticada con las credenciales locales disponibles. La definición `integrations/kestra/louksnapg_phase4_to9_supervisor.yml` continúa siendo una especificación en el repositorio; no se obtuvo recibo de creación, revisión activa ni ejecución de ese supervisor. No se cambió la configuración de seguridad ni se intentó un bypass.

La inspección ligera del árbol de CUSTOSZ encontró scripts/colas históricos con nombres de V9 y varios artefactos empaquetados V8; el servicio que ya está activo sigue apuntando a V7, que está prohibido para esta misión. No se encontró un ejecutable V9 independiente, verificable y activo con una entrada de misión ligada a este candidato. Por eso no se despachó inferencia o reparación a un trabajador cuya identidad no pueda certificarse. No se ejecutó CUSTOSZ V7.

## Límites de la inspección local

Las operaciones en la PC fueron lecturas de manifiestos, metadatos, nombres de archivo, estado de servicio, memoria y espacio del sistema de archivos. No se cargaron tensores, no se realizó inferencia, no se descargaron modelos, no se modificaron los pesos y no se escribió en el runtime canónico de la PC. La fotografía de disco seguía mostrando 99 % de uso y cero inodos libres; por ello no se intentaron instalaciones, limpiezas, reinicios ni registros que dependieran de escrituras locales adicionales.

## Bloqueo material restante

El manifiesto `evidence/louksnapg/phase4-repair-candidate.json` no existe en la rama activa; tampoco están configurados los secretos de descarga `LOUKSNAPG_PRIVATE_BUNDLE_URL` y `LOUKSNAPG_PRIVATE_BUNDLE_TOKEN`. Sin candidato privado con procedencia y hashes genuinos, la fase 4 no autoriza la fase 5. El código de control no puede reconstruir tensores descartados por la compresión. Se conserva el candidato exacto y no se copian pesos privados a la rama pública.

**Decisión invariable: `HOLD_NOT_CERTIFIED`.** Se validó el control de recursos en CI; no se repararon todavía los cuatro motores que fallan las pruebas de calidad ni la traducción de lenguas antiguas.
