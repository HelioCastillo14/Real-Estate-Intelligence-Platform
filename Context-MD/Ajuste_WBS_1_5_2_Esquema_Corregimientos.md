# Ajuste WBS — Feature 1.5.2: Esquema de tabla `corregimientos`

**Fecha:** 2026-07-15
**Estado:** Diseño aprobado — pendiente de ejecución
**Fuente de las decisiones:** `Feature_1_4_Zone_Health_Composite_Index_Documentacion_Granular.md` (cerrado 2026-07-09) + decisión de esta sesión (9 vs. 5 filas + patrón de herencia)

---

## 1. Decisión de fondo — 9 filas, no 5

`corregimientos` contiene **las 9 zonas del scope de negocio de REIP**, no solo los 5 corregimientos administrativos oficiales de Panamá.

**Razón de negocio, no técnica:** `propiedades.corregimiento` ya tiene 1,177 filas reales cargadas, de las cuales **381 (32% del catálogo)** pertenecen a las 4 zonas no oficiales (El Cangrejo 77, Marbella 49, Obarrio 64, Costa del Este 191). El sistema entrega inteligencia de mercado por zona reconocida comercialmente, no por unidad administrativa — 5 filas dejaría fuera de cualquier relación estructurada casi un tercio del catálogo real.

**Este ajuste vive en documentación interna** (WBS, Context-MD) — no reabre ningún documento oficial ya publicado del proyecto (Acta del Proyecto, Acta de Datos), que describen el scope de 9 zonas en términos de negocio sin comprometerse a un modelo relacional específico.

## 2. Patrón de herencia — consistente con Feature 1.4, no un criterio nuevo

**Regla:** las 4 zonas no oficiales heredan del corregimiento contenedor mediante referencia (`hereda_de`), nunca por duplicación de valores. Esta tabla aplica el **mismo criterio** que Feature 1.4 ya usó para `zone_health_score` — no se inventa un patrón distinto para `geom`.

### 2.1 Verificado contra Feature 1.4 (fuente autoritativa)

| Zona | `hereda_de` | Razón |
|---|---|---|
| San Francisco | `NULL` (corregimiento oficial) | — |
| Bella Vista | `NULL` (corregimiento oficial) | — |
| Parque Lefevre | `NULL` (corregimiento oficial) | — |
| Betania | `NULL` (corregimiento oficial) | — |
| Pedregal | `NULL` (corregimiento oficial) | Score calculado, pero `no_visualizado = TRUE` — no confundir con herencia |
| El Cangrejo | `'Bella Vista'` | Copia literal del composite y desglose de Bella Vista (Feature 1.4 §7) |
| Marbella | `'Bella Vista'` | ídem |
| Obarrio | `'Bella Vista'` | ídem |
| **Costa del Este** | **`NULL`** | **Sin score, sin herencia** — decisión formal de Feature 1.4 §7. Un `hereda_de: "Juan Díaz"` embebido en datos crudos fue detectado y revocado en 1.4.1 (Juan Díaz nunca se extrajo, está fuera del scope de 9 zonas) |

**Nota crítica que distingue esta tabla de una lectura ingenua del dato:** Costa del Este **no tiene fila padre**. No es una zona que "hereda de otra zona con datos faltantes" — es una zona con `estado_zone_health = 'sin_score_datos_insuficientes'` en 4 de 5 dimensiones originales. `hereda_de = NULL` en su fila **no significa "es un corregimiento oficial"** (no lo es) — significa "no hereda de nadie porque no hay padre confiable". El campo `es_oficial` (ver §3) es el que distingue ambos casos; `hereda_de` por sí solo es ambiguo entre "oficial" y "no oficial sin padre".

## 3. Esquema de columnas

```sql
create table if not exists corregimientos (
    -- Identidad
    nombre                  text primary key,
    es_oficial              boolean not null,
    -- TRUE: San Francisco, Bella Vista, Parque Lefevre, Betania, Pedregal
    -- FALSE: El Cangrejo, Marbella, Obarrio, Costa del Este

    -- Geometría — polígono REAL (shapefile STRI/HDX, Feature 1.3.1, cerrada).
    -- Distinto del geom SINTÉTICO de propiedades — no aplicar esa nota aquí.
    geom                    geometry(Polygon, 4326),
    -- NULL para las 4 zonas no oficiales (heredan visualización del padre en capa de
    -- presentación, vía hereda_de — no se duplica el polígono en esta tabla).

    -- Herencia — self-referencing FK, NULL para corregimientos oficiales Y para
    -- Costa del Este (caso especial: no oficial, sin padre confiable).
    hereda_de               text references corregimientos(nombre),

    -- Zone Health Composite Index (Feature 1.4, cerrada 2026-07-09)
    zone_health_score       numeric,
    -- NULL únicamente para Costa del Este.

    desglose_dimensiones    jsonb,
    -- {"seguridad": ..., "transporte": ..., "amenidades": ..., "walkability": ...}
    -- 4 dimensiones (no 5 — socioeconómico eliminado en 1.4.5, peso redistribuido).
    -- NULL únicamente para Costa del Este.

    estado_zone_health      text not null default 'calculado'
        check (estado_zone_health in ('calculado', 'sin_score_datos_insuficientes')),
    -- 'sin_score_datos_insuficientes' únicamente para Costa del Este.

    no_visualizado          boolean not null default false,
    -- TRUE únicamente para Pedregal. Distinto de estado_zone_health: Pedregal SÍ
    -- tiene composite calculado, solo se excluye de la visualización de frontend
    -- (Feature 5.x). No confundir con el caso de Costa del Este.

    motivo_visualizacion    text
    -- Poblado solo cuando no_visualizado = TRUE. Texto libre, sin CHECK a propósito
    -- — mismo criterio que enriquecimiento_error_detalle en propiedades (1.5.1): no
    -- es un conjunto cerrado de valores, es explicación de caso. Fuente real (JSON
    -- de origen) documenta que la exclusión de Pedregal sigue PENDIENTE DE
    -- VALIDACIÓN FORMAL del consejo académico — a diferencia de la exclusión de
    -- KNN/KMeans, que sí tuvo esa validación (Acta de 1.2, sesión 2026-07-08).
);

comment on column corregimientos.hereda_de is
    'Self-referencing FK. NULL para los 5 corregimientos oficiales Y para Costa del '
    'Este (caso especial sin padre confiable). Para las 3 zonas restantes no '
    'oficiales (El Cangrejo, Marbella, Obarrio), apunta a Bella Vista. Ver es_oficial '
    'para distinguir "oficial" de "no oficial sin herencia". Fuente: Feature 1.4 §7.';

comment on column corregimientos.geom is
    'Polígono REAL (shapefile STRI/HDX, Feature 1.3.1). NULL para las 4 zonas no '
    'oficiales — la resolución de qué polígono mostrar para una zona heredada vive '
    'en la capa de presentación (Épica 5), no se duplica el polígono aquí. '
    'Distinto del geom sintético de propiedades — no aplicar esa nota en esta tabla.';

comment on column corregimientos.estado_zone_health is
    'calculado: la zona tiene composite y desglose, propio o heredado. '
    'sin_score_datos_insuficientes: únicamente Costa del Este — 4 de 5 dimensiones '
    'originales carecen de datos reales y no hay padre confiable del cual heredar.';

comment on column corregimientos.motivo_visualizacion is
    'Explicación de por qué no_visualizado = TRUE, texto libre sin CHECK. Único '
    'caso actual: Pedregal (cobertura de amenidades insuficiente, 12 POIs vs. '
    '32-52 promedio del resto de zonas). NOTA DE GOBERNANZA: esta exclusión sigue '
    'pendiente de validación formal con el consejo académico — a diferencia de la '
    'exclusión de KNN/KMeans, que sí la tuvo (Acta de 1.2, sesión 2026-07-08).';
```

## 4. Verificación de consistencia contra `1.5.1` (ya ejecutada)

`propiedades.corregimiento` tiene actualmente un CHECK con 10 valores (9 zonas + `zona_no_determinada`), sin FK formal — condicionado explícitamente a esta decisión. Los 9 valores del CHECK coinciden exactamente con las 9 filas de `nombre` en este esquema. Cuando se decida convertir el CHECK en FK dura (fuera del alcance de 1.5.2), la migración deberá excluir `'zona_no_determinada'` del scope de la FK o mantenerla como caso especial fuera de `corregimientos`.

## 4bis. Fuente de datos — verificada contra el JSON real (no solo contra documentación)

`pipeline/data/processed/zone_health_composite_1_4_6.json` (112 líneas), estructura:

```json
{
  "zonas": {
    "<nombre>": {
      "nombre": "...",
      "composite": <float o null>,
      "desglose": {"seguridad": ..., "transporte": ..., "amenidades": ..., "walkability": ...} o null,
      "estado_zone_health": "calculado" | "sin_score_datos_insuficientes",
      "estado_visualizacion": "no_visualizado"   // presente SOLO en Pedregal
      "motivo_visualizacion": "..."                // presente SOLO en Pedregal
      "hereda_de": "Bella Vista"                   // presente SOLO en las 3 zonas heredadas
      "motivo_estado": "..."                       // presente SOLO en Costa del Este
    }, ...
  }
}
```

**Nota de mapeo para el script de carga — campos ausentes vs. NULL:** el JSON omite las claves `hereda_de`, `estado_visualizacion`/`motivo_visualizacion`, y `motivo_estado` en las filas donde no aplican, en vez de incluirlas con valor `null`. El script de carga debe tratar clave ausente como equivalente a `NULL`, usando `.get(clave, None)`, no asumir que la clave siempre existe.

**Discrepancia de pesos detectada, no bloqueante:** los pesos en el JSON (seguridad 0.352941176, transporte 0.235294118, amenidades 0.235294118, walkability 0.176470588 — 4 dimensiones, redistribuidos) son los pesos FINALES correctos según Feature 1.4 §1 (post-eliminación de socioeconómico). `CLAUDE.md` sigue citando los pesos ORIGINALES de 5 dimensiones (seguridad 0.30, transporte 0.20, amenidades 0.20, walkability 0.15, socioeconómico 0.15) — desactualizado, no afecta esta carga, pero debe corregirse para evitar confusión futura.

## 5. Checkpoint de cierre de 1.5.2

- [ ] Migración `CREATE TABLE corregimientos` ejecutada contra Supabase (con confirmación explícita, mismo protocolo que 1.5.1)
- [ ] 9 filas cargadas: 5 con `es_oficial = TRUE`, `geom` real, `hereda_de = NULL`
- [ ] 3 filas (El Cangrejo, Marbella, Obarrio) con `es_oficial = FALSE`, `geom = NULL`, `hereda_de = 'Bella Vista'`, `zone_health_score`/`desglose_dimensiones` copiados literalmente de Bella Vista
- [ ] 1 fila (Costa del Este) con `es_oficial = FALSE`, `geom = NULL`, `hereda_de = NULL`, `zone_health_score = NULL`, `estado_zone_health = 'sin_score_datos_insuficientes'`
- [ ] Fila Pedregal con `no_visualizado = TRUE`, `zone_health_score` poblado (no NULL), `motivo_visualizacion` con el texto del JSON de origen
- [ ] Fuente de carga: `pipeline/data/processed/zone_health_composite_1_4_6.json` (Feature 1.4.6, ya cerrado)

## 6. Pendiente explícito, fuera de alcance de 1.5.2

Dónde vive la lógica de resolución de herencia de `geom` para el mapa (backend vs. frontend) — decisión de arquitectura de Épica 5, no de esquema. La estructura de esta tabla queda lista para soportar cualquiera de las dos rutas sin cambio de schema.
