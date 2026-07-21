"""Escalamiento del Quality Scorer (6.2.6) al catálogo completo.

Job de batch de producción, corre una sola vez sobre el catálogo estático
(pipeline/data/processed/catalogo_residencial_limpio_6_2_1.csv). No es un
notebook de Feature 6.2 (ya cerrada) ni una etapa recurrente del pipeline.

Reutiliza exactamente la metodología validada en notebooks/04_m2_quality_scorer.ipynb
(6.2.6): rúbrica de 4 dimensiones, salida estructurada v2 (100% de parseo en la
muestra de 150), circuit breaker diferenciado por tipo de error, checkpoint
incremental, timeout explícito de cliente. Ver Context-MD/Feature_6_2_6_M2_QualityScorer_Cierre.md
para el detalle de esa validación.

Decisión de esta corrida (confirmada con el equipo antes de escribir este script):
- Re-evalúa el catálogo completo (1,168 filas evaluables) desde cero, con un solo
  modelo de producción — no reutiliza los 150 scores mixtos (2 modelos) de 6.2.6.
- Modelo inicial: gemini-3.5-flash (GA, id fijo). Verificado en vivo antes de la
  corrida: 23/25 (92%) de éxito en frío, 2/25 fallos por 503 UNAVAILABLE.

CAMBIO DE MODELO A MITAD DE CORRIDA (2026-07-15): gemini-3.5-flash mostró latencia
degradada sostenida durante la ejecución real (565 filas en ~9h40m, ritmo medido en
vivo muy por debajo del esperado por el diagnóstico en frío -- ver diagnóstico de
ritmo en la sesión). El proceso se detuvo con SIGTERM (no destructivo, checkpoint
verificado íntegro tras detener: 565 filas, 529 válidas, 36 fallidas, todas
gemini-3.5-flash) y se relanza con MODELO_LLM = "gemini-3.1-flash-lite" para las
filas restantes. El checkpoint por fila ya registraba "modelo" desde el diseño
original -- el relanzamiento no reevalúa las 565 filas ya hechas, solo continúa con
las pendientes bajo el nuevo modelo.

Esta mezcla de modelos NO es una sustitución silenciosa: se justifica con la misma
validación de equivalencia ya exigida para el cambio de modelo de M3 en 6.2.7 --
ver pipeline/models/validacion_equivalencia_3_1_flash_lite_vs_3_5_flash.pkl (25
listings ya evaluados por gemini-3.5-flash, re-evaluados con gemini-3.1-flash-lite:
0% de filas con diferencia >1 punto en cualquier dimensión, ninguna dimensión supera
el umbral de 0.5 en diferencia de medias -- misma convención de "diferencia notable"
usada en 6.2.6). El artifact final documenta el conteo exacto de filas por modelo.
"""
import json
import os
import pickle
import time
from pathlib import Path

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel, Field, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_CATALOGO = REPO_ROOT / "pipeline" / "data" / "processed" / "catalogo_residencial_limpio_6_2_1.csv"
RUTA_MODELOS = REPO_ROOT / "pipeline" / "models"
RUTA_CHECKPOINT = RUTA_MODELOS / "quality_scores_produccion_checkpoint.pkl"
RUTA_FINAL_PKL = RUTA_MODELOS / "quality_scores_produccion_final.pkl"
RUTA_FINAL_CSV = RUTA_MODELOS / "quality_scores_produccion_final.csv"

MODELO_LLM = "gemini-3.1-flash-lite"
CODIGOS_CONTENCION_CAPACIDAD = (503, 504)  # contención de capacidad del modelo, no cuota propia

RUBRICA = """Evalúas la calidad de un anuncio inmobiliario en 4 dimensiones, cada una en escala
de 1 (muy débil) a 5 (excelente):

1. completitud_informativa: ¿el texto da información real y específica (área, características,
   ubicación concreta) o es vago/genérico ("excelente oportunidad", sin datos verificables)?
2. calidad_presentacion: profesionalismo y claridad de la redacción — puntuación, estructura,
   ausencia de errores obvios o texto tipo spam/relleno repetido.
3. diferenciadores_amenidades: ¿comunica valor agregado real y específico (vista, acabados,
   amenidades concretas) o solo adjetivos genéricos sin sustancia ("lujoso", "excelente")?
4. transparencia_precio: dado el precio de referencia provisto, ¿el texto presenta el precio de
   forma clara y coherente con lo descrito (o, si el anuncio tiene varios modelos/unidades,
   explica el rango de forma comprensible)? Un texto que no menciona precio en absoluto, cuando
   se te da un precio de referencia, es baja transparencia aunque el resto del anuncio sea bueno.
"""


class QualityScore(BaseModel):
    completitud_informativa: int = Field(ge=1, le=5)
    calidad_presentacion: int = Field(ge=1, le=5)
    diferenciadores_amenidades: int = Field(ge=1, le=5)
    transparencia_precio: int = Field(ge=1, le=5)


def construir_prompt(fila):
    precio_ctx = f"${fila['price_usd']:,.0f}" if pd.notna(fila["price_usd"]) else "no disponible"
    return f"""{RUBRICA}

Anuncio a evaluar:
Título: {fila['title']}
Tipo de inmueble: {fila['tipo_inmueble']}
Precio de referencia (dato del scraper, no necesariamente mencionado en el texto): {precio_ctx}
Área: {fila['area_m2']} m² | Habitaciones: {fila['bedrooms']} | Baños: {fila['bathrooms']}

Descripción del anuncio:
{fila['descripcion'][:4000]}
"""


def cargar_checkpoint():
    if RUTA_CHECKPOINT.exists():
        with open(RUTA_CHECKPOINT, "rb") as f:
            return pickle.load(f)
    return {}


def guardar_checkpoint(resultados):
    with open(RUTA_CHECKPOINT, "wb") as f:
        pickle.dump(resultados, f)


def llamar_con_reintento_red(fn_llamada, errors_mod, max_reintentos_red=1):
    intentos_red = 0
    while True:
        try:
            return fn_llamada()
        except errors_mod.APIError:
            raise
        except Exception:
            if intentos_red < max_reintentos_red:
                intentos_red += 1
                time.sleep(5)
                continue
            raise


def verificar_disponibilidad(client, errors_mod, types_mod, modelo):
    try:
        resp = client.models.generate_content(model=modelo, contents="prueba de disponibilidad")
        print(f"Verificación de disponibilidad OK: {modelo} (model_version={resp.model_version})")
    except errors_mod.APIError as e:
        raise SystemExit(
            f"ABORTA: {modelo} no respondió en el chequeo de arranque ({e.code} {e.status}). "
            "No asumas disponibilidad de una corrida anterior -- re-verifica antes de reintentar."
        )


def main():
    ruta_env = find_dotenv(usecwd=True)
    assert ruta_env, "No se encontró .env en el árbol de directorios"
    load_dotenv(ruta_env)
    assert os.environ.get("GEMINI_API_KEY"), "GEMINI_API_KEY no está cargada"

    from google import genai
    from google.genai import errors, types

    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=types.HttpOptions(timeout=45_000),
    )
    verificar_disponibilidad(client, errors, types, MODELO_LLM)

    config_v2 = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=QualityScore,
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
    )
    info_modelo = client.models.get(model=MODELO_LLM)

    def llamar_v2(fila, max_reintentos_429=1, max_reintentos_capacidad=1):
        prompt = construir_prompt(fila)
        intentos_429 = 0
        intentos_capacidad = 0
        while True:
            try:
                resp = llamar_con_reintento_red(
                    lambda: client.models.generate_content(
                        model=MODELO_LLM, contents=prompt, config=config_v2
                    ),
                    errors,
                )
                data = json.loads(resp.text)
                score = QualityScore(**data)
                return score, None
            except errors.APIError as e:
                if e.code == 429 and intentos_429 < max_reintentos_429:
                    intentos_429 += 1
                    time.sleep(90)
                    continue
                if e.code in CODIGOS_CONTENCION_CAPACIDAD and intentos_capacidad < max_reintentos_capacidad:
                    intentos_capacidad += 1
                    time.sleep(20)
                    continue
                return None, str(e)
            except (ValidationError, json.JSONDecodeError, TypeError) as e:
                return None, str(e)
            except Exception as e:
                return None, f"{type(e).__name__}: {e}"

    assert RUTA_CATALOGO.exists(), f"No existe {RUTA_CATALOGO}"
    RUTA_MODELOS.mkdir(exist_ok=True)

    df_catalogo = pd.read_csv(RUTA_CATALOGO)
    total = len(df_catalogo)
    no_evaluables = df_catalogo[df_catalogo["descripcion_fuente"] == "ninguna"]
    df_evaluable = df_catalogo[df_catalogo["descripcion_fuente"] != "ninguna"].copy()

    print(f"Catálogo total: {total} filas")
    print(f"No evaluables (sin texto de descripción): {len(no_evaluables)} filas "
          f"({len(no_evaluables) / total:.2%})")
    print(f"Población a evaluar en este batch: {len(df_evaluable)} filas")

    resultados = cargar_checkpoint()
    print(f"Checkpoint existente: {len(resultados)} listings ya registrados")

    detenido_por_429 = False
    pendientes = 0
    for _, fila in df_evaluable.iterrows():
        lid = fila["listing_id"]
        if resultados.get(lid, {}).get("score") is not None:
            continue
        score, error = llamar_v2(fila)
        if score is None and error and "429" in error:
            detenido_por_429 = True
            print(f"Circuit breaker: 429 persistente en listing {lid} tras reintento. Deteniendo corrida.")
            break
        resultados[lid] = {
            "score": score.model_dump() if score is not None else None,
            "error": error,
            "modelo": MODELO_LLM,
        }
        if score is None:
            pendientes += 1
            print(f"Listing {lid} sin score tras reintento ({error}) -- queda pendiente para relanzamiento.")
        guardar_checkpoint(resultados)
        time.sleep(1)

    print(f"\nTotal registrado en checkpoint: {len(resultados)} / {len(df_evaluable)}")
    if detenido_por_429:
        print("ADVERTENCIA: la corrida se detuvo por rate limiting (429) antes de completar el catálogo. "
              "Vuelve a correr el script para continuar desde el checkpoint.")
        return
    if pendientes:
        print(f"ADVERTENCIA: {pendientes} filas quedaron sin score tras agotar reintentos de 503/504. "
              "Vuelve a correr el script para reintentarlas (el checkpoint no las descarta).")

    if len(resultados) < len(df_evaluable):
        print("Catálogo incompleto -- corre el script de nuevo antes de generar el artifact final.")
        return

    filas_resultado = []
    fallidos = 0
    for lid, registro in resultados.items():
        if registro["score"] is None:
            fallidos += 1
            continue
        filas_resultado.append({"listing_id": lid, "modelo": registro["modelo"], **registro["score"]})

    df_scores = pd.DataFrame(filas_resultado)
    df_scores = df_scores.merge(
        df_catalogo[["listing_id", "corregimiento", "tipo_inmueble", "price_usd", "descripcion_fuente"]],
        on="listing_id", how="left",
    )

    print(f"\nScores válidos: {len(df_scores)} / {len(df_evaluable)} evaluados ({fallidos} fallidos)")

    modelos_por_fila = df_scores["modelo"].value_counts().to_dict()
    print(f"Distribución de filas por modelo: {modelos_por_fila}")

    RUTA_VALIDACION_EQUIVALENCIA = RUTA_MODELOS / "validacion_equivalencia_3_1_flash_lite_vs_3_5_flash.pkl"
    justificacion_mezcla = None
    if len(modelos_por_fila) > 1 and RUTA_VALIDACION_EQUIVALENCIA.exists():
        with open(RUTA_VALIDACION_EQUIVALENCIA, "rb") as f:
            _validacion = pickle.load(f)
        justificacion_mezcla = {
            "tipo": "cambio de modelo a mitad de corrida por latencia degradada de gemini-3.5-flash, "
                    "no una sustitución silenciosa -- validado con la misma convención exigida para "
                    "el cambio de modelo de M3 en 6.2.7",
            "n_muestra_validacion": _validacion["n_muestra"],
            "resumen_validacion": _validacion["df_resumen"].to_dict(orient="records"),
            "ruta_validacion": str(RUTA_VALIDACION_EQUIVALENCIA),
        }

    artifact = {
        "df_scores": df_scores,
        "modelos_por_fila": modelos_por_fila,
        "modelo_final_usado_para_filas_pendientes": MODELO_LLM,
        "modelo_version_final": info_modelo.version,
        "justificacion_mezcla_de_modelos": justificacion_mezcla,
        "thinking_level": "LOW",
        "prompt_version": "v2_structured_output",
        "n_catalogo_total": total,
        "n_no_evaluables_sin_texto": len(no_evaluables),
        "n_evaluados": len(df_evaluable),
        "n_fallidos": fallidos,
    }
    with open(RUTA_FINAL_PKL, "wb") as f:
        pickle.dump(artifact, f)
    df_scores.to_csv(RUTA_FINAL_CSV, index=False)

    print(f"Artifact guardado en {RUTA_FINAL_PKL}")
    print(f"CSV guardado en {RUTA_FINAL_CSV}")


if __name__ == "__main__":
    main()
