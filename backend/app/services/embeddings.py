"""Generación de embeddings semánticos vía `gemini-embedding-001`.

Compartido por M1 (Preference Matching) y M3 (NLP Orchestration). Modelo y
dimensión (3072) confirmados contra la API real en Notebook 1 (Feature 6.2.3,
`notebooks/01_m1_preference_matching.ipynb`, celda de verificación de entorno)
— ver `CLAUDE.md`. `text-embedding-004` (nombre de versiones anteriores de la
documentación pública de Gemini) ya no existe en esta API y devuelve 404.
"""

import os
from functools import lru_cache

from google import genai
from google.genai import types

MODELO_EMBEDDING = "gemini-embedding-001"
DIMENSION_ESPERADA = 3072

# Convención de 6.2.6/6.2.7 (CLAUDE.md): timeout explícito en todo genai.Client(),
# el default de la librería (sin límite) causó un bloqueo real de ~3 horas.
TIMEOUT_MS = 30_000


class EmbeddingError(RuntimeError):
    """La API de Gemini no respondió o devolvió un embedding con forma inesperada."""


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EmbeddingError(
            "GEMINI_API_KEY no está configurada en el entorno. "
            "Verificar el .env de la raíz del repo."
        )
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=TIMEOUT_MS),
    )


def generar_embedding(texto: str) -> list[float]:
    """Genera el embedding semántico de `texto` con `gemini-embedding-001`.

    Lanza `EmbeddingError` si la API falla o si el vector devuelto no tiene
    exactamente 3072 dimensiones — nunca devuelve un vector incorrecto en
    silencio.
    """
    if not texto or not texto.strip():
        raise EmbeddingError("El texto de entrada está vacío.")

    cliente = _get_client()
    try:
        resultado = cliente.models.embed_content(
            model=MODELO_EMBEDDING,
            contents=texto,
        )
    except Exception as exc:
        raise EmbeddingError(
            f"Falló la llamada a la API de Gemini ({MODELO_EMBEDDING}): {exc}"
        ) from exc

    if not resultado.embeddings:
        raise EmbeddingError(
            f"La API de Gemini no devolvió ningún embedding para el texto dado."
        )

    vector = resultado.embeddings[0].values
    if len(vector) != DIMENSION_ESPERADA:
        raise EmbeddingError(
            f"Dimensión inesperada del embedding: {len(vector)} "
            f"(se esperaban {DIMENSION_ESPERADA}). "
            f"Verificar si el modelo {MODELO_EMBEDDING} cambió su forma de salida."
        )

    return list(vector)
