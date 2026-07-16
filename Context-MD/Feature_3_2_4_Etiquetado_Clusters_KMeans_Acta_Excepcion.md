# Feature 3.2.4 — Etiquetado cualitativo de clusters KMeans
## Acta de cierre con excepción documentada

**Fecha:** 2026-07-15
**Estado:** CERRADA, con excepción documentada al requisito original de revisión por ≥2 miembros del equipo.

---

## 1. Contexto

La condición de Done original de `3.2.4` en el WBS exige que el etiquetado cualitativo de los clusters de KMeans sea revisado por al menos 2 integrantes del equipo (Besto, Copri, Montoya, Rives), como control de calidad sobre una interpretación subjetiva de datos cuantitativos.

Adicionalmente, el WBS original especificaba **5 clusters** a etiquetar. Esta discrepancia ya fue resuelta formalmente en sesión previa (`Feature_6_2_5_M2_KMeans_Cierre.md`, 2026-07-14): el k óptimo medido por método del codo + Silhouette score sobre el dataset real es **k=2** (Silhouette=0.388), no k=5. La decisión de k=2 no se reabre aquí.

## 2. Decisión de excepción

**No hay tiempo disponible en la sesión de hoy para convocar una revisión formal con ≥2 miembros del equipo.** Se aplica la misma excepción ya usada y documentada en Feature 1.4 (Zone Health Composite Index) para la revisión cualitativa de dimensiones: el etiquetado se realiza y confirma únicamente entre Besto (PM/líder técnico) y Claude, dejando constancia explícita de la desviación en vez de omitirla o presentarla como si hubiera cumplido el estándar completo.

Esta excepción queda disponible para re-apertura y revisión formal por el resto del equipo en cualquier momento posterior, sin que eso invalide el trabajo de producción que dependa de estas etiquetas mientras tanto.

## 3. Etiquetado confirmado

Basado en `Feature_6_2_5_M2_KMeans_Cierre.md` (k=2, Silhouette=0.388):

| `cluster_id` | Etiqueta descriptiva | n | Mediana precio | Mediana área |
|---|---|---|---|---|
| 0 | Compacto / económico | 662 | $270,000 | 92 m² |
| 1 | Grande / premium | 380 | $736,000 | 300 m² |

**Observación ya documentada, no nueva:** Costa del Este y San Francisco sesgan hacia el segmento premium — consistente con los hallazgos de precio y volumen ya reportados en Feature 1.4 y en el análisis de MAE por zona de `3.1.4` (San Francisco concentra la mayor variabilidad de precio del catálogo).

## 4. Dónde vive esta etiqueta — decisión de esquema ya cerrada

Confirmado contra `Ajuste_WBS_1_5_4_Esquema_Scores.md`: `valuacion_segmento_kmeans.cluster_id` almacena únicamente el entero crudo (0/1), **sin interpretación textual embebida** en la tabla de producción. Esta Acta es la fuente de verdad de la etiqueta legible; si se decide persistirla en base de datos, debe vivir en una tabla de metadata separada (`cluster_id → nombre, fecha_asignada`), nunca como string directo en `valuacion_segmento_kmeans` — para no congelar una interpretación que podría invalidarse si el KMeans se recalcula en el futuro.

## 5. Estado

**Feature 3.2.4: CERRADA**, con excepción de revisión de una sola persona (Besto + Claude) documentada explícitamente, siguiendo el precedente ya establecido y aceptado en Feature 1.4. No bloquea `3.2.5`.
