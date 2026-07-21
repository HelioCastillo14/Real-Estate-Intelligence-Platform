"""Materializa el ground truth de Feature 6.2.3 (M1: Preference Matching) a disco.

Copia exacta de la lógica de las celdas 2, 5, 7, 8 y 11 de
notebooks/01_m1_preference_matching.ipynb (carga de catálogo, PERFILES_LIFESTYLE,
filtro estructural, KEYWORDS_CUALITATIVOS, filtro cualitativo) — no reinterpreta
ninguna regla ni criterio ya cerrado en esa notebook. Produce
pipeline/data/processed/conjunto_referencia_m1_6_2_3.json.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_CATALOGO = REPO_ROOT / "pipeline" / "data" / "processed" / "catalogo_residencial_limpio_6_2_1.csv"
RUTA_ZONE_HEALTH = REPO_ROOT / "pipeline" / "data" / "processed" / "zone_health_composite_1_4_6.json"
RUTA_SALIDA = REPO_ROOT / "pipeline" / "data" / "processed" / "conjunto_referencia_m1_6_2_3.json"


# --- Celda 5: carga del catálogo y Zone Health ---

df_catalogo = pd.read_csv(RUTA_CATALOGO)

antes = len(df_catalogo)
df_catalogo = df_catalogo[df_catalogo["corregimiento"] != "zona_no_determinada"]
df_catalogo = df_catalogo[df_catalogo["precio_no_evaluable"] == False]
print(f"Catálogo filtrado para construcción de referencia: {len(df_catalogo)} / {antes} filas")

with open(RUTA_ZONE_HEALTH, encoding="utf-8") as f:
    zone_health = json.load(f)["zonas"]


# --- Celda 7: perfiles de lifestyle sintéticos y reglas de ground truth ---

PERFILES_LIFESTYLE = {
    "familia_con_ninos": {
        "descripcion": "Familia con niños que prioriza seguridad y cercanía a parques/colegios, necesita espacio.",
        "corregimientos": ["Betania", "San Francisco"],  # mayor (seguridad + amenidades) del desglose
        "price_usd_min": 150000,
        "price_usd_max": 700000,
        "bedrooms_min": 3,
        "area_m2_min": 120,
    },
    "profesional_joven": {
        "descripcion": "Profesional joven soltero que prioriza transporte y caminabilidad, unidad compacta.",
        "corregimientos": ["Bella Vista", "El Cangrejo", "Marbella", "Obarrio"],  # mayor (transporte + walkability)
        "price_usd_max": 450000,
        "bedrooms_min": 1,
        "bedrooms_max": 2,
    },
    "pareja_presupuesto_medio": {
        "descripcion": "Pareja sin hijos con presupuesto medio, busca balance general de calidad de zona.",
        "corregimientos": [z for z, r in zone_health.items() if r["composite"] is not None and r["composite"] >= 0.5],
        "price_usd_min": 236325,
        "price_usd_max": 650000,
        "bedrooms_min": 2,
        "bedrooms_max": 2,
    },
    "inversionista_renta_corta": {
        "descripcion": "Inversionista de renta corta, busca zona reconocida y buena conectividad, unidad pequeña.",
        "corregimientos": ["San Francisco", "Bella Vista", "El Cangrejo", "Marbella", "Obarrio"],
        "price_usd_min": 150000,
        "bedrooms_min": 1,
        "bedrooms_max": 2,
        "area_m2_max": 100,
    },
    "retirado_tranquilidad": {
        "descripcion": "Persona retirada que prioriza seguridad y amenidades, no depende de transporte diario.",
        "corregimientos": ["Betania"],  # mayor (seguridad + amenidades) combinado, ver sección 1
        "bedrooms_min": 2,
        "bedrooms_max": 3,
    },
    "presupuesto_ajustado_sin_auto": {
        "descripcion": "Presupuesto ajustado, depende de transporte público, unidad pequeña.",
        "corregimientos": ["Bella Vista", "El Cangrejo", "Marbella", "Obarrio", "Betania", "San Francisco"],
        "price_usd_max": 200000,
    },
}
print(f"{len(PERFILES_LIFESTYLE)} perfiles definidos.")


# --- Celda 8: filtro estructural ---

def aplicar_filtro_estructural(df, perfil):
    m = df["corregimiento"].isin(perfil["corregimientos"])
    if "price_usd_min" in perfil:
        m &= df["price_usd"] >= perfil["price_usd_min"]
    if "price_usd_max" in perfil:
        m &= df["price_usd"] <= perfil["price_usd_max"]
    if "bedrooms_min" in perfil:
        m &= df["bedrooms"] >= perfil["bedrooms_min"]
    if "bedrooms_max" in perfil:
        m &= df["bedrooms"] <= perfil["bedrooms_max"]
    if "area_m2_min" in perfil:
        m &= df["area_m2"] >= perfil["area_m2_min"]
    if "area_m2_max" in perfil:
        m &= df["area_m2"] <= perfil["area_m2_max"]
    return m

ground_truth_estructural = {}
for nombre, perfil in PERFILES_LIFESTYLE.items():
    m = aplicar_filtro_estructural(df_catalogo, perfil)
    ground_truth_estructural[nombre] = set(df_catalogo.loc[m, "listing_id"])


# --- Celda 11: criterio cualitativo y ground truth final ---

KEYWORDS_CUALITATIVOS = {
    "familia_con_ninos": {"incluye": ["familiar", "colegio", "escuela"]},
    "profesional_joven": {"incluye": ["restaurante", "bar", "vida nocturna", "caminable"],
                           "excluye": ["renta corta", "airbnb"]},
    "pareja_presupuesto_medio": {"incluye": ["tranquil", "céntric"], "excluye": ["vida nocturna"]},
    "inversionista_renta_corta": {"incluye": ["renta corta", "airbnb", "piscina", "gimnasio", "amoblado"]},
    "retirado_tranquilidad": {"incluye": ["tranquil", "residencial"], "excluye": ["vía principal", "avenida"]},
    "presupuesto_ajustado_sin_auto": {"incluye": ["metro", "parada", "transporte"]},
}

def aplicar_filtro_cualitativo(df, criterio):
    descripciones = df["descripcion"].fillna("").str.lower()
    tiene_texto = df["descripcion_fuente"] != "ninguna"  # regla explicita: sin texto, no cuenta como match
    incluye = criterio.get("incluye", [])
    m = descripciones.str.contains("|".join(incluye), regex=True, na=False) if incluye else pd.Series(True, index=df.index)
    for kw in criterio.get("excluye", []):
        m &= ~descripciones.str.contains(kw, regex=False, na=False)
    return m & tiene_texto

ground_truth_final = {}
for nombre, perfil in PERFILES_LIFESTYLE.items():
    m_estructural = aplicar_filtro_estructural(df_catalogo, perfil)
    m_cualitativo = aplicar_filtro_cualitativo(df_catalogo, KEYWORDS_CUALITATIVOS[nombre])
    m_final = m_estructural & m_cualitativo
    ids_final = set(df_catalogo.loc[m_final, "listing_id"])
    ground_truth_final[nombre] = ids_final

for nombre, ids in ground_truth_final.items():
    assert len(ids) > 0, f"Perfil '{nombre}' quedó sin ningún match tras el filtro cualitativo sobre descripcion"
print("Los 6 perfiles tienen al menos un match en el ground truth reconstruido sobre descripcion.")


# --- Materialización a JSON ---

def sha256_archivo(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()

salida = {
    "fuente_catalogo": RUTA_CATALOGO.name,
    "hash_catalogo": sha256_archivo(RUTA_CATALOGO),
    "fecha_materializacion": datetime.now(timezone.utc).isoformat(),
    "perfiles": {},
}

for nombre, perfil in PERFILES_LIFESTYLE.items():
    reglas_estructurales = {k: v for k, v in perfil.items() if k != "descripcion"}
    salida["perfiles"][nombre] = {
        "reglas_estructurales": reglas_estructurales,
        "criterio_cualitativo": KEYWORDS_CUALITATIVOS[nombre],
        "n_solo_estructural": len(ground_truth_estructural[nombre]),
        "listing_ids_ground_truth": sorted(int(i) for i in ground_truth_final[nombre]),
    }

RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
with open(RUTA_SALIDA, "w", encoding="utf-8") as f:
    json.dump(salida, f, ensure_ascii=False, indent=2)

print(f"\nArchivo materializado en: {RUTA_SALIDA}")
print("\nConteos finales por perfil:")
for nombre, datos in salida["perfiles"].items():
    print(f"  {nombre}: {len(datos['listing_ids_ground_truth'])}")
