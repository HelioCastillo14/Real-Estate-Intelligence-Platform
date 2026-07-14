# REIP — Contexto para Claude Code

**Real Estate Intelligence Platform | Tesis, Universidad Tecnológica de Panamá — Curso 0698**

Este archivo existe porque el repo no tenía contexto de features para agentes de código.
Se actualiza cada vez que se cierra una decisión formal en una Acta. Si algo aquí contradice
una Acta más reciente, **la Acta gana** — pero avísale al equipo, porque significa que este
archivo quedó desactualizado.

No inventes decisiones de scope, cobertura de zonas, o metodología que no estén aquí.
Si una tarea requiere una decisión que no está documentada, pregunta antes de asumir.

---

## Stack

- **DB:** Supabase (PostgreSQL + PostGIS + pgvector) — `ezutrurenerqgfmozbzz.supabase.co`
- **Backend:** FastAPI, deploy en Railway (`real-estate-intelligence-platform-production.up.railway.app`)
- **Frontend:** Next.js 14 + MapLibre GL JS, deploy en Vercel
- **Pipeline:** Python (Miniconda/venv, Mac/zsh)
- **Notebooks (Feature 6.2):** entorno propio `notebooks/venv` (sibling de `pipeline/venv` y
  `backend/venv`), kernel Jupyter `reip-notebooks`. Es el entorno oficial para los 7 notebooks de
  análisis/entrenamiento — no usar `pipeline/venv` para notebooks nuevos (ver nota abajo).
- **NLP:** ~~Gemini 2.5 Flash~~ **desactualizado (hallazgo 6.2.6, 2026-07-14): `gemini-2.5-flash`
  devuelve 404 "no longer available to new users" pese a figurar en `client.models.list()` — esa
  lista no es fuente confiable de disponibilidad, solo una llamada de prueba real lo confirma.**
  En 6.2.6 (Quality Scorer) se usó `gemini-3-flash-preview` (`version=3-flash-preview-12-2025`)
  tras degradación de disponibilidad sostenida de `gemini-3.5-flash` (100% de fallo en un lote
  diagnóstico de 25 llamadas). **No se hereda esa decisión sin comprobarla de nuevo en cada
  notebook posterior — la disponibilidad de un modelo Gemini es una condición del momento de
  ejecución, no una garantía permanente.** En 6.2.7 (M3 NLP Orchestration), el mismo lote
  diagnóstico de 25 llamadas contra `gemini-3.5-flash` dio 100% de éxito — **modelo usado
  actualmente en 6.2.7: `gemini-3.5-flash` (GA, id fijo)**, no el "preview" de 6.2.6. Cualquier
  notebook futuro que dependa de la API debe repetir esta verificación real, no asumir el
  resultado de la corrida más reciente. `GEMINI_API_KEY` generado 2026-07-13 — ya no bloquea
  M3/embeddings. **Modelo de embeddings de M1 confirmado contra
  la API real:** `gemini-embedding-001` (3072 dimensiones). `text-embedding-004` (nombre de
  versiones anteriores de la documentación pública de Gemini) ya no existe en esta API — devuelve
  404, no usar esa referencia.
- **Monorepo:** `backend/`, `frontend/`, `pipeline/` como carpetas hermanas. Rama activa: `dev`.

## Módulos (nombres técnicos aprobados — no usar nombres previos deprecados)

- **M1 — Preference Matching Module:** matching lifestyle-propiedad, embeddings semánticos + scoring híbrido estructurado/semántico (0.6/0.4)
- **M2 — Property Valuation Engine:** evaluación multidimensional (no solo forecasting) — KNN semáforo de precio, KMeans segmentación, Random Forest como comparación metodológica, LLM Quality Scorer
- **M3 — NLP Orchestration Layer:** orquesta M1 y M2 vía Gemini, no escanea listings directamente

**Cadena de dependencia dura:** Data Pipeline → M1, M2 → M3. No desarrollar M3 antes de que M1/M2 sean funcionales.

## Zonas del scope — 9 nombres, pero solo 5 son corregimientos administrativos reales

Reales (tienen `geom` propio, extracción independiente de SIEC/INEC/GTFS):
San Francisco, Bella Vista, Parque Lefevre, Betania, Pedregal.

Sin `geom` propio, heredan Zone Health de su corregimiento contenedor:
- El Cangrejo, Marbella, Obarrio → heredan de **Bella Vista** (las 5 dimensiones)
- Costa del Este → **NO hereda de nada** (ver decisión abajo). Tiene amenidades propias
  reales (24 POIs, Google Places), pero ningún score compuesto.

## Feature 6.2 — Notebooks de análisis y entrenamiento (actualizado 2026-07-13)

- **Entorno:** `notebooks/venv` es el entorno oficial para los 7 notebooks (0, 0B, 1-5), con
  `notebooks/requirements.txt` propio (pandas, jupyter/ipykernel, matplotlib, seaborn,
  scikit-learn, `google-genai`/`python-dotenv` para 6.2.6-6.2.7). Kernel Jupyter: `reip-notebooks`.
  `pipeline/venv` tiene las mismas librerías instaladas por una decisión de sesión anterior — es un
  remanente, no se retira (por si el scraper depende indirectamente de algo ahí), pero **no se usa
  para notebooks nuevos**.
- **Convención de artifacts de M1/M2 nueva:** `pipeline/models/` (no existía antes de 6.2.1) — los
  notebooks de entrenamiento (6.2.3, 6.2.4, 6.2.5) exportan sus `.pkl`/serializados ahí.
- **Notebook 0 (6.2.1), CERRADO:** catálogo consolidado de los 9 archivos de `pipeline/data/raw/`
  reveló 184 registros duplicados cross-file (Bella Vista se solapa con El Cangrejo/Obarrio/Marbella).
  Cifra operativa: 1,177 filas, de las cuales 1,124 tienen `corregimiento` resuelto (53 quedan
  `zona_no_determinada`, documentadas para revisión manual). Enriquecimiento de `tipo_inmueble` +
  `descripcion` ejecutado sobre el catálogo completo (`pipeline/scraper/enriquecer_detalle.py`) —
  "comparable" en M2 usa `corregimiento + tipo_inmueble`, ya no degradado a solo corregimiento.
  Detalle completo en `Context-MD/Acta_1.2_Adenda_Duplicados.md`.
- **Notebook 0B (6.2.2), CERRADO:** Zone Health Composite Index reproducido desde los módulos de
  producción de `pipeline/zone_health/`, sin recomputar la fórmula. Detalle en `Context-MD/`.
- **Notebook 1 (6.2.3), CERRADO:** M1 Preference Matching, scorer híbrido 0.6 estructurado / 0.4
  semántico (`gemini-embedding-001`, 3072-dim). Detalle completo, incluyendo limitación conocida y
  próximo paso lógico para el Quality Scorer (6.2.6), en
  `Context-MD/Feature_6_2_3_M1_Preference_Matching_Cierre.md`. **Nota operativa para 6.2.6/6.2.7:**
  el plan gratuito de la API de Gemini para embeddings no alcanza para volumen de catálogo completo
  — se activó facturación de pago (crédito prepago, sin recarga automática).
- **Notebook 2 (6.2.4), CERRADO:** M2 semáforo de precio (KNN, modelo de producción confirmado) +
  Random Forest (comparación metodológica, no reemplaza al producto). MAE test: KNN \$187,543
  (33.4% del precio promedio), RF \$149,270 (26.6%) — diferencia 20.4%, documentada como hallazgo
  sin iterar (umbral >15% ya cerrado). Umbral del semáforo recalibrado sobre el residual real
  (±1.5×MAE), reemplaza el ±10% original que estaba mal calibrado. Hallazgo de investigación no
  adoptado: RF+embedding de 6.2.3 reduce MAE ~20%, pendiente de reducción de dimensionalidad antes
  de cualquier uso en producción — fuera de alcance de Feature 6.2. Detalle completo en
  `Context-MD/Feature_6_2_4_M2_KNN_RF_Cierre.md`.
- **Notebook 3 (6.2.5), CERRADO:** M2 KMeans segmentación de mercado, mismo dataset filtrado que
  6.2.4. k óptimo=2, Silhouette=0.388 — dos segmentos: compacto/económico (662, mediana \$270K/92m²)
  y grande/premium (380, mediana \$736K/300m²). Detalle en
  `Context-MD/Feature_6_2_5_M2_KMeans_Cierre.md`.
- **Notebook 4 (6.2.6), CERRADO:** M2 Quality Scorer (LLM sobre texto de `descripcion`, tipo
  Experimentación). 4 dimensiones (1-5): completitud, presentación, diferenciadores, transparencia
  de precio. Muestra n=150, prompt v2 (salida estructurada del SDK) 100% válido contra el esquema
  (umbral 90% superado). **Hallazgo de modelo:** `gemini-2.5-flash` (CLAUDE.md) devuelve 404 real;
  `gemini-3.5-flash` (versión fija confirmada) mostró disponibilidad degradada sostenida durante la
  ejecución — 100% de fallo en un lote diagnóstico completo, no un corte puntual — así que el modelo
  final usado es `gemini-3-flash-preview` (no GA, limitación de reproducibilidad documentada). 112
  filas evaluadas con `gemini-3.5-flash` y 38 con `gemini-3-flash-preview`, columna `modelo` por
  fila en el artifact; comparación de medias entre ambos modelos sin diferencia notable (máx. 0.14
  en escala 1-5), por lo que combinarlos en un solo análisis es metodológicamente razonable.
  Convenciones nuevas para 6.2.7 en adelante: checkpoint incremental en *toda* fase que llame a la
  API (no solo la corrida principal) y `http_options=types.HttpOptions(timeout=...)` explícito en
  todo `genai.Client()` (el default de la librería, sin límite, causó un bloqueo real de ~3 horas).
  Detalle completo en `Context-MD/Feature_6_2_6_M2_QualityScorer_Cierre.md`.
- **Notebook 5 (6.2.7), CERRADO — último notebook de Feature 6.2, Feature completa (23 SP):** M3
  NLP Orchestration. **Modelo LLM re-verificado, no heredado de 6.2.6:** `gemini-3.5-flash` pasó de
  100% de fallo sostenido (6.2.6) a 100% de éxito en un lote diagnóstico idéntico de 25 llamadas —
  se usa `gemini-3.5-flash` (GA, id fijo) en vez de `gemini-3-flash-preview`. La disponibilidad de
  modelos Gemini es una condición del momento de ejecución, se debe re-verificar en cada notebook
  futuro que dependa de la API, no asumir el resultado de una corrida anterior.
  **Umbral de confianza de extracción de intención: 0.65**, calibrado sobre 5 consultas claras + 5
  ambiguas + 1 caso límite de control — marcado explícitamente como calibración provisional, no
  optimizada (salto limpio de 0.45 sin casos intermedios reales observados). **Mecanismo de
  fallback de 3 causas separables, no un solo score de confianza:** fuera de tema
  (`es_consulta_inmobiliaria=False`), cobertura geográfica (ubicación real mencionada pero fuera de
  las 9 zonas del scope) y ambigüedad (confianza <0.65) — necesario porque una consulta bien
  formada sobre una zona fuera de scope puede extraer con la misma confianza alta que una consulta
  válida. Medición final sobre 20 consultas (10 válidas + 5 fuera de alcance + 5 ambiguas,
  WBS 4.2.2): 50% éxito, 20% fallback por cobertura, 5% por tema, 25% por ambigüedad — conjunto
  diseñado deliberadamente con casos extremos por categoría, **no es una predicción de la tasa de
  fallback en producción con consultas reales**. Orquesta M1/M2 vía un contrato de función
  simulado (`v0 — sujeto a revisión en Épica 4`), que detecta la falta de cobertura estructural de
  KNN/KMeans para Pedregal/Parque Lefevre (columnas dummy inexistentes en el modelo entrenado,
  Acta 1.2 §5.3) antes de intentar una predicción fuera de dominio, y devuelve una respuesta
  honesta que distingue "sin candidatos de M1" de "sin cobertura de M2" en vez de colapsar ambos
  casos en un mensaje genérico. Detalle completo en
  `Context-MD/Feature_6_2_7_M3_Orchestration_Cierre.md`.

## Estado del pipeline de datos (al 2026-07-09)

- **Feature 1.2 (scraping):** CERRADO. Catálogo real: 1,361 registros (~34% de lo proyectado).
  Pedregal y Parque Lefevre excluidos de KNN/KMeans por volumen insuficiente para 5-fold CV
  (siguen dentro del Zone Health Index, que es determinístico y no depende de volumen).
  `geom` de propiedades es sintético (jitter), solo para visualización — nunca insumo de modelo.
- **Feature 1.3 (datos externos):** extracción y cómputo CERRADOS. Carga física a Supabase
  PENDIENTE de Feature 1.5 (la tabla `corregimientos` con las columnas de Zone Health no existe
  todavía). Los 7 archivos canónicos están en `pipeline/data/external/`.
- **Feature 1.5 (schema DB):** no iniciado.
- **Feature 1.4 (Zone Health Composite Index):** en progreso. Ver decisiones cerradas abajo.

## Decisiones formales cerradas — no las reabras sin que el equipo lo pida explícitamente

1. **Pedregal:** permanece dentro de la fórmula del Zone Health Index (4/5 dimensiones sólidas).
   Excluido de la *visualización activa* por amenidades débiles (12 POIs vs. 32-52 promedio) —
   se calcula, no se muestra. Pendiente validación con consejo académico.
2. **Costa del Este:** NO recibe score compuesto. 4 de 5 dimensiones no tienen insumo (dependían
   de Juan Díaz, que nunca se extrajo por estar fuera del scope de 9 zonas). Estado de UI:
   "cobertura de datos insuficiente", igual que Pedregal pero con causa distinta y más severa
   (ausencia estructural, no debilidad de un componente). Sus 24 POIs de amenidades pueden
   mostrarse como dato descriptivo separado, nunca dentro del composite.
3. **Normalización de seguridad (1.4.1):** min-max invertido sobre `tasa_por_100k`
   (`score = 1 - ((x - min) / (max - min))`), calculado solo sobre las 5 zonas reales.
   Limitación conocida y documentada: n=5, sensible a outliers (Parque Lefevre 21.01 muy
   por encima del resto, 3.26–15.60).
4. **M2 comparables:** redefinidos de proximidad geográfica (`ST_Distance`) a coincidencia de
   corregimiento + tipo de inmueble — inmopanama.com no expone coordenadas reales.

## Pesos del Zone Health Composite Index (Feature 1.4)

Seguridad 0.30, transporte 0.20, amenidades 0.20, walkability 0.15, socioeconómico 0.15.
Tráfico vehicular = etiqueta cualitativa por clasificación de vía OSM, no score numérico.

## Regla de citas de features — no copiar sin verificar

Ninguna referencia a un número de Feature/Acta (ej. "Feature 1.4.6", "Acta 1.3 §5") se
copia de un script a otro sin verificarla contra el documento fuente real. Si un script
hereda una cita de otro script anterior (por convención de patrón, copy-paste de
docstring, etc.), se verifica de nuevo — no se asume que la verificación anterior sigue
vigente solo porque ya estaba en el código existente.

**Caso encontrado (2026-07-09):** `normalizacion_seguridad.py`, `normalizacion_transporte.py`
y `normalizacion_amenidades.py` compartían una cita a "Feature 1.4.6" en su docstring,
copiada de script a script, que no existe en ningún documento del repo — no era una
referencia real, sino una inferencia plausible que se propagó sin verificación. Corregida
tras auditoría explícita; los 3 scripts fueron corregidos en la misma sesión.

## Regla de verificación geométrica — obligatoria para TODO archivo de amenidades, sin importar el método de extracción

Todo registro de amenidades (`lat`/`lng`), sin importar si vino de OSM Overpass o de
Google Places, debe pasar por `asignar_corregimiento()` antes de usarse en cualquier
cálculo de Feature 1.4. No asumas que un archivo está limpio solo porque su método de
origen es distinto al que ya falló — la verificación geométrica no es específica de un
método, es una validación de correctitud general que debe aplicarse siempre.

**Caso encontrado (2026-07-09):** los 3 archivos Google Places del proyecto
(`amenidades_bella_vista_google_places.jsonl`, `amenidades_san_francisco_google_places.jsonl`,
`amenidades_costa_del_este_google_places.jsonl`) nunca pasaron por esta verificación —
solo los archivos OSM la tenían, dentro de `normalizacion_amenidades._contar_osm()`.
Auditoría posterior encontró 3 de 18 registros de Bella Vista mal asignados
(2 fuera de las 5 zonas reales, 1 perteneciente a San Francisco). San Francisco y
Costa del Este quedaron pendientes de la misma auditoría en el momento de este hallazgo.

---

*Fuente de verdad completa: Actas de cada feature en `Context-MD/` y `REIP_WBS.md`. Este archivo
es un resumen operativo para agentes de código, no reemplaza las Actas.*
*(Notion quedó desactualizado y ya no se usa como fuente de verdad para esto — 2026-07-13.)*