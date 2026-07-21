"""Explainer de compatibilidad propiedad-perfil (Feature 2.2.4).

M1 (6.2.3) genera un score numérico de compatibilidad (estructurado 0.6 / semántico 0.4) pero
NO genera ninguna explicación en lenguaje/estructura legible — gap real confirmado contra el
mockup de frontend ("¿Por qué X% de compatibilidad?"). Esta función NO recalcula el score: toma
el perfil ya estructurado (salida de `estructurar_perfil_usuario()`, Feature 2.2.2) y los
atributos reales de una propiedad, y lista, por dimensión, si el criterio del perfil se cumplió
o no — lógica de dominio pura, sin conexión a Supabase.

Output: `list[dict]`, una entrada por dimensión, con claves fijas (`dimension`, `cumplido`,
`criterio_perfil`, `valor_propiedad`, `detalle`). Esa forma sirve tal cual para
`json.dumps(...)` al persistir en `scores_compatibilidad.explicacion` (columna `text`, Feature
1.5.4) y para iterar directo en el frontend sin transformación adicional — no se decide aquí
si se serializa a JSON o se deja como texto, esa decisión es de quien llame a esta función.

Dimensión "transporte" — SIN distancia real disponible, resuelto contra lo que sí existe:
`estructurar_perfil_usuario()` (2.2.2) quitó `distancia_metro_maxima_m` porque no existe esa
columna en `propiedades` ni en `corregimientos` (solo un score compuesto 0-1,
`corregimientos.desglose_dimensiones->>'transporte'`, ponderado 0.20 en el Zone Health Index).
Como el perfil de 2.2.2 no tiene ningún campo de transporte, esta función recibe el criterio de
transporte como parámetro APARTE (`transporte_minimo`), no como parte de `perfil` — no se
reabre 2.2.2 para agregarle un campo que no tiene dato real detrás. `transporte_minimo` es un
umbral sobre ese score compuesto (0-1), NO una distancia. Sugerencia documentada (no forzada
como default, ver razonamiento en `UMBRAL_TRANSPORTE_SUGERIDO` abajo): 0.5 — punto medio del
rango normalizado, sin calibración cuantitativa contra datos reales de satisfacción de usuario
(no existe ese dato en el proyecto), mismo tipo de limitación ya documentada para el umbral de
confianza 0.65 de 6.2.7. Si `transporte_minimo` no se pasa, la dimensión queda "no evaluada"
(regla general de esta función, no una excepción para transporte).

Costa del Este es un caso aparte dentro de "transporte": por decisión ya cerrada del proyecto
("Costa del Este NO recibe score compuesto" — depende de Juan Díaz, nunca extraído), su
`transporte_score` es `None` aun si el perfil sí pide un `transporte_minimo`. Esta función
distingue esto de "criterio no especificado" — se marca "no evaluada" con motivo de cobertura
de datos insuficiente, no se confunde con la ausencia de preferencia del usuario.
"""

# Umbral sugerido para transporte_minimo si quien llama a esta función necesita un valor por
# defecto razonable — NO se usa como default real del parámetro (ver regla de "no evaluada"
# cuando un criterio está ausente, especificación de esta tarea). Punto medio del rango
# normalizado 0-1 del score compuesto de transporte; no calibrado contra datos de satisfacción
# de usuario real, mismo tipo de limitación que el umbral 0.65 de 6.2.7.
UMBRAL_TRANSPORTE_SUGERIDO = 0.5


def explicar_compatibilidad(perfil: dict, propiedad: dict, transporte_minimo: float | None = None) -> list[dict]:
    """Compara `perfil` (salida de `estructurar_perfil_usuario()`) contra `propiedad`, dimensión
    por dimensión, y devuelve el detalle de cumplimiento.

    `perfil`: dict con `precio_maximo`, `habitaciones_min`, `zonas_preferidas` (claves
    ausentes o en `None` se tratan igual que "no especificado").

    `propiedad`: dict con al menos `price_usd`, `bedrooms`, `corregimiento`, y
    `transporte_score` (el score compuesto de `corregimientos.desglose_dimensiones`,
    `None` si esa zona no tiene score compuesto — ej. Costa del Este). Esta función no
    consulta Supabase: quien la llama ya debe traer `transporte_score` resuelto.

    `transporte_minimo`: umbral 0-1 sobre `transporte_score`, aparte de `perfil` (ver docstring
    del módulo). `None` => dimensión "transporte" no evaluada.

    Cada entrada de la lista de salida trae `cumplido` en `{True, False, None}` — `None`
    significa explícitamente "no evaluada" (criterio ausente o dato no disponible), nunca se
    reinterpreta como cumplido por default.
    """
    resultado = []

    precio_maximo = perfil.get("precio_maximo")
    price_usd = propiedad.get("price_usd")
    if precio_maximo is None:
        resultado.append({
            "dimension": "precio",
            "cumplido": None,
            "criterio_perfil": None,
            "valor_propiedad": price_usd,
            "detalle": "No evaluada: el perfil no especificó precio_maximo.",
        })
    else:
        cumplido = price_usd <= precio_maximo
        resultado.append({
            "dimension": "precio",
            "cumplido": cumplido,
            "criterio_perfil": f"precio_maximo={precio_maximo}",
            "valor_propiedad": price_usd,
            "detalle": (
                f"Precio de la propiedad (${price_usd:,}) "
                f"{'cumple' if cumplido else 'excede'} el máximo del perfil (${precio_maximo:,})."
            ),
        })

    habitaciones_min = perfil.get("habitaciones_min")
    bedrooms = propiedad.get("bedrooms")
    if habitaciones_min is None:
        resultado.append({
            "dimension": "habitaciones",
            "cumplido": None,
            "criterio_perfil": None,
            "valor_propiedad": bedrooms,
            "detalle": "No evaluada: el perfil no especificó habitaciones_min.",
        })
    else:
        cumplido = bedrooms is not None and bedrooms >= habitaciones_min
        resultado.append({
            "dimension": "habitaciones",
            "cumplido": cumplido,
            "criterio_perfil": f"habitaciones_min={habitaciones_min}",
            "valor_propiedad": bedrooms,
            "detalle": (
                f"La propiedad tiene {bedrooms} habitación(es), "
                f"{'cumple' if cumplido else 'no cumple'} el mínimo del perfil ({habitaciones_min})."
            ),
        })

    zonas_preferidas = perfil.get("zonas_preferidas")
    corregimiento = propiedad.get("corregimiento")
    if not zonas_preferidas:
        resultado.append({
            "dimension": "zona",
            "cumplido": None,
            "criterio_perfil": None,
            "valor_propiedad": corregimiento,
            "detalle": "No evaluada: el perfil no especificó zonas_preferidas.",
        })
    else:
        cumplido = corregimiento in zonas_preferidas
        resultado.append({
            "dimension": "zona",
            "cumplido": cumplido,
            "criterio_perfil": f"zonas_preferidas={zonas_preferidas}",
            "valor_propiedad": corregimiento,
            "detalle": (
                f"La propiedad está en {corregimiento}, "
                f"{'está' if cumplido else 'no está'} entre las zonas preferidas del perfil."
            ),
        })

    transporte_score = propiedad.get("transporte_score")
    if transporte_minimo is None:
        resultado.append({
            "dimension": "transporte",
            "cumplido": None,
            "criterio_perfil": None,
            "valor_propiedad": transporte_score,
            "detalle": "No evaluada: no se especificó transporte_minimo (no hay distancia real disponible; "
                       "ver UMBRAL_TRANSPORTE_SUGERIDO en este módulo).",
        })
    elif transporte_score is None:
        resultado.append({
            "dimension": "transporte",
            "cumplido": None,
            "criterio_perfil": f"transporte_minimo={transporte_minimo}",
            "valor_propiedad": None,
            "detalle": f"No evaluada: {corregimiento} no tiene score compuesto de transporte "
                       f"(cobertura de datos insuficiente, decisión ya cerrada del proyecto).",
        })
    else:
        cumplido = transporte_score >= transporte_minimo
        resultado.append({
            "dimension": "transporte",
            "cumplido": cumplido,
            "criterio_perfil": f"transporte_minimo={transporte_minimo}",
            "valor_propiedad": transporte_score,
            "detalle": (
                f"Score de transporte de {corregimiento} ({transporte_score:.2f}) "
                f"{'cumple' if cumplido else 'no alcanza'} el umbral del perfil ({transporte_minimo})."
            ),
        })

    return resultado
