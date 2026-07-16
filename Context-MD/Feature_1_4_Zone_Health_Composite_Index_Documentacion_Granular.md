# Feature 1.4 — Zone Health Composite Index
## Documentación granular completa
 
**Proyecto:** REIP (Real Estate Intelligence Platform) — Tesis, Universidad Tecnológica de Panamá, Curso 0698
**Responsable:** Helio Castillo (Besto), PM y líder técnico
**Fecha de cierre:** 2026-07-09
**Estado:** CERRADO (1.4.1 → 1.4.7, 7 de 7 subtareas)
 
---
 
## 0. Resumen ejecutivo
 
Feature 1.4 calcula el Zone Health Composite Index — el índice compuesto que mide
calidad de zona para las 9 zonas del scope de REIP. Se ejecutó de forma estrictamente
secuencial (1.4.1 → 1.4.7), con verificación numérica independiente en cada paso antes
de aprobar el siguiente.
 
**Hallazgo transversal más importante:** de las 4 tareas de cómputo por zona
(1.4.1–1.4.4), **solo una (1.4.2, transporte) cerró sin ningún hallazgo de datos
corruptos, mal ubicados, o incompletos heredados de Feature 1.3.** Las otras tres
requirieron al menos una corrección de datos antes de poder calcularse correctamente.
Esto se documenta como patrón, no como incidentes aislados: la fase de "extracción y
cómputo cerrados" de Feature 1.3 subestimó sistemáticamente cuánto quedaba sin
verificar contra ejecución real de código.
 
**Cambio de diseño más importante:** la dimensión socioeconómica (1.4.5) se eliminó
por completo del índice — el dato disponible (densidad poblacional) no es un proxy
defendible de nivel socioeconómico. Su peso (0.15) se redistribuyó proporcionalmente
entre las 4 dimensiones restantes.
 
**Composite final:**
 
| Zona | Composite | Estado |
|---|---|---|
| Betania | 0.8783 | Calculado |
| San Francisco | 0.6888 | Calculado |
| Bella Vista | 0.5367 | Calculado |
| Parque Lefevre | 0.3765 | Calculado |
| Pedregal | 0.1076 | Calculado, **no visualizado** (cobertura de amenidades insuficiente) |
| El Cangrejo | 0.5367 | Heredado de Bella Vista |
| Marbella | 0.5367 | Heredado de Bella Vista |
| Obarrio | 0.5367 | Heredado de Bella Vista |
| Costa del Este | — | **Sin score** (datos estructuralmente insuficientes) |
 
---
 
## 1. Pesos del índice — evolución durante Feature 1.4
 
**Pesos originales (5 dimensiones, heredados del WBS/Acta de Datos):**
 
| Dimensión | Peso |
|---|---|
| Seguridad | 0.30 |
| Transporte | 0.20 |
| Amenidades | 0.20 |
| Walkability | 0.15 |
| Socioeconómico | 0.15 |
 
**Pesos finales (4 dimensiones, tras eliminación de socioeconómico en 1.4.5):**
 
| Dimensión | Peso original | Peso final (÷0.85) |
|---|---|---|
| Seguridad | 0.30 | **0.352941176** |
| Transporte | 0.20 | **0.235294118** |
| Amenidades | 0.20 | **0.235294118** |
| Walkability | 0.15 | **0.176470588** |
 
La redistribución es proporcional, no equitativa — preserva el orden relativo de
prioridad trazado a la Encuesta de Requerimientos §2.2, en vez de repartir el 0.15
sobrante en partes iguales sin justificación.
 
---
 
## 2. Feature 1.4.1 — Normalización de seguridad
 
**Objetivo:** normalizar `tasa_por_100k` (homicidios SIEC 2023) a escala [0,1] por
corregimiento.
 
**Alcance real:** 5 zonas con extracción propia (San Francisco, Bella Vista, Parque
Lefevre, Betania, Pedregal) — no 8 ni 9, corrección de precisión sobre la redacción
original del WBS.
 
**Método (decisión formal):** min-max invertido.
```
score_seguridad = 1 - ((x - min) / (max - min))
```
Inversión necesaria: tasa de homicidios alta = mala seguridad; sin invertir, la zona
más peligrosa saldría con el score más alto.
 
**Limitación documentada:** n=5, sensible a valores extremos (Parque Lefevre 21.01
muy por encima del resto del rango, 3.26–15.60).
 
**Scripts:** `pipeline/zone_health/normalizacion_seguridad.py`,
`pipeline/zone_health/tests/test_normalizacion_seguridad.py` (10/10 tests).
 
**Resultado final:**
 
| Zona | tasa_por_100k | Score |
|---|---|---|
| San Francisco | 3.26 | 1.0000 |
| Betania | 4.74 | 0.9166 |
| Bella Vista | 14.83 | 0.3482 |
| Pedregal | 15.60 | 0.3048 |
| Parque Lefevre | 21.01 | 0.0000 |
 
### Hallazgos y correcciones durante 1.4.1
 
1. **Archivo canónico roto.** `pipeline/data/External/SEIC/seguridad_homicidios_2023.jsonl`
   (ruta y mayúsculas incorrectas respecto a Acta 1.3 §7) tenía `tasa_por_100k: null`
   en todas las filas. Los valores reales estaban en un duplicado huérfano
   (`... (1).jsonl`) con nombre de descarga repetida, en carpeta equivocada (`INEC`
   en vez de `seguridad`), con typo de acrónimo (`SEIC` vs `SIEC`).
2. **`pipeline/data/external/` nunca estuvo versionado en git** — la carpeta completa
   era `??` en `git status`, sin ningún commit. Confirmado que no era exclusión
   intencional de `.gitignore`, sino omisión simple.
3. **Campo `hereda_de: "Juan Díaz"` para Costa del Este** encontrado embebido
   directamente en los datos — decisión ya revocada en esta misma sesión, pero el
   archivo no lo reflejaba. Corregido a `null` con `motivo_estado` explícito.
4. **Archivo canónico nuevo creado** en la ruta correcta
   (`pipeline/data/external/seguridad/seguridad_homicidios_2023.jsonl`), separado del
   archivo de socioeconómico (violación de la estructura de Acta 1.3 §7 detectada y
   corregida).
---
 
## 3. Feature 1.4.2 — Densidad de transporte
 
**Objetivo:** calcular densidad de puntos de transporte (paradas GTFS + estaciones
Metro) por km², normalizada [0,1].
 
**Método (decisión formal):**
```
conteo_total = paradas_gtfs + estaciones_metro   (sin ponderar, cuentan igual)
densidad = conteo_total / superficie_km2
score = (x - min) / (max - min)   (sin inversión — más densidad = mejor)
```
 
**Limitación documentada:** tratar metro y bus por igual subestima la calidad real
de transporte en zonas con acceso a metro. No se corrigió con un peso arbitrario por
falta de sustento para elegir un factor específico.
 
**Scripts:** `pipeline/zone_health/normalizacion_transporte.py`,
`pipeline/zone_health/tests/test_normalizacion_transporte.py` (8/8 tests).
 
**Resultado final:**
 
| Zona | Conteo total | Densidad/km² | Score |
|---|---|---|---|
| Bella Vista | 46 | 10.04 | 1.0000 |
| Betania | 62 | 7.53 | 0.6969 |
| San Francisco | 49 | 7.36 | 0.6769 |
| Parque Lefevre | 44 | 6.08 | 0.5227 |
| Pedregal | 50 | 1.75 | 0.0000 |
 
### Hallazgos y correcciones durante 1.4.2
 
**Único cierre limpio de las 4 tareas de cómputo por zona** — pero destapó, en el
proceso de investigación de un problema aparente, dos hallazgos importantes que
afectaban a Feature 1.3:
 
1. **`corregimiento_id` en `metro_estaciones_final_30.jsonl` estaba 30/30 en `null`.**
   Investigación con `git log`/`git blame` reveló que **el script de cruce espacial
   documentado en Acta 1.3 §6.3 nunca existió en el repo** — se documentó el método
   pero no se versionó el código. Se creó `pipeline/zone_health/cruce_espacial_corregimiento.py`
   (shapely `Point().contains()`), aplicado por primera vez: pobló 4/30 estaciones
   reales (Iglesia Del Carmen y Vía Argentina → Bella Vista; Pedregal-Las Acacias y
   Don Bosco → Pedregal).
2. **`corregimiento_id` en `paradas_mibus_gtfs.jsonl` (903/1150, 78%, en `null`)
   se verificó como geográficamente correcto, no un bug** — MiBus cubre toda la
   ciudad, la mayoría de sus paradas están, correctamente, fuera del scope de 9 zonas.
3. **Reorganización completa de `pipeline/data/external/`**, incluyendo salto técnico
   por `core.ignorecase=true` en macOS (`External → external_tmp → external`) para
   que el rename de mayúsculas se registrara correctamente en git (crítico para
   despliegue en Railway/Linux, case-sensitive).
---
 
## 4. Feature 1.4.3 — Densidad de amenidades ponderada por categoría
 
**Objetivo:** calcular densidad de amenidades ponderada por categoría, normalizada
[0,1].
 
**Taxonomía (5 categorías, Acta 1.3.7 §7):** supermercado, farmacia, salud
(hospital+clinica fusionados), parque, colegio.
 
**Pesos (decisión formal, fundamentada en Encuesta §2.3):**
 
| Categoría | % demanda (encuesta) | Peso final |
|---|---|---|
| Supermercado | 80% | 0.3137 |
| Parque | 65% | 0.2549 |
| Salud | 60% | 0.2353 |
| Colegio | 25% | 0.0980 |
| Farmacia | sin dato — asignado = colegio | 0.0980 |
 
Farmacia no fue incluida como opción en la encuesta original — se le asignó el peso
de la categoría de menor demanda conocida (criterio conservador, no un valor
inventado sin ancla).
 
**Método:**
```
conteo_ponderado_zona = Σ (peso_categoria × conteo_categoria)
score = (x - min) / (max - min)   (sin inversión)
```
 
**Scripts:** `pipeline/zone_health/normalizacion_amenidades.py`,
`pipeline/zone_health/tests/test_normalizacion_amenidades.py`,
`pipeline/data/external/amenidades/LOG_EXTRACCION.md` (log de extracción creado
en esta sesión — no existía antes).
 
**Resultado final (post todas las correcciones de esta sección):**
 
| Zona | conteo_ponderado | Score |
|---|---|---|
| Betania | 20.0765 | 1.0000 |
| Parque Lefevre | 11.4510 | 0.5133 |
| San Francisco | 5.1757 | 0.1593 |
| Bella Vista | 2.5094 | 0.0088 |
| Pedregal | 2.3527 | 0.0000 |
 
### Hallazgos y correcciones durante 1.4.3 (la tarea con más incidencias de toda Feature 1.4)
 
1. **Sesgo de búsqueda por categoría en Bella Vista (`hospital=0`).** Mismo patrón ya
   documentado para Costa del Este en Acta 1.3.7 §7. Verificado externamente
   (búsqueda web) que Bella Vista sí tiene hospitales reales. Re-extracción manual
   (sin acceso a API de Google Places en la sesión): 2 candidatos evaluados, 1
   descartado tras fallar verificación geométrica programática (Hospital Nacional,
   cae en Calidonia, no Bella Vista), 1 confirmado (Complejo Hospitalario Dr. Arnulfo
   Arias Madrid). Resultado: `hospital` 0→1 (el segundo candidato inicial también
   fue descartado en una ronda posterior de auditoría — ver punto 4).
2. **Hueco de bounding box en Betania.** El archivo OSM combinado original cubría
   solo ~26% de la extensión norte-sur del polígono real de Betania, dando
   `supermercado=0, farmacia=0, salud=0`. Re-extraído vía Overpass API acotado al
   bbox completo: 217 elementos → 104 confirmados dentro de Betania. Nuevo archivo
   dedicado: `amenidades_betania_osm.geojson` (el archivo combinado original,
   `amenidades_betania_obarrio_cangrejo_marbella_osm.geojson`, no se tocó).
3. **Auditoría del mismo problema en Obarrio/Cangrejo/Marbella (no bloqueante):**
   - El Cangrejo: sin problema de cobertura.
   - Obarrio: hueco parcial (100% de parques faltantes, 1 farmacia).
   - Marbella: no verificable (OSM solo tiene punto-centro, sin polígono de límite).
   - No se corrigió — estas 3 zonas heredan de Bella Vista, no usan su propia
     extracción en el composite. Documentado para cuando se toque Feature 5.3.6.
4. **Contaminación geométrica en los 3 archivos de Google Places (Bella Vista, San
   Francisco, Costa del Este) — nunca habían pasado por verificación espacial,**
   a diferencia de los archivos OSM. Auditoría completa con `asignar_corregimiento()`:
   - **Bella Vista (18 registros):** 15 correctos, 1 mal asignado (movido a San
     Francisco: Escuela Isabel Herrera Obaldía), 2 fuera de scope (eliminados:
     Clínica Bella Vista, Farmacia Carbono — Calidonia).
   - **San Francisco (34 registros):** 29 correctos, 2 mal asignados (Centro Médico
     San Luis movido a Parque Lefevre; Andrés Bello Park eliminado por ser duplicado
     exacto ya existente en Bella Vista), 3 fuera de scope (eliminados: Supermercados
     Rey 12 de Octubre, Clínica + Sala de Urgencias Hospital San Fernando).
   - **Costa del Este (24 registros):** 0 dentro (estructural — sin polígono propio),
     13 caen en Parque Lefevre, 11 fuera de las 5 zonas. No corregido — decisión
     pendiente de presentación para Feature 5.3.6 (documentada en CLAUDE.md).
5. **Cita documental inventada — "Feature 1.4.6"** aparecía en el docstring de los 3
   scripts de normalización (`seguridad`, `transporte`, `amenidades`), copiada de
   script a script sin verificarse contra ningún documento real del repo. Corregida
   en los 3 archivos. Se agregó regla permanente a `CLAUDE.md`: ninguna cita de
   Feature/Acta se copia entre scripts sin re-verificar contra la fuente.
6. **Regla nueva agregada a CLAUDE.md:** verificación geométrica (`asignar_corregimiento()`)
   obligatoria para TODO archivo de amenidades, sin importar el método de origen
   (OSM o Google Places) — la causa raíz del punto 4 fue que la verificación se
   aplicó solo a un tipo de fuente.
**Limitación abierta, documentada y aceptada explícitamente para el cierre (decisión
formal):** sub-cobertura conocida en Bella Vista (Riba Smith, supermercado grande y
conocido, confirmado ausente del archivo) y San Francisco (no auditado con el mismo
nivel de detalle). Se decidió no re-extraer en esta ronda — 7 rondas de corrección
acumuladas en Feature 1.4 hacían necesario declarar un punto de cierre. El ranking
relativo entre Bella Vista y Parque Lefevre podría cambiar si se completara la
cobertura (margen actual no es amplio).
 
---
 
## 5. Feature 1.4.4 — Walkability
 
**Objetivo original (WBS):** proxy de dos componentes — densidad vial peatonal +
distancia a amenidades clave (PostGIS).
 
**Cambio de diseño (decisión formal):** eliminado el componente de densidad vial.
Verificación exhaustiva (`grep` sobre todo `pipeline/`) confirmó que no existe ningún
dato de red vial/peatonal en el repo — ni siquiera parcial o mal ubicado, a
diferencia de los casos anteriores. Se decidió no extraerlo porque el objetivo real
de la dimensión es medir cercanía a lo necesario, no la infraestructura vial en sí.
 
**Amenidades clave confirmadas (Encuesta §2.3, §2.2):** supermercado, parque, metro.
 
**Método:**
```
Para cada zona: centroide del polígono (shapely)
Distancia mínima a supermercado/parque: contra el conjunto COMBINADO de las 5 zonas
  reales (no solo el archivo propio — el más cercano puede cruzar frontera administrativa)
Distancia mínima a metro: contra las 30 estaciones completas (no solo las 4 con
  corregimiento_id poblado)
Promedio simple de las 3 distancias (sin ponderar entre categorías)
score = 1 - ((x - min) / (max - min))   (invertido — más cerca = mejor)
```
 
**Scripts:** `pipeline/zone_health/normalizacion_walkability.py`,
`pipeline/zone_health/tests/test_normalizacion_walkability.py`.
 
**Resultado final:**
 
| Zona | Distancia promedio (m) | Score |
|---|---|---|
| Bella Vista | 304.1 | 1.0000 |
| Betania | 583.8 | 0.8812 |
| San Francisco | 802.1 | 0.7885 |
| Parque Lefevre | 888.0 | 0.7520 |
| Pedregal | 2658.7 | 0.0000 |
 
### Hallazgos y correcciones durante 1.4.4
 
1. **Verificación de cobertura de datos de entrada (Punto 1 previo al cálculo):**
   confirmó que los polígonos OSM tienen mezcla de `Point`/`Polygon` (resuelto con
   centroide vía shapely), y que el GeoJSON de corregimientos trae 10 features en vez
   de 5 (mezcla de polígono real con nodo `admin_centre`) — filtrado por
   `geometry.type in (Polygon, MultiPolygon) AND properties.name presente`.
2. **Descubrimiento: OSM usa "Bethania" (con h), el resto del proyecto usa "Betania"
   (sin h).** El fix de normalización ya existía en `cruce_espacial_corregimiento.py`
   (de 1.4.2), pero **nunca se había ejercido contra un caso real** — ninguna
   estación de Metro cae dentro del polígono de Betania, y no había test dedicado.
   Se agregó un caso de test real (coordenada de una amenidad de Betania) para cerrar
   la zona ciega de cobertura antes de continuar.
3. **Reutilización correcta de fuentes ya corregidas:** el script importó `RUTA_OSM`
   directamente de `normalizacion_amenidades.py` en vez de redeclarar la ruta —
   heredó automáticamente el archivo corregido de Betania (104 features) sin
   necesitar intervención manual.
---
 
## 6. Feature 1.4.5 — Dimensión socioeconómica: ELIMINADA
 
**Objetivo original (WBS):** integrar variables INEC (población, vivienda,
alfabetización, composición de hogares) a un score socioeconómico normalizado.
 
**Hallazgo:** solo población y densidad están disponibles a nivel de corregimiento
(Acta 1.3, decisión #8) — alfabetización y composición de hogares no existen a ese
nivel de granularidad en el Censo 2023.
 
**Decisión formal:** densidad poblacional no es un proxy defendible de nivel
socioeconómico — no tiene una dirección normativa justificable sin inventar un
supuesto (más densidad puede leerse como mayor centralidad urbana deseable, o como
hacinamiento; ambas lecturas igualmente plausibles con la evidencia disponible).
 
**Se eliminó la dimensión completa del composite**, en vez de forzar una dirección
arbitraria o repartir el peso en partes iguales. Peso (0.15) redistribuido
proporcionalmente entre las 4 dimensiones restantes (ver Sección 1).
 
**Consecuencia documentada:** los datos de población/densidad ya extraídos
(`socioeconomico/inec_poblacion_densidad_2023.jsonl`) quedan disponibles como dato
informativo de zona (ej. ficha descriptiva en frontend), pero no alimentan el score
compuesto.
 
**Consecuencia pendiente para Épica 5:** Feature 5.2.6 especifica "6 toggles
independientes, uno por dimensión" para las capas del mapa — con esta eliminación,
el composite queda en 4 dimensiones cuantitativas + 1 capa cualitativa de tráfico = 5,
no 6. Marcado como pendiente de ajuste cuando se toque Épica 5, no corregido en 1.4.
 
---
 
## 7. Feature 1.4.6 — Fórmula ponderada final + herencia
 
**Fórmula:**
```
composite_zona = Σ (peso_dimension × score_dimension)   [4 dimensiones]
```
Sin renormalización adicional — el resultado ya cae en [0,1] porque los 4
componentes lo están y los pesos suman exactamente 1.0.
 
**Reglas de herencia (ya decididas en Feature 1.3, operacionalizadas aquí):**
 
- **El Cangrejo, Marbella, Obarrio** → copia literal del composite Y desglose completo
  de Bella Vista (no un promedio, no un ajuste — mismo valor, mismos 4 scores).
- **Costa del Este** → sin composite, sin desglose. `estado_zone_health:
  "sin_score_datos_insuficientes"`. Decisión revocada respecto al plan original de
  Acta 1.3.7 §5.3 (que proponía heredar de Juan Díaz) — Juan Díaz nunca fue extraído
  (fuera del scope de 9 zonas), no hay datos reales que heredar en 4 de 5 dimensiones.
- **Pedregal** → SÍ se calcula el composite (entra a la fórmula determinística), pero
  con `estado_visualizacion: "no_visualizado"` — la exclusión es de frontend
  (Feature 5.x), no de cómputo.
**Script:** `pipeline/zone_health/composite_zone_health.py`,
`pipeline/zone_health/tests/test_composite_zone_health.py` (6 tests: suma de pesos,
rango [0,1], herencia idéntica campo por campo, Costa del Este null, coexistencia de
composite+no_visualizado en Pedregal, regresión exacta de Betania).
 
**Output:** `pipeline/data/processed/zone_health_composite_1_4_6.json` — 9 zonas,
sin tocar Supabase (Feature 1.5 sigue pendiente).
 
**Resultado final (post-corrección de contaminación de 1.4.3):**
 
| Zona | Composite | Estado |
|---|---|---|
| Betania | 0.8783 | Calculado |
| San Francisco | 0.6888 | Calculado |
| Bella Vista | 0.5367 | Calculado |
| Parque Lefevre | 0.3765 | Calculado |
| Pedregal | 0.1076 | Calculado, no visualizado |
| El Cangrejo | 0.5367 | Heredado (Bella Vista) |
| Marbella | 0.5367 | Heredado (Bella Vista) |
| Obarrio | 0.5367 | Heredado (Bella Vista) |
| Costa del Este | — | Sin score |
 
### Hallazgo y corrección durante 1.4.6
 
Se recalculó todo el composite después de que la limpieza de contaminación de 1.4.3
(Sección 4, punto 4) cambiara los scores de amenidades de Bella Vista (0.0332→0.0088),
San Francisco (0.2257→0.1593) y Parque Lefevre (0.5000→0.5133). Una discrepancia
aritmética detectada en la primera ronda de verificación (Bella Vista) se rastreó a
que la verificación independiente no había propagado la eliminación de "Clínica
Bella Vista" (fuera de scope, Calidonia) — corregido, confirmado 0.0088 exacto.
 
---
 
## 8. Feature 1.4.7 — Revisión cualitativa
 
**Desviación de la condición de Done original:** el WBS especifica revisión por "al
menos 2 integrantes del equipo". Esta revisión se realizó entre Besto (PM) y Claude
únicamente — decisión explícita de Besto, documentada como desviación consciente, no
como cumplimiento de la condición original. Recomendado (no ejecutado): que un
integrante adicional (Copri, Montoya o Rives) revise la tabla final antes de la
entrega.
 
**Resultado de la revisión:**
 
| Zona | ¿Coincide con intuición de mercado? |
|---|---|
| San Francisco | ✅ Consistente — zona premium reconocida |
| Pedregal | ✅ Consistente — coincide con el ejemplo textual del WBS |
| Parque Lefevre | ✅ Consistente — menor perfil relativo del scope |
| Betania | ⚠️ Anómalo — score más alto de las 5, contraintuitivo |
| Bella Vista | ⚠️ Más bajo de lo esperado para zona financiera/comercial central |
 
**Causa raíz identificada para ambas anomalías (misma causa, dos síntomas):**
diferencias en qué tan agresivamente se auditó y corrigió cada archivo de amenidades
por zona — Betania recibió re-extracción completa (bbox corregido, 104 features);
Bella Vista y San Francisco quedaron con sub-cobertura conocida y no corregida
(Riba Smith, entre otros). El ranking actual refleja en parte "qué tan bien se auditó
cada fuente" además de "qué tan buena es cada zona real" — esto debe quedar explícito
en la sección de limitaciones de la tesis, no presentado como resultado limpio.
 
---
 
## 9. Inventario completo de artefactos generados
 
### Scripts de producción
- `pipeline/zone_health/normalizacion_seguridad.py`
- `pipeline/zone_health/normalizacion_transporte.py`
- `pipeline/zone_health/normalizacion_amenidades.py`
- `pipeline/zone_health/normalizacion_walkability.py`
- `pipeline/zone_health/cruce_espacial_corregimiento.py`
- `pipeline/zone_health/composite_zone_health.py`
- `pipeline/__init__.py`, `pipeline/zone_health/__init__.py`
### Tests (todos versionados, suite completa en verde al cierre)
- `pipeline/zone_health/tests/test_normalizacion_seguridad.py`
- `pipeline/zone_health/tests/test_normalizacion_transporte.py`
- `pipeline/zone_health/tests/test_normalizacion_amenidades.py`
- `pipeline/zone_health/tests/test_normalizacion_walkability.py`
- `pipeline/zone_health/tests/test_cruce_espacial_corregimiento.py`
- `pipeline/zone_health/tests/test_composite_zone_health.py`
### Datos de salida (`pipeline/data/processed/`)
- `zone_health_seguridad_1_4_1.json`
- `zone_health_transporte_1_4_2.json`
- `zone_health_amenidades_1_4_3.json`
- `zone_health_walkability_1_4_4.json`
- `zone_health_composite_1_4_6.json`
### Datos de entrada corregidos (`pipeline/data/external/`)
- `seguridad/seguridad_homicidios_2023.jsonl` (reconstruido)
- `socioeconomico/inec_poblacion_densidad_2023.jsonl` (movido de `INEC/`, `hereda_de` corregido)
- `metro/` (movido de `Metro/`, `corregimiento_id` poblado para 4/30)
- `gtfs/paradas_mibus_gtfs.jsonl` (extraído a carpeta propia)
- `amenidades/amenidades_bella_vista_google_places.jsonl` (hospital agregado, contaminación limpiada)
- `amenidades/amenidades_san_francisco_google_places.jsonl` (contaminación limpiada)
- `amenidades/amenidades_betania_osm.geojson` (nuevo, re-extracción completa)
- `amenidades/LOG_EXTRACCION.md` (nuevo — no existía antes de esta sesión)
### Documentación de gobernanza
- `CLAUDE.md` (raíz del repo) — actualizado 3 veces durante esta sesión: estado del
  proyecto, regla de citas de features, regla de verificación geométrica obligatoria.
### Commits relevantes
- `5616809` — snapshot previo a correcciones
- `93009ea` — rutas alineadas, herencia sincronizada, cruce espacial de Metro poblado
---
 
## 10. Deuda técnica y decisiones pendientes explícitas
 
| Ítem | Prioridad | Contexto |
|---|---|---|
| Sub-cobertura de amenidades en Bella Vista (Riba Smith) y San Francisco (no auditado) | Media | Aceptada como limitación documentada al cierre de 1.4.3 |
| ~~Presentación de los 13 POIs de Costa del Este que caen en Parque Lefevre~~ **RESUELTO 2026-07-16** en `GET /zone-health/{corregimiento}` (`backend/app/routers/zone_health.py`): amenidades se filtran por `zona_etiquetada_origen` (zona del lote de extracción), no por `corregimiento_asignado` (polígono geométrico) — Costa del Este recupera sus 24 POIs reales, Parque Lefevre deja de mostrar los 13 ajenos. Ver nota de duplicados abajo, que este fix expuso. | — | Cerrado en sesión de Épica 5 frontend |
| Hueco de amenidades en Obarrio (parques), Marbella no verificable | Baja — zonas heredan, no calculan propio | Documentado en LOG_EXTRACCION.md |
| Feature 5.2.6 especifica 6 toggles, quedaron 5 tras eliminar socioeconómico | Media | Pendiente de ajuste en Épica 5 |
| Revisión cualitativa sin 2° integrante humano | Alta para la defensa | Riesgo aceptado explícitamente por PM |
| `superficie_km2` duplicado en `seguridad/` y `socioeconomico/`, auditoría de coincidencia pendiente | Media | No bloqueó 1.4.2/1.4.4, sí debe cerrarse antes de 1.5 |
| **Pedregal — `desglose_dimensiones` real muestra `transporte=0.0`, `walkability=0.0`, `amenidades=0.0` (solo `seguridad=0.30` no-cero).** Descubierto durante construcción de `GET /zone-health/{corregimiento}`, Épica 5 (2026-07-16), al consultar la fila real contra Supabase. Más amplio que "amenidades débiles" (la única causa de exclusión de visualización documentada en §9/decisión formal de CLAUDE.md) — 3 de 4 dimensiones en cero, no solo una. **Sin resolver:** pendiente de decisión del equipo sobre si esto es dato real (Pedregal genuinamente carece de esas 3 dimensiones) o un gap de carga no detectado en Feature 1.4. No se investigó más a fondo ni se corrigió — solo se documenta para que no se pierda. | Alta — afecta la validez del score compuesto de Pedregal, no solo su presentación | Pendiente, sin dueño asignado |
| **4 POIs físicos cargados dos veces con `id` distinto, misma entidad real** — Boston School International, Parque Felipe Motta, Este Park, The Casco School. Una copia viene del lote de Costa del Este (Google Places), la otra del lote de Parque Lefevre (OSM); ambas caen geométricamente dentro del polígono de Parque Lefevre. Descubierto en la misma sesión que la fila de arriba, al auditar `corregimiento_asignado='Parque Lefevre'` agrupado por `nombre`. El fix de `zona_etiquetada_origen` (fila de arriba) evita que las 2 copias aparezcan juntas en una sola respuesta del endpoint, pero **no las deduplica en la tabla** — siguen siendo 2 filas de `amenidades` con `id` distinto. **Sin resolver:** requiere decisión de qué registro es canónico (¿se prefiere Google Places por tener `rating`/`place_id`, o el de origen geográfico correcto — Parque Lefevre, no Costa del Este?) antes de borrar o fusionar cualquiera de las dos filas. | Media — no bloquea 5.3.6 con el fix de origen, pero afecta conteos totales de amenidades por zona si se agregan en otro contexto | Pendiente, sin dueño asignado |