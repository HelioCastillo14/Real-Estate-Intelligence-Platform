# Ajuste WBS — Feature 1.5.5: Esquema de `conjunto_referencia_m1`

**Fecha:** 2026-07-15
**Estado:** Diseño aprobado — pendiente de ejecución
**Fuente de las decisiones:** `Feature_6_2_3_M1_Preference_Matching_Cierre.md` (cerrado 2026-07-13) + `pipeline/data/processed/conjunto_referencia_m1_6_2_3.json` (materializado en esta sesión) + decisión de esta sesión (formato perfil+reglas, congelado no dinámico)

---

## 1. Decisión de fondo — dos discrepancias resueltas, no una

### 1.1 Formato: perfiles + reglas + N:M, no pares individuales

El WBS original (`2.3.1`) especificaba 15-25 pares perfil-propiedad con ranking conocido por construcción. Lo que `6.2.3` construyó y ya validó (Precision@k aprobado, CP-2) son **6 perfiles de lifestyle** con reglas estructuradas + criterio cualitativo, cada uno matched contra un conjunto de propiedades (n=43 a n=199), no contra un ranking par-a-par.

**Se adopta el formato real**, no se reconstruye en pares — más barato, más fiel a la evidencia ya generada y aprobada, consistente con el patrón que M3 ya usa para resultados estructurados.

### 1.2 Congelado, no dinámico — decisión nueva de esta sesión

**Hallazgo que forzó esta decisión:** los `listing_id` del ground truth nunca se materializaron — vivían únicamente en memoria del notebook (`ground_truth_final`), recalculados en cada ejecución. Solo los conteos agregados (43-199) sobrevivieron como output guardado.

**Se decidió congelar (no recalcular dinámicamente) por una razón concreta:** el Precision@k de `6.2.3` ya fue calculado y aprobado (CP-2) contra un catálogo específico, en un momento específico. Si el ground truth se recalculara en cada consulta contra el catálogo vigente, cualquier comparación futura de Precision@k perdería validez — es el equivalente a que un conjunto de test de ML cambie entre evaluaciones sin que nadie lo note. Congelar preserva la comparabilidad de la métrica ya reportada, consistente con lo que la propia Acta de Datos ya establecía: *"Nunca mezclado con el catálogo real."*

**Consecuencia de diseño:** el ground truth se materializó como script standalone (`pipeline/scripts/materializar_ground_truth_m1.py`, copia exacta de la lógica de celdas 2/5/7/8/11 del notebook, sin reinterpretación) contra `catalogo_residencial_limpio_6_2_1.csv`, produciendo `pipeline/data/processed/conjunto_referencia_m1_6_2_3.json` con hash SHA-256 del catálogo fuente para trazabilidad de versión. Conteos verificados exactos contra los ya reportados en `Feature_6_2_3_M1_Preference_Matching_Cierre.md` (49, 153, 60, 199, 43, 73).

## 2. Esquema — dos tablas, no una

Se separan reglas (estables, por perfil) de membresía (relación N:M hacia `propiedades`), en vez de forzar ambas en una sola tabla ancha — mismo criterio de normalización que ya aplicamos en `1.5.2` al separar atributos de zona de la relación de herencia.

```sql
create table if not exists perfiles_lifestyle (
    perfil                    text primary key,
    -- familia_con_ninos, profesional_joven, pareja_presupuesto_medio,
    -- inversionista_renta_corta, retirado_tranquilidad, presupuesto_ajustado_sin_auto

    reglas_estructurales      jsonb not null,
    -- {"corregimientos": [...] | "dinamico_zone_health_composite_min": 0.5,
    --  "corregimientos_resueltos_al_materializar": [...],  -- SOLO para perfiles con
    --  criterio dinámico (ver nota abajo)
    --  "price_min": ..., "price_max": ..., "bedrooms_min": ..., "bedrooms_max": ...,
    --  "area_min": ...}
    -- Nota: pareja_presupuesto_medio usa un criterio DINÁMICO (corregimientos con
    -- composite >= 0.5, no una lista fija). Se guarda AMBAS cosas: la regla dinámica
    -- (para que quede claro cómo se derivó) Y la lista resuelta al momento de
    -- materializar (para que el perfil sea auditable sin depender de que
    -- corregimientos.zone_health_score no cambie en el futuro). Sin la lista
    -- resuelta, este único perfil quedaría con trazabilidad más débil que los otros
    -- 5 — rompería la garantía de congelamiento que justifica toda esta tabla.

    criterio_cualitativo      jsonb not null,
    -- {"incluye": [...], "excluye": [...]} sobre `descripcion`, aplicado junto con
    -- `descripcion_fuente != 'ninguna'`.

    n_solo_estructural        integer not null,
    -- Conteo antes de aplicar el filtro cualitativo — preservado para trazabilidad
    -- del efecto de cada capa de filtro (ya reportado en 6.2.3 §4).

    n_ground_truth            integer not null,
    -- Conteo final (estructural + cualitativo) — debe coincidir con
    -- count(*) de conjunto_referencia_m1 para este perfil (constraint de aplicación,
    -- no de BD — ver §4).

    hash_catalogo_fuente      text not null,
    fecha_materializacion     timestamp not null
    -- Trazabilidad de versión: contra qué snapshot exacto de propiedades se generó
    -- este ground truth. Si el catálogo cambia sustancialmente, este campo permite
    -- confirmar si el ground truth sigue siendo válido o requiere re-materialización.
);

create table if not exists conjunto_referencia_m1 (
    perfil              text not null references perfiles_lifestyle(perfil),
    listing_id          bigint not null references propiedades(listing_id),
    flag_sintetico       boolean not null default true
        check (flag_sintetico = true),
    -- Constraint fijo por diseño (WBS original) — este conjunto nunca se mezcla con
    -- datos de usuario real. TRUE siempre, forzado explícitamente.

    primary key (perfil, listing_id)
);

comment on column perfiles_lifestyle.reglas_estructurales is
    'Filtros estructurales exactos de la celda 7 del notebook 01_m1_preference_matching.ipynb. '
    'Copia literal de la lógica ya cerrada en Feature 6.2.3 — no reinterpretar.';

comment on column perfiles_lifestyle.hash_catalogo_fuente is
    'SHA-256 de catalogo_residencial_limpio_6_2_1.csv al momento de materializar. '
    'Permite confirmar si este ground truth sigue correspondiendo al catálogo vigente.';

comment on table conjunto_referencia_m1 is
    'Ground truth CONGELADO (no recalculado dinámicamente) — preserva la validez '
    'comparativa del Precision@k ya aprobado en Feature 6.2.3 (CP-2). Fuente: '
    'pipeline/data/processed/conjunto_referencia_m1_6_2_3.json.';
```

## 3. Por qué dos tablas y no una tabla ancha con array de `listing_id`

Un `jsonb` o `bigint[]` con los IDs embebidos en `perfiles_lifestyle` sería más simple de escribir, pero rompe dos cosas: (1) no permite `FOREIGN KEY` real hacia `propiedades.listing_id` — la integridad referencial quedaría solo en el código de aplicación, no garantizada por Postgres; (2) no permite consultas directas tipo "¿en qué perfiles aparece esta propiedad?" sin deserializar JSON en cada query. La tabla de relación N:M es el patrón estándar para esto, y es consistente con cómo Postgres ya maneja el resto de tus relaciones (ej. `hereda_de` en `1.5.2`).

## 4. Verificación de consistencia — antes de cargar

`n_ground_truth` en `perfiles_lifestyle` debe coincidir exactamente con `COUNT(*)` de filas en `conjunto_referencia_m1` agrupadas por `perfil`, una vez cargados los datos. No es un CHECK de base de datos (Postgres no puede validar un conteo contra otra tabla vía CHECK simple) — es una verificación de aplicación que el script de carga debe correr como paso final, comparando contra los 6 valores ya confirmados: 49, 153, 60, 199, 43, 73.

## 5. Checkpoint de cierre de 1.5.5

- [ ] Migraciones `CREATE TABLE perfiles_lifestyle` y `CREATE TABLE conjunto_referencia_m1` ejecutadas contra Supabase (confirmación explícita, mismo protocolo)
- [ ] 6 filas en `perfiles_lifestyle`, con `hash_catalogo_fuente` poblado
- [ ] Total de filas en `conjunto_referencia_m1` = 49+153+60+199+43+73 = **577**
- [ ] Verificación de conteo por perfil coincide exactamente contra `perfiles_lifestyle.n_ground_truth`
- [ ] Todos los `listing_id` referenciados existen en `propiedades` (garantizado por la FK — si algún ID del JSON no existe en `propiedades`, el INSERT falla y hay que investigar por qué antes de forzar nada)
- [ ] `flag_sintetico = TRUE` en las 577 filas, sin excepción

## 6. Pendiente explícito, fuera de alcance de 1.5.5

- Si el catálogo se actualiza sustancialmente en el futuro (más scraping, correcciones), decidir si se re-materializa el ground truth (rompiendo comparabilidad con el CP-2 histórico) o se mantiene como snapshot fijo permanente — no es una decisión técnica, es de gobernanza académica sobre qué significa "el mismo experimento" para efectos de la tesis.
