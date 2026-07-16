"""Estructuración/validación de un perfil de usuario persistente (Feature 2.2.2).

Distinto de la extracción de una consulta conversacional puntual (M3, Feature 6.2.7,
`notebooks/05_m3_nlp_orchestration.ipynb`, contrato `extraer()`/`m1_buscar_matches()`) — esa
función interpreta lenguaje natural de una sola consulta vía Gemini. Esta función NO llama a
ningún LLM: el input ya llega estructurado (ej. un formulario del frontend), y el trabajo aquí
es validar y normalizar esos valores antes de persistirlos como preferencias de un perfil de
usuario real. Confirmado contra el resto del proyecto: `perfiles_lifestyle` (Feature 1.5.5) ya
guarda sus reglas como JSON estructurado (`reglas_estructurales`), no como texto libre — los 6
perfiles cargados ahí son sintéticos/de referencia para el ground truth de M1 (6.2.3), pero la
*forma* de sus atributos (`price_usd_min/max`, `bedrooms_min/max`, `corregimientos`) confirma
que un perfil de usuario real, en este proyecto, se representa como datos estructurados, no NLP.

Zonas válidas: las 9 del scope del proyecto (`CLAUDE.md` — 5 corregimientos reales +
El Cangrejo/Marbella/Obarrio que heredan de Bella Vista + Costa del Este). Hardcodeadas aquí
(no una consulta a `corregimientos` en cada llamada) a propósito: son 9 nombres fijos,
documentados como decisión cerrada del proyecto, y esta función debe ser pura/testeable de
forma aislada sin depender de una conexión a Supabase (especificación de esta tarea). Si el
scope de zonas cambia alguna vez, se actualiza esta constante junto con `CLAUDE.md`.

"""

# distancia_metro_maxima_m: pendiente — no existe columna de distancia real en
# propiedades/corregimientos, solo score compuesto de transporte 0-1. Agregar cuando exista
# dato de MiBus GTFS o similar.

ZONAS_VALIDAS = frozenset({
    "San Francisco", "Bella Vista", "Parque Lefevre", "Betania", "Pedregal",
    "El Cangrejo", "Marbella", "Obarrio", "Costa del Este",
})


def estructurar_perfil_usuario(
    precio_maximo: float | None = None,
    habitaciones_min: int | None = None,
    zonas_preferidas: list[str] | None = None,
) -> dict:
    """Valida y normaliza las preferencias de un perfil de usuario ya estructurado
    (ej. un formulario del frontend) — no interpreta texto libre.

    `habitaciones_min`: criterio de MÍNIMO (no exacto) — un usuario que pide "2 habitaciones"
    normalmente acepta 2 o más, mismo criterio que `bedrooms_min` en `reglas_estructurales` de
    `perfiles_lifestyle` y que el parámetro `habitaciones_min` ya usado en
    `buscar_propiedades_ann()` (Feature 2.2.1) — consistencia deliberada para que este perfil
    se pueda pasar directo a esa función más adelante.

    Lanza `ValueError` explícito (no silencia ni corrige) si:
    - alguna zona de `zonas_preferidas` no está en las 9 zonas válidas del scope,
    - `precio_maximo` no es positivo,
    - `habitaciones_min` no es positivo.
    """
    if zonas_preferidas is not None:
        zonas_invalidas = [z for z in zonas_preferidas if z not in ZONAS_VALIDAS]
        if zonas_invalidas:
            raise ValueError(
                f"Zona(s) inválida(s), no están en el scope de 9 zonas del proyecto: "
                f"{zonas_invalidas}. Zonas válidas: {sorted(ZONAS_VALIDAS)}."
            )

    if precio_maximo is not None and precio_maximo <= 0:
        raise ValueError(f"precio_maximo debe ser positivo, recibido: {precio_maximo}")

    if habitaciones_min is not None and habitaciones_min <= 0:
        raise ValueError(f"habitaciones_min debe ser positivo, recibido: {habitaciones_min}")

    return {
        "precio_maximo": precio_maximo,
        "habitaciones_min": habitaciones_min,
        "zonas_preferidas": list(zonas_preferidas) if zonas_preferidas is not None else [],
    }
