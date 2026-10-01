# LUNA R4 — referencia visual y baseline KDE

Estado: `REFERENCE_ONLY / NOT_CANONICAL / NOT_CERTIFIED`.

Este directorio preserva dos artefactos autorizados por el propietario como referencia para la interfaz restante de LUNA R4:

1. `LUNA_R4_UI_REFERENCE_PARTS_1_9.jpg` — maqueta visual aprobada como referencia estética de las partes 1–9.
2. `KDE_UI_REFERENCE_20260929T020349Z.7z` — snapshot de configuración/estado visual de KDE utilizado como baseline estructural.

## Alcance

- No modifica `Louksna.md`.
- No transfiere autoridad canónica.
- No concede G23/G24.
- No declara pixel-perfect la maqueta.
- La imagen conserva la tonalidad y organización aprobadas; el fondo de pantalla del equipo no debe sustituirse por esta referencia.
- El snapshot KDE sirve para derivar paneles, temas, geometría, widgets, KWin, KScreen y configuración visual reproducible.

## Identidades esperadas

- Imagen de referencia:
  - SHA-256: `8a9852c4155d64fd74059c7239e67c82e16e5acd556627d70575db85078d4ed4`
  - bytes: `374879`
  - formato real: JPEG
- Snapshot KDE:
  - SHA-256: `c21e04d5447e123b59fc9b94d2e9684bc03ea164999ef6f60210e257557a16dc`
  - bytes observados en la copia de conversación: `281114`
  - nombre: `KDE_UI_REFERENCE_20260929T020349Z.7z`

El workflow `.github/workflows/r4-ui-reference-import.yml` reconstruye la imagen desde transporte base64, toma el snapshot KDE de solo lectura desde el escritorio del runner LOUKSNA, verifica ambos SHA-256 y únicamente entonces los incorpora a esta rama junto con evidencia.

Doctrina: `EVIDENCE_FIRST / FAIL_CLOSED / NO_SILENT_OPERATIONS / EXTEND_DO_NOT_REPLACE`.

## Referencia física en el servidor

Además de la copia versionada en GitHub, la referencia debe estar materializada en el host LOUKSNA bajo:

```text
/home/diegoignacionorambuenamiranda/Descargas/LUNA_R4_UI_REFERENCE/
```

Contenido esperado:

- `LUNA_R4_UI_REFERENCE_PARTS_1_9.jpg`
- `KDE_UI_REFERENCE_20260929T020349Z.7z`
- `REFERENCE_MANIFEST.json`
- `README.md`
- `LOCAL_REFERENCE_MANIFEST.json`

La copia física es una referencia operativa local, no una nueva autoridad. Debe coincidir por SHA-256 con los artefactos versionados en esta rama. Cualquier divergencia produce `HOLD` y no debe sobreescribirse silenciosamente.
