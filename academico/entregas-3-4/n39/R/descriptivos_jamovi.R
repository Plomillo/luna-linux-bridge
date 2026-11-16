#!/usr/bin/env Rscript
# Corre descriptives() del jmv que viene dentro de jamovi 28.17, no de un archivo suelto.
.libPaths(c("/app/lib/jamovi/modules/jmv/R", .libPaths()))
suppressPackageStartupMessages(library(jmv))
root <- "/workspace/lunita-n39"
raw <- read.csv(file.path(root, "datos", "base_frecuencias_n39.csv"), stringsAsFactors = FALSE, check.names = FALSE)
raw$nivel <- as.numeric(raw$nivel)
raw$frecuencia <- as.integer(raw$frecuencia)
preguntas <- unique(raw$n_pregunta)
rows <- lapply(preguntas, function(q) {
  sub <- raw[raw$n_pregunta == q, ]
  x <- rep(sub$nivel, times = sub$frecuencia)
  df <- data.frame(x = x)
  fit <- descriptives(
    df, vars = "x",
    freq = FALSE, hist = FALSE, dens = FALSE, bar = FALSE, box = FALSE,
    violin = FALSE, dot = FALSE, qq = FALSE,
    mean = TRUE, median = TRUE, sd = TRUE, min = TRUE, max = TRUE,
    n = TRUE, missing = TRUE
  )
  tab <- as.data.frame(fit$descriptives)
  pick <- function(suffix) as.numeric(tab[[paste0("x[", suffix, "]")]][1])
  data.frame(
    motor = "jamovi-jmv",
    version_jmv = as.character(packageVersion("jmv")),
    n_pregunta = q,
    n = pick("n"),
    media = pick("mean"),
    mediana = pick("median"),
    de = pick("sd"),
    minimo = pick("min"),
    maximo = pick("max"),
    stringsAsFactors = FALSE
  )
})
out <- do.call(rbind, rows)
dir.create(file.path(root, "salidas"), showWarnings = FALSE)
write.csv(out, file.path(root, "salidas", "descriptivos_jamovi_jmv.csv"), row.names = FALSE)
print(out)
cat("JMV", as.character(packageVersion("jmv")), "JMVCORE", as.character(packageVersion("jmvcore")), "\n")
