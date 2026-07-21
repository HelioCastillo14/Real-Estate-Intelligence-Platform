# Feature 1.5.1 — Tabla `propiedades` — Acta de Cierre

**Fecha de ejecución:** 2026-07-15
**Fuente de la migración:** `supabase/migrations/20260715040000_propiedades_create_table.sql`
**Esquema aprobado en:** `Context-MD/Ajuste_WBS_1_5_1_Esquema_Propiedades.md`
**Ejecutado por:** confirmación explícita del usuario, vía `supabase db push` (regla operativa de infraestructura compartida respetada — ninguna migración corrió sin autorización en el momento).

---

## 1. Contexto de ejecución

El proyecto Supabase (`ezutrurenerqgfmozbzz`) se encontraba en estado *paused* por inactividad (free tier) al momento de iniciar esta sesión. Se resumió manualmente desde el dashboard antes de proceder. No se detectaron efectos adversos del pause ni del incidente de plataforma reportado por Supabase ese mismo día sobre la ejecución de la migración.

Primera migración ejecutada contra este proyecto — no existía historial previo en `supabase_migrations.schema_migrations`.

## 2. Migraciones aplicadas

Dos archivos pendientes en `supabase/migrations/`, aplicados en orden de timestamp vía `supabase db push`:

| Archivo | Resultado |
|---|---|
| `20260715032111_propiedades_embedding.sql` | **No-op** — `NOTICE: relation "propiedades" does not exist, skipping`. Confirmado como redundante (Opción A: `embedding` fusionado en 1.5.1), tal como anticipaba el comentario del propio archivo. Se conserva en el repo como registro histórico de la decisión de dimensión (Feature 1.5b), no se ejecuta de nuevo. |
| `20260715040000_propiedades_create_table.sql` | **Aplicado exitosamente.** Crea la tabla `propiedades` completa con 25 columnas, constraints y el índice GiST. |

## 3. Verificación de cierre

Nota técnica: `supabase db psql` no existe en la versión del CLI usada (2.109.1); tampoco `supabase db query` soporta meta-comandos `\d`/`\di` de `psql` (ejecuta contra el endpoint SQL de la Management API, no un cliente `psql` real). La verificación se hizo con consultas SQL equivalentes contra `information_schema` y `pg_catalog`.

### 3.1 Columnas (`\d propiedades` equivalente)

25 columnas creadas, todas coinciden exactamente con la migración aprobada:

`listing_id` (PK, bigint) · `listing_url` (unique) · `title` · `zone_raw` · `corregimiento` · `zone_source` · `price_raw` · `price_usd` · `precio_no_evaluable` · `precio_no_evaluable_motivo` · `bedrooms` · `bathrooms` · `area_m2` · `operation` · `source` · `scraped_at` · `corregimiento_archivo` · `tipo_inmueble` · `descripcion` · `descripcion_fuente` · `enriquecimiento_estado` · `enriquecimiento_error_detalle` · `embedding` (vector) · `geom` (geometry) · `imagenes` (text[])

### 3.2 Constraints

| Constraint | Definición | Estado |
|---|---|---|
| `propiedades_pkey` | `PRIMARY KEY (listing_id)` | ✓ |
| `propiedades_listing_url_key` | `UNIQUE (listing_url)` | ✓ |
| `chk_propiedades_corregimiento` | 9 zonas de scope + `zona_no_determinada` (10 valores) | ✓ verificado carácter por carácter |
| `propiedades_zone_source_check` | `zone_raw` / `zone_raw_barrio_mapeado` / `pagina_scrapeada_no_resuelto` | ✓ |
| `propiedades_operation_check` | `venta` / `alquiler` | ✓ |
| `propiedades_tipo_inmueble_check` | `Apartamentos` / `Casas` / `Edificios` / `Locales` / `Terrenos` | ✓ |
| `propiedades_descripcion_fuente_check` | `completa` / `preview` / `ninguna` | ✓ |
| `propiedades_enriquecimiento_estado_check` | `ok` / `sin_descripcion` / `error_red` / `sin_url` | ✓ |

### 3.3 Índices (`\di idx_propiedades_geom` equivalente)

```
CREATE INDEX idx_propiedades_geom ON public.propiedades USING gist (geom)
```

Presente y correcto — GiST sobre `geom`, tal como especifica §4.1 del esquema aprobado.

**Índice HNSW sobre `embedding`: diferido a propósito, no se creó.** No es condición de Done de esta tarea — queda gated a `1.5.6` (spike de rendimiento bajo volumen real), que determinará los parámetros `m`/`ef_construction`.

## 4. Decisiones confirmadas por esta ejecución (no reabrir)

- **PK de `propiedades` es `listing_id`**, no `listing_url` — confirmado en el esquema real de la BD, no solo en documentación.
- **`embedding vector(3072)`** existe con tipo correcto (`udt_name: vector`) — la dimensión de Feature 1.5b quedó materializada sin necesidad de una segunda migración.
- **`geom` es sintético** — columna presente (`udt_name: geometry`), pendiente de poblarse vía `ST_GeneratePoints` en trabajo posterior; nunca será insumo de modelo.
- **FK de `corregimiento` hacia `corregimientos` queda condicionada a 1.5.2**, tal como estaba planeado — hoy solo existe el CHECK con valores fijos, sin relación formal a otra tabla (que todavía no existe).
- **La migración de Feature 1.5b (`20260715032111`) queda archivada de facto** (no ejecuta nada al re-correr `db push` en el futuro, por sus guards `IF EXISTS`/`IF NOT EXISTS`) — no requiere limpieza manual del repo para evitar conflictos futuros.

## 5. Estado

**Feature 1.5.1: CERRADA.** Checkpoint cumplido en su totalidad, sin discrepancias entre lo aprobado y lo ejecutado.

**Siguiente tarea en la secuencia:** `1.5.2` — tabla `corregimientos`, decisión de diseño pendiente (9 vs. 5 filas).
