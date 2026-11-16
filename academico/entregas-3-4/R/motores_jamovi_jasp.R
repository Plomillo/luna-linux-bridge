#!/usr/bin/env Rscript
# Ejecuta el motor de descriptivos de jamovi (jmv 2.8.0) y las funciones
# de descriptivos de JASP (jaspDescriptives, archivo upstream) sobre las
# mismas marginales. No es la interfaz gráfica. No calcula correlaciones.

root <- "/workspace/lunita-e3e4"
raw <- read.csv(file.path(root, "datos/frecuencias_agregadas_n27.csv"),
                stringsAsFactors = FALSE, fileEncoding = "UTF-8")
raw$nivel_codigo <- as.numeric(raw$nivel_codigo)
raw$frecuencia <- as.integer(raw$frecuencia)

suppressPackageStartupMessages(library(jmvcore))
sys.source("/tmp/jmvsrc/jmv/R/descriptives.h.R", envir = globalenv())
sys.source("/tmp/jmvsrc/jmv/R/descriptives.b.R", envir = globalenv())
source("/tmp/jasp_descriptives.R")

jmv_ver <- "2.8.0"
jasp_src <- "/tmp/jasp_descriptives.R"

opts <- list(
  meanArithmetic = TRUE, sd = TRUE, seMean = FALSE, median = FALSE, mode = FALSE,
  minimum = FALSE, maximum = FALSE, valid = TRUE, missing = TRUE,
  meanGeometric = FALSE, meanHarmonic = FALSE, coefficientOfVariation = FALSE,
  mad = FALSE, madRobust = FALSE, iqr = FALSE, variance = FALSE, kurtosis = FALSE,
  skewness = FALSE, shapiroWilkTest = FALSE, sum = FALSE, range = FALSE,
  quartiles = FALSE, quantilesForEqualGroups = FALSE, percentiles = FALSE,
  meanCi = FALSE, sdCi = FALSE, varianceCi = FALSE, quantilesType = 7
)

rows <- list()
for (v in unique(raw$variable_id)) {
  sub <- raw[raw$variable_id == v, ]
  x <- rep(sub$nivel_codigo, times = sub$frecuencia)
  stopifnot(length(x) == 27L)

  fit <- descriptives(
    data.frame(x = x), vars = "x",
    freq = FALSE, hist = FALSE, dens = FALSE, bar = FALSE, box = FALSE,
    violin = FALSE, dot = FALSE, qq = FALSE,
    mean = TRUE, median = TRUE, sd = TRUE, min = TRUE, max = TRUE,
    n = TRUE, missing = TRUE
  )
  tab <- as.data.frame(fit$descriptives)
  # columnas del objeto jmv: x[n], x[mean], ...
  pick <- function(suffix) as.numeric(tab[[paste0("x[", suffix, "]")]][1])

  jasp <- .descriptivesDescriptivesTable_subFunction(
    x, "scale", list(Variable = v), opts, FALSE, FALSE, NULL
  )$resultsCol
  jasp_median <- as.numeric(.descriptivesMedian(x, list(quantilesType = 7), identity))

  r_mean <- mean(x)
  r_sd <- sd(x)
  r_med <- median(x)
  jam_mean <- pick("mean")
  jam_sd <- pick("sd")
  jam_med <- pick("median")
  jasp_mean <- as.numeric(jasp$MeanArithmetic)
  jasp_sd <- as.numeric(jasp[["Std. Deviation"]])

  rows[[v]] <- data.frame(
    variable_id = v,
    n = length(x),
    r_media = r_mean, jamovi_media = jam_mean, jasp_media = jasp_mean,
    r_de = r_sd, jamovi_de = jam_sd, jasp_de = jasp_sd,
    r_mediana = r_med, jamovi_mediana = jam_med, jasp_mediana = jasp_median,
    max_abs_media = max(abs(c(r_mean - jam_mean, r_mean - jasp_mean, jam_mean - jasp_mean))),
    max_abs_de = max(abs(c(r_sd - jam_sd, r_sd - jasp_sd, jam_sd - jasp_sd))),
    stringsAsFactors = FALSE
  )
  cat(v, "dmedia", rows[[v]]$max_abs_media, "dde", rows[[v]]$max_abs_de, "\n")
}

out <- do.call(rbind, rows)
rownames(out) <- NULL
dir.create(file.path(root, "salidas"), showWarnings = FALSE)
write.csv(out, file.path(root, "salidas/validacion_cruzada_motores_reales.csv"),
          row.names = FALSE)
ok <- all(out$max_abs_media < 1e-9 & out$max_abs_de < 1e-9)
cat("CONCORDANCIA", ok, "\n")
cat("jmv", jmv_ver, "jasp_src", jasp_src, "\n")
if (!ok) quit(status = 2)
quit(status = 0)
