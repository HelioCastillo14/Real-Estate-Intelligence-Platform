-- Feature 1.5b — decisión de dimensión de embedding (Context-MD/Feature_1_5b_Embedding_Dimension_Cierre.md)
-- Alcance: SOLO la columna embedding. El resto de la tabla propiedades (1.5.1 completo,
-- incluyendo geom, campos de DOC-05 §4.2, índice GiST) no está definido en este repo todavía
-- y no se inventa aquí. No ejecutado contra Supabase — artifact de repo pendiente de aplicar.

-- Requiere pgvector habilitado (1.1.1, completado).

alter table if exists propiedades
    add column if not exists embedding vector(3072);

-- Índice HNSW (parte de la condición de Done de 1.5.1, cosine similarity — mismo espacio
-- vectorial que M3, ver 2.1.1). Crear después de tener volumen de catálogo cargado
-- (1.5.6 mide rendimiento bajo volumen real antes de fijar parámetros m/ef_construction).
-- create index if not exists idx_propiedades_embedding_hnsw
--     on propiedades using hnsw (embedding vector_cosine_ops);
