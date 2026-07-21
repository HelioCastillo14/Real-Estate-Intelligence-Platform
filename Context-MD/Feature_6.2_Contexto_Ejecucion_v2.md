# Feature 6.2 — Notebooks de Análisis y Entrenamiento — Contexto de Ejecución (v2)

**Alcance de este documento: SOLO Feature 6.2. No se toca Feature 1.5, ni las dependencias de Épica 2/3, ni el SP de ninguna otra tarea.**

**v2 vs v1:** esta versión reemplaza la tabla de dependencias del §3 (error corregido) y agrega §7 y §8, que documentan las decisiones de arquitectura cerradas y los checkpoints de revisión humana obligatorios antes de dar por cerrado cualquier notebook de entrenamiento. El resto del documento original permanece vigente sin cambios.

---

## 1. Qué es REIP y por qué existe Feature 6.2

REIP (Real Estate Intelligence Platform) es un proyecto de capstone (curso 0698, Gestión de Información, UTP) con tres módulos interdependientes:
- **M1 — Preference Matching**: matching de estilo de vida a propiedad, con embeddings + hybrid scorer.
- **M2 — Property Valuation Engine**: evaluación multidimensional (KNN semáforo de precio, KMeans segmentación, RF como comparación metodológica, Quality Scorer con LLM).
- **M3 — NLP Orchestration Layer**: búsqueda conversacional que orquesta M1 y M2.

El entregable académico final es un **paper corto formato IEEE (plantilla IEOM Society Panama 2026, máximo 12 páginas)** — no una tesis completa. La profesora exige evidencia del proceso analítico completo (EDA, limpieza, feature engineering, entrenamiento, storytelling) en notebooks de Jupyter. Esa evidencia no vive en el paper ni en el código de producción — vive aquí, en Feature 6.2.

**Principio rector:** *"el objetivo de este proyecto no es el producto, es resolver el problema de gestión de la información."* El software es el vehículo de entrega; los notebooks son la evidencia del método científico.

---

## 2. Restricciones de arquitectura — aplican a los 7 notebooks

1. **El notebook es la fuente de verdad del modelo entrenado. El backend consume, no re-entrena.** Cada notebook de entrenamiento (0, 0B, 1, 2, 3) exporta un artefacto serializado (`.pkl`, embeddings, o composite ya calculado) a una carpeta convenida — **la convención exacta se verifica contra el repo, no se asume** (ver Regla de Verificación, §7.4).

2. **No depender de Supabase ni del esquema de Feature 1.5.** Todos los notebooks leen directamente de los archivos que ya produce el pipeline (CSV/Parquet/JSON en `pipeline/data/processed/` y `pipeline/data/external/`, según extracción cerrada de Features 1.2/1.3/1.4) — no de consultas a Postgres. Rutas exactas se confirman contra el estado real del repo antes de codear (§7.4).

3. **EDA no se duplica.** Notebook 0 (catálogo) y Notebook 0B (Zone Health) son la única fuente de EDA general. Notebooks 1–5 importan/referencian su output, solo agregan EDA específico de su algoritmo.

4. **Dos categorías de notebook, formatos distintos:**
   - **Entrenamiento** (0, 0B, 1, 2, 3): dataset → split → métrica de validación (MAE, Silhouette, Precision@k).
   - **Experimentación** (4, 5): componentes LLM (Gemini), sin entrenamiento real — reporta iteración de prompt, % de éxito/parseo, distribución sobre muestra representativa.

5. **Toda cifra reportada debe ser trazable.** Si un hallazgo ya está documentado en una Acta, el notebook lo reproduce con código y gráfico — no lo redescubre ni lo contradice sin justificación explícita.

6. **Zone Health Composite Index (6.2.2) es un eje evaluativo independiente — nunca se cruza como feature de modelos de precio.** Decisión cerrada por colinealidad perfecta: es función determinística de corregimiento, y corregimiento ya es variable de agrupación en KNN/RF. No se usa en 6.2.4 ni 6.2.5, bajo ninguna variante.

---

## 3. Los 7 notebooks — tabla de dependencias corregida

| ID | Notebook | Tipo | SP | Depende de |
|---|---|---|---|---|
| 6.2.1 | Notebook 0 — EDA general del catálogo residencial | EDA base | 2 | Acta 1.2 (scraping cerrado) |
| 6.2.2 | Notebook 0B — Zone Health Composite Index | EDA + feature engineering | 2 | Acta 1.4 (Zone Health cerrado) |
| 6.2.3 | Notebook 1 — M1: embeddings + hybrid scorer + Precision@k | Entrenamiento | 5 | 6.2.1 |
| 6.2.4 | Notebook 2 — M2: KNN semáforo + Random Forest (fusionado, mismo dataset/split/CV) | Entrenamiento | 5 | 6.2.1 |
| 6.2.5 | Notebook 3 — M2: KMeans segmentación de mercado | Entrenamiento | 3 | 6.2.1 |
| 6.2.6 | Notebook 4 — M2: Quality Scorer | Experimentación | 3 | 6.2.1, GEMINI_API_KEY |
| 6.2.7 | Notebook 5 — M3: NLP Orchestration | Experimentación | 3 | **6.2.3, 6.2.4, 6.2.5, GEMINI_API_KEY** |

**Corrección respecto a v1:** 6.2.7 dependía únicamente de GEMINI_API_KEY en la versión original — error, dado que M3 orquesta M1 y M2 y no puede ejecutarse sin sus artefactos. 6.2.6 gana dependencia explícita de 6.2.1 (el Quality Scorer opera sobre el catálogo limpio, no el crudo).

**Total: 23 SP.**

---

## 4. Hallazgos ya documentados que cada notebook DEBE incorporar

*(sin cambios respecto a v1 — ver documento original para el detalle completo por notebook)*

- **Notebook 0 (6.2.1):** contaminación de tipo corregida; volumen real 1,361 vs. 3,800–4,200 proyectados (34%); "comparable" redefinido a corregimiento + tipo_inmueble.
- **Notebook 0B (6.2.2):** Costa del Este sin score; dimensión socioeconómica eliminada (peso redistribuido); seguridad con min-max invertido (n=5 documentado); walkability solo distancia-a-amenidades; 4 zonas no oficiales heredan del corregimiento padre; anomalías Betania/Bella Vista explicadas por profundidad desigual de auditoría, no calidad real — storytelling explícito obligatorio.
- **Notebook 1 / M1 (6.2.3):** conjunto de referencia sintético — advertencia de validación circular obligatoria; modelo de embeddings y dimensión documentados con precisión (desbloquea 1.5b a futuro).
- **Notebook 2 / KNN+RF (6.2.4):** Pedregal y Parque Lefevre excluidos (volumen insuficiente); dataset/split compartido entre KNN y RF; RF es evidencia metodológica, su `.feature_importances_` es el price driver ranking.
- **Notebook 3 / KMeans (6.2.5):** misma exclusión de Pedregal/Parque Lefevre; Silhouette se documenta aunque salga bajo.
- **Notebook 4 / Quality Scorer (6.2.6):** versiones de prompt, % JSON parseado, distribución de 4 scores, % no evaluable.
- **Notebook 5 / M3 (6.2.7):** conjunto mínimo del WBS 4.2.2 (10 válidas + 5 fuera de scope + 5 ambiguas); tasa de éxito/clarificación/fallback con ejemplos.

---

## 5. Bloqueos conocidos

- **GEMINI_API_KEY sin generar** — bloquea 6.2.6 y 6.2.7. Puede generarse en paralelo mientras se ejecutan 6.2.1–6.2.5.
- 6.2.1 y 6.2.2 pueden empezar de inmediato.

---

## 6. Entregable esperado de esta fase

7 notebooks `.ipynb` ejecutables de principio a fin sin errores, cada uno con: EDA, limpieza documentada, feature engineering, entrenamiento/experimento, gráficos, y celda final de storytelling. Notebooks de entrenamiento exportan artefacto serializado a ruta convenida.

---

## 7. Decisiones de arquitectura cerradas en esta sesión

**7.1 — Orquestación de Notebook 5 (M3): simulación de contrato de función.**
Notebook 5 no llama directamente `pickle.load()` + función en aislamiento (Opción descartada). Se define un wrapper con input/output fijo que imita la interfaz que tendrá el backend real de Épica 4 (FastAPI llamando a M1/M2). Esto prueba el patrón de orquestación, no solo el resultado del modelo combinado.

- El contrato debe marcarse explícitamente como **`v0 — sujeto a revisión en Épica 4`**.
- Debe definirse **en un solo lugar reutilizable** (un módulo o celda única de definición de funciones), nunca reescrito informalmente en cada celda de uso — para que actualizarlo en Épica 4 sea un cambio de una función, no de siete.

**7.2 — Zone Health Index fuera de KNN/RF.**
Confirmado: colinealidad perfecta con corregimiento (variable de agrupación ya presente). No se agrega dependencia 6.2.4→6.2.2. No se prueban variantes con/sin — el resultado es predecible por diseño, no vale el SP.

**7.3 — Precision@k de M1: múltiples cortes, no un k único.**
El producto real consume M1 de dos formas simultáneas: UI de lista (ranking visible) y M3 conversacional (top-1/3 sin ranking visible al usuario). Ambas leen del mismo ranking subyacente. Notebook 1 (6.2.3) reporta Precision@3, @5 y @10 sobre un único modelo — no se construyen matchers separados por caso de uso.

**7.4 — Regla de verificación de rutas (Paso 1 obligatorio, antes de cualquier celda de código).**
Aplicable a los 7 notebooks. Primera celda markdown de cada notebook debe confirmar y documentar, contra el estado real del repo (no asumido):
- Carpeta de artifacts serializados (dónde se guardan/leen modelos pickled de M1/M2).
- Rutas de lectura de `pipeline/data/processed/` y `pipeline/data/external/` que consume ese notebook específico.

Mismo patrón ya aplicado en las 7 subtareas de Feature 1.4 — no se rompe la disciplina al entrar a Épica 6.

---

## 8. Checkpoints de revisión humana obligatorios (no automatizables por Claude Code)

Dos decisiones quedan **explícitamente sin umbral numérico predefinido** — no por descuido, sino porque dependen de datos que aún no existen. Ambas requieren una revisión de Besto antes de que el notebook correspondiente se declare cerrado:

| Checkpoint | Notebook | Qué se revisa | Acción si falla |
|---|---|---|---|
| CP-1 | 6.2.4 (KNN) | MAE real del modelo de precio contra rango de precios del catálogo | Besto decide iterar features o cerrar — no hay umbral automático |
| CP-2 | 6.2.3 (M1) | Precision@3/@5/@10 real contra expectativa de uso en producto | Besto decide si el matching es aceptable para UI de lista + M3 — no hay umbral automático |

**Regla operativa:** Claude Code ejecuta, reporta las métricas y se detiene. No decide "aprobado" o "iterar" en CP-1 ni CP-2 por sí mismo — eso requiere la revisión explícita de Besto con el dato real en mano.

Otros umbrales sí quedan cerrados y automatizables:
- RF vs. KNN: diferencia >15% en MAE → documentar como hallazgo, no iterar.
- KMeans: Silhouette bajo → documentar como limitación, no bloquea (precedente ya sentado).
- Quality Scorer: % parseo JSON válido <90% → iterar el prompt antes de reportar.
