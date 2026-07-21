# Feature 6.2.7 — Notebook 5 (M3: NLP Orchestration) — Cierre

**Notebook:** `notebooks/05_m3_nlp_orchestration.ipynb`
**Fecha de cierre:** 2026-07-14
**Estado:** CERRADO
**Tipo:** Experimentación (no Entrenamiento — no aplica MAE ni Silhouette)

---

## 1. Qué construimos

Un flujo de orquestación conversacional que (a) extrae criterios estructurados de una consulta en
español vía LLM con un campo de confianza explícito, (b) aplica tres chequeos deterministicos
independientes del score de confianza para decidir si procede o pide clarificación, y (c) orquesta
M1 (Preference Matching) y M2 (Property Valuation) sobre los criterios extraídos vía un contrato
de función simulado (`v0`), devolviendo una respuesta conversacional honesta sobre las
limitaciones de cobertura ya documentadas del catálogo.

**Alcance:** valida el diseño de las Features 4.1 y 4.2 del WBS de Épica 4 (extracción de
intención, lógica de fallback, conjunto de validación). La Feature 4.3 (endpoints `POST
/search/nlp`, `/search/filtros`) es implementación de backend en producción — fuera de 6.2.7.

## 2. Modelo LLM — verificación repetida, no heredada

6.2.6 había terminado usando `gemini-3-flash-preview` porque `gemini-3.5-flash` mostró
degradación sostenida (100% de fallo en un lote diagnóstico de 25 llamadas). No heredamos esa
decisión sin comprobarla de nuevo: un sondeo rápido de 10 llamadas dio un resultado ambiguo
(50% de éxito), así que corrimos el mismo tamaño de lote diagnóstico que estableció el criterio en
6.2.6 (25 llamadas, timeout explícito 45s, backoff corto ~20s ante 503/504).

**Resultado: 25/25 = 100% de éxito**, con solo 2/25 (8%) requiriendo el reintento corto por un 503
puntual — saturación momentánea, no la degradación sostenida de 6.2.6. **Decisión final:
`gemini-3.5-flash`** (GA, identificador fijo) — recupera el argumento de reproducibilidad/citación
para el paper que el modelo "preview" de 6.2.6 no ofrecía. La disponibilidad de modelos Gemini es
una condición del momento de ejecución, no una garantía permanente; cualquier corrida futura debe
repetir esta misma verificación.

## 3. Contrato de función v0 — decisión de arquitectura

M3 no llama `pickle.load()` + funciones de M1/M2 en aislamiento. Se define un wrapper único y
reutilizable (`m1_buscar_matches`, `m2_enriquecer_semaforo`, `orquestar_m3`) con input/output fijo
que imita la interfaz que tendrá el backend real de Épica 4 — marcado explícitamente como
**`v0 — sujeto a revisión en Épica 4`**.

**Regla de cobertura estructural en M2 (KNN):** el artifact `knn_semaforo_precio_6_2_4.pkl` no
incluye columnas dummy para Pedregal ni Parque Lefevre (excluidas del entrenamiento por volumen,
Acta 1.2 §5.3) ni admite `tipo_inmueble` distinto de Apartamento (6.2.4 restringió el pool por
contaminación no residencial). El contrato detecta esto **antes** de llamar `.predict()` y
devuelve `cobertura_insuficiente=True` explícito, en vez de forzar una predicción fuera del
dominio de entrenamiento — mismo principio que la UI de "cobertura de datos insuficiente" ya usada
para Pedregal/Costa del Este en el Zone Health Index (CLAUDE.md, decisiones cerradas).

## 4. Mecanismo de confianza — tres chequeos, no uno

Verificamos antes de correr el conjunto de medición final que un solo score de confianza no
distingue "zona real pero fuera del scope" de "consulta genuinamente ambigua" — ambas pueden
extraer con confianza igual de alta porque sus entidades no-zona están igual de ancladas. Se
agregaron dos chequeos deterministicos adicionales, independientes del LLM:

1. `es_consulta_inmobiliaria == False` → fallback por fuera de tema.
2. Ubicación mencionada que no contiene ninguna de las 9 zonas válidas del scope, con `zona`
   resuelto a null → fallback por cobertura geográfica (mensaje distinto: "no cubrimos esa zona
   todavía", no "no entendí tu consulta").
3. `confianza < umbral` → fallback por ambigüedad (aplica solo si los 2 chequeos anteriores no
   dispararon).

**Bug corregido durante la implementación:** la primera versión del chequeo 2 disparaba cobertura
ante cualquier mención de ubicación no resuelta a una zona válida, sin distinguir "ubicación real
fuera del scope" de "dos zonas válidas mencionadas sin desempate" (este segundo caso es
ambigüedad, no cobertura). Corregido verificando si el texto mencionado contiene el nombre de
alguna zona válida antes de clasificar como cobertura.

## 5. Calibración del umbral de confianza (WBS 4.1.1, 4.1.3)

Conjunto de calibración: 5 consultas claras + 5 ambiguas + 1 caso límite de control adicional
(fuera del mínimo del WBS), corridas contra `gemini-3.5-flash`.

| Grupo | Confianza promedio |
|---|---|
| Claras | 0.950 |
| Ambiguas | 0.280 |
| Límite (entidades duras + calificativo sin ancla) | 0.800 |

El caso límite se comportó como claro, no como ambiguo — el modelo no penaliza un calificativo
subjetivo cuando coexiste con suficientes entidades ancladas. Salto limpio de 0.45 entre el techo
del grupo ambiguo (0.35) y el caso límite (0.80), sin puntos intermedios observados.

**Umbral fijado: 0.65.** Razón: sesgo conservador — el costo de proceder con confianza
insuficiente (resultados equivocados, silenciosos para el usuario) es mayor que el costo de pedir
clarificación de más. Mantiene colchón bajo el caso límite (0.80) sin acercarse al techo ambiguo
(0.35).

**Calibración explícitamente provisional, no optimizada:** 11 puntos con un salto limpio sin casos
intermedios reales no prueban que 0.65 sea el punto de corte óptimo, solo que cae en un rango
seguro dados los datos de este ejercicio.

## 6. Medición final (WBS 4.2.2, 4.2.3)

Conjunto de 20 consultas — 10 válidas + 5 fuera de alcance + 5 ambiguas, distinto del conjunto de
calibración — con desglose por causa, no agregado en un solo número:

| Categoría | n | % |
|---|---|---|
| Éxito | 10/20 | 50% |
| Fallback por cobertura geográfica | 4/20 | 20% |
| Fallback por fuera de tema | 1/20 | 5% |
| Fallback por ambigüedad | 5/20 | 25% |
| **Fallback total (agregado, formato WBS 4.2.3)** | **10/20** | **50%** |

Cada uno de los 20 casos cayó exactamente donde el diseño predecía. Ninguna consulta cayó en la
banda de vigilancia 0.55–0.75 cercana al umbral — no hay evidencia nueva de un punto de quiebre
genuino distinto al observado en la calibración.

**Advertencia explícita, mismo formato que la advertencia de validación circular de 6.2.3:** el
conjunto de 20 fue diseñado deliberadamente con casos extremos por categoría, no es una muestra de
consultas reales de usuarios. El 50% de fallback y el 100% de clasificación correcta demuestran que
los tres mecanismos funcionan como se diseñaron — no son una predicción de la tasa de fallback en
producción con tráfico real.

## 7. Verificación end-to-end del contrato — las 4 combinaciones, con evidencia real

La medición de la sección 6 valida extracción + clasificación, no la orquestación con M1/M2. El
contrato `orquestar_m3` distingue 4 combinaciones en su respuesta final (candidatos de M1
presentes/ausentes × cobertura de M2 disponible/no disponible). Las 4 quedaron verificadas con
evidencia real del pipeline completo (extracción LLM → contrato v0 → respuesta), no con filtros
construidos a mano:

| Combinación | Caso | Texto de la respuesta final |
|---|---|---|
| Con candidatos × con cobertura | V1 (El Cangrejo) | "Encontramos 2 propiedades que coinciden con tu busqueda, con semaforo de precio incluido." |
| Con candidatos × SIN cobertura | V6 (Parque Lefevre) | "Encontramos 14 propiedades que coinciden con tu busqueda en Parque Lefevre. No podemos mostrar el semaforo de precio para esta zona/tipo porque el modelo de valoracion no tiene suficientes datos de entrenamiento ahi (...) - te mostramos los resultados de coincidencia sin ese dato." |
| SIN candidatos × SIN cobertura | V7 (Pedregal) | "No encontramos propiedades que coincidan con esos criterios en Pedregal (0 candidatos). Nota adicional: aunque hubiera candidatos, tampoco podriamos mostrar el semaforo de precio para esta zona/tipo (...)." |
| SIN candidatos × con cobertura | Caso de control (Costa del Este, <\$50,000) | "No encontramos propiedades que coincidan con esos criterios en Costa del Este (0 candidatos). Prueba ajustando el rango de precio o el numero de habitaciones." |

**Hallazgo real #1:** el primer borrador del ensamblado de respuesta solo distinguía "con/sin
cobertura de M2", sin rama separada para "M1 sin candidatos". Para V7 esto producía un mensaje
engañoso ("te mostramos los resultados... sin ese dato" cuando no había ningún resultado).
Corregido separando las 4 combinaciones explícitas antes de dar V7 por confirmado.

**Hallazgo real #2 — corrección metodológica sobre la propia verificación:** ninguna de las 10
consultas "válidas" del conjunto de medición ejercitaba naturalmente la combinación "sin
candidatos × con cobertura" (las que dan 0 candidatos, V4 y V7, lo hacen en zonas/tipos que
tampoco tienen cobertura de M2). Un primer intento de cubrir esta rama construyó un filtro a mano
(`habitaciones_min=10` en San Francisco) para forzar el resultado — un atajo que probaba el
código, no el sistema completo. **Ese caso fue descartado explícitamente**, no reportado como
verificación válida, y reemplazado por una consulta plausible ("Apartamento en Costa del Este por
menos de \$50,000") verificada primero contra el catálogo real (0 candidatos confirmados, con un
hallazgo adicional en el camino: 4 filas de Costa del Este tienen `price_usd=1` como placeholder
de `precio_bajo_umbral`, no un precio real, que habrían colado la verificación si no se excluían
con el mismo filtro `precio_no_evaluable` que usa `m1_buscar_matches`) y corrida por el pipeline
completo — extracción LLM real, no criterios reescritos a mano.

## 8. Limitación conocida, dirección de trabajo futura (no implementada en 6.2.7)

El punto de quiebre real del umbral de confianza permanece sin observar directamente — ni la
calibración de 11 ni la medición de 20 (ambas diseñadas con casos extremos por categoría)
produjeron un caso con confianza intermedia genuina. Ajustar el umbral con más certeza requeriría
un conjunto de consultas reales de usuarios, no diseñado por el equipo — tarea de Épica 4.

## 8bis. Hallazgo post-cierre (2026-07-15, previo a 4.3.1) — manejo de excepciones incompleto en `extraer()`

**Feature 6.2 ya estaba cerrada cuando se encontró esto.** Se documenta aquí, no como reapertura
de 6.2.7, porque afecta directamente al artifact (el contrato v0) que la Feature 4.3 del WBS de
Épica 4 va a heredar tal cual para el endpoint `POST /search/nlp`.

Durante una medición de latencia de 27 llamadas reales contra `extraer()` (mismo contrato,
`gemini-3.5-flash`, corrida antes de comprometer el objetivo de 5s de SRS-024 en 4.3.3), una de las
llamadas produjo `httpx.ReadTimeout` al agotar el timeout explícito de 45s del cliente
(`http_options=types.HttpOptions(timeout=45_000)`). El bloque original de `extraer()` (y el del
lote diagnóstico de la sección 2) solo capturaba `except ServerError` — el error de transporte de
`httpx` **no es subclase de `ServerError`** (ese cubre únicamente 5xx devueltos por la API), así
que el `ReadTimeout` se propagó sin pasar por el mismo backoff/reintento que ya existía para un
503, tumbando el script.

**Corrección aplicada en el notebook (`notebooks/05_m3_nlp_orchestration.ipynb`, celdas 4 y 10 —
la celda de `extraer()` era la 9 al momento de este hallazgo; se corrió a la 10 tras la inserción
de la celda de §8ter):**
el `except` ahora captura `(ServerError, httpx.TransportError)`. `httpx.TransportError` es la clase
base que cubre `ReadTimeout`, `ConnectError`, `ConnectTimeout`, `PoolTimeout`,
`RemoteProtocolError` y el resto de excepciones de transporte de la librería — verificado contra
la jerarquía real de excepciones de `httpx` (`issubclass()`), no asumido por el nombre. No se
capturó `Exception` genérico a propósito: errores de parseo/validación del propio schema de
Pydantic deben seguir propagando sin reintento, porque un reintento no los resuelve.

**Implicación directa para 4.3.1:** el endpoint de orquestación debe heredar este mismo manejo de
excepciones (o uno equivalente) antes de ponerse en producción — sin esto, cualquier timeout de red
real (no solo un 503 de la API) tumbaría la request sin caer en el flujo de fallback ya diseñado en
6.2.7, en vez de responder con un mensaje controlado.

## 8ter. Hallazgo post-cierre (2026-07-15, adoptado) — modelo y prompt del contrato v0 reemplazados por `gemini-3.1-flash-lite`

**Esto reemplaza la decisión de modelo LLM de la sección 2, no reabre 6.2.7.** El contrato v0 de
`extraer()` en `notebooks/05_m3_nlp_orchestration.ipynb` ahora usa `gemini-3.1-flash-lite` en vez
de `gemini-3.5-flash`, con el `SYSTEM_PROMPT` corregido — ambos cambios ya aplicados directamente
en el notebook.

**Motivo — latencia.** La medición de 27 llamadas del hallazgo de §8bis mostró que
`gemini-3.5-flash` no cumple el objetivo de ≤5s de SRS-024 (WBS 4.3.3) ni en el camino sin
reintento: mediana 11.3s / p90 14.2s / max 25.5s sobre 21 llamadas de intento único; con el
backoff de 503 de por medio, hasta 71.6s. Antes de comprometerse a relajar el objetivo o rediseñar
el backoff, se verificó — mismo criterio ya aplicado en 6.2.6/6.2.7 (`client.models.list()` no es
fuente confiable, solo una llamada de prueba real lo confirma) — si existía una variante más
ligera en la familia 3.x: `gemini-3.1-flash-lite` (identificador GA, no `-preview`), 12/12 éxito
en diagnóstico, ~0.5s por llamada.

**Comparación pareada, mismas 13 consultas, extracción completa con `response_schema`:**

| | mediana | p90 | max | reintentos 503 (de 13) |
|---|---|---|---|---|
| `gemini-3.5-flash` | 12.3s | 32.6s | 71.6s | 3/13 |
| `gemini-3.1-flash-lite` | **1.3s** | 1.5s | 1.7s | **0/13** |

Mediana ~9x más rápida, sin contención de capacidad observada.

**Motivo — dos correcciones de prompt necesarias.** El modelo más ligero no reproducía el
comportamiento cualitativo del `SYSTEM_PROMPT` original en 2 de 4 verificaciones dirigidas,
corridas contra las 31 consultas completas de calibración (11) + medición (20) de este mismo
notebook:

1. **F3** ("terreno agrícola en Chiriquí para sembrar") caía en `es_consulta_inmobiliaria=False`
   — el modelo lite trataba "no es vivienda residencial" como "fuera de tema". Corregido
   aclarando explícitamente que Terreno (agrícola, para construir, cualquier uso) es un
   `tipo_inmueble` tan válido como Apartamento o Casa, y que una consulta sobre un terreno SIEMPRE
   es `es_consulta_inmobiliaria=True`.
2. **AM2** ("...en una zona tranquila") poblaba `zona_mencion_texto="zona tranquila"` — un
   calificativo cualitativo sin nombre de lugar concreto. Corregido distinguiendo explícitamente
   nombre de lugar concreto (ciudad, corregimiento, barrio, punto de referencia geográfico — sí
   puebla `zona_mencion_texto`) de calificativo cualitativo sobre ubicación ("zona tranquila",
   "cerca del trabajo", "buena zona" — NO lo puebla, queda `null`, se refleja como ambigüedad en
   `confianza`).

**Con el prompt corregido, 31/31 consultas exitosas (mediana ~1.4s) reproducen el mismo
comportamiento cualitativo que `gemini-3.5-flash` en las 4 verificaciones:**

1. Caso límite (`L1_LIMITE`): confianza 0.80 — idéntica al valor de referencia original.
2. Cobertura geográfica (`F1`, `F2`, `F3`, `F5`): las 4 → `fallback_cobertura` correcto, F3 ya
   corregida.
3. `F4` (fuera de tema con zona válida mencionada): `es_consulta_inmobiliaria=False` — correcto.
4. Ambiguas (`AM1`-`AM5`): las 5 con confianza <0.65 y las 5 → `fallback_ambiguedad`, AM2 ya
   corregida.

**Desglose final de las 20 de medición — idéntico al original:** 10 éxito / 4 cobertura / 1 fuera
de tema / 5 ambigüedad (50%/20%/5%/25%), mismas proporciones que la Fase 2 de este notebook con
`gemini-3.5-flash`.

**Alcance de este cambio — explícitamente NO afecta a:**
- **6.2.3 (M1, Preference Matching):** usa embeddings semánticos, no tiene prompt de extracción de
  intención — sin relación.
- **6.2.6 (M2, Quality Scorer):** prompt y modelo propios, **sigue usando `gemini-3.5-flash`** —
  decisión independiente, no heredada ni afectada por este cambio. `gemini-3.1-flash-lite` es
  específico al mecanismo de extracción de intención de M3, no una migración general de modelo del
  proyecto (ver CLAUDE.md — ambos modelos quedan diferenciados explícitamente).

**Resultado para 4.3.3/4.3.1:** el riesgo de latencia queda mitigado antes de construir el
endpoint de orquestación, resolviendo la causa raíz (latencia base del modelo) en vez de ajustar
el backoff o relajar el objetivo de SRS-024.

## 9. Artifacts

`pipeline/models/model_availability_check_6_2_7_batch25.pkl`,
`pipeline/models/calibracion_umbral_6_2_7_checkpoint.pkl`,
`pipeline/models/medicion_final_6_2_7_checkpoint.pkl`,
`pipeline/models/caso_control_sin_candidatos_con_cobertura_6_2_7.pkl`.

## 10. Cierre de Feature 6.2

Con 6.2.7 cerrado, **Feature 6.2 (23 SP) queda completa** — los 7 notebooks (EDA del catálogo,
Zone Health, M1 Preference Matching, M2 KNN/RF, M2 KMeans, M2 Quality Scorer, M3 Orchestration)
están documentados con evidencia de proceso, listos como fuente de verdad de los modelos que el
backend de Épica 4 consumirá.
