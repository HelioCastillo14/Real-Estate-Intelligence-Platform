# Hallazgo — Fuga de datos por auto-comparación en el batch de producción de 3.1.6 — Cierre

**Feature:** 3.1.6 (M2, KNN semáforo de precio — batch de carga a `valuacion_semaforo_knn`)
**Fecha de detección y cierre:** 2026-07-15
**Estado:** CERRADO, corrección aplicada y verificada. Batch aún no cargado a Supabase
(pendiente de confirmación final del usuario tras esta corrección).

---

## 1. Contexto — qué se estaba haciendo

3.1.6 valúa con el semáforo de precio KNN (3.1.1→3.1.5) el catálogo completo de propiedades
elegibles en `propiedades` (Supabase), no el CSV de `pipeline/data/processed/` que usó el
Notebook 2 (Feature 6.2.4) para entrenar/evaluar el modelo. El universo elegible resultó ser
1,042 filas (zona soportada por el KNN + `tipo_inmueble == "Apartamentos"` + datos completos) —
la misma población, en número, que el dataset filtrado del notebook.

## 2. El hallazgo

El primer dry-run del batch dio una distribución de semáforo notablemente distinta a la ya
publicada en el paper:

```
             paper (n=209, test del notebook)    batch (n=1042, catálogo completo)
verde        9.1%  (n=19)                        6.3%  (n=66)
amarillo    82.3%  (n=172)                       87.5%  (n=912)   <- +5.2pp, activa la regla de oro
rojo         8.6%  (n=18)                        6.1%  (n=64)
```

Por la regla de oro del proyecto (ninguna desviación notable frente a un número ya publicado se
resuelve ajustando código/filtros por cuenta propia), el batch se detuvo antes de insertar, sin
tocar nada, y se investigó la causa.

## 3. Causa raíz — aislada experimentalmente, no asumida

El pickle de producción del KNN (`knn_semaforo_precio_6_2_4.pkl`) fue entrenado sobre 833 filas
(80% de las 1,042, split de Notebook 2, `RANDOM_STATE=42`). El universo elegible del batch de
3.1.6 (1,042 filas del catálogo real en Supabase) resultó ser, en número exacto, la misma
población de 833 train + 209 test del notebook. `buscar_comparables_knn()` no tenía forma de
saber si la propiedad que se le pasaba ya era parte del training set del modelo — así que para
esas 833 filas, el modelo devolvía la propia propiedad como uno de sus 5 comparables (distancia
0, mismo `price_usd`), sesgando el residual hacia 0 y por lo tanto la etiqueta hacia "amarillo".

**Verificación experimental de la causa, antes de corregir nada:** se reprodujo la misma
partición train/test del notebook (mismo `RANDOM_STATE=42`) para etiquetar cada una de las 1,042
filas del batch como "fue train" o "fue test" del KNN, y se separó la distribución:

```
Filas que fueron TEST del KNN (n=209, nunca vistas durante el fit):
  verde 9.1% (19) / amarillo 82.3% (172) / rojo 8.6% (18)   -> IDÉNTICO al paper, exacto

Filas que fueron TRAIN del KNN (n=833, con auto-comparación):
  verde 5.6% (47) / amarillo 88.8% (740) / rojo 5.5% (46)   -> el sesgo vive aquí, únicamente
```

El subconjunto de test reproduce el paper número por número. El 100% del desvío del batch
completo proviene de las 833 filas con auto-comparación — no hay ningún otro problema en
3.1.1-3.1.5, ni en el umbral (±1.5×MAE, ya corregido en 3.1.3), ni en el pipeline de features.

## 4. Corrección aplicada

`KNeighborsRegressor` no asocia ningún identificador a sus datos de entrenamiento — `knn._y` es
un array plano de `price_usd` en el orden posicional exacto en que se llamó `knn.fit()`, sin
`listing_id`. Ese mapeo no existía en ningún artifact de 6.2.4.

1. **`pipeline/scripts/generar_mapeo_listing_id_knn_6_2_4.py`** (nuevo): reproduce la misma
   partición train/test del notebook, lleva `listing_id` como array paralelo a través del mismo
   `train_test_split()`, y **verifica antes de exportar** que `knn._y[posición]` coincide
   exactamente con el `price_usd` real del `listing_id` en cada una de las 833 posiciones —
   aborta sin exportar si no coincide. Exporta
   `pipeline/models/knn_semaforo_precio_6_2_4_listing_ids_train.pkl`.
2. **`buscar_comparables_knn()`** (3.1.1, `backend/app/services/comparables_knn.py`): nuevo
   parámetro opcional `listing_id: int | None = None`, agregado al final de la firma (no rompe
   ninguna llamada existente — ver §5). Si `listing_id` coincide con una posición del training
   set, pide `k+1` vecinos al modelo y descarta esa posición exacta del resultado (por posición,
   no por precio — ver verificación de precisión abajo), completando con un 6to comparable real.
3. **`valuacion_knn.py`** (3.1.5): pasa `listing_id` hacia `buscar_comparables_knn()` — ya lo
   recibía como parámetro, solo faltaba propagarlo.

**Verificación de precisión de la exclusión (por posición, no por precio):** un caso real de
prueba tenía dos comparables empatados en distancia 0 con precios distintos (`listing_id=136594`,
precio real \$120,000, comparable en \$119,000 de otra propiedad distinta con los mismos
atributos escalados). Sin corrección, ambos aparecían con distancia 0. Con corrección, solo se
excluyó el de \$120,000 (la posición real de 136594) — el de \$119,000, una propiedad legítima
distinta, se mantuvo. Una exclusión ingenua "por precio" habría corrompido este caso.

## 5. Verificación de no-regresión

- **Las 209 filas que fueron test del KNN:** comparadas programáticamente con y sin `listing_id`
  — **0 diferencias en las 209**. Ninguna está en el mapeo de training, así que el código sigue
  el mismo camino que antes de la corrección.
- **Épica 2 (M1), producción existente antes de esta sesión:** `buscar_comparables_knn()` no
  existía antes de hoy (es la tarea 3.1.1). El único router de producción de Épica 2
  (`backend/app/routers/match.py`) importa `busqueda_ann.py`/`explicador_compatibilidad.py`/
  `perfil_usuario.py` — ninguno importa ni referencia `comparables_knn.py`. `buscar_propiedades_ann()`
  (2.2.1, M1, búsqueda ANN vía pgvector) y `buscar_comparables_knn()` (3.1.1, M2, KNN sobre
  atributos estructurados) son funciones distintas sin relación de código, pese al nombre
  parecido. El cambio de firma es además retrocompatible por construcción: `listing_id` es el
  último parámetro, con default `None`.

## 6. Distribución final del batch (1,042 filas, tras la corrección)

```
             paper (n=209, test)    batch ANTES (n=1042)    batch DESPUÉS (n=1042)
verde        9.1%  (n=19)           6.3%  (n=66)             7.7%  (n=80)
amarillo    82.3%  (n=172)         87.5%  (n=912)            85.2%  (n=888)
rojo         8.6%  (n=18)           6.1%  (n=64)              7.1%  (n=74)
```

Ningún delta supera el umbral de 5 puntos porcentuales tras la corrección (máximo: amarillo
+2.9pp). La distribución no es idéntica al paper porque el batch sigue combinando train+test —
remover el auto-match elimina el sesgo más grosero (el match perfecto), no convierte las 833
filas de train en observaciones genuinamente out-of-sample. Esa diferencia residual es esperada
y honesta, no un error a perseguir.

## 7. Para el paper / defensa

Este hallazgo es citable como evidencia de rigor metodológico: se detectó una desviación frente
a un resultado ya publicado, se aisló experimentalmente la causa (comparando el subconjunto que
reproduce el paper exacto contra el subconjunto sesgado) antes de tocar cualquier código, se
corrigió con verificación de integridad explícita (el mapeo aborta si no coincide con los datos
reales), y se verificó no-regresión sobre la población no afectada (test set) y sobre el resto
del sistema (Épica 2). Ningún ajuste se hizo para forzar coincidencia con el número publicado —
la corrección resuelve la causa (auto-comparación), no el síntoma (el porcentaje).
