#!/usr/bin/env Rscript
pkgs <- "/app/Modules/binary_pkgs"
lib <- "/tmp/jasp-r-lib"
unlink(lib, recursive = TRUE)
dir.create(lib, showWarnings = FALSE)
for (d in list.dirs(pkgs, recursive = FALSE, full.names = TRUE)) {
  desc <- file.path(d, "DESCRIPTION")
  if (!file.exists(desc)) next
  nm <- NA_character_
  for (line in readLines(desc, n = 8, warn = FALSE)) {
    if (startsWith(line, "Package: ")) nm <- sub("^Package: ", "", line)
  }
  if (!is.na(nm)) file.symlink(d, file.path(lib, nm))
}
.libPaths(c(lib, .libPaths()))
suppressPackageStartupMessages(library(jaspDescriptives))
fn <- get(".descriptivesDescriptivesTable_subFunction", envir = asNamespace("jaspDescriptives"))

root <- "/workspace/lunita-n39"
raw <- read.csv(file.path(root, "datos", "base_frecuencias_n39.csv"), stringsAsFactors = FALSE, check.names = FALSE)
raw$nivel <- as.numeric(raw$nivel)
raw$frecuencia <- as.integer(raw$frecuencia)

opts <- list(
  meanArithmetic = TRUE, sd = TRUE, seMean = FALSE, median = TRUE,
  mode = FALSE, minimum = TRUE, maximum = TRUE, valid = TRUE, missing = TRUE,
  meanGeometric = FALSE, meanHarmonic = FALSE, coefficientOfVariation = FALSE,
  mad = FALSE, madRobust = FALSE, iqr = FALSE, variance = FALSE, kurtosis = FALSE,
  skewness = FALSE, shapiroWilkTest = FALSE, sum = FALSE, range = FALSE,
  quartiles = FALSE, quantilesForEqualGroups = FALSE, percentiles = FALSE,
  meanCi = FALSE, sdCi = FALSE, varianceCi = FALSE, quantilesType = 7,
  splitBy = ""
)

rows <- lapply(unique(raw$n_pregunta), function(q) {
  sub <- raw[raw$n_pregunta == q, ]
  x <- rep(sub$nivel, times = sub$frecuencia)
  got <- fn(x, "scale", list(Variable = paste0("p", q)), opts, FALSE, FALSE, NULL)
  col <- got$resultsCol
  if (q == unique(raw$n_pregunta)[1]) {
    capture.output(str(col), file = file.path(root, "salidas", "jasp_col_str.txt"))
  }
  grab <- function(v) {
    if (is.null(v)) return(NA_real_)
    if (is.numeric(v) && !inherits(v, "vctrs_vctr")) return(as.numeric(v)[1])
    u <- unclass(v)
    if (is.list(u) && length(u) && !is.null(u[[1]]$value)) return(as.numeric(u[[1]]$value))
    NA_real_
  }
  data.frame(
    motor = "JASP-0.99-jaspDescriptives-0.96.5",
    n_pregunta = q,
    n = length(x),
    media = grab(col$MeanArithmetic),
    mediana = grab(col$Median),
    de = grab(col[["Std. Deviation"]]),
    minimo = grab(col$Minimum),
    maximo = grab(col$Maximum),
    stringsAsFactors = FALSE
  )
})
out <- do.call(rbind, rows)
dir.create(file.path(root, "salidas"), showWarnings = FALSE)
write.csv(out, file.path(root, "salidas", "descriptivos_jasp.csv"), row.names = FALSE)
print(out)
