-- 3.1.6 (pre-batch) — agrega confianza_reducida y n_comparables a valuacion_semaforo_knn.
--
-- Decisión tomada explícitamente antes de cargar el batch de 3.1.6: evaluar_precio_propiedad()
-- (3.1.5, backend/app/services/valuacion_knn.py) ya calcula confianza_reducida y n_comparables
-- por fila (diagnóstico de cuántos de los k=5 comparables esperados realmente se encontraron),
-- pero el DDL original aprobado de esta tabla (20260715040004_scores_valuacion_compatibilidad_
-- sesiones.sql) no reservó columnas para ese diagnóstico. Se migra ahora, antes del batch, en
-- vez de descartar esa trazabilidad en el INSERT.
--
-- ADVERTENCIA — hallazgo de esta sesión, no asumir el estado de CLAUDE.md sin re-verificar:
-- CLAUDE.md ("Feature 1.5 (schema DB): no iniciado") y el propio encabezado de
-- 20260715040004_scores_valuacion_compatibilidad_sesiones.sql ("NO EJECUTADA CONTRA SUPABASE")
-- describen un schema todavía no aplicado. Verificado contra la base real
-- (ezutrurenerqgfmozbzz.supabase.co) en esta sesión: las 7 migraciones locales YA están
-- aplicadas remotamente (`supabase migration list`, local == remote para todas), con datos reales
-- cargados (propiedades=1177, corregimientos=9, amenidades=238, conjunto_referencia_m1=577,
-- valuacion_quality_scorer=1168). valuacion_semaforo_knn específicamente existe con las 5
-- columnas documentadas y 0 filas (consistente con "vacía hasta que el batch 3.1.6 corra"). Esta
-- migración es segura de todos modos (ADD COLUMN con DEFAULT sobre una tabla vacía, no
-- destructiva), pero la discrepancia de CLAUDE.md/encabezados anteriores debe corregirse aparte
-- — no se corrige en este archivo para no mezclar una ALTER TABLE real con edición de
-- documentación.
--
-- APLICADA CONTRA SUPABASE — ejecutada 2026-07-15 vía `supabase db push` con confirmación
-- explícita del usuario, verificada con `supabase migration list` (local == remote) y con
-- `information_schema.columns` (las 2 columnas nuevas existen, `confianza_reducida` boolean not
-- null default false, `n_comparables` smallint nullable). Como parte de la misma sesión, se
-- corrigieron además los 6 encabezados de migración con el "NO EJECUTADA CONTRA SUPABASE" falso
-- (este archivo incluido) y las afirmaciones de estado de Feature 1.5 en CLAUDE.md.

alter table valuacion_semaforo_knn
    add column confianza_reducida boolean not null default false,
    add column n_comparables       smallint;

comment on column valuacion_semaforo_knn.confianza_reducida is
    'De evaluar_precio_propiedad() (3.1.5): true cuando buscar_comparables_knn() (3.1.1) '
    'devolvió menos de k=5 comparables para esa zona/tipo/atributos — la categoría de semáforo '
    'se calculó igual (no se descarta), pero con menos evidencia que el diseño ideal del modelo. '
    'Default false para filas existentes/futuras que no pasen por este cálculo explícitamente.';

comment on column valuacion_semaforo_knn.n_comparables is
    'De evaluar_precio_propiedad() (3.1.5): cuántos comparables reales sostuvieron precio_predicho '
    '(<=5, el k de diseño del KNN de producción, Notebook 2 / Feature 6.2.4). NULL para filas '
    'que no pasen por este cálculo (no se fuerza un 5 falso).';
