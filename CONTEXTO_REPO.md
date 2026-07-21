# REIP — Guía de contexto del repositorio

**Para colaboradores nuevos.** Este archivo explica *qué hay en cada carpeta* y *cómo
correrlo*. Para decisiones de scope, pesos, metodología y reglas de trabajo, la fuente
de verdad es [`CLAUDE.md`](CLAUDE.md) — no la dupliques, léela también.

> ⚠️ **Discrepancia detectada al escribir este documento (2026-07-13):** `CLAUDE.md`
> dice que el Zone Health Composite Index usa 5 dimensiones (seguridad 0.30, transporte
> 0.20, amenidades 0.20, walkability 0.15, socioeconómico 0.15). El código real en
> `pipeline/zone_health/composite_zone_health.py` usa **4 dimensiones** (socioeconómico
> eliminado en "Feature 1.4.5", pesos redistribuidos: seguridad 0.352941176, transporte
> 0.235294118, amenidades 0.235294118, walkability 0.176470588). Según la propia regla
> de `CLAUDE.md` ("si algo aquí contradice una Acta más reciente, la Acta gana"), el
> código parece reflejar una decisión más reciente que el CLAUDE.md no tiene actualizada.
> **No asumas cuál es correcto — confírmalo con el equipo antes de tocar pesos.**

---

## 1. Qué es esto

Plataforma de recomendación inmobiliaria para Panamá (tesis UTP, curso 0698):
scoring de "salud de zona" por corregimiento, semáforo de precios (KNN/KMeans/Random
Forest) y búsqueda en lenguaje natural sobre listings. Ver `CLAUDE.md` para el mapa
completo de módulos (M1/M2/M3) y decisiones de scope cerradas.

Monorepo con tres carpetas hermanas independientes — cada una con su propio entorno
y dependencias:

```
backend/    → FastAPI (esqueleto, casi vacío todavía)
frontend/   → Next.js 14 + MapLibre GL (mapa base funcionando)
pipeline/   → Python: scraping, datos externos, Zone Health Index (lo más avanzado)
notebooks/  → vacío (placeholder, .gitkeep)
```

Rama activa de trabajo: `dev`. `main` es la rama estable para PRs.

---

## 2. `pipeline/` — el corazón actual del proyecto

Es la parte más madura del repo. Todo en Python puro (sin framework), organizado por
etapa de datos.

### 2.1 `pipeline/scraper/inmopanama_scraper.py`

Scraper Selenium de listings de venta de apartamentos en inmopanama.com, parametrizado
por corregimiento. Producto: `pipeline/data/raw/{corregimiento}_listings.{csv,json}` +
un log de paginación por zona.

Puntos clave (documentados en el docstring del propio archivo, léelo antes de tocarlo):
- robots.txt permite rastreo completo; rate-limiting respetuoso por defecto.
- El campo `zone` prioriza la etiqueta propia del listing (`zone_raw`) sobre la zona
  de la URL scrapeada — las páginas de categoría de inmopanama no filtran estrictamente
  por corregimiento. `zone_source` deja trazabilidad de cuál fuente ganó.
- Filtro heurístico por palabras clave en el título para excluir tipos de inmueble no
  residenciales (bodegas, locales, terrenos) — pendiente reemplazar por campo
  estructurado real (Feature 1.2.7).
- Selectores CSS confirmados por inspección manual — si inmopanama cambia su HTML,
  correr `python inmopanama_scraper.py --corregimiento bella-vista --discover --no-headless`.
- Bugs conocidos de Selenium/Chrome ya resueltos (page_load_strategy, race condition al
  arrancar el driver) — ver docstring para los fixes exactos antes de "redescubrirlos".

Dependencias: `pip install -r pipeline/requirements.txt` (incluye selenium,
webdriver-manager, shapely, requests).

### 2.2 `pipeline/data/` — datos en sus distintas etapas

- **`raw/`** — output crudo del scraper, uno por corregimiento (9 zonas). CSV + JSON +
  log de paginación. Evidencia del scraping, se versiona en git.
- **`external/`** — datos externos ya extraídos y organizados por fuente:
  - `amenidades/` — Google Places (3 zonas) + OSM Overpass (varias zonas, algunos
    archivos multi-zona). **Ver `LOG_EXTRACCION.md` en esa misma carpeta antes de tocar
    estos archivos** — documenta un sesgo de extracción ya encontrado y corregido
    (búsquedas de categoría incompletas en Google Places) y advierte que no existe
    script de extracción versionado para esos 3 archivos (reconstrucción post-hoc).
  - `corregimientos/` — polígonos administrativos reales (OSM) de las 5 zonas reales.
  - `gtfs/` — paradas de MiBus.
  - `metro/` — estaciones de metro (líneas 1 y 2, crudo + final con `corregimiento_id`).
  - `seguridad/` — homicidios 2023 (SIEC), 9 filas (una por zona del scope).
  - `socioeconomico/` — densidad poblacional INEC 2023.
- **`processed/`** — outputs de `zone_health/`, un JSON por feature de cómputo
  (`zone_health_seguridad_1_4_1.json`, etc., y el compuesto final `_1_4_6.json`).
- **`synthetic/`** — vacío por ahora (placeholder).

Carga a Supabase de estos datos: **pendiente**, bloqueada por Feature 1.5 (la tabla
`corregimientos` con columnas de Zone Health todavía no existe en el schema).

### 2.3 `pipeline/zone_health/` — Zone Health Composite Index

Cada script normaliza **una** dimensión a escala 0-1 por corregimiento y solo cubre las
5 zonas con corregimiento administrativo real (Bella Vista, Betania, Parque Lefevre,
Pedregal, San Francisco) — El Cangrejo/Marbella/Obarrio y Costa del Este se resuelven
aparte (herencia / sin score, ver `CLAUDE.md`).

| Script | Qué normaliza | Fuente(s) de datos |
|---|---|---|
| `normalizacion_seguridad.py` | Tasa de homicidios por 100k, min-max invertido | `external/seguridad/seguridad_homicidios_2023.jsonl` |
| `normalizacion_transporte.py` | Densidad de transporte (metro + MiBus) | `external/metro/`, `external/gtfs/`, área de `external/seguridad/` (fuente de conveniencia, no autoritativa — auditoría pendiente) |
| `normalizacion_amenidades.py` | Densidad ponderada de amenidades por categoría (5 categorías, `hospital`+`clinica` fusionados en `salud`) | `external/amenidades/*` |
| `normalizacion_walkability.py` | Proxy de un solo componente: distancia promedio a supermercado/parque/metro | `external/amenidades/*`, `external/metro/` |
| `cruce_espacial_corregimiento.py` | Utilitario: punto-en-polígono (`shapely`) para asignar `corregimiento_id` a cualquier punto lat/lng | `external/corregimientos/corregimientos_5zonas_poligonos_raw_osm.geojson` |
| `composite_zone_health.py` | Combina las 4 dimensiones anteriores con pesos fijos + aplica herencia/exclusión por zona | Los 4 JSON de `data/processed/` |

**Regla obligatoria (ver `CLAUDE.md`):** todo archivo de amenidades con lat/lng, sin
importar el método de extracción (OSM o Google Places), debe pasar por
`asignar_corregimiento()` antes de usarse en cualquier cómputo — una auditoría ya
encontró registros mal asignados que habían escapado esta verificación.

Tests: `pipeline/zone_health/tests/` — un archivo de test por script, `pytest` desde la
raíz del repo:
```bash
cd pipeline && python -m pytest zone_health/tests/ -v
```

### 2.4 Setup del entorno de `pipeline/`

```bash
cd pipeline
python3 -m venv venv && source venv/bin/activate   # o conda, ver CLAUDE.md
pip install -r requirements.txt
```

---

## 3. `backend/` — FastAPI (esqueleto)

Estado real: **casi vacío**. Solo existe:

```python
# backend/app/main.py
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
```

`app/models/`, `app/routers/`, `app/services/` son carpetas placeholder (`.gitkeep`,
sin contenido). Nada de esto está conectado todavía a Supabase ni expone endpoints
reales de M1/M2/M3 — eso es trabajo futuro, condicionado a que Feature 1.5 (schema DB)
se cierre primero (ver cadena de dependencia dura en `CLAUDE.md`: Data Pipeline → M1,
M2 → M3).

Variables de entorno esperadas (`backend/.env`, no versionado):
```
SUPABASE_URL=
SUPABASE_KEY=      # Secret key de Supabase (Project Settings → API Keys)
DATABASE_URL=      # Connection string de Supabase (modo Session)
GEMINI_API_KEY=    # Google AI Studio — aún no generada, bloquea M3
```

Setup:
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Deploy: Railway (`real-estate-intelligence-platform-production.up.railway.app`).

---

## 4. `frontend/` — Next.js 14 + MapLibre GL

Estado real: un mapa base funcionando, nada más. `frontend/app/page.tsx` monta un
`maplibregl.Map` a pantalla completa, centrado en Ciudad de Panamá (`[-79.5199, 8.9824]`,
zoom 12), usando el estilo público `tiles.openfreemap.org/styles/liberty`. Sin capas de
datos, sin componentes de UI, sin conexión al backend todavía.

Stack: Next.js 14.2.35 (App Router), React 18, Tailwind (configurado pero apenas usado),
TypeScript.

Setup:
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

Deploy: Vercel.

---

## 5. `notebooks/`

Vacío (`.gitkeep`). Placeholder para exploración/análisis futuro (probablemente M2:
KNN, KMeans, Random Forest).

---

## 6. Cómo orientarte rápido

1. Lee `CLAUDE.md` primero — ahí están las decisiones de scope, pesos, y las reglas
   de citas/verificación que ya causaron bugs reales cuando no se siguieron.
2. Si vas a tocar `zone_health/`, lee el docstring completo del script antes de editar
   — cada uno documenta auditorías previas, bugs encontrados y por qué el código hace
   lo que hace (no es solo estilo, es historial de decisiones).
3. Si vas a tocar `amenidades/`, lee `LOG_EXTRACCION.md` primero.
4. Backend y frontend están en fase de esqueleto — no asumas que hay endpoints o
   componentes que "deberían" existir por el nombre de la carpeta; revisa el archivo
   real.
5. Antes de citar un número de Feature/Acta en código nuevo, verifícalo contra el
   documento fuente (Notion) — no lo copies de otro script, aunque parezca establecido
   (ver la regla y el caso real documentado en `CLAUDE.md`).
