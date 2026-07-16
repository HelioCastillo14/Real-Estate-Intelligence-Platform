"""Router `/search` — dos endpoints sin relación entre sí más allá del prefijo compartido.

`POST /search/filtros` (Feature 4.3.2) se agregó a este mismo archivo en vez de uno nuevo: ambos
endpoints devuelven propiedades bajo el mismo prefijo `/search` (consistencia de API para el
frontend, que ya trata `/search/*` como un solo namespace), y `busqueda_estructurada.py` (el
servicio que realmente hace el trabajo de 4.3.2) ya vive separado de `extraccion_intencion_nlp.py`
— no hay código NLP en este archivo por compartir router, solo el `include_router` y el prefijo.
Si este archivo creciera más, separar por sub-router sería razonable, pero 2 endpoints no lo
justifica todavía.

## `POST /search/nlp` (Feature 4.3.1) — orquestación completa de M3.

Encadena, sobre servicios de producción reales (no la simulación en memoria del notebook):
extracción de intención (`extraccion_intencion_nlp.py`, 4.1.2/4.2.1, `gemini-3.1-flash-lite`) ->
3 chequeos de fallback deterministicos (`clasificar()`) -> si procede, `generar_embedding()`
(2.1.2) -> `buscar_propiedades_ann()` (2.2.1) -> por candidato, `evaluar_precio_propiedad()`
(3.1.5) si la zona/tipo tiene cobertura en el KNN.

**Referencia de diseño, no copiada literal:** `orquestar_m3()` (Notebook 5, Feature 6.2.7, celda
8, contrato "v0 — sujeto a revisión en Épica 4") filtra un `DataFrame` en memoria y llama a un
prototipo de semáforo (`m2_enriquecer_semaforo()`) que no corrige el umbral desactualizado del
pickle (ver `comparables_knn.py`). Este endpoint usa los servicios reales ya cerrados: ANN sobre
`propiedades` vía HNSW (2.2.1) en vez del filtro en memoria, y `evaluar_precio_propiedad()`
(3.1.5, que sí corrige el umbral vía `calcular_semaforo_precio()`, 3.1.3) en vez del prototipo.

**Decisión — llamada interna a `buscar_propiedades_ann()`, no HTTP a `/match/score` (spec 1 de
esta tarea, decisión explícita):** `/match/score` (2.2.5) está diseñado para un perfil
*persistente* de usuario (`PerfilRequest` con `zonas_preferidas` como lista, pensado para
`explicar_compatibilidad()` por dimensión) — una consulta NLP puntual de M3 no tiene ese perfil,
tiene los campos de `ExtraccionIntencion` (`zona` singular, `tipo_inmueble`, rangos de precio,
`banos_min`), que mapean 1:1 a los parámetros nativos de `buscar_propiedades_ann()`. Llamar a
`/match/score` por HTTP forzaría además una segunda ronda de conexión/pool para algo que ya
corre en el mismo proceso — el pool de conexiones (2.2.5) ya resolvió el overhead de reconexión
que motivaría ir por HTTP en primer lugar. Este endpoint toma su propia conexión de
`app.db.pool` y llama las funciones de servicio directamente, igual que hace `match.py`.

**Enriquecimiento de semáforo, por candidato, no por lote (a diferencia del prototipo v0):** la
`zona` de la consulta es fija (un solo filtro SQL), pero `tipo_inmueble` es opcional en la
extracción — si no se especifica, los candidatos ANN pueden mezclar tipos. Se evalúa cobertura
de M2 por candidato (`corregimiento` + `tipo_inmueble` reales de esa fila), no una sola vez para
todo el lote, para no ocultar candidatos evaluables detrás de uno no evaluable del mismo lote.
`ComparablesKnnError` (3.1.1) se captura aquí, por candidato — el caller (este endpoint) decide
seguir procesando el resto, no lo mismo que 3.1.6 (batch de carga), que sí deja propagar el
error porque ahí cada fila es una corrida independiente que se loguea y salta.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.pool import obtener_pool
from app.services.busqueda_ann import TIPO_SINGULAR_A_PLURAL, buscar_propiedades_ann
from app.services.busqueda_estructurada import (
    FiltroBusquedaError,
    buscar_propiedades_filtros,
)
from app.services.comparables_knn import (
    TIPO_INMUEBLE_SOPORTADO,
    ZONAS_SOPORTADAS,
    ComparablesKnnError,
)
from app.services.embeddings import EmbeddingError, generar_embedding
from app.services.extraccion_intencion_nlp import (
    ExtraccionIntencionError,
    clasificar,
    extraer,
)
from app.services.valuacion_knn import evaluar_precio_propiedad

router = APIRouter(prefix="/search", tags=["search"])

_MOTIVO_POR_CATEGORIA = {
    "fallback_fuera_tema": "fuera_tema",
    "fallback_cobertura": "cobertura",
    "fallback_ambiguedad": "ambiguedad",
}


class SearchNlpRequest(BaseModel):
    consulta: str
    k: int = 10


class CriteriosExtraidosResponse(BaseModel):
    zona: str | None
    tipo_inmueble: str | None
    precio_min: float | None
    precio_max: float | None
    habitaciones_min: int | None
    banos_min: int | None
    confianza: float


class SemaforoResponse(BaseModel):
    categoria: Literal["verde", "amarillo", "rojo"]
    precio_predicho: float
    residual: float
    mae_referencia: float
    confianza_reducida: bool
    n_comparables: int


class CandidatoNlpResponse(BaseModel):
    listing_id: int
    corregimiento: str
    tipo_inmueble: str
    price_usd: int
    bedrooms: int | None
    bathrooms: int | None
    area_m2: float | None
    distancia_coseno: float
    semaforo: SemaforoResponse | None
    motivo_sin_semaforo: str | None


class ResultadosNlpResponse(BaseModel):
    n_candidatos: int
    candidatos: list[CandidatoNlpResponse]
    respuesta_final: str


class FallbackNlpResponse(BaseModel):
    motivo: Literal["fuera_tema", "cobertura", "ambiguedad"]
    mensaje: str
    zona_mencion_texto: str | None
    confianza: float


class SearchNlpResponse(BaseModel):
    consulta: str
    tipo: Literal["resultados", "fallback"]
    criterios_extraidos: CriteriosExtraidosResponse | None = None
    resultados: ResultadosNlpResponse | None = None
    fallback: FallbackNlpResponse | None = None


def _cobertura_m2(corregimiento: str | None, tipo_inmueble: str | None) -> tuple[bool | None, str | None]:
    """`True`/`False` si `corregimiento`+`tipo_inmueble` (singular, como los devuelve la
    extracción) tienen cobertura estructural en el KNN de producción (`comparables_knn.py`).
    `None` si no hay suficiente información (alguno de los dos es `None`) — la cobertura real
    solo se puede determinar por candidato en ese caso."""
    if corregimiento is None or tipo_inmueble is None:
        return None, None
    tipo_plural = TIPO_SINGULAR_A_PLURAL.get(tipo_inmueble, tipo_inmueble)
    motivos = []
    if corregimiento not in ZONAS_SOPORTADAS:
        motivos.append(f"'{corregimiento}' fuera del pool de entrenamiento KNN (Acta 1.2 §5.3)")
    if tipo_plural != TIPO_INMUEBLE_SOPORTADO:
        motivos.append(f"tipo_inmueble '{tipo_inmueble}' fuera del pool de entrenamiento (solo Apartamentos)")
    if motivos:
        return False, "; ".join(motivos)
    return True, None


@router.post("/nlp", response_model=SearchNlpResponse)
def search_nlp(request: SearchNlpRequest) -> SearchNlpResponse:
    try:
        extraccion = extraer(request.consulta)
    except ExtraccionIntencionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    categoria = clasificar(extraccion)

    if categoria != "exito":
        mensajes = {
            "fallback_fuera_tema": (
                "Tu consulta no parece tratarse de una búsqueda de propiedades — no la "
                "procesamos como tal. Si buscas un inmueble, prueba especificando zona, tipo "
                "de propiedad o presupuesto."
            ),
            "fallback_cobertura": (
                f"Mencionaste '{extraccion['zona_mencion_texto']}', pero esa ubicación está "
                f"fuera de las 9 zonas que cubre REIP actualmente. No podemos buscar ahí."
            ),
            "fallback_ambiguedad": (
                f"Tu consulta es ambigua para extraer criterios de búsqueda concretos "
                f"(confianza {extraccion['confianza']:.2f}, umbral 0.65: {extraccion['razon_confianza']}). "
                f"Prueba siendo más específico sobre zona, tipo de propiedad, precio o habitaciones."
            ),
        }
        return SearchNlpResponse(
            consulta=request.consulta,
            tipo="fallback",
            fallback=FallbackNlpResponse(
                motivo=_MOTIVO_POR_CATEGORIA[categoria],
                mensaje=mensajes[categoria],
                zona_mencion_texto=extraccion["zona_mencion_texto"],
                confianza=extraccion["confianza"],
            ),
        )

    try:
        embedding = generar_embedding(request.consulta)
    except EmbeddingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    db_pool = obtener_pool()
    conn = db_pool.getconn()
    try:
        candidatos_db = buscar_propiedades_ann(
            embedding,
            k=request.k,
            zona=extraccion["zona"],
            tipo_inmueble=extraccion["tipo_inmueble"],
            precio_min=extraccion["precio_min"],
            precio_max=extraccion["precio_max"],
            habitaciones_min=extraccion["habitaciones_min"],
            banos_min=extraccion["banos_min"],
            conn=conn,
        )
    finally:
        db_pool.putconn(conn)

    candidatos_response = []
    n_con_semaforo = 0
    for candidato in candidatos_db:
        semaforo = None
        motivo_sin_semaforo = None
        if candidato["bedrooms"] is None or candidato["bathrooms"] is None or candidato["area_m2"] is None:
            motivo_sin_semaforo = "faltan bedrooms/bathrooms/area_m2 en el listado — no hay vector de comparación."
        else:
            try:
                evaluacion = evaluar_precio_propiedad(
                    listing_id=candidato["listing_id"],
                    corregimiento=candidato["corregimiento"],
                    bedrooms=candidato["bedrooms"],
                    bathrooms=candidato["bathrooms"],
                    area_m2=candidato["area_m2"],
                    precio_real=candidato["price_usd"],
                    tipo_inmueble=candidato["tipo_inmueble"],
                )
                registro = evaluacion["registro_db"]
                diagnostico = evaluacion["diagnostico"]
                semaforo = SemaforoResponse(
                    categoria=registro["categoria_semaforo"],
                    precio_predicho=registro["precio_predicho"],
                    residual=diagnostico["diferencia_absoluta"],
                    mae_referencia=registro["mae_referencia"],
                    confianza_reducida=diagnostico["confianza_reducida"],
                    n_comparables=diagnostico["n_comparables"],
                )
                n_con_semaforo += 1
            except ComparablesKnnError as exc:
                motivo_sin_semaforo = str(exc)

        candidatos_response.append(CandidatoNlpResponse(
            listing_id=candidato["listing_id"],
            corregimiento=candidato["corregimiento"],
            tipo_inmueble=candidato["tipo_inmueble"],
            price_usd=candidato["price_usd"],
            bedrooms=candidato["bedrooms"],
            bathrooms=candidato["bathrooms"],
            area_m2=float(candidato["area_m2"]) if candidato["area_m2"] is not None else None,
            distancia_coseno=candidato["distancia_coseno"],
            semaforo=semaforo,
            motivo_sin_semaforo=motivo_sin_semaforo,
        ))

    n_matches = len(candidatos_response)
    zona_extraida = extraccion["zona"]
    tipo_extraido = extraccion["tipo_inmueble"]
    cobertura_ok, motivo_cobertura = _cobertura_m2(zona_extraida, tipo_extraido)

    if n_matches == 0 and cobertura_ok is False:
        respuesta_final = (
            f"No encontramos propiedades que coincidan con esos criterios en "
            f"{zona_extraida} (0 candidatos). Nota adicional: aunque hubiera candidatos, "
            f"tampoco podríamos mostrar el semáforo de precio para esta zona/tipo, porque el "
            f"modelo de valoración no tiene suficientes datos de entrenamiento ahí "
            f"({motivo_cobertura})."
        )
    elif n_matches == 0:
        respuesta_final = (
            f"No encontramos propiedades que coincidan con esos criterios en "
            f"{zona_extraida or 'la zona indicada'} (0 candidatos). Prueba ajustando el rango "
            f"de precio, el tipo de propiedad o el número de habitaciones."
        )
    elif n_con_semaforo == 0:
        motivo = motivo_cobertura or candidatos_response[0].motivo_sin_semaforo
        respuesta_final = (
            f"Encontramos {n_matches} propiedades que coinciden con tu búsqueda. No podemos "
            f"mostrar el semáforo de precio para ninguna ({motivo}) — te mostramos los "
            f"resultados de coincidencia sin ese dato."
        )
    elif n_con_semaforo < n_matches:
        respuesta_final = (
            f"Encontramos {n_matches} propiedades que coinciden con tu búsqueda, con semáforo "
            f"de precio disponible para {n_con_semaforo} de ellas (el resto no tiene cobertura "
            f"suficiente del modelo de valoración)."
        )
    else:
        respuesta_final = (
            f"Encontramos {n_matches} propiedades que coinciden con tu búsqueda, "
            f"con semáforo de precio incluido."
        )

    return SearchNlpResponse(
        consulta=request.consulta,
        tipo="resultados",
        criterios_extraidos=CriteriosExtraidosResponse(
            zona=zona_extraida,
            tipo_inmueble=tipo_extraido,
            precio_min=extraccion["precio_min"],
            precio_max=extraccion["precio_max"],
            habitaciones_min=extraccion["habitaciones_min"],
            banos_min=extraccion["banos_min"],
            confianza=extraccion["confianza"],
        ),
        resultados=ResultadosNlpResponse(
            n_candidatos=n_matches,
            candidatos=candidatos_response,
            respuesta_final=respuesta_final,
        ),
    )


## `POST /search/filtros` (Feature 4.3.2) — barra de filtros del frontend (5.2.2), sin NLP.
#
# Sin llamada a Gemini/`generar_embedding()` en ningún punto — filtrado SQL puro
# (`buscar_propiedades_filtros()`, `busqueda_estructurada.py`), sin `ORDER BY <=>` porque no hay
# embedding de consulta que rankear. Ver docstring de ese módulo para el criterio de orden
# (`price_usd asc, listing_id asc`) y de paginación (`LIMIT`/`OFFSET`, `total` vía `count(*)`
# separado bajo el mismo `WHERE`).


class FiltrosBusquedaRequest(BaseModel):
    zona: str | None = None
    tipo_inmueble: str | None = None
    precio_min: float | None = None
    precio_max: float | None = None
    habitaciones_min: int | None = None
    banos_min: int | None = None
    limit: int = 20
    offset: int = 0


class PropiedadFiltroResponse(BaseModel):
    listing_id: int
    corregimiento: str
    tipo_inmueble: str
    price_usd: int
    bedrooms: int | None
    bathrooms: int | None
    area_m2: float | None
    title: str
    imagenes: list[str] | None
    descripcion: str | None


class FiltrosBusquedaResponse(BaseModel):
    total: int
    limit: int
    offset: int
    propiedades: list[PropiedadFiltroResponse]


@router.post("/filtros", response_model=FiltrosBusquedaResponse)
def search_filtros(request: FiltrosBusquedaRequest) -> FiltrosBusquedaResponse:
    if request.limit < 1 or request.limit > 100:
        raise HTTPException(status_code=422, detail="limit debe estar entre 1 y 100.")
    if request.offset < 0:
        raise HTTPException(status_code=422, detail="offset no puede ser negativo.")

    db_pool = obtener_pool()
    conn = db_pool.getconn()
    try:
        try:
            resultado = buscar_propiedades_filtros(
                zona=request.zona,
                tipo_inmueble=request.tipo_inmueble,
                precio_min=request.precio_min,
                precio_max=request.precio_max,
                habitaciones_min=request.habitaciones_min,
                banos_min=request.banos_min,
                limit=request.limit,
                offset=request.offset,
                conn=conn,
            )
        except FiltroBusquedaError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        db_pool.putconn(conn)

    return FiltrosBusquedaResponse(
        total=resultado["total"],
        limit=request.limit,
        offset=request.offset,
        propiedades=[
            PropiedadFiltroResponse(
                listing_id=p["listing_id"],
                corregimiento=p["corregimiento"],
                tipo_inmueble=p["tipo_inmueble"],
                price_usd=p["price_usd"],
                bedrooms=p["bedrooms"],
                bathrooms=p["bathrooms"],
                area_m2=float(p["area_m2"]) if p["area_m2"] is not None else None,
                title=p["title"],
                imagenes=p["imagenes"],
                descripcion=p["descripcion"],
            )
            for p in resultado["propiedades"]
        ],
    )
