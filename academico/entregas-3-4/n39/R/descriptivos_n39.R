#!/usr/bin/env Rscript
# Descriptivos univariados desde frecuencias marginales n=39.
# No expande a personas inventadas y no calcula correlaciones.
args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args) >= 1) args[[1]] else "/workspace/lunita-n39"
motor <- if (length(args) >= 2) args[[2]] else "R-base"
freq_path <- file.path(root, "datos", "base_frecuencias_n39.csv")
out_dir <- file.path(root, "salidas")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

raw <- read.csv(freq_path, stringsAsFactors = FALSE, fileEncoding = "UTF-8", check.names = FALSE)
raw$nivel <- as.numeric(raw$nivel)
raw$frecuencia <- as.integer(raw$frecuencia)
stopifnot(!anyNA(raw$nivel), !anyNA(raw$frecuencia))

mode_of <- function(x) {
  ux <- unique(x)
  tab <- tabulate(match(x, ux))
  paste(sort(ux[tab == max(tab)]), collapse = "|")
}

preguntas <- unique(raw$n_pregunta)
rows <- lapply(preguntas, function(q) {
  sub <- raw[raw$n_pregunta == q, ]
  if (sum(sub$frecuencia) != 39L) stop("N distinto de 39 en pregunta ", q)
  x <- rep(sub$nivel, times = sub$frecuencia)
  data.frame(
    motor = motor,
    n_pregunta = q,
    pregunta = sub$pregunta[[1]],
    n = length(x),
    media = mean(x),
    mediana = median(x),
    moda = mode_of(x),
    de = sd(x),
    minimo = min(x),
    maximo = max(x),
    stringsAsFactors = FALSE
  )
})
out <- do.call(rbind, rows)
rownames(out) <- NULL
out_file <- file.path(out_dir, paste0("descriptivos_", gsub("[^A-Za-z0-9]+", "_", motor), ".csv"))
write.csv(out, out_file, row.names = FALSE)
print(out[, c("n_pregunta", "n", "media", "mediana", "moda", "de")])
cat("WROTE", out_file, "\n")
