# LUNITA — adenda de despacho y corrección de enrutamiento
Fecha: 2026-11-15

## Naturaleza de esta adenda

Adenda append-only a la misión `lunita-entrega3-entrega4-20261115`. No reemplaza ni modifica `MISSION.md`, no altera el runtime, no reconstruye el SquashFS y no crea motores, agentes, comandos o módulos.

## Corrección de enrutamiento

- La misión se encuentra físicamente en la rama `fix/lunita-v18-rootfs-bound-checkpoint-20261109`.
- El encabezado de `MISSION.md` nombra `recovery/lunita-custoszv9-operational-20261020` como rama de publicación, pero esa rama no contiene el archivo de misión.
- Para evitar una segunda desviación, la ejecución queda ligada a la rama que contiene simultáneamente el expediente y el runtime v1.8: `fix/lunita-v18-rootfs-bound-checkpoint-20261109`.
- No se reescribe el encabezado histórico; esta adenda registra explícitamente la discrepancia.

## Imagen autorizada para esta ejecución

La misión inicial hacía referencia al artefacto histórico del run `43498177123`. Para esta ejecución se fija la imagen certificada posterior:

- Run: `43730042509`
- Artifact ID: `14169257477`
- Artifact: `lunita-v1-8-squashfs-certified`
- SquashFS SHA-256: `21e6503fb7c531b1f452c9983dba157a5988e183c9fd8247807409988132fbab`
- Certificación publicada: candidato funcional v1.8, limitada al alcance de funcionalidad del SquashFS derivado.

La ejecución debe verificar este hash antes de extraer o invocar motores. No puede sustituir la imagen por otra compilación, rama o candidato.

## Despacho operativo

Se añadió el workflow `.github/workflows/lunita-academic-mission-execution.yml` en el commit `500a3d7346c2cc12c8155d6f77fd5da7958a2ca1`. El workflow descarga el artefacto fijado, verifica su identidad y opera dentro del rootfs extraído de esa imagen. No modifica la imagen ni el árbol de runtime.

Run de ejecución observado al emitir esta adenda: `43750235605`. Estado observado: `in_progress`. Su estado final, respuestas de motores y artefactos deben registrarse desde Actions; esta adenda no afirma que el trabajo ya haya terminado.

## Alcance de fuentes y límite probatorio

En la rama inspeccionada solo está versionado el expediente de misión, que resume el instrumento aplicado y frecuencias agregadas de 26 respuestas. No están versionados los documentos fuente completos de Entrega 3/4 ni una exportación individual CSV/XLSX. Por tanto:

- No es posible declarar una auditoría línea por línea de los documentos fuente originales.
- No se deben construir microdatos ni presentar filas artificiales como participantes.
- Con el instrumento descrito no pueden probarse hipótesis que requieran BFI-2-S, intervención aleatoria, grupo control, CAM informatizada, RT o errores objetivos.
- Los resultados válidos con el material disponible son descriptivos y agregados.
- La detección de una instalación de JASP o Jamovi no equivale a haber ejecutado un análisis en esas aplicaciones. No se admite generar un proyecto vacío ni resultados ficticios.

## Estado de cierre

La misión permanece ABIERTA hasta disponer de los documentos fuente originales y la exportación de datos individuales, y hasta verificar los resultados reproducibles y las salidas estadísticas requeridas. Cualquier salida parcial debe identificarse como parcial; ninguna certificación funcional del SquashFS implica certificación académica automática.
