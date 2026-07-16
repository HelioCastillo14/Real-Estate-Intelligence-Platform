# Escalamiento del Quality Scorer (6.2.6) al catálogo completo — batch de producción

**Script:** `pipeline/scripts/escalar_quality_scorer_6_2_6.py`
**Estado:** CERRADO — catálogo completo evaluado, 0 filas fallidas
**Fecha de inicio:** 2026-07-14 · **Fecha de cierre:** 2026-07-15

---

## 1. Qué es esto

Job de batch de producción, corre una sola vez sobre el catálogo estático completo
(1,168 filas evaluables de `catalogo_residencial_limpio_6_2_1.csv`). No es un notebook de
Feature 6.2 (ya cerrada) — reutiliza su metodología (rúbrica de 4 dimensiones, prompt v2
estructurado, checkpoint incremental, circuit breaker diferenciado por tipo de error, timeout
explícito de 45s), documentada en `Context-MD/Feature_6_2_6_M2_QualityScorer_Cierre.md`.

Decisión de alcance (confirmada antes de lanzar): re-evaluación completa desde cero, no reutiliza
los 150 scores mixtos de 6.2.6 (job de experimentación).

## 2. Cambio de modelo a mitad de corrida (2026-07-15)

**Modelo inicial:** `gemini-3.5-flash` (GA). Verificado en vivo antes de lanzar: 23/25 (92%) de
éxito en frío, 2/25 fallos por `503 UNAVAILABLE` — no era el 100% de fallo sostenido que forzó el
cambio de modelo en 6.2.6, así que se decidió proceder con `gemini-3.5-flash` confiando en el
circuit breaker de 503/504 para absorber la contención transitoria.

**Diagnóstico de ritmo (2026-07-15):** tras ~9h40m, el batch solo había llegado a 565/1,168 filas
(529 válidas, 36 fallidas por 503/504 y errores de transporte). Diagnóstico realizado antes de
tocar el proceso:
- Ritmo medido en vivo (ventana de 5 min, no estimado): ~1.8 filas/min, vs. ~13-26 filas/min
  esperadas según el diagnóstico en frío original.
- Timeout explícito confirmado en el código real (`http_options=types.HttpOptions(timeout=45_000)`,
  no asumido por herencia).
- Pacing (`time.sleep(1)` entre llamadas) confirmado idéntico al usado en el diagnóstico que sí
  rindió bien — descarta pausa mal calibrada como causa.
- Proceso confirmado activo (checkpoint escribiéndose, conexión TCP `ESTABLISHED`), no colgado.
- **Conclusión:** degradación de latencia sostenida del lado del proveedor para
  `gemini-3.5-flash`, no un bug de código. Punto ciego identificado: el checkpoint no guarda
  timestamp por fila, así que no se pudo aislar con precisión si la desaceleración fue progresiva
  o constante a lo largo de las 9h40m — queda anotado para agregar en cualquier corrida futura.

**Validación de equivalencia (justificación del cambio, misma convención exigida en 6.2.7 para
M3):** `pipeline/models/validacion_equivalencia_3_1_flash_lite_vs_3_5_flash.pkl` — 25 listings ya
evaluados por `gemini-3.5-flash` en el checkpoint del batch, re-evaluados con
`gemini-3.1-flash-lite` (confirmado disponible en vivo antes de la validación). Resultado:

| Dimensión | Diff. de medias | Diff. abs. máxima/fila | % filas con diff >1pt |
|---|---|---|---|
| completitud_informativa | 0.08 | 1 | 0.0% |
| calidad_presentacion | 0.00 | 1 | 0.0% |
| diferenciadores_amenidades | 0.24 | 1 | 0.0% |
| transparencia_precio | 0.04 | 1 | 0.0% |

Ninguna dimensión supera el umbral de 0.5 en diferencia de medias (convención de "diferencia
notable" ya usada en 6.2.6). **Esto no es una sustitución silenciosa de modelo** — se exigió y
aprobó con la misma validación de equivalencia ya usada en 6.2.7 para el cambio de modelo de M3.

**Ejecución del cambio:** proceso original (PID 18340) detenido con `SIGTERM` (no destructivo) el
2026-07-15. Checkpoint verificado íntegro y cargable tras detener el proceso: 565 filas, 529
válidas, 36 fallidas, todas etiquetadas `gemini-3.5-flash`. Script editado (`MODELO_LLM =
"gemini-3.1-flash-lite"`) y relanzado apuntando al mismo archivo de checkpoint — el checkpoint por
fila ya registraba `modelo` desde el diseño original del script, así que el relanzamiento no
reevalúa las 565 filas ya hechas, solo continúa con las pendientes (incluyendo reintento de las 36
previamente fallidas) bajo el nuevo modelo. Timeout explícito y circuit breaker (429/503/504/
transporte) confirmados como código genérico, no específico de modelo — se heredan automáticamente
al nuevo modelo sin cambios adicionales.

## 3. Resultado final

Catálogo completo evaluado: **1,168 / 1,168 filas evaluables, 0 fallidas.** (1,177 filas totales
del catálogo − 9 sin texto de `descripcion`, no evaluables por diseño desde 6.2.6.)

**Distribución de filas por modelo:**

| Modelo | Filas |
|---|---|
| `gemini-3.5-flash` | 529 |
| `gemini-3.1-flash-lite` | 639 |
| **Total** | **1,168** |

Tras el cambio de modelo, las 36 filas que habían quedado fallidas bajo `gemini-3.5-flash`
(503/504 y errores de transporte) se reintentaron automáticamente por el mismo checkpoint y
completaron sin fallos bajo `gemini-3.1-flash-lite` — 0 filas fallidas en el resultado final.
El ritmo también mejoró notablemente tras el cambio (de ~1.8 filas/min medido en vivo con
`gemini-3.5-flash` a un ritmo sostenido que completó las ~600 filas restantes en un tiempo mucho
menor), consistente con el diagnóstico de latencia degradada del §2.

**Distribución de scores (1,168 filas, escala 1-5):**

| Dimensión | Media | Desv. estándar |
|---|---|---|
| completitud_informativa | 4.66 | 0.67 |
| calidad_presentacion | 4.73 | 0.61 |
| diferenciadores_amenidades | 4.51 | 0.84 |
| transparencia_precio | 3.68 | 1.81 |

(Ver `pipeline/models/quality_scores_produccion_final.csv` para la distribución completa de las 4
dimensiones y los metadatos por fila — corregimiento, tipo_inmueble, price_usd,
descripcion_fuente, modelo.)

**`modelos_por_fila` y `justificacion_mezcla_de_modelos` quedan embebidos directamente en el
artifact** (`quality_scores_produccion_final.pkl`), no solo en este documento — trazabilidad a
nivel de dato, no solo de documentación.

### 3.1 Nota de interpretación — `transparencia_precio` es bimodal, no dispersa (2026-07-15)

`transparencia_precio` no sigue una distribución continua como las otras 3 dimensiones —
`value_counts()` sobre las 1,168 filas muestra dos picos marcados y casi nada en el medio:

| Score | Filas | % |
|---|---|---|
| 1 | 315 | 27.0% |
| 2 | 85 | 7.3% |
| 3 | 13 | 1.1% |
| 4 | 6 | 0.5% |
| 5 | 749 | 64.1% |

**Investigación de causa (no se dejó como número agregado sin explicar, mismo estándar que 6.2.6
para esta misma dimensión):** se comparó el grupo bajo (score=1, n=315) contra el grupo alto
(score=5, n=749) sobre `precio_no_evaluable`, `descripcion_fuente`, longitud de texto, modelo LLM
usado, y presencia literal de lenguaje de precio en `descripcion`.

- **`precio_no_evaluable`**: 3.8% del grupo bajo vs. 0.0% del grupo alto — sobrerrepresentado pero
  explica solo 12/315 filas, no la mayoría.
- **`descripcion_fuente == "preview"`** (texto corto): 8.6% del grupo bajo vs. 0.5% del grupo
  alto — sobrerrepresentado pero también minoritario (27/315).
- **Modelo LLM usado** (gemini-3.5-flash vs. gemini-3.1-flash-lite): proporción similar a la
  distribución global en ambos grupos — no es un artefacto del cambio de modelo documentado en §2.
- **Causa dominante, confirmada sobre las filas con `descripcion_fuente == "completa"` (texto
  completo, no corto):** el grupo bajo menciona `$` literalmente en solo **7.6%** de los casos y
  la palabra "precio" en **18.1%**, contra **93.7%** y **81.3%** respectivamente en el grupo alto.
  Inspección manual de ejemplos del grupo bajo confirma que son descripciones **completas, bien
  redactadas y detalladas** (área, distribución de ambientes, amenidades del edificio) que
  **simplemente nunca mencionan el precio en el texto** — aunque `price_usd` sí existe como dato
  estructurado separado capturado por el scraper (ej. listing 143196: `price_usd=200000`, texto
  completo sobre distribución y amenidades, cero menciones de precio).

**Conclusión:** esto no es ruido de la evaluación del LLM — es una señal real y binaria en el
contenido del catálogo, exactamente el criterio que la rúbrica de 6.2.6 define como baja
transparencia ("un texto que no menciona precio en absoluto, cuando se te da un precio de
referencia, es baja transparencia aunque el resto del anuncio sea bueno"). Los agentes/anunciantes
de inmopanama.com se dividen de forma casi binaria entre "escriben el precio en la descripción" y
"no lo escriben en absoluto" (aunque el precio sí está disponible en otro campo de la página, de
donde lo capturó el scraper) — hay muy pocos casos intermedios (parciales/ambiguos, solo 8.9% del
catálogo en scores 2-4). Es una observación real sobre el mercado, útil como señal potencial (ej.
para UX de listings o para el propio scorer), no un defecto a corregir en el prompt ni en el
modelo.

### 3.2 Decisión de UI pendiente — nota aclaratoria en el desglose de "Confiabilidad del anuncio"
(NO implementado, solo documentado — 2026-07-15)

**Gap identificado (mismo tipo de nota ya dejada para el frontend con el bloque "¿Por qué X% de
compatibilidad?" de M1, ver `Context-MD/WBS_Pendiente_Epicas_2_3_4.md`, tarea 2.2.4):** el
hallazgo de §3.1 tiene una implicación de producto, no solo de interpretación de datos. Cuando el
frontend muestre el desglose por dimensión del Quality Scorer (score de "Confiabilidad del
anuncio"), un `transparencia_precio` bajo (1/5, 27.0% del catálogo) **no significa que el precio
sea sospechoso o poco confiable** — `price_usd` existe como dato estructurado capturado
directamente por el scraper, independiente de si el anunciante lo escribió en el texto del
anuncio. Sin una aclaración explícita en la UI, un usuario puede leer "1/5 en transparencia de
precio" como una señal de alerta genuina sobre el precio mismo, cuando en realidad mide únicamente
un patrón de redacción del anunciante (no menciona el precio en el copy).

**Pendiente de decidir en el diseño del componente de UI que consuma este score:** ¿el desglose
por dimensión debe incluir una nota aclaratoria específica cuando `transparencia_precio` sale bajo,
indicando explícitamente que `price_usd` sí está disponible como dato estructurado confiable
aunque el anuncio no lo mencione en el texto? No se implementa nada de esto todavía — queda como
decisión abierta para cuando se diseñe ese componente (candidato natural para agregarse al mismo
WBS de gaps de frontend donde ya vive el gap de M1, `Context-MD/WBS_Pendiente_Epicas_2_3_4.md`).

## 4. Artifacts

- `pipeline/models/quality_scores_produccion_checkpoint.pkl` — checkpoint incremental por fila
  (`score`, `error`, `modelo`).
- `pipeline/models/quality_scores_produccion_final.pkl` / `.csv` — artifact final, generado solo
  al completar el 100% del catálogo evaluable. Incluye `modelos_por_fila` (conteo exacto) y
  `justificacion_mezcla_de_modelos` (referencia a la validación de equivalencia).
- `pipeline/models/validacion_equivalencia_3_1_flash_lite_vs_3_5_flash.pkl` — validación de
  equivalencia entre modelos que justifica la mezcla.
