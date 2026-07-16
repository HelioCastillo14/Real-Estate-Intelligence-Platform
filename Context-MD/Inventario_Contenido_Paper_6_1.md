# Inventario de contenido para el paper académico (Feature 6.1) — y estado del WBS de 6.1

**Fecha:** 2026-07-15
**Alcance:** solo inventario y verificación de vigencia del WBS de Feature 6.1. No redacta ninguna
sección del paper. Fuente de la hoja del WBS: `Context-MD/REIP_WBS.xlsx`, hoja
`6.0 Doc. Académica y Técnica`, bloque `Feature 6.1 — Paper académico (IEEE, máx. 12 páginas)`.

**Nota metodológica sobre las fuentes pedidas — léase antes de lo demás:** se pidió revisar
`Feature_6.2_Documentacion_Completa_v2.md` (sección 8, meta-hallazgo "cerrado no significa
verificado"; sección 7.2, cambio de modelo de M3 con dos rondas de validación). **Ese archivo no
existe en el repo.** El único documento con nombre similar es
`Context-MD/Feature_6.2_Contexto_Ejecucion_v2.md` (abierto en el IDE al momento de esta tarea), que
tiene una estructura distinta (§7 son decisiones de arquitectura, §8 son checkpoints de revisión
humana CP-1/CP-2 — no hay meta-hallazgo de verificación ni comparación M3 de dos rondas en ese
documento). El contenido que el encargo describía (verificación repetida de disponibilidad de
modelo, sin heredar decisiones) sí existe, pero vive en otro lugar:
`Context-MD/Feature_6_2_7_M3_Orchestration_Cierre.md` §2 y §8ter. Esto se reporta como
discrepancia/gap explícito más abajo — no se asumió ni se inventó el contenido de la sección 8
faltante.

---

## Por cada subtarea de 6.1

### 6.1.1 — Introducción y planteamiento del problema (2 SP)

**Condición de Done (texto exacto del WBS):** *"Sección redactada; problemática argumentada con al
menos 1 referencia local y 1 internacional, por requisito del documento del curso"*

**¿Vigente?** Sí, sin ajuste — es una condición de redacción/citación bibliográfica, no depende de
ningún hallazgo técnico posterior de Feature 6.2.

**Contenido real disponible:** ninguno específico a esta subtarea — el "problema" (asimetría de
información inmobiliaria en Panamá) se puede fundamentar con:
- `CLAUDE.md` §"Stack"/"Zonas del scope" — contexto del proyecto y su alcance real (9 zonas, 5
  corregimientos administrativos reales).
- `Context-MD/Feature_1_2...Acta.md` — volumen real del catálogo (1,361 registros, ~34% de lo
  proyectado), que en sí mismo es evidencia de la escasez/fragmentación de datos inmobiliarios
  abiertos en Panamá, un argumento a favor de la asimetría de información.

**Vacíos reales:** las referencias bibliográficas local/internacional en sí (ninguna investigación
de citas está hecha en el repo — hay que buscarlas, no existen todavía).

---

### 6.1.2 — Trabajos relacionados con discusión comparativa (3 SP)

**Condición de Done (texto exacto del WBS):** *"Sección discute resultados/enfoques de trabajos
relacionados, no solo los describe; cumple el requisito explícito del documento del curso de
'discutir resultados de acuerdo a trabajos relacionados'"*

**¿Vigente?** Sí, sin ajuste en el texto de la condición — pero el vacío de contenido es total (ver
abajo).

**Contenido real disponible:** ninguno.

**Vacíos reales — confirmado por búsqueda directa en el repo:**
`grep -ril "properati|goplaceit|homie"` sobre todo el repo (`.md`, `.py`, `.ipynb`) → **cero
resultados.** No existe ninguna investigación, nota, ni borrador sobre plataformas LATAM
(Properati, Goplaceit, HOMIE) ni sobre estado del arte de retrieval semántico en ningún archivo del
proyecto. Esta subtarea parte de cero — no hay ni siquiera un punto de partida documentado.

---

### 6.1.3 — Metodología: arquitectura M1/M2/M3, pipeline de datos, técnica aplicada (2 SP)

**Condición de Done (texto exacto del WBS):** *"Sección resume la arquitectura sin reproducir el
SAD completo; nivel de detalle apropiado para 12 páginas"*

**¿Vigente?** Sí, sin ajuste.

**Contenido real disponible (abundante):**
- `CLAUDE.md` §"Módulos" — definición aprobada de M1/M2/M3 (nombres técnicos, no deprecados).
- `CLAUDE.md` §"Feature 6.2" completo — resumen operativo de los 7 notebooks, con decisiones de
  modelo, umbrales y artifacts.
- `Context-MD/Feature_6.2_Contexto_Ejecucion_v2.md` §1-§2 — descripción de arquitectura de los 7
  notebooks y restricciones (notebook como fuente de verdad del modelo entrenado, backend no
  reentrena, EDA no se duplica).
- Cada cierre de notebook (`Feature_6_2_X_*_Cierre.md`) §1 ("Qué construimos") — resumen técnico
  por módulo, listo para condensar.
- Nota operativa: `Ajuste_WBS_1_5_1_Esquema_Propiedades.md` §2.4 documenta la arquitectura de
  `imagenes` (hotlink de URLs, no descarga) — dato de pipeline reciente, mencionable como detalle
  de arquitectura de datos si el paper cubre el schema, pero es menor, no central a M1/M2/M3.

**Vacíos reales:** ninguno de contenido — es trabajo de condensación/redacción, no de investigación
nueva.

---

### 6.1.4 — Resultados integrando figuras/tablas seleccionadas de los notebooks (3 SP)

**Condición de Done (texto exacto del WBS):** *"Cada figura/tabla citada existe en un notebook
cerrado de Feature 6.2; ninguna cifra se redacta sin trazabilidad al notebook fuente"*

**¿Vigente?** Vigente en su exigencia de trazabilidad — pero el WBS enumera métricas
("Precision@k, MAE, Silhouette, tasa de éxito M3") sin mencionar el Quality Scorer (6.2.6/M2) ni
distinguir que dos de los 7 notebooks (6.2.6, 6.2.7) son de tipo Experimentación y no producen
MAE/Silhouette por diseño (confirmado en cada cierre: *"Tipo: Experimentación (no Entrenamiento —
no aplica MAE ni Silhouette)"*). No es un error del WBS, pero conviene que quien redacte sepa que
"cada notebook aporta una métrica distinta", no que todos comparten el mismo formato de resultado.

**Contenido real disponible:** ver la tabla consolidada de figuras/tablas y la de métricas más
abajo — cubre los 7 notebooks con trazabilidad exacta a celda/sección.

**Vacíos reales:** ninguno — hay más contenido del que cabe en 12 páginas; el trabajo real de esta
subtarea es *selección*, no generación.

---

### 6.1.5 — Discusión: hipótesis vs. resultados empíricos (2 SP)

**Condición de Done (texto exacto del WBS):** *"Sección responde explícitamente si la hipótesis se
confirmó, se rechazó, o los datos son insuficientes para concluir"*

**¿Vigente?** Sí, sin ajuste — pero depende de que exista una "hipótesis" formal en algún documento
previo del proyecto (SRS, Acta de planteamiento). No se encontró un documento de hipótesis
formalmente enunciada dentro de `Context-MD/` en esta revisión — sería necesario ubicarlo (fuera
del alcance de esta revisión, que se limitó a las fuentes listadas por el usuario) o formularla
como parte de 6.1.1/6.1.5.

**Contenido real disponible para responder "qué pasó" (aunque no la hipótesis formal en sí):**
- M1: lift semántico heterogéneo, no una mejora uniforme (`Feature_6_2_3...Cierre.md` §4) —
  resultado mixto, ni confirma ni rechaza limpiamente un beneficio uniforme del componente
  semántico.
- M2 KNN vs. RF: RF gana 20.4% en MAE pero se descarta como producto por explicabilidad
  (`Feature_6_2_4...Cierre.md` §3) — un caso claro de "la métrica más baja no ganó" por una razón
  de producto, buen material para la sección de discusión.
- M3: tasa de fallback de 50% en un conjunto diseñado con casos extremos, explícitamente no
  representativo de tráfico real (`Feature_6_2_7...Cierre.md` §6) — dato que exige matizar
  cualquier afirmación de "funciona/no funciona" en producción.

---

### 6.1.6 — Limitaciones consolidadas (2 SP)

**Condición de Done (texto exacto del WBS):** *"Cumple el requisito explícito del documento del
curso de 'presentar las limitaciones de su estudio'; consolidada en una sola sección, no dispersa"*
— el WBS enumera explícitamente 5 limitaciones esperadas: *"validación circular de M1, exclusión
KNN/KMeans en Pedregal/Lefevre, anomalías de auditoría en Zone Health, cobertura GTFS 2016, n=20 en
encuesta"*.

**¿Vigente?** **Necesita ajuste — la lista de 5 limitaciones nombradas en el WBS está incompleta
frente a lo que Feature 6.2 realmente generó.** Las 5 nombradas sí existen y son reales (ver abajo),
pero Feature 6.2 (cerrada después de escribirse el WBS original) documentó limitaciones adicionales
igual de citables que el WBS no menciona: el patrón repetido de verificación de modelo LLM (no es
una limitación única, es un patrón metodológico recurrente citable como tal), el hallazgo bimodal de
`transparencia_precio`, la mezcla de 2 modelos LLM dentro de una misma muestra (dos veces: 6.2.6 y
el batch de producción), y la limitación de reproducibilidad del modelo "preview" usado
temporalmente en 6.2.6. Ver la lista completa con citas exactas en la sección dedicada más abajo.
**No se resuelve aquí — se reporta para decisión del usuario en la sección de discrepancias.**

**Contenido real disponible:** ver sección "Limitaciones ya documentadas" más abajo — cada una con
cita exacta.

**Vacíos reales:** "cobertura GTFS 2016" y "n=20 en encuesta" — mencionadas en el WBS pero **no
verificadas en esta revisión** porque no forman parte de los 7 notebooks ni de los cierres de
Feature 6.2 (pertenecen a Feature 1.3/1.4, fuera del alcance de fuentes que se pidió revisar en este
encargo). No asumir que están documentadas solo porque aparecen en el WBS — se necesitaría revisar
`Context-MD/ETL_Feature_1_3_1_4_Proceso_Completo.md` y el material de encuesta (si existe) antes de
redactar esta parte.

---

### 6.1.7 — Conclusiones y trabajo futuro (1 SP)

**Condición de Done (texto exacto del WBS):** *"Conclusiones claras (requisito explícito del
documento del curso); conectadas a los OE-01 a OE-05"*

**¿Vigente?** Sí, en su forma — pero **no se localizó ningún documento en `Context-MD/` que enuncie
los objetivos específicos OE-01 a OE-05** dentro del alcance revisado en este encargo. Esto es un
vacío de trazabilidad: la condición de done cita un artefacto (OE-01..OE-05) cuya fuente no se
verificó en esta pasada — mismo principio que `CLAUDE.md` exige para cualquier cita de Feature/Acta
("no copiar sin verificar"). Antes de redactar 6.1.7, ubicar el documento fuente de los OE.

**Contenido real disponible:** "trabajo futuro" tiene material fuerte y ya explícito en varios
cierres — no son especulación nueva, son líneas de trabajo que el propio proyecto ya declaró
pendientes:
- Reemplazo de la keyword de exclusión `"renta corta"/"airbnb"` de M1 por una etiqueta estructurada
  vía LLM (`Feature_6_2_3...Cierre.md` §5).
- Reducción de dimensionalidad del embedding antes de usarlo en un modelo de precio de producción
  (`Feature_6_2_4...Cierre.md` §5).
- Calibración del umbral de confianza de M3 con consultas reales de usuario, no diseñadas por el
  equipo (`Feature_6_2_7...Cierre.md` §8).
- Nota de UI pendiente sobre cómo explicar `transparencia_precio` bajo sin que se lea como alerta de
  precio (`Escalamiento_QualityScorer_Produccion_Cierre.md` §3.2).

---

### 6.1.8 — Formato IEOM/IEEE + referencias en Mendeley/Zotero (2 SP)

**Condición de Done (texto exacto del WBS):** *"Documento cumple plantilla IEOM Society Panamá 2026;
todas las referencias gestionadas en Mendeley/Zotero, formato IEEE, con fecha de consulta en fuentes
web"*

**¿Vigente?** Sí, sin ajuste — es un requisito de formato/gestión bibliográfica, no depende de
ningún hallazgo técnico.

**Contenido real disponible:** ninguno aplicable (no hay plantilla ni biblioteca de referencias en
el repo).

**Vacíos reales:** la plantilla IEOM Society Panamá 2026 y la biblioteca de referencias en
Mendeley/Zotero no están en este repo — herramientas/artefactos externos, fuera del control de
código.

---

## Tabla resumen de figuras/tablas disponibles (los 7 notebooks, sin excepción)

| Notebook | Figura/tabla | Qué muestra | Métrica clave | Reutilizable directo (sí/no, por qué) |
|---|---|---|---|---|
| 00 (6.2.1) | Fig., celda 7 | Contaminación bruta de tipo de inmueble por zona | Pedregal 73%, Parque Lefevre 55%, Marbella 23% | Sí — figura de motivación del pipeline de limpieza |
| 00 (6.2.1) | Fig., celda 14 | Discrepancia de volumen real vs. proyectado por zona | Costa del Este -83.7%, Marbella -75%, San Francisco -48.1% | Sí — fuerte para el planteamiento del problema (6.1.1) y limitaciones |
| 00 (6.2.1) | Fig. (3 subplots), celda 33 | Distribución de precio/área/habitaciones del catálogo limpio | n=1,177 (1,163 con precio evaluable) | Sí — EDA general, útil en metodología o resultados |
| 00 (6.2.1) | Tabla, celda 26 | Conteo final por corregimiento tras dedup | 1,177 filas limpias (de 1,361), 184 duplicados cross-file eliminados | Sí — cifra operativa central del catálogo |
| 00b (6.2.2) | Fig. (2 subplots), celda 6 | Tasa de homicidios cruda y score de seguridad normalizado | San Francisco 3.26/100k → score 1.0; Parque Lefevre 21.01 → score 0.0 | Sí — con nota de n=5 |
| 00b (6.2.2) | Fig., celda 10 | Score de transporte normalizado (densidad GTFS+Metro) | Bella Vista 1.0, Pedregal 0.18 (más bajo) | Sí |
| 00b (6.2.2) | Fig. (2 subplots), celda 15 | Conteo crudo y score de amenidades | Betania score 1.0 (mayor amenidades ponderadas) | Sí |
| 00b (6.2.2) | Fig., celda 19 | Score de walkability normalizado | Bella Vista más alto, Pedregal más bajo | Sí |
| 00b (6.2.2) | Fig., celda 25 | Zone Health Composite Index — 9 zonas del scope | Betania 0.878, San Francisco 0.689, Bella Vista/heredadas 0.537, Parque Lefevre 0.376, Pedregal (calculado, oculto en UI) | Sí, con nota de exclusión de visualización de Pedregal y de Costa del Este sin score |
| 00b (6.2.2) | Tabla, celda 23 | Pesos finales del composite (4 dimensiones) | seguridad 0.353, transporte 0.235, amenidades 0.235, walkability 0.176 | Sí — **ver discrepancia con `CLAUDE.md` más abajo, no citar los pesos de `CLAUDE.md` sin corregir primero** |
| 01 (6.2.3) | Tabla, celda 26 | Precision@3/5/10 por perfil (scorer híbrido) | Ver tabla de métricas consolidadas abajo | Sí, con la advertencia de validación circular obligatoria (notebook §5, celda markdown) |
| 01 (6.2.3) | Tabla, celda 28 | Lift semántico por perfil (híbrido vs. solo-estructural) | 2 perfiles con ganancia clara, 1 con caída a 0, 3 mixtos | Sí — narrativa rica para discusión (6.1.5) |
| 01 (6.2.3) | Tabla, celda 38 | Sensitivity sweep de 5 combinaciones de peso | 0.8/0.2, 0.7/0.3, 0.6/0.4 dan resultado idéntico; 1.0/0.0 y 0.5/0.5 difieren | Sí — evidencia de que 0.6/0.4 no es un default sin verificar |
| 01 (6.2.3) | — | **No genera ninguna figura (0 imágenes PNG)** | — | El notebook es 100% tablas; si el paper quiere una figura de M1, hay que construirla nueva a partir de estas tablas |
| 02 (6.2.4) | Fig. (3 subplots), celda 10 | Distribución de precio/área/hab/baños del dataset filtrado (n=1,042) | — | Sí |
| 02 (6.2.4) | Fig., celda 20 | Feature importances de Random Forest | `area_m2` domina con 88.8% | Sí — evidencia visual fuerte para price drivers |
| 02 (6.2.4) | Tabla, celda 22 | MAE CV/test, KNN vs. RF, % del precio promedio | KNN 33.4%, RF 26.6% | Sí — tabla central de resultados de M2 |
| 02 (6.2.4) | Tabla, celda 33 | Distribución final del semáforo (umbral recalibrado ±1.5×MAE) | amarillo 82.3%, verde 9.1%, rojo 8.6% (n=209 test) | Sí, con la explicación explícita de que "amarillo" no es precio neutro |
| 03 (6.2.5) | Fig. (4 subplots), celda 6 | EDA de variables de segmentación | — | Sí |
| 03 (6.2.5) | Fig. (2 subplots), celda 11 | Método del codo + Silhouette vs. k (k=2 a 10) | k óptimo=2, Silhouette=0.388 | Sí — tabla de selección de k, buena para metodología |
| 03 (6.2.5) | Fig., celda 16 | Visualización de los 2 clusters finales | Cluster 0 (compacto/económico, n=662), Cluster 1 (grande/premium, n=380) | Sí |
| 03 (6.2.5) | Tabla, celda 18 | Distribución de clusters por corregimiento | Costa del Este 64% premium, San Francisco 45% premium | Sí — descriptiva, no insumo del modelo |
| 04 (6.2.6) | Fig. (4 subplots), celda 24 | Distribución de los 4 scores del Quality Scorer (n=150) | Ver tabla de métricas consolidadas | Sí |
| 04 (6.2.6) | Fig. (2 subplots), celda 25 | (segunda vista de distribución/correlación de scores) | correlación completitud↔diferenciadores 0.72 | Sí |
| 04 (6.2.6) | Tabla, celda 4 | Confirmación de disponibilidad de modelo LLM contra API real | `gemini-2.5-flash` 404, `gemini-3.5-flash` 503 (en ese momento) | Sí — buena evidencia metodológica de "no confiar en `client.models.list()`" |
| 04 (6.2.6) | Tabla, celda 27-28 | Comparación de medias por modelo (`gemini-3.5-flash` vs. `gemini-3-flash-preview`) | máx. diferencia 0.14/5 | Sí |
| 05 (6.2.7) | — | **No genera ninguna figura (0 imágenes PNG)** | — | El notebook es experimentación/tablas; cualquier figura para el paper (ej. barra de tasa de éxito/fallback) debe construirse nueva |
| 05 (6.2.7) | Tabla, celda 11 | Calibración del umbral: confianza promedio por grupo | Claras 0.950, Ambiguas 0.280, Límite 0.800 | Sí |
| 05 (6.2.7) | Tabla, celda 14 | Medición final: desglose de 20 consultas por categoría | éxito 50%, cobertura 20%, tema 5%, ambigüedad 25% | Sí, con la advertencia explícita de no-representatividad |
| 05 (6.2.7) | Tabla, celda 17 | Verificación end-to-end de las 4 combinaciones M1×M2 | 4 casos con texto de respuesta real citado | Sí — buen material cualitativo/de caso de uso |

**Nota sobre 6.2.1/6.2.2 y sus cierres formales:** no existe un `Feature_6_2_1_*_Cierre.md` ni
`Feature_6_2_2_*_Cierre.md` dedicado (a diferencia de 6.2.3-6.2.7). El contenido equivalente para
6.2.1 vive en `Context-MD/Acta_1.2_Adenda_Duplicados.md`; para 6.2.2, en
`Context-MD/Feature_1_4_Zone_Health_Composite_Index_Documentacion_Granular.md` — ambos ya citados
arriba. No asumir que falta documentación solo porque el nombre de archivo no sigue el patrón de
6.2.3-6.2.7.

---

## Métricas clave consolidadas

| Módulo | Métrica | Valor | Notebook fuente | Contexto necesario |
|---|---|---|---|---|
| M1 | Precision@3/5/10 (scorer híbrido 0.6/0.4) | Varía por perfil, 0.000 a 1.000 — **no hay un número único agregable sin distorsionar** | 01 (6.2.3), celda 26 | Ground truth sintético, no usuarios reales — advertencia de validación circular obligatoria en cualquier cita |
| M1 | Lift semántico promedio (híbrido vs. solo-estructural) | P@3: -0.000, P@5: -0.067, P@10: -0.083 | 01 (6.2.3), celda 31 | **El promedio es engañoso leído solo** — 2 perfiles ganan, 1 cae a 0, 3 mixtos. Citar siempre junto con el desglose por perfil |
| M2 (KNN, producción) | MAE test | \$187,543 (33.4% del precio promedio) | 02 (6.2.4), celda 26 | % del precio promedio es la lectura correcta, no el valor absoluto en USD — el precio promedio del dataset es \$561,495 |
| M2 (RF, comparación) | MAE test | \$149,270 (26.6% del precio promedio) | 02 (6.2.4), celda 26 | RF gana 20.4% en MAE pero **no es el modelo de producción** — KNN se eligió por explicabilidad, no por error. Citar RF solo como comparación metodológica, nunca como "el resultado de M2" sin aclarar esto |
| M2 (RF, feature importance) | `area_m2` | 88.8% de la importancia | 02 (6.2.4), celda 20 | Price driver dominante — consistente en ambos experimentos (con y sin embedding) |
| M2 (KMeans) | k óptimo / Silhouette | k=2, Silhouette=0.388 | 03 (6.2.5), celda 14 | Silhouette bajo mencionado explícitamente como limitación esperada, no oculta |
| M2 (Quality Scorer, experimento 6.2.6) | % JSON válido (prompt v2) | 100% (25/25 diagnóstico), 100% (150/150 muestra) | 04 (6.2.6), celdas 16, 22 | Umbral de aceptación era 90% — superado con margen |
| M2 (Quality Scorer, experimento 6.2.6) | Distribución de 4 dimensiones (n=150) | completitud 4.57, presentación 4.75, diferenciadores 4.61, transparencia_precio 3.47 (± 1.91) | 04 (6.2.6), tabla consolidación §9 | Muestra n=150 sobre N=1,168, margen de error ±7.5% — exploratorio, no decisión de producto |
| M2 (Quality Scorer, **batch de producción, fuera de Feature 6.2**) | Distribución de 4 dimensiones (n=1,168, catálogo completo) | completitud 4.66, presentación 4.73, diferenciadores 4.51, transparencia_precio 3.68 (± 1.81) | `Escalamiento_QualityScorer_Produccion_Cierre.md` §3 (no notebook — script de producción `pipeline/scripts/escalar_quality_scorer_6_2_6.py`) | **Esta es la cifra sobre el catálogo completo, más fuerte que la muestra de 150 para el paper** — pero no vive en un notebook, vive en el script de producción y su cierre; citar la fuente correcta |
| M2 (Quality Scorer, producción) | `transparencia_precio` bimodal | score=1: 27.0% (n=315), score=5: 64.1% (n=749), casi nada en medio (8.9% en 2-4) | `Escalamiento_QualityScorer_Produccion_Cierre.md` §3.1 | Hallazgo real de mercado (anunciantes que mencionan precio en texto vs. no), no ruido del LLM — investigado con evidencia (`$` literal en 93.7% del grupo alto vs. 7.6% del grupo bajo) |
| M3 | Tasa de éxito/fallback (conjunto de medición, n=20) | Éxito 50%, cobertura 20%, tema 5%, ambigüedad 25% | 05 (6.2.7), celda 14 | Conjunto diseñado con casos extremos por categoría — **no es una predicción de tasa de fallback en producción con tráfico real**, advertencia explícita en el cierre |
| M3 | Umbral de confianza | 0.65 | `Feature_6_2_7...Cierre.md` §5 | Calibración provisional sobre 11 puntos con salto limpio, no optimizada — explícito en el cierre |
| M3 | Latencia (mediana, `gemini-3.1-flash-lite` vs. `gemini-3.5-flash`) | 1.3s vs. 12.3s (mediana), 0/13 vs. 3/13 reintentos 503 | `Feature_6_2_7...Cierre.md` §8ter | Post-cierre (2026-07-15), reemplaza la decisión de modelo original de la sección 2 del mismo documento — no está en el notebook con el modelo antiguo, el notebook actual ya corre con `gemini-3.1-flash-lite` |

---

## Limitaciones ya documentadas, listas para 6.1.6

| Limitación | Cita exacta |
|---|---|
| Validación circular de M1 — ground truth sintético construido por el mismo equipo, no usuarios reales | `notebooks/01_m1_preference_matching.ipynb`, celda markdown "## 5. Advertencia de validación circular (obligatoria)" |
| Exclusión de Pedregal/Parque Lefevre de KNN/KMeans por volumen insuficiente para 5-fold CV | `Context-MD/Feature_6_2_4_M2_KNN_RF_Cierre.md` §1, con referencia a Acta de Feature 1.2 §5.3; confirmado también en `Feature_6_2_5...Cierre.md` §1 |
| Anomalías de auditoría en Zone Health (Betania/Bella Vista, profundidad desigual de auditoría, no calidad real) | `Context-MD/Feature_1_4_Zone_Health_Composite_Index_Documentacion_Granular.md` (sección de revisión cualitativa 1.4.7); reproducido en `notebooks/00b_zone_health_composite_index.ipynb`, celda 28 |
| Patrón recurrente de verificación de modelo LLM — "cerrado no significa verificado" en sustancia, aunque esa frase exacta no aparece en ningún documento del repo | Instancias concretas listadas abajo |
| Hallazgo bimodal de `transparencia_precio` — no es dispersión de ruido, es una señal real de mercado (anunciantes mencionan o no mencionan precio en el texto) | `Context-MD/Escalamiento_QualityScorer_Produccion_Cierre.md` §3.1 |
| Mezcla de 2 modelos LLM dentro de una misma muestra — ocurre **dos veces**, no una: (a) 6.2.6 experimental (112 filas `gemini-3.5-flash` + 38 `gemini-3-flash-preview`), (b) batch de producción (529 filas `gemini-3.5-flash` + 639 `gemini-3.1-flash-lite`), cada vez con validación de equivalencia explícita antes de combinar | `Context-MD/Feature_6_2_6_M2_QualityScorer_Cierre.md` §8; `Context-MD/Escalamiento_QualityScorer_Produccion_Cierre.md` §2 |
| Mezcla de 2 modelos LLM en M3 también — el notebook 6.2.7 corrió originalmente con `gemini-3.5-flash`, luego se reemplazó por `gemini-3.1-flash-lite` post-cierre, verificado por reproducción de comportamiento en 31/31 consultas, no asumido | `Context-MD/Feature_6_2_7_M3_Orchestration_Cierre.md` §8ter |
| Limitación de reproducibilidad — `gemini-3-flash-preview` es un modelo "preview", no GA, usado en 6.2.6 por necesidad (degradación sostenida de `gemini-3.5-flash`) | `Context-MD/Feature_6_2_6_M2_QualityScorer_Cierre.md` §4, punto 3 |
| Manejo de excepciones incompleto en `extraer()` de M3 (no capturaba `httpx.TransportError`, solo `ServerError`) — hallazgo post-cierre, corregido, con implicación directa para el endpoint de producción de Épica 4 | `Context-MD/Feature_6_2_7_M3_Orchestration_Cierre.md` §8bis |
| Umbral de confianza de M3 (0.65) explícitamente provisional, no optimizado — sin casos de confianza intermedia genuina observados | `Context-MD/Feature_6_2_7_M3_Orchestration_Cierre.md` §5, §8 |
| Cobertura GTFS 2016 (mencionada en el WBS 6.1.6) | **No verificada en esta revisión** — fuera de las fuentes que se pidió revisar; no confirmar sin leer `ETL_Feature_1_3_1_4_Proceso_Completo.md` primero |
| n=20 en encuesta (mencionada en el WBS 6.1.6) | **No verificada en esta revisión** — no se encontró el material de encuesta dentro de las fuentes revisadas; no asumir que existe documentación lista |

**Instancias concretas del patrón "verificar antes de heredar/citar" (para sustentar la fila de
arriba sobre modelo LLM, ya que la sección 8 con este meta-hallazgo específico no existe en el
repo — ver nota al inicio del documento):**

1. `gemini-2.5-flash` (nombre declarado entonces en `CLAUDE.md`) devuelve 404 real pese a aparecer
   en `client.models.list()` — `Context-MD/Feature_6_2_6_M2_QualityScorer_Cierre.md` §4.
2. `gemini-3.5-flash` pasó de 100% de fallo sostenido (6.2.6) a 100% de éxito (6.2.7) en el mismo
   tipo de lote diagnóstico — re-verificado, no heredado — `Feature_6_2_7...Cierre.md` §2.
3. `gemini-3.1-flash-lite` adoptado para M3 solo tras diagnóstico real (no por aparecer en
   `client.models.list()`) — `Feature_6_2_7...Cierre.md` §8ter.
4. Cita a "Feature 1.4.6" copiada de script a script sin existir en ningún documento del repo —
   `CLAUDE.md` §"Regla de citas de features".
5. Archivos de amenidades de Google Places nunca pasaron por `asignar_corregimiento()` porque su
   método de extracción era distinto al de OSM (que sí la tenía) — `CLAUDE.md` §"Regla de
   verificación geométrica".
6. Cita a `DOC-05 §4.2` en la Condición de Done de 1.5.1 — documento inexistente en el repo,
   confirmado por búsqueda — `Context-MD/Gobernanza_WBS_vs_Feature_6_2.md`, entrada "1.5.1".
7. Validación de equivalencia entre modelos antes de combinar resultados en producción (no
   sustitución silenciosa) — `Context-MD/Escalamiento_QualityScorer_Produccion_Cierre.md` §2.

---

## Discrepancias detectadas entre el WBS de 6.1 y el estado real del proyecto

Mismo formato que `Context-MD/Gobernanza_WBS_vs_Feature_6_2.md`. **No se resuelven aquí — se
reportan para decisión del usuario.**

1. **Fuente documental citada en el encargo no existe en el repo.**
   - **Se pidió revisar:** `Feature_6.2_Documentacion_Completa_v2.md`, específicamente §8
     (meta-hallazgo "cerrado no significa verificado") y §7.2 (cambio de modelo de M3, dos rondas
     de validación).
   - **Estado real:** ese archivo no existe. `Context-MD/Feature_6.2_Contexto_Ejecucion_v2.md` es
     el único documento con nombre similar, pero su §7 y §8 tratan de temas distintos (decisiones
     de arquitectura de notebooks; checkpoints de revisión humana CP-1/CP-2). El contenido
     temáticamente equivalente al que se pidió (verificación repetida de modelo LLM, cambio de
     modelo de M3) vive en `Feature_6_2_7_M3_Orchestration_Cierre.md` §2 y §8ter.
   - **Decisión pendiente:** ¿el documento `Documentacion_Completa_v2.md` se perdió/nunca se creó y
     hay que reconstruirlo, o la referencia del encargo estaba basada en un plan que cambió de
     nombre/ubicación? No se puede saber sin que el usuario lo confirme.

2. **6.1.6 del WBS enumera 5 limitaciones específicas, pero Feature 6.2 generó más limitaciones
   igual de citables que el WBS no menciona** (ver tabla completa arriba: patrón de verificación de
   modelo LLM, hallazgo bimodal de `transparencia_precio`, mezcla de modelos en 2 puntos distintos
   del proyecto, limitación de reproducibilidad del modelo "preview").
   - **Por qué importa:** el WBS fue escrito antes de que Feature 6.2 ejecutara — es plan original,
     no lo ejecutado (mismo principio que ya aplica `Gobernanza_WBS_vs_Feature_6_2.md` a otras
     tareas del WBS). Redactar 6.1.6 solo con las 5 limitaciones nombradas dejaría fuera hallazgos
     reales y ya documentados del propio proyecto.
   - **Decisión pendiente:** ¿se amplía la Condición de Done de 6.1.6 para reflejar la lista
     completa, o se mantiene el texto original y las limitaciones adicionales se consideran
     material "extra" a discreción de quien redacte?

3. **6.1.4 del WBS lista "Precision@k, MAE, Silhouette, tasa de éxito M3" como las métricas a
   integrar, sin mencionar el Quality Scorer (M2, 6.2.6/producción).**
   - **Por qué importa:** el Quality Scorer generó una de las cifras más ricas del proyecto (el
     hallazgo bimodal de `transparencia_precio` sobre 1,168 filas de producción) y no tiene
     representación en la lista de métricas del WBS.
   - **Decisión pendiente:** ¿se agrega explícitamente a la Condición de Done de 6.1.4, o se asume
     implícito en "figuras/tablas seleccionadas de los notebooks" sin necesidad de listarlo?

4. **6.1.7 cita conexión con "OE-01 a OE-05" sin que se haya localizado el documento fuente de esos
   objetivos específicos dentro del alcance de fuentes revisado en este encargo.**
   - **Decisión pendiente:** confirmar dónde viven los OE antes de redactar, o si hay que
     formularlos como parte de 6.1.1.

5. **Los pesos del Zone Health Composite Index citados en `CLAUDE.md` no coinciden con los que el
   notebook 6.2.2 realmente reproduce y exporta — esto no es un hallazgo nuevo de esta revisión, es
   una discrepancia interna del propio `CLAUDE.md` que afecta directamente a cualquier cifra de
   Zone Health citada en el paper (6.1.3 y 6.1.4).**
   - **`CLAUDE.md` dice** (§"Pesos del Zone Health Composite Index"): *"Seguridad 0.30, transporte
     0.20, amenidades 0.20, walkability 0.15, socioeconómico 0.15."* — 5 dimensiones.
   - **El notebook `00b_zone_health_composite_index.ipynb` (celda 23) y
     `Context-MD/Feature_1_4_Zone_Health_Composite_Index_Documentacion_Granular.md` (§6) muestran:**
     4 dimensiones, dimensión socioeconómica eliminada, pesos redistribuidos proporcionalmente:
     seguridad 0.352941176, transporte 0.235294118, amenidades 0.235294118, walkability
     0.176470588.
   - **Por qué importa:** es exactamente el caso que el propio `CLAUDE.md` anticipa en su
     encabezado — *"Si algo aquí contradice una Acta más reciente, la Acta gana — pero avísale al
     equipo, porque significa que este archivo quedó desactualizado."* La Acta
     (`Feature_1_4_Zone_Health...Documentacion_Granular.md`) y el notebook coinciden entre sí; solo
     `CLAUDE.md` quedó con los pesos viejos de 5 dimensiones.
   - **Decisión pendiente:** actualizar la sección de pesos de `CLAUDE.md` (fuera del alcance de
     este documento de inventario, que no modifica `CLAUDE.md`) — reportado aquí porque cualquier
     cifra de Zone Health que el paper cite debe usar los 4 pesos reales, no los 5 de `CLAUDE.md`.

No quedan más discrepancias identificadas entre el WBS de 6.1 y el estado real del proyecto dentro
del alcance de fuentes revisado.
