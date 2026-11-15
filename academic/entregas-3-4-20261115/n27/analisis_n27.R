# Frecuencias agregadas n=27. No fabrica personas ni cruza variables.
edad <- c(18,19,19,26,28,31,32,33,33,33,34,39,43,44,44,45,47,48,50,50,55,57,59,61,63,65,66)
esfuerzo <- c(rep(0,9),rep(1,2),rep(2,2),rep(3,4),4,rep(5,5),6,rep(8,2),10)
stopifnot(length(edad)==27, length(esfuerzo)==27)
cat("edad_media", round(mean(edad),2), "mediana", median(edad), "DE", round(sd(edad),2), "\n")
cat("esfuerzo_media", round(mean(esfuerzo),2), "mediana", median(esfuerzo), "DE", round(sd(esfuerzo),2), "\n")
moda <- function(x) { t <- table(x); as.numeric(names(t)[which.max(t)]) }
cat("moda_edad", moda(edad), "moda_esfuerzo", moda(esfuerzo), "\n")
tabs <- list(
  planificacion=c(0,0,6,7,14),
  continuidad=c(2,4,6,10,5),
  objeto=c(3,10,8,4,2),
  poema=c(19,4,1,1,2)
)
for (nm in names(tabs)) {
  f <- tabs[[nm]]
  stopifnot(sum(f)==27)
  cat(nm, "pct", round(100*f/27,1), "suma_pct", sum(round(100*f/27,1)), "\n")
}
cat("Correlaciones: no calculadas. Faltan respuestas emparejadas.\n")
