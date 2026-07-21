"""Endpoint `GET /valuation/transparencia` (Feature 3.5.2) — página de transparencia del semáforo KNN.

Expone los 209 pares predicho/real del conjunto de test de 6.2.4 (3.5.1) para que el
frontend/paper puedan mostrar el desempeño real del modelo, no solo su categoría. Sin filtros ni
paginación — son 209 filas fijas, un `GET` simple es suficiente (ver `transparencia_valuacion.py`
para la justificación de por qué esto es un CSV cacheado y no una tabla de Supabase).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.transparencia_valuacion import (
    TransparenciaValuacionError,
    obtener_transparencia_valuacion,
)

router = APIRouter(prefix="/valuation", tags=["valuation"])


class ParPrediccionResponse(BaseModel):
    propiedad_id: int
    precio_real: float
    precio_predicho: float
    diferencia_absoluta: float
    zona: str


class ResumenTransparenciaResponse(BaseModel):
    n_muestras: int
    mae_absoluto: float
    mae_porcentual: float
    poblacion_mae_absoluto: str
    poblacion_mae_porcentual: str


class TransparenciaResponse(BaseModel):
    resumen: ResumenTransparenciaResponse
    pares: list[ParPrediccionResponse]


@router.get("/transparencia", response_model=TransparenciaResponse)
def transparencia() -> TransparenciaResponse:
    try:
        datos = obtener_transparencia_valuacion()
    except TransparenciaValuacionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return TransparenciaResponse(**datos)
