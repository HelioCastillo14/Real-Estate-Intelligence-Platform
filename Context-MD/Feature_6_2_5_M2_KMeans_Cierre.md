# Feature 6.2.5 — Notebook 3 (M2: KMeans segmentación de mercado) — Cierre

**Notebook:** `notebooks/03_m2_kmeans_segmentacion.ipynb`
**Fecha de cierre:** 2026-07-13
**Estado:** CERRADO

---

## 1. Dataset

Mismo filtrado que 6.2.4: 1,042 filas, 7 corregimientos (Pedregal/Parque Lefevre excluidos por
volumen), `tipo_inmueble == "Apartamentos"`.

## 2. Features de clustering

`price_usd`, `area_m2`, `precio_por_m2`, `bedrooms`, `bathrooms` — escaladas. No se usó
`corregimiento` como feature (para segmentar por tipo de propiedad, no redescubrir la partición
geográfica ya conocida); se cruzó después de forma descriptiva.

## 3. Selección de k y resultado

k probado de 2 a 10 (método del codo + Silhouette). **k óptimo = 2, Silhouette = 0.388.**

| Cluster | n | Precio mediana | Área mediana | Hab/Baños mediana |
|---|---|---|---|---|
| 0 — compacto/económico | 662 | \$270,000 | 92 m² | 2/2 |
| 1 — grande/premium | 380 | \$736,000 | 300 m² | 3/3 |

## 4. Distribución geográfica de los clusters (descriptiva, no insumo del modelo)

Costa del Este (64%) y San Francisco (45%) concentran mayor proporción del cluster premium que el
resto de las zonas (14-21%).

## 5. Artifacts

`pipeline/models/kmeans_segmentacion_6_2_5.pkl`, `escalador_kmeans_6_2_5.pkl`.
