# Estado — Entregas 3 y 4, n = 27

Rama de trabajo. `main` no se modifica.

## Resuelto en este commit

- El CSV que entra al repositorio es el archivo oficial adjunto, sin reedición: `datos/frecuencias_agregadas_n27.csv`, SHA-256 `d06ae497705feeb16a31e71782ede466f2c9038806f72f0c67806c7d4c96688c`.
- Cada tabla suma 27. Los porcentajes del archivo coinciden con `100 * frecuencia / 27` redondeado a un decimal.
- R 4.5.3, `descriptives()` de jmv 2.8.0 y las funciones de descriptivos de JASP se ejecutaron sobre ese CSV. Diferencia máxima de media y de DE: 0.
- Edad: media 42,30, mediana 44, moda 33. Esfuerzo: media 2,93, mediana 3, moda 0.
- Entregas 3 y 4 originales no están en este árbol y no se reescribieron. Los informes de `informes/` son documentos aparte.
- No hay correlaciones ni filas de personas inventadas. La plantilla del protocolo sigue en 0 filas.

## Sigue bloqueado, y no se tapa

- `LUNITA.squashfs` local mide 3576823808 bytes y el superbloque anuncia 3993154438. `unsquashfs` falla en la tabla de ids. No está como blob en `main`. No se montó y no se certificó un arranque desde esa imagen.
- No se abrió la ventana de jamovi ni la de JASP. Corrió el código de descriptivos de ambos, dentro del R de Lunita.
- H1, H2 y H3 siguen no examinables: no hay BFI-2-S, no hay CAM, no hay condición, no hay microdatos. Eso no se resuelve rellenando celdas.
