# Proceso de ETL — Features 1.3 y 1.4
## Data Pipeline de datos externos y Zone Health Composite Index
 
**Proyecto:** REIP (Real Estate Intelligence Platform)
**Alcance de este documento:** describe el proceso de Extracción, Transformación y
Carga (ETL) que produce el Zone Health Composite Index, desde las fuentes externas
originales hasta el archivo compuesto final. No cubre el pipeline de scraping de
listings (Feature 1.2), que es un proceso ETL independiente y paralelo.
 
---
 
## 1. Arquitectura general del proceso
 
```
EXTRACT                    TRANSFORM                       LOAD
────────                   ─────────                       ────
Fuentes externas    →    Normalización por     →    Archivos JSON
(SIEC, INEC, OSM,        dimensión (1.4.1-4)         intermedios
Overpass, Google                                     (pipeline/data/
Places, GTFS,        →    Fórmula ponderada +         processed/)
datosabiertos.gob.pa)      herencia (1.4.6)      →
                                                       Supabase
                      →    Revisión cualitativa        (PENDIENTE —
                            (1.4.7)                     Feature 1.5)
```
 
**Estado actual del Load:** la carga física a Supabase está deliberadamente diferida
a Feature 1.5 (diseño de esquema). Todo el proceso de Extract y Transform está
completo y verificado en archivos JSON locales — la arquitectura del pipeline no
depende de que la base de datos exista para producir resultados, por diseño.
 
---
 
## 2. Fase EXTRACT — Fuentes y método por dimensión
 
| Dimensión | Fuente(s) | Método de extracción | Feature |
|---|---|---|---|
| Seguridad | SIEC — Informe de Criminalidad 2023 | PDF estructurado (extracción con Camelot, `flavor='stream'`) | 1.3.5 |
| Transporte — Metro | datosabiertos.gob.pa | CSV georreferenciado oficial (30 estaciones) | 1.3.2 |
| Transporte — Bus | panatrans-dataset (comunidad MiBus) | GTFS estándar (`stops.txt`) | 1.3.3 |
| Amenidades | Google Places API (3 zonas) + OSM Overpass API (3 zonas/grupos) | Búsqueda por categoría (Google Places) / consulta espacial por bounding box (Overpass) | 1.3.7 |
| Socioeconómico | INEC — Censo 2023 | CSV/tablas web | 1.3.6 |
| Polígonos administrativos | OSM Overpass (relaciones `boundary=administrative`) | Consulta por relation ID confirmado | 1.3.1 |
| Walkability (distancia) | Derivado — no es fuente nueva | Reutiliza amenidades + polígonos ya extraídos | 1.4.4 |
 
**Decisión de scope crítica que determina el Extract completo:** de las 9 zonas
nominales del proyecto, solo 5 son corregimientos administrativos oficiales con
polígono propio (San Francisco, Bella Vista, Parque Lefevre, Betania, Pedregal). Las
otras 4 (El Cangrejo, Marbella, Obarrio, Costa del Este) son barrios reconocidos
comercialmente sin geometría administrativa independiente — su tratamiento se resuelve
en la fase Transform (Sección 3.5), no en la extracción.
 
### 2.1 Elección de fuente por dimensión — criterio y alternativas descartadas
 
- **Metro:** se descartó OSM como fuente primaria porque solo cubría 18 de 30
  estaciones reales incluso ampliando el bounding box. El dataset oficial del
  gobierno panameño es completo y georreferenciado directamente.
- **Amenidades — Bella Vista, San Francisco, Costa del Este:** Google Places elegido
  sobre OSM porque ya existía extracción manual verificada con metadata rica
  (teléfono, rating, `place_id`); para Costa del Este específicamente, el filtro de
  polígono necesario para evitar fuga hacia Parque Lefevre reducía el conteo de OSM
  por debajo de lo ya verificado con Google Places.
- **Amenidades — Betania, Parque Lefevre, Pedregal, y el grupo Obarrio/Cangrejo/Marbella:**
  OSM Overpass elegido porque una sola consulta por bounding box trae todos los tags
  de amenidad de una vez — no depende de búsquedas por categoría independientes
  (relevante para la Sección 4.2 de este documento).
- **Seguridad — año de referencia 2023, no 2024/2025:** no existen reportes anuales
  completos de SIEC para años posteriores; los reportes mensuales disponibles solo
  cubren ~30 corregimientos de mayor incidencia, insuficiente para las 9 zonas del
  scope del proyecto.
---
 
## 3. Fase TRANSFORM — Normalización y composición
 
### 3.1 Principio general de normalización
 
Cada una de las 4 dimensiones activas del índice (seguridad, transporte, amenidades,
walkability) se normaliza independientemente a escala [0,1] mediante min-max, con
dirección (invertida o no) decidida explícitamente según si el valor crudo es
deseable en sentido creciente o decreciente:
 
| Dimensión | Variable cruda | Dirección | Razón |
|---|---|---|---|
| Seguridad | Tasa de homicidios/100k hab. | Invertida | Tasa alta = mala seguridad |
| Transporte | Puntos de transporte/km² | Directa | Más densidad = mejor acceso |
| Amenidades | Conteo ponderado por categoría | Directa | Más amenidades = mejor servicio |
| Walkability | Distancia promedio a amenidades clave (m) | Invertida | Más cerca = mejor caminabilidad |
 
Todas las normalizaciones se calculan **exclusivamente sobre las 5 zonas con
extracción propia** (n=5) — nunca sobre las 9 nominales, porque las 4 zonas sin
polígono no tienen variable cruda propia que normalizar (ver Sección 3.5).
 
### 3.2 Transformación de seguridad (1.4.1)
 
```
tasa_por_100k = (homicidios_2023 / poblacion_2023) × 100,000
score = 1 - ((tasa - tasa_min) / (tasa_max - tasa_min))
```
Se usa la tasa calculada, no el conteo crudo de homicidios — el conteo crudo altera
el ranking relativo de riesgo entre zonas (por población: Pedregal parece la más
peligrosa por conteo bruto; por tasa real, Parque Lefevre resulta la de mayor riesgo
real, 21.01 vs. 15.60 por 100k).
 
### 3.3 Transformación de transporte (1.4.2)
 
```
conteo_total = paradas_gtfs_en_zona + estaciones_metro_en_zona
densidad = conteo_total / superficie_km2_zona
score = (densidad - min) / (max - min)
```
Requiere un paso de geoprocesamiento previo: asignación de cada parada/estación a su
corregimiento mediante cruce espacial punto-en-polígono (`shapely.geometry.Point().contains()`
contra el polígono real de cada corregimiento) — este cruce es un prerequisito técnico
compartido con la dimensión de walkability.
 
### 3.4 Transformación de amenidades (1.4.3)
 
```
conteo_ponderado = Σ (peso_categoria × conteo_categoria)   [5 categorías]
score = (conteo_ponderado - min) / (max - min)
```
Los pesos por categoría se derivan de la Encuesta de Requerimientos propia del
proyecto (n=20, §2.3 "Datos del Entorno Críticos") — no son arbitrarios: supermercado
80% de demanda declarada, parque 65%, salud (hospital+clínica fusionados) 60%,
colegio 25%. La categoría farmacia no fue incluida en la encuesta original; se le
asignó el peso de la categoría de menor demanda conocida (colegio) como supuesto
conservador explícito, no como hallazgo empírico.
 
### 3.5 Transformación de walkability (1.4.4)
 
```
Para cada zona: centroide = shapely.centroid(poligono_corregimiento)
distancia_supermercado = min(haversine(centroide, cada_supermercado_de_las_5_zonas))
distancia_parque = min(haversine(centroide, cada_parque_de_las_5_zonas))
distancia_metro = min(haversine(centroide, cada_una_de_las_30_estaciones))
distancia_promedio = mean(distancia_supermercado, distancia_parque, distancia_metro)
score = 1 - ((distancia_promedio - min) / (max - min))
```
Diseño original del WBS contemplaba un segundo componente (densidad de red vial
peatonal vía PostGIS) — eliminado porque no existe ningún dato de infraestructura
vial en las fuentes del proyecto; se redefinió walkability como proxy de un solo
componente (distancia a lo necesario), documentado como simplificación metodológica
explícita.
 
Nota metodológica relevante para la sección de limitaciones de la tesis: la búsqueda
del punto más cercano se hace contra el **conjunto combinado de las 5 zonas**, no
solo contra el archivo de la propia zona — porque la amenidad más cercana a un
centroide puede estar administrativamente en la zona vecina, y restringir la
búsqueda a la propia zona infla artificialmente la distancia en zonas fronterizas.
 
### 3.6 Dimensión socioeconómica — eliminada en fase Transform, no en fase Extract
 
El dato (población, densidad) sí se extrajo (Sección 2) pero se decidió no
transformarlo en un score del índice compuesto. Motivo: el Censo 2023 no reporta
alfabetización ni composición de hogares a nivel de corregimiento (solo a nivel de
provincia), y la variable que sí queda disponible (densidad poblacional) no tiene una
dirección normativa defendible como proxy de nivel socioeconómico — a diferencia de
las otras 4 dimensiones, donde "mejor"/"peor" tiene una lectura consensuable. El peso
correspondiente (0.15) se redistribuyó proporcionalmente entre las 4 dimensiones
restantes, preservando el orden de prioridad relativo ya trazado a la encuesta.
 
### 3.7 Composición final (1.4.6)
 
```
composite_zona = Σ (peso_dimension_final × score_dimension)   [4 dimensiones]
```
Pesos finales (redistribuidos): seguridad 0.3529, transporte 0.2353, amenidades
0.2353, walkability 0.1765. El resultado cae naturalmente en [0,1] sin necesidad de
una segunda normalización, porque los 4 componentes ya están en esa escala y los
pesos suman exactamente 1.0.
 
### 3.8 Tratamiento de las 4 zonas sin polígono propio (herencia)
 
Regla aplicada en fase Transform, no en Extract:
 
- **El Cangrejo, Marbella, Obarrio** heredan el composite y desglose completo de
  **Bella Vista** (copia literal, no cálculo propio) — están geográficamente
  contenidos en ese corregimiento oficial.
- **Costa del Este** no hereda de ningún corregimiento — el corregimiento contenedor
  candidato (Juan Díaz) nunca fue extraído por estar fuera del scope de 9 zonas
  definido al inicio del proyecto. Se le asigna un estado explícito de "datos
  insuficientes" en vez de forzar una herencia sin sustento real.
- **Pedregal** es la única zona con polígono propio que recibe un tratamiento
  especial: su composite SÍ se calcula (entra a la fórmula determinística de las 5
  zonas reales) pero se marca como "no visualizado" en el frontend — decisión de
  presentación, no de cómputo, por cobertura de amenidades insuficiente para ser
  comparable con el resto del scope (12 POIs vs. 32–104 en el resto).
---
 
## 4. Hallazgos metodológicos del proceso ETL — relevantes para la sección de
   limitaciones de la tesis
 
### 4.1 Brecha sistemática entre "extracción documentada" y "extracción verificada
   contra ejecución real"
 
De las 4 dimensiones con cómputo por zona, 3 de 4 (seguridad, amenidades,
walkability) requirieron al menos una corrección de datos antes de poder calcularse
correctamente — típicamente archivos con campos nulos donde debía haber datos
calculados, o joins espaciales documentados en el Acta de datos externos que nunca se
ejecutaron en código versionado. Esto se interpreta como una limitación del proceso
de control de calidad del pipeline original, no de la metodología del índice en sí:
declarar una extracción "cerrada" no garantizó que el archivo resultante fuera
consumible por el código de transformación sin intervención.
 
### 4.2 Asimetría de método entre fuentes Google Places y OSM
 
Las extracciones vía OSM Overpass traen todos los tags de amenidad de una sola
consulta por polígono — estructuralmente no pueden omitir una categoría completa de
forma independiente. Las extracciones vía Google Places se hicieron por búsqueda de
texto independiente por categoría — un método donde omitir la búsqueda de una sola
categoría (ej. "hospital") no afecta a las demás, y ese tipo de omisión resultó no
ser detectable sin comparación cruzada entre zonas. Esto generó sub-cobertura
puntual en 2 de las 3 zonas extraídas por Google Places, documentada como limitación
conocida en la sección de resultados.
 
De forma relacionada, solo los archivos OSM tenían verificación geométrica
(confirmación de que cada punto cae realmente dentro del polígono de su zona nominal)
incorporada desde el diseño original del pipeline; los archivos Google Places no la
tenían, lo que permitió que puntos geográficamente mal atribuidos (ej. amenidades de
una zona vecina, o fuera de las 9 zonas del scope) permanecieran sin detectar hasta
una auditoría posterior dedicada.
 
### 4.3 Cobertura de datos como variable de diseño, no solo de calidad
 
El propio proceso de extracción impuso límites al diseño del índice, no solo a su
precisión: la dimensión socioeconómica se eliminó porque el dato disponible no
sostenía la definición original; el componente de red vial de walkability se eliminó
porque no existía en ninguna fuente disponible del proyecto; y una zona completa
(Costa del Este) queda fuera del índice compuesto por ausencia estructural de dato
en su corregimiento contenedor. Estas tres decisiones se documentan como resultado
directo de las limitaciones reales de las fuentes de datos disponibles para Panamá,
consistente con la hipótesis de riesgo de proyecto ya identificada desde el inicio:
la disponibilidad y calidad de datos, no la sofisticación técnica, es el principal
factor limitante de REIP.
 
---
 
## 5. Trazabilidad de pesos a la Encuesta de Requerimientos
 
Todos los pesos usados en el índice (tanto entre dimensiones como entre categorías
de amenidades) están fundamentados en la Encuesta de Requerimientos propia del
proyecto (n=20), no en supuestos del equipo:
 
- **Jerarquía de dimensiones** (§2.2): seguridad como criterio #3 explícito y
  "eliminador primario" para el 40% de encuestados, sostiene su peso más alto
  (0.30 original / 0.3529 final) entre las dimensiones cuantitativas.
- **Categorías de amenidades** (§2.3): supermercado, parque y salud como los tres
  pilares de mayor demanda declarada, en ese orden — reflejado directamente en el
  orden de los pesos de la Sección 3.4.
- **Amenidades clave de walkability** (§2.3, §2.2): supermercado y parque por
  demanda directa; metro incluido por su posición en la jerarquía general de
  factores de decisión de compra.
Excepción documentada: el peso de farmacia (dentro de amenidades) no tiene respaldo
de encuesta — es la única ponderación del índice basada en un supuesto conservador
en vez de en evidencia directa, y debe presentarse así en la tesis.