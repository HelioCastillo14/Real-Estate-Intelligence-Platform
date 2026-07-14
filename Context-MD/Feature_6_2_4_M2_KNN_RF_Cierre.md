# Feature 6.2.4 — Notebook 2 (M2: KNN semáforo + Random Forest) — Cierre

**Notebook:** `notebooks/02_m2_knn_semaforo_rf.ipynb`
**Fecha de cierre:** 2026-07-13
**Estado:** CERRADO (con CP-1 revisado)

---

## 1. Dataset de entrenamiento

1,042 filas, 7 corregimientos (Pedregal y Parque Lefevre excluidos por volumen insuficiente para
5-fold CV, Acta de Feature 1.2 §5.3). Comparable = corregimiento + tipo_inmueble (Notebook 6.2.1),
restringido a `tipo_inmueble == "Apartamentos"` — hallazgo nuevo en este notebook: el enriquecimiento
de 6.2.1 reveló contaminación no residencial que el filtro de título de Feature 1.2 no había
detectado (un salón de belleza, un local comercial, un terreno, y un hotel de \$13,000,000 dentro de
la categoría "Edificios", con `bedrooms == 0` como señal de venta de edificio completo, no unidad
individual). Documentado en el notebook §1.1, no como corrección retroactiva de 6.2.1.

## 2. Resultado MAE (CP-1)

| Modelo | MAE CV | MAE test | % del precio promedio |
|---|---|---|---|
| KNN (k=5) | \$165,707 | \$187,543 | 33.4% |
| Random Forest | \$132,388 | \$149,270 | 26.6% |

Diferencia RF vs. KNN: 20.4% — sobre el umbral de 15% ya cerrado en Feature 6.2 (documentar como
hallazgo, no iterar automáticamente).

## 3. Modelo de producción del semáforo — decisión final

**KNN.** RF se mantiene como comparación metodológica obligatoria (su `.feature_importances_` es
el ranking de price drivers — `area_m2` domina con ~89% de la importancia), no reemplaza al
producto. Razón: explicabilidad ante audiencia no técnica — KNN produce una respuesta directamente
defendible ("estos son los comparables más similares, esto costaron"), consistente con el diseño
original de comparables del Acta de Feature 1.2 (decisión #4). No se reabre esa decisión.

## 4. Umbral del semáforo — recalibrado

El umbral original (±10% del precio predicho) se diseñó antes de conocer el MAE real y resultó mal
calibrado: su semi-ancho es menor que el MAE del modelo en 95-97% de las propiedades de test — la
mayoría de las etiquetas verde/rojo bajo ese umbral reflejaban ruido del modelo, no señal real.

**Umbral final:** derivado del residual real (`price_usd_real - price_usd_predicho`) de KNN.
- **Amarillo:** entre -1.5×MAE y +1.5×MAE (±\$281,315 sobre el precio predicho, con MAE test de
  \$187,543)
- **Rojo:** más de +1.5×MAE (sobrevalorado)
- **Verde:** menos de -1.5×MAE (buen precio)

Sin zona sin definir — el hueco que había entre 0.5 y 1.5 MAE en una propuesta intermedia queda
absorbido dentro de "amarillo".

**Lectura correcta de "amarillo", explícita:** no significa "precio neutro" ni "precio justo" —
significa que no hay evidencia estadística suficiente, dado el error típico del modelo, para
afirmar que la propiedad está sobre o subvalorada. Es una zona de incertidumbre del modelo, no un
veredicto de precio.

**Distribución final sobre el set de test (n=209):**

| Etiqueta | n | % |
|---|---|---|
| Amarillo | 172 | 82.3% |
| Verde | 19 | 9.1% |
| Rojo | 18 | 8.6% |

## 5. Hallazgo de investigación — RF + embedding semántico (no adoptado)

Experimento diagnóstico: RF con las 4 features estructurales + el embedding de `gemini-embedding-001`
(3072-dim, ya calculado en 6.2.3, sin nueva llamada a la API) reduce el MAE de forma medible
(~16% CV, ~21% test) frente al RF solo-estructural, sin señales claras de sobreajuste
desproporcionado (proporción test/train similar, `area_m2` sigue dominando la importancia).

**No se adopta como modelo de producción ni como reemplazo del RF-comparación.** 833 filas de
entrenamiento contra 3,082 columnas totales es una proporción features/filas alta — la mejora es
real dentro de este split, no una validación robusta para producción.

**Dirección de trabajo futura, fuera de alcance de Feature 6.2:** reducir la dimensionalidad del
embedding antes de considerar cualquier incorporación de señal semántica a un modelo de precio.

## 6. Artifacts

`pipeline/models/knn_semaforo_precio_6_2_4.pkl`, `random_forest_6_2_4.pkl`,
`escalador_knn_6_2_4.pkl`.
