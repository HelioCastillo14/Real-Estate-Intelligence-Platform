"""Extracción de intención NLP para M3 (Feature 4.1.2 / 4.2.1, ya cerradas en 6.2.7 — este
módulo puerta a producción el contrato ya validado, no lo rediseña).

Modelo, `ExtraccionIntencion`, `SYSTEM_PROMPT` y `extraer()`: portados desde
`notebooks/05_m3_nlp_orchestration.ipynb` (celda 10, Feature 6.2.7, ya con el modelo/prompt de
la adenda post-cierre — ver abajo). `clasificar()`: portado desde la celda 14 del mismo notebook
(Feature 4.2.1 — las 3 causas de fallback separables, independientes del score de confianza).

**Modelo — `gemini-3.1-flash-lite`, no `gemini-3.5-flash`. Fuente exacta, verificada, no una
referencia genérica a CLAUDE.md:** `Context-MD/Feature_6_2_7_M3_Orchestration_Cierre.md` §8ter,
"Hallazgo post-cierre (2026-07-15, adoptado) — modelo y prompt del contrato v0 reemplazados por
`gemini-3.1-flash-lite`" — reemplaza la decisión de modelo de la sección 2 de esa misma Acta
(`gemini-3.5-flash`, 25/25 llamadas), sin reabrirla. Motivo documentado ahí: `gemini-3.5-flash`
no cumplía el objetivo ≤5s de SRS-024 (WBS 4.3.3) — mediana 11.3s/p90 14.2s sin reintento, hasta
71.6s con backoff de 503; comparación pareada de 13 consultas dio 1.3s mediana / 0 reintentos
para `gemini-3.1-flash-lite` vs. 12.3s / 3 reintentos para `gemini-3.5-flash`. Explícitamente NO
afecta a 6.2.6 (Quality Scorer, sigue en `gemini-3.5-flash` — decisión independiente). Ambos
archivos fuente (`Feature_6_2_7_M3_Orchestration_Cierre.md`, `notebooks/05_m3_nlp_orchestration.ipynb`)
ya estaban comprometidos en git antes de esta sesión (commit `8923fc9`) — no es un artefacto de
la limpieza de `CLAUDE.md` hecha en esta misma sesión.

**Re-verificado en vivo para esta tarea (4.3.1, 2026-07-15) antes de comprometerse a esa
decisión ya tomada, no asumido de la corrida de 6.2.7 sin comprobar (regla del proyecto: la
disponibilidad de un modelo Gemini es una condición del momento de ejecución):**
`gemini-3.1-flash-lite` respondió OK en 1.79s; `gemini-3.5-flash` también respondió OK pero en
17.7s — confirma en vivo, hoy, la misma brecha de latencia que documenta §8ter.
"""

import time
from functools import lru_cache
from typing import Optional

import httpx
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from pydantic import BaseModel, Field

MODELO_EXTRACCION = "gemini-3.1-flash-lite"
TIMEOUT_MS = 30_000
UMBRAL_CONFIANZA = 0.65

ZONAS_SCOPE = [
    "San Francisco", "Bella Vista", "Parque Lefevre", "Betania", "Pedregal",
    "El Cangrejo", "Marbella", "Obarrio", "Costa del Este",
]


class ExtraccionIntencionError(RuntimeError):
    """La API de Gemini no respondió tras reintentar (ServerError/TransportError persistente)."""


class ExtraccionIntencion(BaseModel):
    es_consulta_inmobiliaria: bool = Field(description="False si la consulta no trata sobre busqueda/compra de propiedades residenciales, sin importar que mencione una zona valida")
    zona: Optional[str] = Field(description="Una de las 9 zonas del scope, o null si no se menciona o no mapea a ninguna")
    zona_mencion_texto: Optional[str] = Field(description="Texto literal de CUALQUIER ubicacion mencionada, incluso si no esta en la lista de 9 zonas validas. Null solo si no se menciono ninguna ubicacion.")
    tipo_inmueble: Optional[str] = Field(description="Apartamento, Casa, Edificio, Local, Terreno, o null si no se menciona")
    precio_min: Optional[float] = Field(description="Precio minimo en USD si se menciona un rango o piso explicito, si no null")
    precio_max: Optional[float] = Field(description="Precio maximo/techo en USD si se menciona explicitamente un numero, si no null")
    habitaciones_min: Optional[int] = Field(description="Numero minimo de habitaciones si se menciona explicitamente, si no null")
    banos_min: Optional[int] = Field(description="Numero minimo de banos si se menciona explicitamente, si no null")
    caracteristicas_cualitativas: list[str] = Field(description="Frases cualitativas sin ancla numerica ni categorica clara")
    confianza: float = Field(description="0.0 a 1.0: que tan completa y no-ambigua es la extraccion de entidades estructuradas")
    razon_confianza: str = Field(description="Explicacion breve de por que se asigno ese nivel de confianza")


SYSTEM_PROMPT = f'''Eres el modulo de extraccion de intencion de un buscador conversacional de propiedades \
residenciales en Panama (REIP). Tu tarea es extraer entidades estructuradas de la consulta del usuario \
en espanol, y asignar un puntaje de confianza a la extraccion.

PRIMER CHEQUEO -- es_consulta_inmobiliaria: evalua si la consulta trata sobre buscar/comprar/vender una \
propiedad o inmueble (vivienda, local, edificio, o TERRENO -- terrenos agricolas, para construir, o de \
cualquier uso tambien cuentan como consulta inmobiliaria, no solo vivienda residencial). Terreno es un \
tipo_inmueble tan valido como Apartamento o Casa; una consulta sobre comprar/buscar un terreno SIEMPRE \
es es_consulta_inmobiliaria=True, sin importar el uso que se le vaya a dar (sembrar, construir, invertir) \
o si la zona mencionada esta fuera del scope de 9 zonas -- eso se resuelve en el campo zona/zona_mencion_texto, \
no en este chequeo. Marca es_consulta_inmobiliaria=False SOLO si el usuario pregunta por otra cosa que no \
es un inmueble en absoluto (un servicio, un producto, informacion general -- ej. un taller mecanico, un \
restaurante), aunque mencione una zona valida de pasada.

Zonas validas del scope (unicas que puedes asignar al campo zona): {", ".join(ZONAS_SCOPE)}.

Distincion importante para zona_mencion_texto -- NOMBRE DE LUGAR CONCRETO vs. CALIFICATIVO CUALITATIVO:
- zona_mencion_texto se llena SOLO con un nombre de lugar concreto: una ciudad, corregimiento, barrio, \
provincia, o punto de referencia geografico reconocible (ej. "Juan Diaz", "San Miguelito", "Chiriqui", \
"puerto de Colon"). Si el usuario menciona una ubicacion asi pero NO esta en la lista de 9 zonas validas, \
deja zona en null y copia el texto literal en zona_mencion_texto.
- Un calificativo cualitativo sobre ubicacion SIN nombre de lugar (ej. "zona tranquila", "cerca del trabajo", \
"buena zona", "zona segura", "un lugar comodo") NO es un nombre de lugar concreto -- NO debe poblar \
zona_mencion_texto. En ese caso, zona_mencion_texto tambien queda null (igual que si no se hubiera \
mencionado ninguna ubicacion). Esto se refleja como ambiguedad en el campo confianza, no como una \
mencion de zona sin cobertura.
- Si el usuario no menciono ninguna ubicacion en absoluto, zona_mencion_texto tambien debe ser null.
- Si menciona dos zonas validas sin criterio de desempate, zona tambien queda null, y zona_mencion_texto \
debe contener ambas menciones (esas si son nombres de lugar concretos).

Tipos de inmueble validos: Apartamento, Casa, Edificio, Local, Terreno.

Reglas de confianza (aplica solo cuando es_consulta_inmobiliaria=True):
- ALTA (>0.7): la mayoria de las entidades mencionadas tienen ancla numerica o categorica clara.
  Campos simplemente ausentes NO bajan la confianza -- ausencia no es ambiguedad.
- BAJA (<0.4): la consulta usa calificativos subjetivos sin ancla en lugar de numeros o de un nombre de \
lugar concreto, o hay conflicto real (dos zonas sin desempate).
- MEDIA: mezcla de entidades ancladas y calificativos sueltos en la misma consulta.

Extrae SOLO lo que esta explicito o fuertemente implicito. No inventes numeros para calificativos vagos.'''


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    import os

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ExtraccionIntencionError(
            "GEMINI_API_KEY no está configurada en el entorno. Verificar el .env de la raíz del repo."
        )
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=TIMEOUT_MS),
    )


def extraer(consulta: str) -> dict:
    """Extrae entidades estructuradas de `consulta` vía `gemini-3.1-flash-lite`.

    Un reintento con backoff de 20s ante `ServerError` (5xx) o `httpx.TransportError`
    (timeouts/conexión) — mismo criterio que 6.2.7, corregido para no dejar pasar un timeout de
    cliente sin el mismo backoff que un 503 (`httpx.TransportError` no es subclase de
    `ServerError`). Lanza `ExtraccionIntencionError` si el segundo intento también falla.
    """
    client = _get_client()
    for intento in range(2):
        try:
            resp = client.models.generate_content(
                model=MODELO_EXTRACCION,
                contents=consulta,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=ExtraccionIntencion,
                    thinking_config=types.ThinkingConfig(thinking_level="LOW"),
                ),
            )
            return ExtraccionIntencion.model_validate_json(resp.text).model_dump()
        except (ServerError, httpx.TransportError) as exc:
            if intento == 0:
                time.sleep(20)
            else:
                raise ExtraccionIntencionError(
                    f"La API de Gemini ({MODELO_EXTRACCION}) falló tras reintentar: {exc}"
                ) from exc
    raise ExtraccionIntencionError("unreachable")


def _zona_texto_contiene_zona_valida(texto: str | None) -> bool:
    if texto is None:
        return False
    return any(z.lower() in texto.lower() for z in ZONAS_SCOPE)


def clasificar(extraccion: dict) -> str:
    """Una de 4 categorías: `"exito"`, `"fallback_fuera_tema"`, `"fallback_cobertura"`,
    `"fallback_ambiguedad"` — 3 causas de fallback separables (Feature 4.2.1, 6.2.7 celda 14),
    ninguna colapsada en un solo score de confianza."""
    if not extraccion["es_consulta_inmobiliaria"]:
        return "fallback_fuera_tema"
    if (
        extraccion["zona_mencion_texto"] is not None
        and extraccion["zona"] is None
        and not _zona_texto_contiene_zona_valida(extraccion["zona_mencion_texto"])
    ):
        return "fallback_cobertura"
    if extraccion["confianza"] < UMBRAL_CONFIANZA:
        return "fallback_ambiguedad"
    return "exito"
