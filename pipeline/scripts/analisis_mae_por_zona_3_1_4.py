"""MAE por corregimiento del KNN de producción, vía 5-fold CV (Feature 3.1.4, M2).

**Script de análisis/diagnóstico, no servicio de producción — a propósito, no en
`backend/app/services/`.** A diferencia de 3.1.1-3.1.3 (`comparables_knn.py`,
`estimacion_precio_knn.py`, `semaforo_precio_knn.py`), esta tarea no se consume en tiempo real
por ningún endpoint: es evidencia adicional de granularidad sobre el mismo modelo ya entrenado y
cerrado (Notebook 2, Feature 6.2.4), para documentar si el error del KNN es homogéneo entre
zonas o si el umbral global (±1.5×MAE = ±$281,315, 3.1.3) esconde variación real por
corregimiento. Mismo patrón que el resto de `pipeline/scripts/`: se corre una vez, imprime/
persiste su resultado, no expone una función que otro módulo importe en caliente.

**Esto NO existía en el notebook — confirmado, no asumido.** `notebooks/02_m2_knn_semaforo_rf.ipynb`
no tiene ninguna celda que agrupe el MAE por `corregimiento` (grep sobre el notebook completo:
cero resultados de "groupby"/"por zona"/"por corregimiento"). El MAE del notebook (celda 15:
$165,707 CV sobre train; celda 30: $187,543 sobre test) es un único número agregado sobre las 7
zonas juntas.

**Metodología — mide el error del MISMO modelo de producción, no entrena un modelo nuevo por
zona.** Entrenar un KNN separado por zona sería una decisión de diseño distinta (cambiaría qué
modelo se evalúa) y fuera de alcance de esta tarea. En cambio: se reproduce el KNN de producción
completo (mismas 10 features, mismo `k=5`, mismo escalado, mismo `RANDOM_STATE=42` que
`notebooks/02_m2_knn_semaforo_rf.ipynb` celdas 2/4/8/13/15) y se usa
`cross_val_predict` con el mismo `KFold(n_splits=5, shuffle=True, random_state=42)` de la celda
15 para obtener una predicción out-of-fold por cada fila del set de entrenamiento (833 filas) —
cada fila se predice con un modelo que NUNCA la vio. Los residuales resultantes se agrupan por
`corregimiento` (decodificado de las columnas one-hot `zona_*`) para el MAE por zona. Esto es
comparable directamente al $165,707 de CV de la celda 15 (mismo split, mismo mecanismo), no al
$187,543 de test (set de test distinto, más pequeño, no participa en CV).

**Restricción ya cerrada del proyecto, respetada aquí:** Pedregal y Parque Lefevre quedan
excluidos del dataset desde la misma celda 4 del notebook (Acta 1.2 §5.3, volumen insuficiente
para 5-fold CV) — este script hereda ese filtro tal cual, no intenta forzar CV sobre esas 2
zonas. Las 7 zonas restantes tienen entre 49 (Marbella) y 451 (San Francisco) filas — todas
sobradamente viables para 5 folds (mínimo ~10 filas/fold en el caso más chico).

**Esta tarea documenta evidencia, no decide diseño:** si alguna zona se desvía
significativamente del MAE global, este script lo señala en su output — no cambia el umbral de
3.1.3 ni introduce un umbral por zona. Esa decisión, si se toma, es de una tarea futura.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold, cross_val_predict, train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_CATALOGO = REPO_ROOT / "pipeline" / "data" / "processed" / "catalogo_residencial_limpio_6_2_1.csv"
RUTA_MODELOS = REPO_ROOT / "pipeline" / "models"
RUTA_SALIDA = RUTA_MODELOS / "mae_por_zona_3_1_4.pkl"

RANDOM_STATE = 42
K_VECINOS = 5
ZONAS_EXCLUIDAS_ACTA_1_2 = ["Pedregal", "Parque Lefevre"]
COLUMNAS_NUMERICAS = ["bedrooms", "bathrooms", "area_m2"]

MAE_GLOBAL_CV_NOTEBOOK = 165707  # celda 15, redondeado — referencia, no recalculado aquí
MAE_GLOBAL_TEST_NOTEBOOK = 187543.4765550239  # celda 30/33, reproducido exacto en 3.1.3


def _preparar_dataset() -> pd.DataFrame:
    df = pd.read_csv(RUTA_CATALOGO)
    df = df[df["corregimiento"] != "zona_no_determinada"]
    df = df[df["precio_no_evaluable"] == False]
    df = df[~df["corregimiento"].isin(ZONAS_EXCLUIDAS_ACTA_1_2)]
    df = df[df["tipo_inmueble"] == "Apartamentos"]
    df = df.dropna(subset=["area_m2"])
    return df


def calcular_mae_por_zona() -> pd.DataFrame:
    """MAE por corregimiento (OOF, 5-fold CV) del KNN de producción sobre el set de entrenamiento."""
    df = _preparar_dataset()

    df_modelo = pd.get_dummies(
        df[["corregimiento", "bedrooms", "bathrooms", "area_m2"]],
        columns=["corregimiento"], prefix="zona",
    )
    X = df_modelo
    y = df["price_usd"]
    corregimiento_por_fila = df["corregimiento"].reset_index(drop=True)

    X_train, _, y_train, _, corregimiento_train, _ = train_test_split(
        X, y, corregimiento_por_fila, test_size=0.2, random_state=RANDOM_STATE
    )

    escalador = StandardScaler()
    X_train_esc = X_train.copy()
    X_train_esc[COLUMNAS_NUMERICAS] = escalador.fit_transform(X_train[COLUMNAS_NUMERICAS])

    knn = KNeighborsRegressor(n_neighbors=K_VECINOS)
    cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    pred_oof = cross_val_predict(knn, X_train_esc, y_train, cv=cv)

    residual = y_train.values - pred_oof
    tabla = pd.DataFrame({
        "corregimiento": corregimiento_train.values,
        "residual_abs": np.abs(residual),
    })
    resumen = (
        tabla.groupby("corregimiento")["residual_abs"]
        .agg(mae="mean", n="count")
        .sort_values("mae", ascending=False)
        .reset_index()
    )
    resumen["mae_vs_global_cv_pct"] = (resumen["mae"] / MAE_GLOBAL_CV_NOTEBOOK - 1) * 100
    return resumen


if __name__ == "__main__":
    resumen = calcular_mae_por_zona()
    pd.set_option("display.float_format", lambda x: f"{x:,.1f}")
    print(f"MAE global de referencia — CV (celda 15): ${MAE_GLOBAL_CV_NOTEBOOK:,}")
    print(f"MAE global de referencia — test (celda 30/33): ${MAE_GLOBAL_TEST_NOTEBOOK:,.0f}")
    print()
    print(resumen.to_string(index=False))

    with open(RUTA_SALIDA, "wb") as f:
        pickle.dump({
            "resumen": resumen,
            "mae_global_cv_notebook": MAE_GLOBAL_CV_NOTEBOOK,
            "mae_global_test_notebook": MAE_GLOBAL_TEST_NOTEBOOK,
            "random_state": RANDOM_STATE,
        }, f)
    print(f"\nGuardado: {RUTA_SALIDA}")
