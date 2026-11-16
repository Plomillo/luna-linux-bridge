# Análisis descriptivo univariado visible en RStudio.
# Los 234 registros son expansión de frecuencias marginales:
# 39 por pregunta, sin emparejamiento entre preguntas.
args <- commandArgs(trailingOnly = TRUE)
workspace <- Sys.getenv("GITHUB_WORKSPACE", unset = getwd())
csv <- if (length(args)) args[[1]] else file.path(workspace, "academico", "entregas-3-4", "n39", "datos", "base_expandida_marginal_n39.csv")
datos <- read.csv(csv, check.names = FALSE, fileEncoding = "UTF-8-BOM", stringsAsFactors = FALSE)
stopifnot(nrow(datos) == 234L, length(unique(datos$pregunta_id)) == 6L)

resumen <- do.call(rbind, lapply(split(datos, datos$pregunta_id), function(d) {
  x <- d$respuesta_valor
  data.frame(
    Pregunta = paste0("P", d$pregunta_id[1]),
    N = length(x),
    Media = mean(x),
    Mediana = median(x),
    Moda = as.numeric(names(sort(table(x), decreasing = TRUE))[1]),
    DE = sd(x),
    Minimo = min(x),
    Maximo = max(x),
    Q1 = unname(quantile(x, .25)),
    Q3 = unname(quantile(x, .75))
  )
}))
rownames(resumen) <- NULL
print(resumen, digits = 4)

nombres <- c(
  "Edad",
  "Planificacion",
  "Continuidad_atencional",
  "Dificultad_objeto",
  "Comprension_poema",
  "Esfuerzo"
)
op <- par(mfrow = c(2, 3), mar = c(4, 4, 3, 1), oma = c(0, 0, 1, 0))
for (i in seq_along(nombres)) {
  d <- datos[datos$pregunta_id == i, ]
  tab <- table(d$respuesta_valor)
  barplot(tab, main = nombres[i], xlab = "Respuesta", ylab = "Frecuencia",
          col = "steelblue", border = NA, las = 1)
  mtext(paste0("N = ", length(d$respuesta_valor)), side = 3, line = .1, cex = .75)
}
par(op)
