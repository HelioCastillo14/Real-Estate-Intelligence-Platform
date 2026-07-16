"""Endpoint `POST /match/score` (Feature 2.2.5) — consumido internamente por M3 (Épica 4).

Contrato de interfaz de referencia: `m1_buscar_matches()` (Notebook 5, Feature 6.2.7,
"v0 — sujeto a revisión en Épica 4") — usado como referencia de diseño de campos de filtro,
no copiado tal cual (esa versión filtra un DataFrame en memoria y no calcula ANN).

Decisión de diseño — el embedding se RECIBE ya calculado, no se calcula en este endpoint:
`generar_embedding()` (2.1.2) llama a la API de Gemini (latencia de red externa + costo por
llamada, ver `CLAUDE.md`). Este endpoint es puro ANN + explicación estructurada; quien arma la
consulta (M3, Épica 4) es quien tiene el texto de origen (una consulta conversacional, o una
descripción de perfil) y ya debe llamar a `generar_embedding()` por su cuenta antes de golpear
este endpoint — desacopla la latencia/disponibilidad de Gemini de la latencia de este endpoint,
y evita que este endpoint dependa de `GEMINI_API_KEY` para nada. Documentado aquí explícitamente
porque la especificación de esta tarea pedía decidir y documentar, no asumir.

Pooling (Feature 2.2.5, resuelve hallazgo de 2.2.1): la conexión se toma de
`app.db.pool` (inicializado una vez en el `lifespan` de `main.py`), nunca `psycopg2.connect()`
por request.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.pool import obtener_pool
from app.services.busqueda_ann import DIMENSION_ESPERADA, buscar_propiedades_ann
from app.services.explicador_compatibilidad import explicar_compatibilidad
from app.services.perfil_usuario import estructurar_perfil_usuario

router = APIRouter(prefix="/match", tags=["match"])


class PerfilRequest(BaseModel):
    precio_maximo: float | None = None
    habitaciones_min: int | None = None
    zonas_preferidas: list[str] | None = None


class DimensionExplicacionResponse(BaseModel):
    dimension: str
    cumplido: bool | None
    criterio_perfil: str | None
    valor_propiedad: Any
    detalle: str


class CandidatoMatchResponse(BaseModel):
    listing_id: int
    corregimiento: str
    tipo_inmueble: str
    price_usd: int
    bedrooms: int | None
    bathrooms: int | None
    area_m2: float | None
    distancia_coseno: float
    explicacion: list[DimensionExplicacionResponse]


class MatchScoreRequest(BaseModel):
    query_embedding: list[float] = Field(
        ...,
        description=(
            f"Embedding ya calculado ({DIMENSION_ESPERADA}-dim, gemini-embedding-001) — este "
            f"endpoint no llama a Gemini, ver docstring del módulo."
        ),
    )
    perfil: PerfilRequest
    k: int = Field(default=10, ge=1, le=100)
    transporte_minimo: float | None = Field(
        default=None,
        description="Umbral 0-1 sobre el score compuesto de transporte (2.2.4) — no una distancia.",
    )


class MatchScoreResponse(BaseModel):
    n_candidatos: int
    candidatos: list[CandidatoMatchResponse]


@router.post("/score", response_model=MatchScoreResponse)
def match_score(request: MatchScoreRequest) -> MatchScoreResponse:
    if len(request.query_embedding) != DIMENSION_ESPERADA:
        raise HTTPException(
            status_code=422,
            detail=(
                f"query_embedding debe tener {DIMENSION_ESPERADA} dimensiones "
                f"(gemini-embedding-001), recibió {len(request.query_embedding)}."
            ),
        )

    try:
        perfil = estructurar_perfil_usuario(
            precio_maximo=request.perfil.precio_maximo,
            habitaciones_min=request.perfil.habitaciones_min,
            zonas_preferidas=request.perfil.zonas_preferidas,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # zonas_preferidas es una lista (perfil persistente, 2.2.2); buscar_propiedades_ann()
    # (2.2.1) solo filtra por una `zona` singular en SQL (mismo campo que m1_buscar_matches
    # de 6.2.7). No se fuerza aquí un IN-list en la query para no reabrir la firma ya cerrada
    # de 2.2.1 — el filtrado por zonas_preferidas ocurre en la explicación por candidato
    # (dimensión "zona" de explicar_compatibilidad), no restringe el conjunto de candidatos.
    db_pool = obtener_pool()
    conn = db_pool.getconn()
    try:
        candidatos_db = buscar_propiedades_ann(
            request.query_embedding,
            k=request.k,
            precio_max=perfil["precio_maximo"],
            habitaciones_min=perfil["habitaciones_min"],
            conn=conn,
        )
    finally:
        db_pool.putconn(conn)

    candidatos_response = []
    for candidato in candidatos_db:
        explicacion = explicar_compatibilidad(perfil, candidato, transporte_minimo=request.transporte_minimo)
        candidatos_response.append(CandidatoMatchResponse(
            listing_id=candidato["listing_id"],
            corregimiento=candidato["corregimiento"],
            tipo_inmueble=candidato["tipo_inmueble"],
            price_usd=candidato["price_usd"],
            bedrooms=candidato["bedrooms"],
            bathrooms=candidato["bathrooms"],
            area_m2=float(candidato["area_m2"]) if candidato["area_m2"] is not None else None,
            distancia_coseno=candidato["distancia_coseno"],
            explicacion=explicacion,
        ))

    return MatchScoreResponse(n_candidatos=len(candidatos_response), candidatos=candidatos_response)
