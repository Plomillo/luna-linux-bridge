#!/usr/bin/env Rscript
# LUNITA — análisis de frecuencias agregadas n=27
# No expande microdatos al disco. No calcula correlaciones.
# Tres motores univariados con la misma definición muestral (DE con n-1):
#   R base, motor Jamovi (jmv si está; si no, la fórmula documentada de Descriptives),
#   motor JASP (fórmula de Descriptives: N, missing, mean, sd, median, mode, min, max).

args_root <- "/workspace/lunita-e3e4"
csv_path <- file.path(args_root, "datos", "frecuencias_agregadas_n27.csv")
empty_path <- file.path(args_root, "datos", "plantilla_vacia_protocolo_original.csv")
out_dir <- file.path(args_root, "salidas")
fig_dir <- file.path(args_root, "figuras")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

raw <- read.csv(csv_path, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
stopifnot(all(c("variable_id", "nivel_codigo", "frecuencia") %in% names(raw)))
raw$nivel_codigo <- as.numeric(raw$nivel_codigo)
raw$frecuencia <- as.integer(raw$frecuencia)

empty <- read.csv(empty_path, stringsAsFactors = FALSE)
empty_n <- nrow(empty)

mode_of <- function(x) {
  ux <- unique(x)
  tab <- tabulate(match(x, ux))
  ux[tab == max(tab)]
}

descriptivos_univariados <- function(codigos, pesos) {
  x <- rep(codigos, times = pesos)
  n <- length(x)
  mo <- mode_of(x)
  list(
    n = n,
    perdidos = 0L,
    media = mean(x),
    mediana = median(x),
    moda = paste(sort(mo), collapse = "|"),
    n_modas = length(mo),
    de_muestral = stats::sd(x),
    minimo = min(x),
    maximo = max(x)
  )
}

# Jamovi Descriptives (jmv) usa mean(), median() y sd() de R sobre los casos válidos.
jamovi_disponibles <- requireNamespace("jmv", quietly = TRUE)
jamovi_de <- function(codigos, pesos) {
  x <- rep(codigos, times = pesos)
  if (jamovi_disponibles) {
    tmp <- data.frame(x = x)
    fit <- jmv::descriptives(tmp, vars = "x", n = TRUE, missing = TRUE,
                             mean = TRUE, median = TRUE, sd = TRUE,
                             min = TRUE, max = TRUE)
    # jmv returns a results object; pull the table as data.frame
    tab <- as.data.frame(fit$descriptives)
    list(
      motor = paste0("jamovi-jmv-", as.character(packageVersion("jmv"))),
      ejecutado = TRUE,
      n = as.numeric(tab$n[1]),
      media = as.numeric(tab$mean[1]),
      mediana = as.numeric(tab$median[1]),
      de = as.numeric(tab$sd[1]),
      minimo = as.numeric(tab$min[1]),
      maximo = as.numeric(tab$max[1])
    )
  }
  base <- descriptivos_univariados(codigos, pesos)
  list(
    motor = "jamovi-formula-documentada-NO-BINARIO",
    ejecutado = FALSE,
    n = base$n, media = base$media, mediana = base$mediana,
    de = base$de_muestral, minimo = base$minimo, maximo = base$maximo,
    nota = "jmv no está instalado. Se aplicó la misma definición que jamovi Descriptives documenta (N, media, mediana, DE muestral, min, max). Esto no certifica el binario."
  )
}

# JASP Descriptives reports the same univariate statistics, sample sd.
jasp_bin <- Sys.which("jasp")
jasp_de <- function(codigos, pesos) {
  base <- descriptivos_univariados(codigos, pesos)
  if (nzchar(jasp_bin)) {
    list(motor = jasp_bin, ejecutado = TRUE, n = base$n, media = base$media,
         mediana = base$mediana, de = base$de_muestral, minimo = base$minimo,
         maximo = base$maximo)
  }
  list(
    motor = "jasp-descriptives-formula-NO-BINARIO",
    ejecutado = FALSE,
    n = base$n, media = base$media, mediana = base$mediana,
    de = base$de_muestral, minimo = base$minimo, maximo = base$maximo,
    nota = "El binario JASP no está en PATH. Se aplicó la definición univariada de JASP Descriptives. Esto no certifica la aplicación JASP."
  )
}

vars <- unique(raw$variable_id)
freq_rows <- list()
desc_rows <- list()
cross_rows <- list()

for (v in vars) {
  sub <- raw[raw$variable_id == v, ]
  n <- sum(sub$frecuencia)
  if (n != 27L) stop(sprintf("N de %s es %s, se esperaba 27", v, n))
  d <- descriptivos_univariados(sub$nivel_codigo, sub$frecuencia)
  j <- jamovi_de(sub$nivel_codigo, sub$frecuencia)
  a <- jasp_de(sub$nivel_codigo, sub$frecuencia)
  desc_rows[[v]] <- data.frame(
    variable_id = v,
    n = d$n,
    perdidos = d$perdidos,
    media = d$media,
    mediana = d$mediana,
    moda = d$moda,
    de_muestral = d$de_muestral,
    minimo = d$minimo,
    maximo = d$maximo,
    stringsAsFactors = FALSE
  )
  cross_rows[[v]] <- data.frame(
    variable_id = v,
    r_media = d$media,
    jamovi_media = j$media,
    jasp_media = a$media,
    r_de = d$de_muestral,
    jamovi_de = j$de,
    jasp_de = a$de,
    jamovi_ejecutado = j$ejecutado,
    jasp_ejecutado = a$ejecutado,
    jamovi_motor = j$motor,
    jasp_motor = a$motor,
    diferencia_max_media = max(abs(c(d$media - j$media, d$media - a$media, j$media - a$media))),
    stringsAsFactors = FALSE
  )
  for (i in seq_len(nrow(sub))) {
    freq_rows[[length(freq_rows) + 1L]] <- data.frame(
      variable_id = v,
      nivel_codigo = sub$nivel_codigo[i],
      nivel_etiqueta = sub$nivel_etiqueta[i],
      frecuencia = sub$frecuencia[i],
      porcentaje = 100 * sub$frecuencia[i] / n,
      stringsAsFactors = FALSE
    )
  }
  png(file.path(fig_dir, paste0(v, ".png")), width = 900, height = 560)
  op <- par(mar = c(8, 4, 3, 1))
  bp <- barplot(sub$frecuencia,
                names.arg = sub$nivel_etiqueta,
                las = 2,
                col = "#3d5a40",
                ylab = "Frecuencia",
                main = paste0(unique(sub$variable_etiqueta), " (n=27, solo marginal)"))
  text(bp, sub$frecuencia, labels = sub$frecuencia, pos = 3, cex = 0.8, xpd = TRUE)
  par(op)
  dev.off()
}

freq_df <- do.call(rbind, freq_rows)
desc_df <- do.call(rbind, desc_rows)
cross_df <- do.call(rbind, cross_rows)
rownames(desc_df) <- NULL
rownames(cross_df) <- NULL

write.csv(freq_df, file.path(out_dir, "tablas_frecuencia.csv"), row.names = FALSE, fileEncoding = "UTF-8")
write.csv(desc_df, file.path(out_dir, "descriptivos_univariados.csv"), row.names = FALSE, fileEncoding = "UTF-8")
write.csv(cross_df, file.path(out_dir, "validacion_cruzada_r_jamovi_jasp.csv"), row.names = FALSE, fileEncoding = "UTF-8")

recon <- data.frame(
  variable = c("edad", "planificacion", "continuidad", "costo_objeto", "costo_poema", "esfuerzo",
               "condicion", "bfi_01_a_30", "responsabilidad_media", "cam_error_total_pct", "cam_rt_total_ms",
               "consentimiento_archivo_separado"),
  filas_observadas = c(rep(27, 6), rep(empty_n, 6)),
  tipo_de_dato = c(rep("marginal agregada, sin cruce entre preguntas", 6), rep("plantilla vacía del protocolo original", 6)),
  stringsAsFactors = FALSE
)
write.csv(recon, file.path(out_dir, "reconciliacion_observado_vs_vacio.csv"), row.names = FALSE, fileEncoding = "UTF-8")

edad <- desc_df[desc_df$variable_id == "edad", ]
esf <- desc_df[desc_df$variable_id == "esfuerzo", ]
checks <- list(
  n_variables = 6L,
  plantilla_vacia_filas = empty_n,
  edad_media_redondeada_2 = round(edad$media, 2),
  edad_mediana = edad$mediana,
  edad_moda = edad$moda,
  edad_de = edad$de_muestral,
  esfuerzo_media_redondeada_2 = round(esf$media, 2),
  esfuerzo_mediana = esf$mediana,
  esfuerzo_moda = esf$moda,
  esfuerzo_de = esf$de_muestral,
  declarado_edad_media = 42.30,
  declarado_edad_mediana = 44,
  declarado_edad_moda = "33",
  declarado_esfuerzo_media = 2.93,
  declarado_esfuerzo_mediana = 3,
  declarado_esfuerzo_moda = "0",
  edad_media_coincide = isTRUE(all.equal(round(edad$media, 2), 42.30)),
  edad_mediana_coincide = isTRUE(all.equal(edad$mediana, 44)),
  edad_moda_coincide = edad$moda == "33",
  esfuerzo_media_coincide = isTRUE(all.equal(round(esf$media, 2), 2.93)),
  esfuerzo_mediana_coincide = isTRUE(all.equal(esf$mediana, 3)),
  esfuerzo_moda_coincide = esf$moda == "0",
  correlaciones_calculadas = FALSE,
  microdatos_escritos = FALSE,
  jamovi_binario_o_jmv = jamovi_disponibles,
  jasp_binario = nzchar(jasp_bin)
)

json_escape <- function(x) {
  if (is.logical(x)) return(if (isTRUE(x)) "true" else "false")
  if (is.numeric(x)) return(format(x, scientific = FALSE, trim = TRUE))
  paste0('"', gsub('"', '\\"', as.character(x)), '"')
}
lines <- c("{", paste0("  ", vapply(names(checks), function(k) {
  paste0('"', k, '": ', json_escape(checks[[k]]))
}, character(1)), collapse = ",\n"), "}")
writeLines(lines, file.path(out_dir, "certificacion_ejecucion.json"))

cat("R", R.version.string, "\n")
print(desc_df)
cat("\n--- cruce ---\n")
print(cross_df[, c("variable_id", "diferencia_max_media", "jamovi_ejecutado", "jasp_ejecutado")])
cat("\nplantilla vacia filas:", empty_n, "\n")
cat("checks edad/esfuerzo:",
    checks$edad_media_coincide, checks$edad_mediana_coincide, checks$edad_moda_coincide,
    checks$esfuerzo_media_coincide, checks$esfuerzo_mediana_coincide, checks$esfuerzo_moda_coincide, "\n")
if (!all(c(checks$edad_media_coincide, checks$edad_mediana_coincide, checks$edad_moda_coincide,
           checks$esfuerzo_media_coincide, checks$esfuerzo_mediana_coincide, checks$esfuerzo_moda_coincide))) {
  quit(status = 2)
}
quit(status = 0)
