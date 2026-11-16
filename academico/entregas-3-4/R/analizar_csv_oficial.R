#!/usr/bin/env Rscript
# Lee el CSV oficial adjunto (tabla, categoria, orden, frecuencia, n, porcentaje, nota).
# No modifica el CSV. No fabrica microdatos ni correlaciones.

root <- "/workspace/lunita-e3e4"
csv_path <- file.path(root, "datos", "frecuencias_agregadas_n27.csv")
out_dir <- file.path(root, "salidas")
fig_dir <- file.path(root, "figuras")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

raw <- read.csv(csv_path, stringsAsFactors = FALSE, fileEncoding = "UTF-8", check.names = FALSE)
need <- c("tabla", "categoria", "orden", "frecuencia", "n", "porcentaje", "nota")
stopifnot(all(need %in% names(raw)))
raw$frecuencia <- as.integer(raw$frecuencia)
raw$n <- as.integer(raw$n)
raw$orden <- as.integer(raw$orden)

nivel_de <- function(tabla, categoria, orden) {
  if (tabla %in% c("edad", "esfuerzo")) return(as.numeric(categoria))
  as.numeric(orden)
}
raw$nivel <- mapply(nivel_de, raw$tabla, raw$categoria, raw$orden)

for (t in unique(raw$tabla)) {
  sub <- raw[raw$tabla == t, ]
  if (sum(sub$frecuencia) != 27L) stop("N distinto de 27 en ", t)
  if (any(sub$n != 27L)) stop("columna n distinta de 27 en ", t)
}

suppressPackageStartupMessages(library(jmvcore))
sys.source("/tmp/jmvsrc/jmv/R/descriptives.h.R", envir = globalenv())
sys.source("/tmp/jmvsrc/jmv/R/descriptives.b.R", envir = globalenv())
source("/tmp/jasp_descriptives.R")

jasp_opts <- list(
  meanArithmetic = TRUE, sd = TRUE, seMean = FALSE, median = FALSE, mode = FALSE,
  minimum = FALSE, maximum = FALSE, valid = TRUE, missing = TRUE,
  meanGeometric = FALSE, meanHarmonic = FALSE, coefficientOfVariation = FALSE,
  mad = FALSE, madRobust = FALSE, iqr = FALSE, variance = FALSE, kurtosis = FALSE,
  skewness = FALSE, shapiroWilkTest = FALSE, sum = FALSE, range = FALSE,
  quartiles = FALSE, quantilesForEqualGroups = FALSE, percentiles = FALSE,
  meanCi = FALSE, sdCi = FALSE, varianceCi = FALSE, quantilesType = 7
)

mode_of <- function(x) {
  ux <- unique(x)
  tab <- tabulate(match(x, ux))
  paste(sort(ux[tab == max(tab)]), collapse = "|")
}

rows <- list()
for (t in unique(raw$tabla)) {
  sub <- raw[raw$tabla == t, ]
  x <- rep(sub$nivel, times = sub$frecuencia)
  fit <- descriptives(
    data.frame(x = x), vars = "x",
    freq = FALSE, hist = FALSE, dens = FALSE, bar = FALSE, box = FALSE,
    violin = FALSE, dot = FALSE, qq = FALSE,
    mean = TRUE, median = TRUE, sd = TRUE, min = TRUE, max = TRUE,
    n = TRUE, missing = TRUE
  )
  tab <- as.data.frame(fit$descriptives)
  pick <- function(suffix) as.numeric(tab[[paste0("x[", suffix, "]")]][1])
  jasp <- .descriptivesDescriptivesTable_subFunction(
    x, "scale", list(Variable = t), jasp_opts, FALSE, FALSE, NULL
  )$resultsCol
  jasp_med <- as.numeric(.descriptivesMedian(x, list(quantilesType = 7), identity))
  rows[[t]] <- data.frame(
    tabla = t,
    n = length(x),
    r_media = mean(x), jamovi_media = pick("mean"), jasp_media = as.numeric(jasp$MeanArithmetic),
    r_mediana = median(x), jamovi_mediana = pick("median"), jasp_mediana = jasp_med,
    r_de = sd(x), jamovi_de = pick("sd"), jasp_de = as.numeric(jasp[["Std. Deviation"]]),
    moda_frecuencia = mode_of(x),
    minimo = min(x), maximo = max(x),
    stringsAsFactors = FALSE
  )
  png(file.path(fig_dir, paste0(t, ".png")), width = 900, height = 560)
  op <- par(mar = c(8, 4, 3, 1))
  bp <- barplot(sub$frecuencia, names.arg = sub$categoria, las = 2, col = "#3d5a40",
                ylab = "Frecuencia", main = paste0(t, " (n=27, CSV oficial, solo marginal)"))
  text(bp, sub$frecuencia, labels = sub$frecuencia, pos = 3, cex = 0.8, xpd = TRUE)
  par(op)
  dev.off()
}

out <- do.call(rbind, rows)
rownames(out) <- NULL
out$max_abs_media <- pmax(abs(out$r_media - out$jamovi_media), abs(out$r_media - out$jasp_media), abs(out$jamovi_media - out$jasp_media))
out$max_abs_de <- pmax(abs(out$r_de - out$jamovi_de), abs(out$r_de - out$jasp_de), abs(out$jamovi_de - out$jasp_de))
write.csv(out, file.path(out_dir, "validacion_csv_oficial.csv"), row.names = FALSE)

edad <- out[out$tabla == "edad", ]
esf <- out[out$tabla == "esfuerzo", ]
ok_num <- isTRUE(all.equal(round(edad$r_media, 2), 42.30)) &&
  isTRUE(all.equal(edad$r_mediana, 44)) && edad$moda_frecuencia == "33" &&
  isTRUE(all.equal(round(esf$r_media, 2), 2.93)) &&
  isTRUE(all.equal(esf$r_mediana, 3)) && esf$moda_frecuencia == "0"
ok_cross <- all(out$max_abs_media < 1e-9 & out$max_abs_de < 1e-9)
cat("CHECKS", ok_num, ok_cross, "\n")
print(out[, c("tabla", "r_media", "r_mediana", "moda_frecuencia", "r_de", "max_abs_media")])
if (!ok_num || !ok_cross) quit(status = 2)
quit(status = 0)
