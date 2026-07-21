# Épica 4.0 — Módulo 3: NLP Orchestration Layer
## Documentación de cierre

**Fecha de ejecución:** 2026-07-15 (Feature 4.3) — Features 4.1/4.2 cerradas en sesión previa (2026-07-14, Feature 6.2.7)
**Estado:** CERRADA — 22/22 SP completados (10 SP pendientes de backend ejecutados en esta sesión)
**Precondición de entrada:** Épica 2.0 (`/match/score`) y Épica 3.0 (`evaluar_precio_propiedad()`) cerradas en la misma sesión. Extracción de intención NLP y lógica de fallback ya validadas en notebook (Feature 6.2.7).

---

## Resumen ejecutivo

Épica 4.0 es el módulo que cierra el círculo de REIP: orquesta M1 (Preference Matching) y M2 (Property Valuation) a partir de una consulta en lenguaje natural, sin escanear listings directamente. El diseño completo — extracción de intención, umbral de confianza, lógica de fallback de 3 causas — ya estaba validado en notebook desde el 2026-07-14 (Feature 6.2.7). El trabajo de hoy fue exclusivamente de producción: envolver ese contrato ya probado (`orquestar_m3()`, marcado explícitamente "v0 — sujeto a revisión") en endpoints FastAPI reales, contra Supabase y Gemini en vivo, no contra un DataFrame en memoria.

---

## Feature 4.1 — Extracción de intención (Notebook, cerrada 2026-07-14)

Sin trabajo en esta sesión. Resumen de referencia (`Feature_6_2_7_M3_Orchestration_Cierre.md`):

- Extracción de criterios estructurados desde consulta en español vía LLM, con campo de confianza explícito.
- **Modelo LLM verificado en cada corrida, no heredado sin comprobar**: `6.2.6` había usado `gemini-3-flash-preview` por degradación de `gemini-3.5-flash` (100% fallo en lote diagnóstico). `6.2.7` no heredó esa decisión — repitió el mismo protocolo de verificación (25 llamadas, timeout 45s) y obtuvo 25/25 con `gemini-3.5-flash` GA, decisión final de esa Acta.
- **Adenda posterior (§8ter, 2026-07-15, adoptada antes de esta sesión)**: reemplazo por `gemini-3.1-flash-lite` por latencia — mediana 1.3s vs. 11-12s de `gemini-3.5-flash`, con 3/13 reintentos de 503 en el modelo anterior vs. 0/13 en el nuevo. No reabre la Acta original de 6.2.7 (sección 2 queda intacta como registro histórico), la sustituye para efectos de producción. Verificada explícitamente hoy en `4.3.1` como fuente real y fechada, no como artefacto de la limpieza de `CLAUDE.md` de esta sesión.

## Feature 4.2 — Umbral de confianza y fallback (Notebook, cerrada 2026-07-14)

Sin trabajo en esta sesión. Resumen de referencia:

- **Umbral fijado en 0.65** — sesgo conservador deliberado: el costo de proceder con confianza insuficiente (resultados equivocados y silenciosos) es mayor que el costo de pedir clarificación de más. Calibración explícitamente provisional (11 puntos, salto limpio 0.35→0.80 sin casos intermedios reales) — no optimizada, cae en un rango seguro.
- **3 causas de fallback, deterministas e independientes del score de confianza**: ambigüedad, fuera de cobertura geográfica, fuera de tema.
- **Medición sobre 20 consultas** (10 válidas + 5 fuera de alcance + 5 ambiguas): 50% éxito, 50% fallback (20% cobertura, 5% fuera de tema, 25% ambigüedad) — advertencia explícita de que el conjunto fue diseñado con casos extremos por categoría, no representa tasa de fallback esperada en producción real.
- **4 combinaciones del contrato v0 verificadas con evidencia real**, no con filtros construidos a mano — incluyendo el caso más exigente (Pedregal: sin candidatos de M1 y sin cobertura de M2).
- **Meta-hallazgo transversal documentado en Feature 6.2**: un `httpx.ReadTimeout` real no cubierto por `except ServerError` se propagaba sin control — descubierto solo con tráfico prolongado, no en validaciones cortas. Sexta instancia del patrón "cerrado no significa verificado" que atraviesa todo el proyecto.

---

## Feature 4.3 — Endpoints de orquestación (10 SP) — CERRADA hoy

### 4.3.1 — `POST /search/nlp`

**Ubicación:** `backend/app/routers/search.py`

Orquesta el flujo completo: extracción de intención (Gemini) → 3 chequeos de fallback → si procede, `generar_embedding()` (2.1.2) → `buscar_propiedades_ann()` (llamada interna, no HTTP — decisión documentada abajo) → enriquecimiento con `evaluar_precio_propiedad()` (3.1.5) por candidato cuando aplica.

**Decisión de diseño — llamada interna, no HTTP a `/match/score`:** `/match/score` está diseñado para un perfil persistente con `zonas_preferidas` como lista; una consulta NLP puntual mapea 1:1 a los parámetros nativos de `buscar_propiedades_ann()` (zona singular, tipo, rangos). Ir por HTTP habría reintroducido el overhead de reconexión que el pool de `2.2.5` ya resolvió.

**Response model distingue 3 estados:** resultados, fallback (con motivo explícito), y error real de infraestructura (500) — nunca mezclados.

**Cada candidato trae `semaforo` + `motivo_sin_semaforo`:** nunca ambos vacíos — si no hay semáforo (zona/tipo fuera de cobertura KNN), siempre hay explicación textual, nunca un vacío silencioso.

**Verificado en producción real (5 consultas iniciales):**

| Consulta | Resultado | Tiempo |
|---|---|---|
| Apartamento 2 hab. Costa del Este, mín 2 baños | 5 candidatos, todos con semáforo | 3.71s |
| "Algo económico, no sé bien dónde" | Fallback: ambigüedad (confianza 0.20) | 1.46s |
| Apartamento en Pedregal, 3 hab | 0 candidatos + sin cobertura M2, mensaje combinado | 2.01s |
| "¿Mejor taller mecánico cerca de Bella Vista?" | Fallback: fuera de tema | 1.20s |
| Apartamento Bella Vista $300-600k, 2 hab | 5 candidatos, todos con semáforo | 2.09s |

**Caso Pedregal confirmado en producción real** (no solo en notebook): mensaje combinado honesto — cero candidatos en la zona, y aunque los hubiera, tampoco se podría mostrar semáforo (zona fuera del pool de entrenamiento KNN, Acta 1.2 §5.3).

### 4.3.2 — `POST /search/filtros`

**Ubicación:** `backend/app/routers/search.py` (mismo router, namespace `/search/*` compartido con NLP; servicio real, `busqueda_estructurada.py`, completamente separado — sin Gemini, sin embeddings, verificado por grep con 0 coincidencias).

Búsqueda SQL pura para la barra de filtros del frontend (Feature 5.2.2), sin ranking semántico.

**Validación:** zona inválida → `422` con lista de las 9 zonas reales, mismo estándar que `2.2.2`.

**Orden:** `price_usd asc, listing_id asc` — el desempate por `listing_id` no es cosmético: se confirmó en pruebas reales que existen precios duplicados en el catálogo (dos listados a $174,710), y sin segundo criterio la paginación `LIMIT`/`OFFSET` podía duplicar o saltar filas entre páginas de forma silenciosa.

**Paginación:** `LIMIT`/`OFFSET` simple, con `total` desde `count(*)` separado bajo el mismo `WHERE` — justificado por volumen (1,177 filas totales, el costo de `OFFSET` en páginas altas es irrelevante a esta escala).

### 4.3.3 — Medición formal de latencia end-to-end

**Riesgo mitigado antes de construir, no después:** el cambio de modelo a `gemini-3.1-flash-lite` (§8ter) resolvió la causa raíz de latencia (velocidad base del modelo), no un ajuste de backoff ni una relajación del objetivo SRS-024.

**Muestra de 12 consultas reales**, deliberadamente variada por ruta de código (no repetición de las 5 de `4.3.1`): 8 casos de resultados (cobertura M2 completa, parcial y cero) + 4 de fallback (2 ambigüedad, 1 fuera de tema, 1 cobertura), incluyendo el caso Pedregal y un caso análogo nuevo (Parque Lefevre + Terreno).

| Métrica | Valor |
|---|---|
| Promedio | 1.94s |
| Mediana | 1.90s |
| p90 | 2.78s |
| Máximo | 2.87s |
| Mínimo | 1.16s |

**Objetivo SRS-024 (≤5s): cumplido de forma consistente**, con ~2.1s de margen incluso en el peor caso. Cero reintentos de 503 observados en esta corrida.

---

## Decisiones técnicas cerradas — no reabrir sin nueva evidencia

1. **Modelo de extracción NLP: `gemini-3.1-flash-lite`** (§8ter de `Feature_6_2_7_M3_Orchestration_Cierre.md`), no `gemini-3.5-flash`. No afecta a Quality Scorer (`6.2.6`), que permanece en `gemini-3.5-flash`.
2. **Umbral de confianza: 0.65**, calibración provisional documentada como tal.
3. **`/search/nlp` llama a `buscar_propiedades_ann()` internamente**, no vía HTTP a `/match/score` — evita reintroducir overhead de reconexión.
4. **`/search/filtros` no toca Gemini ni embeddings bajo ninguna circunstancia.**
5. **Cada candidato de `/search/nlp` siempre trae explicación de ausencia de semáforo** cuando no lo tiene — nunca un campo vacío sin motivo.

---

## Pendientes de gobernanza / documentación (no bloquean código)

1. **Muestra de latencia de `4.3.3` (n=12) es mayor que el mínimo del WBS (n=10)**, pero sigue siendo pequeña frente a tráfico real de producción — igual advertencia que ya aplica a la medición de 20 consultas de `4.2.3` (Feature 6.2.7): no representa la distribución de latencia bajo carga sostenida.
2. **Registrar en `REIP_WBS.md`/Excel el cierre formal de Feature 4.3**, con fecha 2026-07-15.
3. **§8ter de `Feature_6_2_7_M3_Orchestration_Cierre.md`** debe quedar referenciado directamente (no vía `CLAUDE.md`) en cualquier documentación futura sobre la elección de modelo — la cita genérica generó una confusión evitable durante esta sesión.

---

## Estado de infraestructura al cierre de Épica 4.0

| Componente | Estado |
|---|---|
| `POST /search/nlp` | Producción, verificado con Gemini + Supabase reales |
| `POST /search/filtros` | Producción, sin dependencia de Gemini |
| Extracción de intención | `gemini-3.1-flash-lite`, umbral 0.65 |
| Lógica de fallback | 3 causas separadas, verificadas con ejemplos reales |
| Latencia end-to-end | Mediana 1.90s, máximo 2.87s — objetivo ≤5s con margen amplio |

**Épica 4.0 completa. Los tres módulos de REIP (M1 → M2 → M3) están funcionales de extremo a extremo sobre infraestructura real.**
