"""Búsqueda estructurada pura sobre `propiedades` (Feature 4.3.2) — sin NLP, sin embeddings.

Consumida por `POST /search/filtros`, la barra de filtros del frontend (Feature 5.2.2). A
diferencia de `buscar_propiedades_ann()` (2.2.1, `busqueda_ann.py`), esta función no recibe
`query_embedding` ni ordena por `<=>` — es un `WHERE` estructurado simple, sin componente de
similitud semántica. Vive en su propio módulo, no como una variante de `busqueda_ann.py`, porque
esa función tiene la responsabilidad estrecha de "ANN + filtros" (su propio docstring: "el cast a
halfvec... para que el planner pueda usar el índice HNSW") — forzar un modo sin embedding ahí
mezclaría dos responsabilidades (con-ranking-semántico / sin-ranking-semántico) en una firma que
ya es bastante cargada.

**Filtro base, igual que `buscar_propiedades_ann()`/`m1_buscar_matches()` (decisión de M1, no se
reabre aquí):** excluye `corregimiento = 'zona_no_determinada'` y `precio_no_evaluable = true` —
mismo criterio en todo el proyecto de qué fila es "evaluable" para un usuario final.

**Orden — `price_usd asc, listing_id asc` (spec 4 de esta tarea, decisión explícita):**
precio ascendente es el criterio por defecto más común en una barra de filtros de bienes raíces
(el usuario típicamente filtra por presupuesto y espera ver las opciones más baratas primero
dentro de ese rango). `listing_id asc` como desempate: hay precios repetidos en el catálogo real
(varios listados en el mismo edificio/proyecto cotizan igual), y sin un segundo criterio
determinista Postgres no garantiza el mismo orden entre páginas — con paginación por
`LIMIT`/`OFFSET` (ver abajo) eso puede duplicar o saltar filas entre requests. No se usa
`scraped_at desc` (alternativa considerada, "más recientes primero"): no hay una noción de
"nuevo listado" relevante para un usuario filtrando por precio/zona/tipo — sí sería el criterio
correcto para un futuro feed de "últimos publicados", pero no es el caso de uso de esta tarea.

**Paginación — `LIMIT`/`OFFSET` simple, no cursor-based (spec 5):** el catálogo (1,177 filas) es
lo bastante pequeño para que el costo de `OFFSET` en páginas altas sea irrelevante en la práctica
(a diferencia de un catálogo de millones de filas, donde `OFFSET` se vuelve costoso) — no se
justifica la complejidad adicional de un cursor basado en `(price_usd, listing_id)` para este
volumen. Se devuelve `total` (vía `count(*)` separado, mismo `WHERE`, sin `LIMIT`/`OFFSET`) para
que el frontend pueda calcular el número de páginas sin adivinar.
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

TIPOS_VALIDOS = frozenset(TIPO_SINGULAR_A_PLURAL)

ZONAS_VALIDAS = frozenset({
    "San Francisco", "Bella Vista", "Parque Lefevre", "Betania", "Pedregal",
    "El Cangrejo", "Marbella", "Obarrio", "Costa del Este",
})


class FiltroBusquedaError(ValueError):
    """`zona` o `tipo_inmueble` no están en el conjunto válido del scope del proyecto."""


def _validar_filtros(zona: str | None, tipo_inmueble: str | None) -> None:
    if zona is not None and zona not in ZONAS_VALIDAS:
        raise FiltroBusquedaError(
            f"Zona inválida: '{zona}'. Zonas válidas: {sorted(ZONAS_VALIDAS)}."
        )
    if tipo_inmueble is not None and tipo_inmueble not in TIPOS_VALIDOS:
        raise FiltroBusquedaError(
            f"tipo_inmueble inválido: '{tipo_inmueble}'. Valores válidos: {sorted(TIPOS_VALIDOS)}."
        )


def _where_y_params(
    zona: str | None,
    tipo_inmueble: str | None,
    precio_min: float | None,
    precio_max: float | None,
    habitaciones_min: int | None,
    banos_min: int | None,
) -> tuple[str, dict]:
    where_clauses = ["corregimiento != 'zona_no_determinada'", "precio_no_evaluable = false"]
    params: dict = {}

    if zona is not None:
        where_clauses.append("corregimiento = %(zona)s")
        params["zona"] = zona
    if tipo_inmueble is not None:
        where_clauses.append("tipo_inmueble = %(tipo_inmueble)s")
        params["tipo_inmueble"] = TIPO_SINGULAR_A_PLURAL[tipo_inmueble]
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

    return " and ".join(where_clauses), params


def buscar_propiedades_filtros(
    zona: str | None = None,
    tipo_inmueble: str | None = None,
    precio_min: float | None = None,
    precio_max: float | None = None,
    habitaciones_min: int | None = None,
    banos_min: int | None = None,
    limit: int = 20,
    offset: int = 0,
    conn=None,
) -> dict:
    """Filtrado estructurado puro sobre `propiedades` — sin embedding, sin ranking semántico.

    Lanza `FiltroBusquedaError` si `zona` no está en las 9 zonas del scope o `tipo_inmueble` no
    es uno de los 5 tipos válidos (mismo criterio de validación explícita que
    `estructurar_perfil_usuario()`, 2.2.2 — no se acepta cualquier string).

    Devuelve `{"total": int, "propiedades": [...]}`. `total` es el conteo completo bajo los
    mismos filtros, sin `limit`/`offset` — para que el caller pueda paginar sin adivinar cuántas
    páginas hay. Orden: `price_usd asc, listing_id asc` (ver docstring del módulo).

    `conn`: conexión ya abierta (ej. de `app.db.pool`) — si se pasa, no se cierra aquí, mismo
    contrato que `buscar_propiedades_ann()` (2.2.1/2.2.5).
    """
    _validar_filtros(zona, tipo_inmueble)

    where_sql, params = _where_y_params(
        zona, tipo_inmueble, precio_min, precio_max, habitaciones_min, banos_min
    )

    sql_total = f"select count(*) from propiedades where {where_sql}"
    sql_pagina = f"""
        select listing_id, corregimiento, tipo_inmueble, price_usd, bedrooms, bathrooms, area_m2,
               title, imagenes, descripcion
        from propiedades
        where {where_sql}
        order by price_usd asc, listing_id asc
        limit %(limit)s offset %(offset)s
    """

    conn_propia = conn is None
    if conn_propia:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            cur.execute(sql_total, params)
            total = cur.fetchone()[0]

            cur.execute(sql_pagina, {**params, "limit": limit, "offset": offset})
            columnas = [desc[0] for desc in cur.description]
            propiedades = [dict(zip(columnas, fila)) for fila in cur.fetchall()]
    finally:
        if conn_propia:
            conn.close()

    return {"total": total, "propiedades": propiedades}
