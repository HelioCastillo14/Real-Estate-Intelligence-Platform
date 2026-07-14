# Feature 6.2.6 — Notebook 4 (M2: Quality Scorer) — Cierre

**Notebook:** `notebooks/04_m2_quality_scorer.ipynb`
**Fecha de cierre:** 2026-07-14
**Estado:** CERRADO
**Tipo:** Experimentación (no Entrenamiento — no aplica MAE ni Silhouette)

---

## 1. Qué construimos

Un scorer de calidad de anuncio basado en LLM que evalúa el texto de `descripcion` de cada
listing en 4 dimensiones (escala 1-5): completitud informativa, calidad de presentación/redacción,
diferenciadores/amenidades comunicados y transparencia de precio (con `price_usd` del scraper
provisto como contexto, incluso en filas `precio_no_evaluable`, porque la pregunta de M2.6 es
distinta a la de M2 KNN/RF — transparencia del texto, no plausibilidad de mercado).

## 2. Decisión de filtrado

A diferencia de 6.2.4/6.2.5 (M2 KNN/RF/KMeans), no excluimos `zona_no_determinada` ni
`precio_no_evaluable` — el Quality Scorer evalúa el texto del anuncio, no zona ni valor de mercado.
Única exclusión real: `descripcion_fuente == "ninguna"` (9 filas, 0.76% del catálogo, sin texto que
evaluar) — marcadas explícitamente como no evaluables, no forzadas a un score.

## 3. Muestra

Muestreo aleatorio simple, `n=150` sobre la población evaluable (`N=1,168`), semilla fija. Margen
de error ±7.5% (95% CI, `p=0.5`, con corrección por población finita) — aceptable para lectura
exploratoria de distribución, no para una decisión de producto.

## 4. Modelo LLM — 3 hallazgos, no un nombre asumido

1. **`gemini-2.5-flash`** (declarado en `CLAUDE.md`) devuelve `404 NOT_FOUND` ("no longer available
   to new users") pese a figurar en `client.models.list()` — esa lista no es fuente confiable de
   disponibilidad real, solo una llamada de prueba lo confirma. Mismo problema en
   `gemini-2.5-flash-lite` y `gemini-2.0-flash`.
2. El alias `gemini-flash-latest` responde, pero es móvil (Google puede reapuntarlo sin aviso) —
   inadecuado para citar. Resuelve (via `resp.model_version`) a `gemini-3.5-flash`
   (versión fija `3.5-flash-05-2026`), que usamos directamente en su lugar.
3. **Decisión final:** `gemini-3.5-flash` mostró disponibilidad degradada sostenida durante la
   ejecución real — no un corte puntual. Un lote completo de 25 llamadas de diagnóstico (con
   reintento corto ya aplicado) devolvió `503`/`504` en el 100% de los casos, sostenido a lo largo
   de varias horas en distintos momentos del día. Cambiamos a **`gemini-3-flash-preview`**
   (`version=3-flash-preview-12-2025`) como modelo final. **Limitación metodológica explícita:** es
   un modelo "preview", no GA — Google puede retirarlo o cambiar su comportamiento sin aviso.

`CLAUDE.md` debe actualizarse: el nombre de modelo NLP declarado (`gemini-2.5-flash`) ya no es
válido para llamadas reales en este proyecto.

## 5. Batch API del SDK — no usada, decisión verificada

`google-genai` 2.11.0 expone `client.batches.create()`, pero es un job asíncrono (no una forma de
agrupar requests síncronas de baja latencia) — incompatible con el ciclo de iteración de prompt de
este notebook. Se usó `generate_content` síncrono, una request por listing.

## 6. Iteración de prompt

- **v1** (texto libre, parseo manual con `json.loads` + recorte de fences): 25/25 = 100% válido
  contra el esquema en el diagnóstico final (bajo `gemini-3-flash-preview`; 23/25 en el intento
  anterior bajo condiciones de capacidad degradada).
- **v2 (final)**, salida estructurada del SDK (`response_mime_type="application/json"` +
  `response_schema=QualityScore`, `thinking_level=LOW` dado que es clasificación estructurada, no
  razonamiento multi-paso): 25/25 = 100% válido. Ambas por encima del umbral de 90%.
- La salida estructurada elimina la fuente de error más común de v1 (texto/fences alrededor del
  JSON) porque la validación de forma ocurre en la API; la validación Pydantic (rango 1-5) se
  mantiene igual en ambas versiones.

## 7. Resiliencia de la corrida — hallazgos operativos reales

- **429** (cuota propia): circuit breaker de 90s, un reintento, si vuelve a fallar se detiene la
  corrida y se reporta — sin backoff creciente agresivo.
- **503/504** (contención de capacidad del modelo, no cuota propia): un reintento corto (20s).
- **Errores de transporte** (`ConnectionResetError` sobre el socket): un reintento corto (5s).
- **Timeout de cliente explícito** (`http_options=types.HttpOptions(timeout=45_000)`): sin este
  timeout, el cliente hereda `timeout=None` de `httpx` — una conexión estancada cuelga
  indefinidamente (observamos un bloqueo de ~3 horas) en vez de fallar rápido hacia el reintento.
  **Convención para 6.2.7 y notebooks futuros: todo `genai.Client()` debe fijar timeout explícito.**
- **Checkpoint incremental en las 3 fases con API** (diagnóstico v1, diagnóstico v2, muestra
  completa), no solo en la corrida principal — evita repetir llamadas ya exitosas en cada
  relanzamiento. La primera versión del notebook solo checkpointeaba la muestra completa, lo que
  causó llamadas diagnósticas repetidas en varios relanzamientos.
  **Convención para 6.2.7 y notebooks futuros: checkpointear toda fase que llame a la API.**
- **Bug de checkpoint corregido durante la ejecución:** la lógica original saltaba cualquier
  entrada ya *intentada* (incluyendo fallos), lo que congelaba fallos transitorios como
  permanentes. Corregido para saltar solo entradas *válidas* — un fallo se reintenta en el
  siguiente relanzamiento, no se descarta para siempre.

## 8. Resultado — comparación entre modelos (contingencia de 6.2.6.4)

112 filas evaluadas con `gemini-3.5-flash`, 38 con `gemini-3-flash-preview` (columna `modelo` por
fila en el artifact). Comparamos media y desviación estándar de las 4 dimensiones entre ambos
subconjuntos antes de tratar la muestra como un solo grupo:

| Dimensión | Diferencia de media entre modelos |
|---|---|
| completitud_informativa | 0.05 |
| calidad_presentacion | 0.06 |
| diferenciadores_amenidades | 0.14 |
| transparencia_precio | 0.08 |

Ninguna dimensión supera el umbral de diferencia notable (0.5 en escala 1-5). **Conclusión:**
combinar ambos modelos en un solo análisis es metodológicamente razonable — no hay evidencia de que
el cambio de modelo a mitad de corrida introduzca un sesgo sistemático relevante en los resultados.
El Hallazgo 3 (modelo "preview") queda como limitación de reproducibilidad, no de validez.

## 9. Distribución de los 4 scores (n=150)

| Dimensión | Media | Desv. estándar |
|---|---|---|
| completitud_informativa | 4.57 | 0.73 |
| calidad_presentacion | 4.75 | 0.57 |
| diferenciadores_amenidades | 4.61 | 0.72 |
| transparencia_precio | 3.47 | 1.91 |

Transparencia de precio es la dimensión más baja y con mayor dispersión — consistente con que
varios listings del catálogo son anuncios de proyecto con múltiples modelos/precios (rango de
precios, no un precio único), lo que el prompt trata como menor claridad. Las otras 3 dimensiones
están concentradas hacia el extremo alto (mediana 5 en completitud, presentación y
diferenciadores), sugiriendo que el catálogo de inmopanama.com tiene, en general, descripciones
razonablemente completas y bien redactadas.

`completitud_informativa` y `diferenciadores_amenidades` correlacionan más fuerte entre sí (0.72)
que con `transparencia_precio` (0.57 y 0.40 respectivamente) — un anuncio con texto informativo
tiende a comunicar también sus diferenciadores, pero no necesariamente su precio con claridad.

## 10. % de casos no evaluables

- Sin texto de `descripcion` (catálogo completo): 9 / 1,177 = 0.76%.
- Fallos técnicos dentro de la muestra evaluada tras circuit breaker: 0 / 150 = 0%.

## 11. Artifacts

`pipeline/models/quality_scores_6_2_6_raw.pkl` — incluye `df_scores` (150 filas, columna `modelo`
por fila), modelo final y versión, tasas de parseo v1/v2, y la comparación de medias por modelo.
