# WBS — Épica 4.0: Módulo 3 — NLP Orchestration Layer

Story Points totales: 22 | 4 ingenieros — 23 días disponibles

## Feature 4.1 — Integración Gemini para extracción de intención (7 SP)

| ID | Tarea | SP | Condición de Done | Depende de |
|---|---|---|---|---|
| 4.1.1 | Diseñar system prompt para extracción de entidades (precio, zona, tipo, habitaciones, características cualitativas) y definir schema JSON de respuesta con campo de confianza | 3 | Prompt probado contra 10 consultas de ejemplo (5 claras, 5 ambiguas); JSON parseado correctamente en los 10 casos | 1.1.6 |
| 4.1.2 | Implementar llamada a Gemini API, parseo del JSON de respuesta y manejo de error (retry + fallback) | 2 | Función maneja respuesta malformada sin crash; 3 reintentos antes de declarar fallo; loggea correctamente | 4.1.1 |
| 4.1.3 | Definir y documentar el umbral de confianza: qué valor del campo de confianza activa el fallback | 2 | Umbral documentado en decision log; probado contra el conjunto representativo de consultas antes de fijarlo | 4.1.2 |

## Feature 4.2 — Lógica de fallback y conjunto de validación (5 SP)

| ID | Tarea | SP | Condición de Done | Depende de |
|---|---|---|---|---|
| 4.2.1 | Implementar rama de fallback: cuando confianza < umbral, generar pregunta de clarificación; no llamar M1/M2 | 2 | Ninguna consulta fuera del alcance devuelve resultados genéricos; siempre devuelve una pregunta de clarificación | 4.1.3 |
| 4.2.2 | Construir conjunto representativo de consultas de prueba: mínimo 10 válidas + 5 fuera de alcance + 5 ambiguas | 2 | Conjunto documentado con el resultado esperado para cada consulta; usado tanto en validación de M3 como en el ensayo de demo | 4.2.1 |
| 4.2.3 | Calcular tasa de éxito y tasa de fallback sobre el conjunto representativo; documentar | 1 | Tabla de resultados generada: % consultas correctamente resueltas, % derivadas a fallback, % fallidas | 4.2.2 |

## Feature 4.3 — Endpoint de orquestación (10 SP) — Épica 4, producción, NO alcance de 6.2.7

| ID | Tarea | SP | Condición de Done | Depende de |
|---|---|---|---|---|
| 4.3.1 | Implementar endpoint POST /search/nlp que orquesta el pipeline completo: NLP → M1 → M2 → ensamblado | 5 | Endpoint funcional para el conjunto representativo de consultas; responde con resultados ensamblados de M1 y M2 | 4.1.2, 2.2.5, 3.1.5, 4.2.1 |
| 4.3.2 | Implementar endpoint POST /search/filtros (búsqueda estructurada sin NLP) | 3 | Filtros de precio, tipo y habitaciones funcionan correctamente; resultados consistentes con los parámetros enviados | 1.1.3, 1.5.1 |
| 4.3.3 | Medir y documentar tiempo de respuesta end-to-end del endpoint NLP (objetivo ≤5s, SRS-024) | 2 | Medición realizada con al menos 10 consultas de prueba; promedio documentado; si supera 5s, se abre issue con causa identificada | 4.3.1 |

**Nota de alcance:** Feature 4.3 es implementación de backend (Épica 4, producción con FastAPI). Notebook 6.2.7 es la fase de experimentación que precede y valida el diseño de 4.1–4.2 antes de construir los endpoints reales — no implementa los endpoints en sí.