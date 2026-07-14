# Feature 6.2.3 — Notebook 1 (M1: Preference Matching) — Cierre

**Notebook:** `notebooks/01_m1_preference_matching.ipynb`
**Fecha de cierre:** 2026-07-13
**Estado:** CERRADO

---

## 1. Qué construimos

Un conjunto de referencia sintético (6 perfiles de lifestyle, sin datos de usuario real
disponibles en el proyecto) para evaluar Precision@k del scorer híbrido de M1, y el propio
scorer híbrido evaluado contra ese conjunto.

## 2. Modelo de embeddings

`gemini-embedding-001`, confirmado contra la API real (no asumido de documentación) — 3072
dimensiones. `text-embedding-004` (nombre usado en versiones anteriores de la documentación
pública de Gemini) ya no existe en esta API.

## 3. Scorer híbrido — configuración final

**0.6 estructurado / 0.4 semántico**, sin cambios respecto al valor original de `CLAUDE.md`.
Un sensitivity sweep de 5 combinaciones de peso (1.0/0.0, 0.8/0.2, 0.7/0.3, 0.6/0.4, 0.5/0.5)
confirmó que ningún ajuste fino en el rango 0.2-0.4 de peso semántico cambia el resultado —
mantener 0.6/0.4 es una decisión informada, no un default sin verificar.

## 4. Resultado — lift promedio del componente semántico (híbrido vs. solo-estructurado)

| k | Lift promedio |
|---|---|
| P@3 | -0.000 |
| P@5 | -0.067 |
| P@10 | -0.083 |

**El promedio agregado es engañoso si se lee solo.** El efecto real es heterogéneo por perfil:

- **2 perfiles con ganancia clara y consistente en las 3 métricas:** `retirado_tranquilidad`
  (lift de hasta +1.0 en P@3) e `inversionista_renta_corta` (lift positivo en P@3/P@5/P@10).
- **1 perfil con limitación documentada, no una falla sin explicar:** `profesional_joven` cae de
  un baseline solo-estructurado sólido (0.9 en P@10) a 0.000 en las 3 métricas con el componente
  semántico activo. Causa raíz diagnosticada con evidencia (no supuesta): el embedding correlaciona
  con la riqueza del copy de marketing, y en este catálogo las propiedades con copy más elaborado
  resultan ser sistemáticamente las mismas que se anuncian también para renta corta/Airbnb. La
  regla de exclusión de `profesional_joven` (necesaria para diferenciarlo de
  `inversionista_renta_corta`) separa artificialmente dos audiencias que el propio texto del
  anuncio no separa limpiamente — es una observación real sobre el mercado, no solo una falla del
  método de keywords.
- **3 perfiles cercanos a neutro o con patrones mixtos por k**, sin una lectura única dominante.

## 5. Limitación conocida y dirección de trabajo futura (no implementada en 6.2.3)

La regla de exclusión por palabra clave (`"renta corta"`, `"airbnb"`) es una señal frágil para
separar audiencias objetivo. La solución no es ajustar el peso del scorer (el sweep ya descarta
eso) — es reemplazar la keyword de exclusión por una etiqueta estructurada de audiencia objetivo,
extraída con un criterio más robusto que coincidencia de substring. El Quality Scorer (6.2.6,
basado en LLM) es un candidato natural para generar esa etiqueta en una iteración futura, dado que
ya está diseñado para leer texto libre de listings. Queda anotado como próximo paso lógico, no
como tarea abierta de 6.2.3.

## 6. Artifacts

`pipeline/models/embeddings_catalogo_6_2_3_raw.pkl` (1,110 vectores, 3072-dim) y
`pipeline/models/embeddings_perfiles_6_2_3_raw.pkl` (6 vectores) — no en ruta temporal, reusables
sin volver a llamar la API.

## 7. Nota operativa — cuota de la API de embeddings

La generación de embeddings sobre el catálogo completo requirió activar facturación de pago
(crédito prepago, sin recarga automática) — el plan gratuito de `gemini-embedding-001` no alcanzó
para procesar el volumen del catálogo en una sesión, incluso con pacing conservador (lotes
pequeños, pausas entre lotes). Relevante para cualquier notebook futuro que dependa de esta misma
API (6.2.6, 6.2.7).
