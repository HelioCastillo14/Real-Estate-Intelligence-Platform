# Feature 1.5.2 — Tabla `corregimientos` — Acta de Cierre

**Fecha de ejecución:** 2026-07-15
**Fuente del esquema:** `Ajuste_WBS_1_5_2_Esquema_Corregimientos.md`
**Fuente de los datos:** `pipeline/data/processed/zone_health_composite_1_4_6.json` (Feature 1.4.6, cerrada 2026-07-09)
**Ejecutado por:** confirmación explícita del usuario, en dos pasos separados — migración de estructura y carga de datos.

---

## 1. Contexto de ejecución

Segunda migración ejecutada contra el proyecto (`ezutrurenerqgfmozbzz`), posterior a `1.5.1`. Se mantuvo el mismo protocolo de confirmación explícita para infraestructura compartida.

**Precondición resuelta antes de diseñar el esquema:** se detectó y corrigió una contradicción interna en `Feature_1_4_Zone_Health_Composite_Index_Documentacion_Granular.md` — una versión previa del documento (indexada en project knowledge) contenía en su §5.3 una referencia a que Costa del Este heredaría de "Juan Díaz", contradiciendo su propia tabla de resumen ejecutivo ("Sin score"). La versión del documento que el usuario subió directamente ya tenía esta contradicción resuelta: el campo `hereda_de: "Juan Díaz"` fue identificado como un valor embebido erróneamente en datos crudos, revocado en 1.4.1, con `motivo_estado` documentado explícitamente. El JSON de origen (`zone_health_composite_1_4_6.json`) confirma la versión corregida — Costa del Este no tiene padre de herencia.

## 2. Decisión de diseño — 9 filas, patrón de herencia por referencia

- **9 filas**, no 5: los 5 corregimientos administrativos oficiales + las 4 zonas de scope comercial que heredan del corregimiento contenedor. Justificado por volumen real de catálogo (381 de 1,177 propiedades, 32%, pertenecen a las 4 zonas no oficiales).
- **Herencia por referencia (`hereda_de`), no por duplicación** — mismo patrón que Feature 1.4 ya estableció para `zone_health_score`, aplicado también a `geom`.
- **Columna `es_oficial`** agregada para eliminar la ambigüedad de que `hereda_de = NULL` por sí solo no distingue "corregimiento oficial" de "zona no oficial sin padre confiable" (caso único: Costa del Este).
- **Columna `motivo_visualizacion`** agregada (no estaba en el diseño original) tras encontrar que el JSON de origen documenta que la exclusión de visualización de Pedregal **sigue pendiente de validación formal del consejo académico** — a diferencia de la exclusión de KNN/KMeans, que sí tuvo esa validación. Se preserva ese texto en vez de perderlo tras la carga.

## 3. Migración de estructura

`supabase/migrations/20260715040001_corregimientos_create_table.sql` — aplicada exitosamente vía `supabase db push`. Solo esta migración se ejecutó; las de `propiedades` (1.5.1) ya estaban registradas y no se re-corrieron, confirmando que el tracking del CLI funciona correctamente.

### 3.1 Verificación de estructura

| Elemento | Resultado |
|---|---|
| 9 columnas, tipos correctos | ✓ — `nombre` (text, PK), `es_oficial` (bool), `geom` (geometry, nullable), `hereda_de` (text, nullable), `zone_health_score` (numeric, nullable), `desglose_dimensiones` (jsonb, nullable), `estado_zone_health` (text, default `'calculado'`), `no_visualizado` (bool, default `false`), `motivo_visualizacion` (text, nullable) |
| `corregimientos_pkey` | `PRIMARY KEY (nombre)` ✓ |
| `corregimientos_hereda_de_fkey` | `FOREIGN KEY (hereda_de) REFERENCES corregimientos(nombre)` — self-referencing, verificado ✓ |
| `corregimientos_estado_zone_health_check` | `CHECK (estado_zone_health = ANY (ARRAY['calculado', 'sin_score_datos_insuficientes']))` ✓ |
| `idx_corregimientos_geom` | GiST sobre `geom`, presente ✓ |

## 4. Carga de datos

### 4.1 Incidentes resueltos durante la ejecución

1. **`load_dotenv()` ausente en el script** — `cargar_corregimientos.py` no cargaba `.env` al entorno, causando `KeyError: 'DATABASE_URL'` en el primer intento de conexión real. Corregido siguiendo la misma convención ya usada en `escalar_quality_scorer_6_2_6.py` (`find_dotenv`/`load_dotenv`). **Nota de proceso:** este era el primer intento de ejecución de punta a punta del script — las verificaciones previas (dos corridas de "resumen idéntico") solo probaron la lógica de lectura/transformación, no la conexión real, por lo que el problema no era detectable antes de este punto.
2. **Conectividad DNS al host directo de Supabase** — `db.ezutrurenerqgfmozbzz.supabase.co` resuelve únicamente a IPv6, sin conectividad IPv6 saliente en el entorno de ejecución. Resuelto actualizando `DATABASE_URL` en `.env` de forma permanente al *connection pooler* de Supabase (`aws-0-us-east-1.pooler.supabase.com:5432`, modo *session* — compatible con transacciones multi-statement), verificando que el formato de usuario incluyera el project ref (`postgres.ezutrurenerqgfmozbzz`), requerido en modo pooler. Cambio confirmado como seguro por tratarse de un `.env` de uso exclusivamente individual, sin riesgo de romper trabajo concurrente de otros miembros del equipo.

### 4.2 Resultado de la inserción

Transacción única, todo o nada (`with conn:` de `psycopg2`), SQL parametrizado sin f-strings. **9 filas insertadas exitosamente**, orden ajustado para respetar la FK autoreferenciada (filas sin padre insertadas antes que las dependientes).

### 4.3 Verificación fila por fila contra el checkpoint

| Zona | `es_oficial` | `hereda_de` | `estado_zone_health` | `no_visualizado` | `zone_health_score` |
|---|---|---|---|---|---|
| Bella Vista | true | null | calculado | false | 0.5367... |
| Betania | true | null | calculado | false | 0.8783... |
| Costa del Este | **false** | **null** | **sin_score_datos_insuficientes** | false | **null** |
| El Cangrejo | false | Bella Vista | calculado | false | 0.5367... |
| Marbella | false | Bella Vista | calculado | false | 0.5367... |
| Obarrio | false | Bella Vista | calculado | false | 0.5367... |
| Parque Lefevre | true | null | calculado | false | 0.3765... |
| Pedregal | true | null | calculado | **true** | 0.1076... |
| San Francisco | true | null | calculado | false | 0.6888... |

**Todos los puntos críticos del diseño confirmados:**
- Las 5 oficiales tienen `hereda_de = null`.
- El Cangrejo/Marbella/Obarrio heredan de Bella Vista con score copiado literalmente (mismo valor exacto: `0.5367...`).
- Costa del Este es el único caso con `es_oficial = false` **y** `hereda_de = null` simultáneamente — caso especial sin padre, correctamente distinguido de los 5 oficiales gracias a la columna `es_oficial`.
- Pedregal es el único con `no_visualizado = true`, con `motivo_visualizacion` poblado con el texto completo del JSON de origen (incluyendo la nota de validación pendiente con el consejo académico).

Sin discrepancias entre lo diseñado, los datos de origen, y lo cargado.

## 5. Decisiones confirmadas por esta ejecución (no reabrir)

- **`corregimientos` tiene 9 filas**, con `es_oficial` como discriminador explícito entre corregimiento administrativo real y zona de scope comercial.
- **`hereda_de` es una FK autoreferenciada real**, no solo una convención de aplicación — la integridad referencial la garantiza Postgres, no el código del pipeline.
- **`DATABASE_URL` en `.env` apunta permanentemente al pooler de Supabase**, no al host directo — cualquier script futuro que reutilice esta variable (incluyendo la carga pendiente de `geom`) debe asumir esta ruta de conexión.
- **La exclusión de visualización de Pedregal sigue sin validación formal del consejo académico** — ahora visible directamente en la base de datos vía `motivo_visualizacion`, no solo en un archivo intermedio del pipeline. Queda como pendiente de gobernanza, no de esquema.

## 6. Pendiente explícito, fuera de alcance de esta Acta

1. **`geom`** — poblar desde los shapefiles procesados de Feature 1.3.1 (5 polígonos reales; las 4 zonas heredadas permanecen con `geom = NULL` por diseño).
2. **Dónde vive la lógica de resolución de herencia de `geom`** para el mapa (backend vs. frontend) — decisión de arquitectura de Épica 5.
3. **Corrección de deuda documental:** `CLAUDE.md` sigue citando los pesos originales de 5 dimensiones del Zone Health Index (incluyendo socioeconómico), cuando los pesos vigentes desde Feature 1.4.5 son 4 dimensiones redistribuidas. No afectó esta carga, pero debe corregirse para evitar confusión futura.
4. **Verificar si otros scripts del pipeline que usan `DATABASE_URL`** tienen el mismo olvido de `load_dotenv()` detectado aquí.

## 7. Estado

**Feature 1.5.2: CERRADA.** Estructura y datos verificados, sin discrepancias. FK de `propiedades.corregimiento` hacia `corregimientos(nombre)` queda desbloqueada para convertirse de CHECK a FK dura cuando se decida abordarlo (fuera de alcance de 1.5.2 — nota: la FK debe excluir o tratar aparte el valor `'zona_no_determinada'`, que no tiene fila correspondiente en `corregimientos`).

**Siguiente tarea en la secuencia sugerida:** `1.5.5` (aislada, no depende de las demás; recomendación ya dada pendiente de confirmación formal) o `1.5.3` (investigación previa sobre persistencia de dato crudo de amenidades).
