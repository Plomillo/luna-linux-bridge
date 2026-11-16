# Evidencia gráfica n=39

Esta carpeta contiene capturas producidas desde ventanas de las aplicaciones de escritorio oficiales, no composiciones SVG.

- RStudio Desktop de Posit ejecutando R.
- jamovi Desktop desde Flathub.
- JASP Desktop desde Flathub.

La base de entrada para el trabajo gráfico se deriva de `datos/base_frecuencias_n39.csv`. Para poder abrir las frecuencias marginales en las interfaces, se representa cada una de las seis preguntas mediante 39 valores expandidos a partir de sus recuentos. Son distribuciones univariadas independientes. Los 39 registros de una pregunta NO se emparejan con los 39 registros de otra: el archivo no contiene microdatos enlazados por participante y no permite correlaciones, comparaciones pareadas ni inferencia conjunta.

La expansión reproduce exactamente cada frecuencia y sirve para descriptivos univariados. El manifiesto conserva SHA-256 de entrada y salida. La automatización de captura está en el workflow `.github/workflows/n39-official-gui-captures.yml`.
