-- Feature 1.5b — decisión de dimensión de embedding (Context-MD/Feature_1_5b_Embedding_Dimension_Cierre.md)
-- Alcance: SOLO la columna embedding. El resto de la tabla propiedades (1.5.1 completo,
-- incluyendo geom, campos de DOC-05 §4.2, índice GiST) no está definido en este repo todavía
-- y no se inventa aquí.
--
-- APLICADA CONTRA SUPABASE — verificado 2026-07-15 (sesión Feature 3.1.6, migración 040006):
-- `propiedades.embedding` existe en la base real (`supabase migration list`, local == remote).
-- Esta línea decía "No ejecutado... pendiente de aplicar" y era falsa — corregida como parte de
-- una auditoría completa de encabezados de migración, ver CLAUDE.md para el resto de hallazgos
-- de esa sesión. El índice HNSW comentado más abajo (`embedding vector_cosine_ops`, sin cast a
-- halfvec) NO es el que terminó aplicado: el real es
-- `20260715040005_propiedades_embedding_hnsw_index.sql`
-- (`idx_propiedades_embedding_hnsw`, sobre `halfvec(3072)`, `m=16, ef_construction=64`) — no
-- correr el bloque comentado de este archivo asumiendo que sigue pendiente.

-- Requiere pgvector habilitado (1.1.1, completado).

alter table if exists propiedades
    add column if not exists embedding vector(3072);

-- Índice HNSW (parte de la condición de Done de 1.5.1, cosine similarity — mismo espacio
-- vectorial que M3, ver 2.1.1). Crear después de tener volumen de catálogo cargado
-- (1.5.6 mide rendimiento bajo volumen real antes de fijar parámetros m/ef_construction).
-- create index if not exists idx_propiedades_embedding_hnsw
--     on propiedades using hnsw (embedding vector_cosine_ops);
