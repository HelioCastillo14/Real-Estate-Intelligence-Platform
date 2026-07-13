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
- **NLP:** Gemini 2.5 Flash (M3) — `GEMINI_API_KEY` aún no generado, bloquea trabajo de M3/embeddings
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

*Fuente de verdad completa: Actas de cada feature en Notion (`data_source_id:
36db0373-96cc-8048-b9dc-000b671ef489`) y `REIP_WBS.md`. Este archivo es un resumen operativo
para agentes de código, no reemplaza las Actas.*