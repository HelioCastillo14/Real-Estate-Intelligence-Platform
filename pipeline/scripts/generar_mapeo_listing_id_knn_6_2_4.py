"""Mapeo posición-en-`knn._y` -> `listing_id` para el KNN de producción (hallazgo de 3.1.6, M2).

**Por qué existe este artifact.** El pickle de 6.2.4 (`knn_semaforo_precio_6_2_4.pkl`) guarda el
modelo `KNeighborsRegressor` ya entrenado, pero `KNeighborsRegressor` no asocia ningún
identificador de fila a sus datos de entrenamiento — `knn._y` es un array plano de `price_usd`
en el orden posicional en que se llamó `knn.fit(X_train_esc, y_train)` (Notebook 2, celda 15),
sin ningún `listing_id`. Ese vacío pasó inadvertido hasta el batch de 3.1.6: al valuar el
catálogo completo (1,042 filas elegibles), las 833 que fueron parte del training set del KNN se
comparaban contra sí mismas como uno de sus propios 5 comparables (distancia 0, mismo
`price_usd`), inflando "amarillo" a 87.5% frente al 82.3% ya publicado en el paper — confirmado
aislando el subconjunto de test (209 filas, nunca vistas por el KNN), que sí reproducía el paper
exacto. Corrección: `buscar_comparables_knn()` (3.1.1) necesita poder excluir la propia
propiedad de sus comparables cuando corresponda, y para eso necesita saber en qué posición de
`knn._y` cae cada `listing_id` de train — este script genera exactamente ese mapeo.

**Reproducción, no un cálculo nuevo.** Mismas celdas 2/4/8/13/15 del notebook
(`notebooks/02_m2_knn_semaforo_rf.ipynb`), mismo `RANDOM_STATE=42`, mismo
`catalogo_residencial_limpio_6_2_1.csv` — igual que
`pipeline/scripts/analisis_mae_por_zona_3_1_4.py`. La única diferencia es que aquí se lleva
`listing_id` como un array paralelo a través del mismo `train_test_split()` (pasado como tercer
argumento posicional, mismo mecanismo que `analisis_mae_por_zona_3_1_4.py` usa para
`corregimiento`), para que el orden de `listing_id` quede alineado posición a posición con el
orden real de `X_train`/`y_train` que se le pasó a `knn.fit()`.

**Verificación de integridad, no solo generación.** Antes de exportar, se re-entrena un KNN
idéntico (mismos hiperparámetros/escalado) sobre esta misma reproducción y se compara
`knn._y` contra el `price_usd` real de cada `listing_id` según el mapeo — deben coincidir
exactamente en las 833 posiciones. Si no coinciden, el script aborta sin exportar: un mapeo
posicional desalineado sería peor que no tener mapeo (excluiría el comparable equivocado en
silencio).
"""

import pickle
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_CATALOGO = REPO_ROOT / "pipeline" / "data" / "processed" / "catalogo_residencial_limpio_6_2_1.csv"
RUTA_MODELOS = REPO_ROOT / "pipeline" / "models"
RUTA_KNN = RUTA_MODELOS / "knn_semaforo_precio_6_2_4.pkl"
RUTA_SALIDA = RUTA_MODELOS / "knn_semaforo_precio_6_2_4_listing_ids_train.pkl"

RANDOM_STATE = 42
K_VECINOS = 5
ZONAS_EXCLUIDAS_ACTA_1_2 = ["Pedregal", "Parque Lefevre"]
COLUMNAS_NUMERICAS = ["bedrooms", "bathrooms", "area_m2"]


def _preparar_dataset() -> pd.DataFrame:
    df = pd.read_csv(RUTA_CATALOGO)
    df = df[df["corregimiento"] != "zona_no_determinada"]
    df = df[df["precio_no_evaluable"] == False]
    df = df[~df["corregimiento"].isin(ZONAS_EXCLUIDAS_ACTA_1_2)]
    df = df[df["tipo_inmueble"] == "Apartamentos"]
    df = df.dropna(subset=["area_m2"])
    return df


def generar_mapeo() -> list[int]:
    df = _preparar_dataset()

    df_modelo = pd.get_dummies(
        df[["corregimiento", "bedrooms", "bathrooms", "area_m2"]],
        columns=["corregimiento"], prefix="zona",
    )
    X = df_modelo
    y = df["price_usd"]
    listing_id_por_fila = df["listing_id"].reset_index(drop=True)

    X_train, _, y_train, _, listing_id_train, _ = train_test_split(
        X, y, listing_id_por_fila, test_size=0.2, random_state=RANDOM_STATE
    )

    escalador = StandardScaler()
    X_train_esc = X_train.copy()
    X_train_esc[COLUMNAS_NUMERICAS] = escalador.fit_transform(X_train[COLUMNAS_NUMERICAS])

    knn_verificacion = KNeighborsRegressor(n_neighbors=K_VECINOS)
    knn_verificacion.fit(X_train_esc, y_train)

    listing_ids = listing_id_train.reset_index(drop=True).tolist()

    precio_real_por_listing = dict(zip(df["listing_id"], df["price_usd"]))
    for posicion, listing_id in enumerate(listing_ids):
        if float(knn_verificacion._y[posicion]) != float(precio_real_por_listing[listing_id]):
            raise RuntimeError(
                f"Desalineación en posición {posicion}: knn._y={knn_verificacion._y[posicion]} "
                f"vs. price_usd real de listing_id={listing_id}="
                f"{precio_real_por_listing[listing_id]}. No se exporta el mapeo."
            )

    with open(RUTA_KNN, "rb") as f:
        knn_produccion = pickle.load(f)["modelo"]
    if len(listing_ids) != knn_produccion.n_samples_fit_:
        raise RuntimeError(
            f"El mapeo tiene {len(listing_ids)} posiciones pero el KNN de producción "
            f"({RUTA_KNN.name}) fue entrenado con {knn_produccion.n_samples_fit_} filas — "
            f"no son la misma reproducción, no se exporta."
        )

    return listing_ids


if __name__ == "__main__":
    listing_ids = generar_mapeo()
    print(f"Mapeo generado y verificado: {len(listing_ids)} posiciones, price_usd coincide "
          f"exactamente contra el catálogo real en las {len(listing_ids)}.")
    with open(RUTA_SALIDA, "wb") as f:
        pickle.dump(listing_ids, f)
    print(f"Guardado: {RUTA_SALIDA}")
