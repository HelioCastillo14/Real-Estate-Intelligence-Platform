"""Export del conjunto de TEST del semáforo KNN — predicho vs. real (Feature 3.5.1, M2).

**Población exacta — 209 filas de test, no train (833), no el batch de 1,042 de 3.1.6.**
Reproduce la misma partición del Notebook 2 (Feature 6.2.4, `notebooks/02_m2_knn_semaforo_rf.ipynb`,
celdas 2/4/8/13/15, mismo `RANDOM_STATE=42`, mismo `catalogo_residencial_limpio_6_2_1.csv`) —
igual que `pipeline/scripts/generar_mapeo_listing_id_knn_6_2_4.py` (3.1.6), que generó el mapeo
de las 833 filas de TRAIN. Las de test son el complemento exacto dentro de esa misma
reproducción del split, no "el resto del catálogo" ni "todo lo que no está en el mapeo de
train" calculado por otra vía — se obtienen del mismo `train_test_split()` de una sola pasada,
para garantizar que train y test sean complementarios por construcción y no por dos cálculos
separados que podrían desalinearse.

**Por qué no reusar el batch de 1,042 filas de 3.1.6:** ese batch mezcla train+test a propósito
(valúa el catálogo completo elegible para producción) — es precisamente la población cuya
mezcla causó el hallazgo de fuga de datos documentado en
`Context-MD/Hallazgo_Fuga_Datos_Batch_3_1_6_Cierre.md`. Este export es para la transparencia del
modelo (3.5.2 lo consume después) — necesita el residual *genuinamente* out-of-sample, no el
residual ya corregido por exclusión de auto-comparable (esa corrección resuelve el batch de
producción, no reconstruye una medición de generalización supervisada limpia). Usar `predict()`
directo del modelo entrenado sobre `X_test_esc` (mismo mecanismo que `pred_knn_test` en la celda
15 del notebook) es la forma correcta de reproducir exactamente el número ya publicado
($187,543 test).

**`precio_predicho` viene de `modelo.predict()`, no de promediar comparables de
`buscar_comparables_knn()`:** son matemáticamente equivalentes para k=5 con pesos uniformes
(`predict()` de `KNeighborsRegressor` ES el promedio de los k vecinos), pero usar `predict()`
directo evita cualquier dependencia del mecanismo de exclusión por `listing_id` de 3.1.1/3.1.6 —
irrelevante aquí porque ninguna de estas 209 filas está en el training set, así que esa
exclusión nunca se activaría de todos modos, pero usar el camino más directo (predict) es más
trazable para un artifact cuyo propósito es reproducir el número exacto del notebook.
"""

import pickle
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_CATALOGO = REPO_ROOT / "pipeline" / "data" / "processed" / "catalogo_residencial_limpio_6_2_1.csv"
RUTA_MODELOS = REPO_ROOT / "pipeline" / "models"
RUTA_KNN = RUTA_MODELOS / "knn_semaforo_precio_6_2_4.pkl"
RUTA_LISTING_IDS_TRAIN = RUTA_MODELOS / "knn_semaforo_precio_6_2_4_listing_ids_train.pkl"
RUTA_SALIDA = REPO_ROOT / "pipeline" / "data" / "processed" / "conjunto_test_semaforo_knn_3_5_1.csv"

RANDOM_STATE = 42
ZONAS_EXCLUIDAS_ACTA_1_2 = ["Pedregal", "Parque Lefevre"]
COLUMNAS_NUMERICAS = ["bedrooms", "bathrooms", "area_m2"]

MAE_TEST_REFERENCIA = 187543.4765550239  # reproducido y verificado en 3.1.3, celda 30/33 del notebook
PCT_PRECIO_PROMEDIO_REFERENCIA = 33.4  # ya publicado (Feature_6_2_4_M2_KNN_RF_Cierre.md)


def _preparar_dataset() -> pd.DataFrame:
    df = pd.read_csv(RUTA_CATALOGO)
    df = df[df["corregimiento"] != "zona_no_determinada"]
    df = df[df["precio_no_evaluable"] == False]
    df = df[~df["corregimiento"].isin(ZONAS_EXCLUIDAS_ACTA_1_2)]
    df = df[df["tipo_inmueble"] == "Apartamentos"]
    df = df.dropna(subset=["area_m2"])
    return df


def generar_conjunto_test() -> pd.DataFrame:
    df = _preparar_dataset()

    df_modelo = pd.get_dummies(
        df[["corregimiento", "bedrooms", "bathrooms", "area_m2"]],
        columns=["corregimiento"], prefix="zona",
    )
    X = df_modelo
    y = df["price_usd"]
    listing_id_por_fila = df["listing_id"].reset_index(drop=True)
    corregimiento_por_fila = df["corregimiento"].reset_index(drop=True)

    X_train, X_test, y_train, y_test, listing_id_train, listing_id_test, _, corregimiento_test = train_test_split(
        X, y, listing_id_por_fila, corregimiento_por_fila, test_size=0.2, random_state=RANDOM_STATE
    )

    # Verificación cruzada contra el mapeo de train ya generado en 3.1.6 — deben ser el mismo
    # split, no dos reproducciones que coincidan por casualidad.
    with open(RUTA_LISTING_IDS_TRAIN, "rb") as f:
        listing_ids_train_363 = set(pickle.load(f))
    listing_ids_train_aqui = set(listing_id_train.tolist())
    if listing_ids_train_aqui != listing_ids_train_363:
        raise RuntimeError(
            "El split de train reproducido aquí no coincide con el mapeo ya verificado de 3.1.6 "
            f"({RUTA_LISTING_IDS_TRAIN.name}) — no se exporta el conjunto de test sin esta "
            "garantía, podría no ser el complemento correcto."
        )
    listing_ids_test_aqui = set(listing_id_test.tolist())
    if listing_ids_train_363 & listing_ids_test_aqui:
        raise RuntimeError("Intersección no vacía entre train y test — split corrupto, no se exporta.")

    escalador = StandardScaler()
    X_train_esc = X_train.copy()
    X_test_esc = X_test.copy()
    X_train_esc[COLUMNAS_NUMERICAS] = escalador.fit_transform(X_train[COLUMNAS_NUMERICAS])
    X_test_esc[COLUMNAS_NUMERICAS] = escalador.transform(X_test[COLUMNAS_NUMERICAS])

    with open(RUTA_KNN, "rb") as f:
        modelo = pickle.load(f)["modelo"]

    # Verificación de que el modelo cargado es el mismo que se entrenaría con esta reproducción
    # (mismo n de filas de train) — no repetimos el fit, usamos el pickle de producción tal cual.
    if modelo.n_samples_fit_ != len(X_train):
        raise RuntimeError(
            f"El modelo de producción fue entrenado con {modelo.n_samples_fit_} filas pero esta "
            f"reproducción da {len(X_train)} — no son la misma reproducción, no se exporta."
        )

    pred_test = modelo.predict(X_test_esc)

    return pd.DataFrame({
        "propiedad_id": listing_id_test.values,
        "precio_real": y_test.values,
        "precio_predicho": pred_test,
        "zona": corregimiento_test.values,
    })


if __name__ == "__main__":
    conjunto_test = generar_conjunto_test()
    print(f"Filas exportadas: {len(conjunto_test)} (esperado: 209)")

    mae_recalculado = (conjunto_test["precio_real"] - conjunto_test["precio_predicho"]).abs().mean()

    print(f"MAE recalculado desde el export: ${mae_recalculado:,.4f}")
    print(f"MAE de referencia (3.1.3, celda 30/33 del notebook): ${MAE_TEST_REFERENCIA:,.4f}")
    print(f"Coincide exactamente: {abs(mae_recalculado - MAE_TEST_REFERENCIA) < 1e-6}")
    print()

    # El % publicado (celda 26 del notebook, "Resultado para revisión") divide el MAE de test
    # contra `df["price_usd"].mean()` del dataset COMPLETO de 1,042 filas (df, antes del split),
    # no contra la media de las 209 filas de test — verificado leyendo la celda exacta, no
    # asumido. Recalcular contra la media del propio conjunto de test (209 filas) da un
    # denominador distinto (~$581,000 vs. ~$561,495) y por lo tanto un % distinto (~32.3% vs.
    # 33.4%) — no es un error del export, es una diferencia real de población en el
    # denominador, reproducida aquí exactamente como el notebook la calculó.
    pct_vs_media_test = mae_recalculado / conjunto_test["precio_real"].mean() * 100
    pct_vs_media_catalogo_completo = mae_recalculado / _preparar_dataset()["price_usd"].mean() * 100

    print(f"MAE como % de la media del propio conjunto de test (209 filas): {pct_vs_media_test:.2f}%")
    print(f"MAE como % de la media del catálogo completo de 1,042 filas (metodología real del "
          f"notebook, celda 26): {pct_vs_media_catalogo_completo:.2f}%")
    print(f"Referencia ya publicada (Feature_6_2_4_M2_KNN_RF_Cierre.md): {PCT_PRECIO_PROMEDIO_REFERENCIA}%")
    print(f"Coincide con la metodología real (±0.05pp): "
          f"{abs(pct_vs_media_catalogo_completo - PCT_PRECIO_PROMEDIO_REFERENCIA) < 0.05}")

    conjunto_test.to_csv(RUTA_SALIDA, index=False)
    print(f"\nGuardado: {RUTA_SALIDA}")
