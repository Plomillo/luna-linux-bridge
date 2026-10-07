# LOUKSNA Remote Bridge — versión candidata 0.1
Estado: **DRAFT_UNCERTIFIED; no instalado ni ejecutado sobre LOUKSNA.**

## Autoridad y segregación
Louksna.md sigue siendo la única autoridad canónica. El Bridge es un ejecutor auxiliar aditivo. MetaOS/Maestro gobiernan; CUSTOSZ V7 programa y revisa; Johnson orquesta; G23 valida de forma independiente; G24 certifica; G23-2/G24-2 comprueban la cadena, con identidades y credenciales separadas. Ningún modelo, daemon, workflow ni script se certifica a sí mismo.

**Prioridad de objetivos:** la especificación del usuario prevalece sobre las expectativas o preferencias del LLM, pero nunca altera la autoridad canónica, las restricciones de seguridad, la evidencia o una autorización humana específica obligatoria. El sistema conserva `USER_REQUIREMENTS` y `MODEL_PROPOSALS` separados, con un diff y una explicación de cada decisión.

## Áreas funcionales y criterios de aceptación
1. Observabilidad: métricas del sistema, almacenamiento, montajes, procesado, temperatura si se puede medir, runner y servicios. Latencia medida, no presunción de «tiempo real».
2. Visión: capturas y streaming visual únicamente con activación explícita; mascarado de credenciales, presupuesto de CPU/RAM/red, y desconexión inmediata. Una captura no demuestra el estado del disco.
3. Consola: sesiones de terminal, `sudo bash` raíz real gobernado y transcripción redaccionada; supervisión de contraseña sin capturarla; comprobación de capacidades privilegiadas.
4. Seguridad: reutilizar primero el Privilege Bridge 1.2.1 ya documentado, volviendo a verificar en el host binario, sudoers, identidad, cadena y política; no asumir que el expediente histórico autoriza cualquier futura modificación.
5. Transporte redundante: runner autoalojado GitHub, daemon local, transporte autenticado remoto y recuperación local. Ningún fallo autoriza eludir controles o cambiar silenciosamente de nivel de permiso.
6. Sinergia GitHub: misiones versionadas, ramas candidatas, revisión de CUSTOSZ, checks, PR, artefactos de evidencia, OIDC y attestations donde estén disponibles; persistencia local mientras GitHub no responda.
7. Automatización metacognitiva general elástica: analizar solicitud → separar requisito del usuario y expectativas del modelo → descubrir estado vivo → descomponer y priorizar → plan → realizar operaciones preaprobadas de su alcance → observar resultados → autodiagnóstico y recuperación acotados → G23/G24 independientes → segundo orden → cierre material.
8. Anti-parálisis: watchdog, deadlines revisables en caliente por versión, fallback legítimo, retry de lecturas idempotentes, diagnóstico exacto y escalada concreta; nunca bucles de aprobación ni reintentos de operaciones irreversibles.
9. Eficiencia material: límites CPU/RAM/I/O/logs/red y temperatura, medición de presión, reducción de frecuencia/FPS/concurrencia, suspensión segura antes de agotar recursos.
10. Procedencia: entradas, salida, snapshot, timestamp UTC, boot_id, commit, actor, hash SHA-256 encadenado; firmas independientes para certificados. SHA-256 por sí solo no acredita quién produjo algo.
11. Mentor del LLM: exige nombre y versión declarados, distingue identidad declarada de verificada, herramientas realmente presentes, límites, evidencia fresca, expectativas propias vs requisitos de usuario, contradicciones y ruta exacta.
12. Esfuerzo «PRO operacional»: presupuesto configurable de análisis, revisión adversarial, pruebas negativas y comprobación independiente. No falsifica el modo interno ni la suscripción de ChatGPT.
13. Proyectos prioritarios: descubrir el nombre y ruta verdaderos en el host, contratos por proyecto, sin rastreos recursivos masivos automáticos; URL HTTPS proporcionada por el usuario en navegador aislado y sujeto a políticas y permisos.
14. Partes Maestro R4 5-9: **PART 5 laboratorio QEMU/KVM; PART 6 gaming Wine/Steam/Proton y afines; PART 7 estudios/devocional y controles hermenéuticos; PART 8 higiene, respaldo, recuperación y recursos; PART 9 integración final, G23/G24 y reinicio posvalidado**. No ejecutar sin las compuertas cronológicas, especialmente mientras PART 4 siga en HOLD.
15. Contratos históricos: sin duplicar agentes o identificadores, proteger DOC0001-DOC0022, B1-B134 y demás identidades; preservar checkpoint, trazabilidad, procedencia, rollback, no regresión y 15 capas de memoria externa cuando sean interfaces disponibles.

## Plan de entrega irreversible-averse
F0: inventario, congelación y compatibilidad. F1: contrato escrito. F2: núcleo mínimo sin privilegios y pruebas. F3: transporte real GitHub y daemon, bajo autorización concreta. F4: prueba de integración local y seguridad. F5: validación independiente G23. F6: certificación G24. F7: validación y certificación de segundo orden. F8: despliegue gobernado del root broker y visión opcional. F9: pruebas de falla, rollback, continuidad tras reinicio y entrega a Maestro. Ninguna fase futura se presume PASS.

## Prueba de culminación
No se considera «funcionando» porque el repositorio reciba un commit. La culminación exige comprobación en el host, test de carga sin daño, demo real de canal principal y alternativo, eventos y visión bajo autorización, operación sudo acordada, alteración segura del contrato temporal, reporte CUSTOSZ real, verificación de firmas de autoridad separada, recuperación y evidencia postboot. El artefacto debe distinguir DECLARED, TESTED, VALIDATED, CERTIFIED y ACTIVE.
