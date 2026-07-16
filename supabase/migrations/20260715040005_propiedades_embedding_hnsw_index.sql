-- Índice HNSW sobre propiedades.embedding — Feature 2.1.4 / 1.5.6 (mismo cierre para ambas,
-- ver Context-MD). Diferido desde 20260715032111_propiedades_embedding.sql y
-- 20260715040000_propiedades_create_table.sql hasta tener volumen real de catálogo cargado
-- (1,177/1,177 filas con embedding poblado, Feature 2.1.3 CERRADA).

-- Requiere pgvector >= 0.5.0 para soporte HNSW — confirmado contra la instancia real:
-- extversion = 0.8.0 (select extname, extversion from pg_extension where extname = 'vector').

-- Métrica: cosine. Confirmado, no asumido: el scorer híbrido de M1 (Notebook 1, Feature 6.2.3,
-- notebooks/01_m1_preference_matching.ipynb celda 24, similitud_coseno_matriz()) usa similitud
-- coseno sobre este mismo espacio vectorial (gemini-embedding-001, 3072 dimensiones) para el
-- componente semántico del matching. M3 (2.1.1) opera sobre el mismo espacio vectorial — ver
-- comentario ya existente en 20260715032111_propiedades_embedding.sql. No hay ningún punto del
-- proyecto que use L2 o producto interno sobre este embedding.

-- BLOQUEO ENCONTRADO Y RESUELTO (intento previo de este mismo archivo, no aplicado):
-- `create index ... using hnsw (embedding vector_cosine_ops)` fue RECHAZADO por la instancia
-- real: "column cannot have more than 2000 dimensions for hnsw index" (SQLSTATE 54000).
-- pgvector permite almacenar hasta 16,000 dimensiones en una columna `vector`, pero el índice
-- HNSW sobre el tipo `vector` (32-bit por dimensión) tiene un límite duro de 2,000 dimensiones
-- indexables — no es un problema de m/ef_construction, ningún ajuste de parámetros lo evita.
-- embedding es vector(3072) (decisión ya cerrada de 1.5b/6.2.3/2.1.2, no se reabre aquí).
--
-- Solución aplicada: índice de EXPRESIÓN sobre `halfvec(3072)` (media precisión, 16-bit por
-- dimensión), cuyo límite de HNSW es 4,000 dimensiones — 3072 cabe. Requiere pgvector >= 0.7.0
-- para el tipo halfvec — confirmado contra la misma instancia real (extversion 0.8.0).
-- La columna `propiedades.embedding` NO cambia de tipo: sigue siendo `vector(3072)` full
-- precision. El cast a halfvec ocurre únicamente dentro de la definición del índice; toda
-- consulta que quiera aprovechar este índice debe castear ambos lados del operador `<=>` a
-- `halfvec(3072)` explícitamente (ver prueba de latencia de esta misma tarea).
-- Trade-off aceptado: pérdida de precisión de 32-bit a 16-bit dentro del índice (no en el dato
-- almacenado), impacto esperado marginal en recall de ANN — decisión reversible, documentada
-- aquí, no evaluada cuantitativamente en este repo.

-- Parámetros: m=16, ef_construction=64 — valores por defecto de pgvector. No hay evidencia
-- documentada en el proyecto (medición de latencia bajo volumen real, o cualquier otra) que
-- justifique desviarse de los defaults, así que no se inventa tuning aquí. Si una medición
-- futura bajo carga real de producción muestra que no alcanza el objetivo de latencia, ese
-- ajuste se hace como una decisión separada y documentada, no en esta migración.

create index if not exists idx_propiedades_embedding_hnsw
    on propiedades using hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops)
    with (m = 16, ef_construction = 64);
