"""Búsqueda ANN sobre propiedades.embedding (Feature 2.2.1).

Traduce a SQL real la lógica de filtrado estructurado de `m1_buscar_matches()`
(Notebook 5, Feature 6.2.7, `notebooks/05_m3_nlp_orchestration.ipynb` celda 8, contrato
"v0 — sujeto a revisión en Épica 4") — esa versión filtra sobre un DataFrame en memoria,
esta filtra en SQL contra `propiedades` real, usando el índice HNSW de Feature 2.1.4
(`idx_propiedades_embedding_hnsw`, sobre `halfvec(3072)`, cosine).

Filtro base (igual que `m1_buscar_matches`, no configurable — decisión de M1, no se reabre
aquí): excluye `corregimiento = 'zona_no_determinada'` y `precio_no_evaluable = true`.

Filtros opcionales, mismos nombres que `m1_buscar_matches`: `zona` (=`corregimiento`),
`tipo_inmueble` (singular, ej. "Apartamento" — se mapea a plural como en 6.2.7, la columna
real de `propiedades.tipo_inmueble` guarda plural: "Apartamentos", "Casas", "Edificios",
"Locales", "Terrenos"), `precio_min`, `precio_max`, `habitaciones_min` (`bedrooms >=`),
`banos_min` (`bathrooms >=`).

El cast a `halfvec(3072)` es obligatorio en ambos lados del `<=>` para que el planner pueda
usar `idx_propiedades_embedding_hnsw` (ver Feature 2.1.4: el índice es una expresión sobre
halfvec, la columna `embedding` real sigue siendo `vector(3072)` full precision).

`title`/`imagenes`/`descripcion` (Épica 5, sesión de conexión de Resultados a
`/search/nlp`): mismo criterio ya aplicado en `busqueda_estructurada.py` para
`/search/filtros` — evita que el caller (`/search/nlp`) tenga que hacer un fetch
adicional por candidato a `GET /propiedades/{id}` solo para completar la tarjeta con
foto/título. No afecta a `/match/score` (`match.py`), el otro consumidor de esta
función: `CandidatoMatchResponse` solo lee las claves que ya conocía del dict, las 3
nuevas quedan sin usar ahí, sin romper nada.

`transporte_score` (Feature 2.2.5): la query hace LEFT JOIN contra `corregimientos` para
devolver `desglose_dimensiones->>'transporte'` por fila — es el insumo que
`explicar_compatibilidad()` (2.2.4) necesita para evaluar esa dimensión, sin que el caller
tenga que hacer un segundo round-trip. `NULL` para zonas sin score compuesto (ej. Costa del
Este, decisión ya cerrada del proyecto) — `explicar_compatibilidad()` ya distingue ese caso.

`conn` (Feature 2.2.5 — resuelve el hallazgo de 2.2.1): parámetro opcional. Si se pasa una
conexión (tomada de un pool, ver `backend/app/db/pool.py`), esta función la usa y NO la cierra
— el ciclo de vida es responsabilidad de quien la pidió al pool. Si no se pasa (`None`, default),
mantiene el comportamiento standalone de 2.2.1: abre y cierra su propia conexión — útil para
pruebas aisladas sin depender de un pool ya inicializado, pero es la ruta lenta (~1s de
reconexión por llamada, ver hallazgo de 2.2.1) y NO es la que usa el endpoint de producción.
"""

import os

import psycopg2

TIPO_SINGULAR_A_PLURAL = {
    "Apartamento": "Apartamentos",
    "Casa": "Casas",
    "Edificio": "Edificios",
    "Local": "Locales",
    "Terreno": "Terrenos",
}

DIMENSION_ESPERADA = 3072


def _vector_a_literal(vector: list[float]) -> str:
    if len(vector) != DIMENSION_ESPERADA:
        raise ValueError(f"embedding de consulta con dimensión {len(vector)}, se esperaban {DIMENSION_ESPERADA}")
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


def buscar_propiedades_ann(
    query_embedding: list[float],
    k: int = 10,
    zona: str | None = None,
    tipo_inmueble: str | None = None,
    precio_min: float | None = None,
    precio_max: float | None = None,
    habitaciones_min: int | None = None,
    banos_min: int | None = None,
    conn=None,
) -> list[dict]:
    """Top-k propiedades más cercanas (cosine, vía HNSW) a `query_embedding`, con filtros
    estructurados opcionales aplicados en SQL (WHERE), antes del ORDER BY del `<=>`.

    `conn`: conexión psycopg2 ya abierta (ej. de un pool) — si se pasa, no se cierra aquí. Si
    es `None`, abre y cierra una conexión propia (ver docstring del módulo).
    """
    where_clauses = ["corregimiento != 'zona_no_determinada'", "precio_no_evaluable = false"]
    params: dict = {"query_embedding": _vector_a_literal(query_embedding), "k": k}

    if zona is not None:
        where_clauses.append("corregimiento = %(zona)s")
        params["zona"] = zona
    if tipo_inmueble is not None:
        where_clauses.append("tipo_inmueble = %(tipo_inmueble)s")
        params["tipo_inmueble"] = TIPO_SINGULAR_A_PLURAL.get(tipo_inmueble, tipo_inmueble)
    if precio_min is not None:
        where_clauses.append("price_usd >= %(precio_min)s")
        params["precio_min"] = precio_min
    if precio_max is not None:
        where_clauses.append("price_usd <= %(precio_max)s")
        params["precio_max"] = precio_max
    if habitaciones_min is not None:
        where_clauses.append("bedrooms >= %(habitaciones_min)s")
        params["habitaciones_min"] = habitaciones_min
    if banos_min is not None:
        where_clauses.append("bathrooms >= %(banos_min)s")
        params["banos_min"] = banos_min

    sql = f"""
        select p.listing_id, p.corregimiento, p.tipo_inmueble, p.price_usd, p.bedrooms, p.bathrooms, p.area_m2,
               p.title, p.imagenes, p.descripcion,
               (c.desglose_dimensiones->>'transporte')::float as transporte_score,
               p.embedding::halfvec({DIMENSION_ESPERADA}) <=> %(query_embedding)s::halfvec({DIMENSION_ESPERADA}) as distancia_coseno
        from propiedades p
        left join corregimientos c on c.nombre = p.corregimiento
        where {" and ".join(where_clauses)}
        order by p.embedding::halfvec({DIMENSION_ESPERADA}) <=> %(query_embedding)s::halfvec({DIMENSION_ESPERADA})
        limit %(k)s
    """

    conn_propia = conn is None
    if conn_propia:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columnas = [desc[0] for desc in cur.description]
            return [dict(zip(columnas, fila)) for fila in cur.fetchall()]
    finally:
        if conn_propia:
            conn.close()
