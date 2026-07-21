# Feature 1.3 — Carga de Datos Externos | Acta
**Real Estate Intelligence Platform (REIP) | Universidad Tecnológica de Panamá — Curso 0698**
**Estado: EXTRACCIÓN Y CÓMPUTO CERRADOS — Carga a Supabase pendiente de Feature 1.5** | Última actualización: 2026-07-09
 
---
 
## 1. Resumen ejecutivo
 
Se completó la extracción, verificación y cómputo de las 6 fuentes de enriquecimiento de zona que exige Feature 1.3 (Acta de Datos §2.2): polígonos administrativos, amenidades, Metro de Panamá, paradas de bus MiBus (GTFS), homicidios SIEC y población INEC. Las 9 zonas del scope quedan cubiertas, con 5 de ellas respaldadas por corregimiento administrativo real y 4 (El Cangrejo, Marbella, Obarrio, Costa del Este) resueltas mediante herencia documentada, tras confirmarse que no son corregimientos oficiales.
 
**El hallazgo transversal de todo este Feature no fue de disponibilidad de datos, sino de contaminación por homónimos** — geográficos (topónimos repetidos globalmente vía OpenStreetMap) y administrativos (el mismo nombre de corregimiento existiendo en distintas provincias/distritos de Panamá, confirmado independientemente en tres fuentes distintas: OSM, SIEC e INEC). El método que resuelve este problema de forma consistente — verificación por relation ID o área calificada con "Distrito de Panamá" antes de ejecutar cualquier consulta completa — se estableció en la Sección 4 de este Acta y se aplicó de ahí en adelante sin excepción.
 
**Segundo hallazgo transversal:** el WBS no declara la dependencia real entre Feature 1.3 y Feature 1.5 (esquema de base de datos). Las condiciones de done de 1.3.2, 1.3.3, 1.3.5, 1.3.6 y 1.3.7 exigen "carga en Supabase/PostGIS", pero ninguna depende formalmente de 1.5.1-1.5.5 en el documento. Se decidió, por criterio del equipo, dejar la extracción y el cómputo completos y trasladar la carga física a Feature 1.5, documentado explícitamente en cada sub-feature.
 
---
 
## 2. Estado por sub-feature
 
| Sub-feature | Extracción | Cómputo/Verificación | Carga a Supabase |
|---|---|---|---|
| 1.3.1 — Polígonos de corregimientos | ✅ | ✅ Geometría válida (`ST_IsValid` vía `shapely`) | ⏳ Pendiente de 1.5.2 |
| 1.3.2 — Metro de Panamá | ✅ | ✅ 30/30 estaciones, sin geocoding necesario | ⏳ Pendiente de 1.5.3 |
| 1.3.3 — GTFS MiBus | ✅ | ✅ 1,150 paradas, cruzadas contra polígonos reales | ⏳ Pendiente de 1.5.3 |
| 1.3.4 — Spike SIEC | ✅ | ✅ Cerrado — no requiere carga (es un spike de viabilidad) | N/A |
| 1.3.5 — Homicidios SIEC | ✅ | ✅ Tasa real calculada (no solo conteo crudo) | ⏳ Pendiente de 1.5.2 |
| 1.3.6 — Población INEC | ✅ | ✅ Reducido a Opción 1 (población/densidad) | ⏳ Pendiente de 1.5.2 |
| 1.3.7 — Amenidades | ✅ | ✅ 9 zonas, taxonomía normalizada | ⏳ Pendiente de 1.5.3 |
 
---
 
## 3. Fuentes de datos utilizadas, por sub-feature
 
| Sub-feature | Fuente | Método de acceso |
|---|---|---|
| 1.3.1 | OpenStreetMap (Overpass API) | `relation(id); out geom;` — 5 corregimientos con relation ID verificado |
| 1.3.2 | `datosabiertos.gob.pa` (vía CSV oficial proporcionado por el usuario) | Coordenadas directas, sin geocoding |
| 1.3.3 | `github.com/merlos/panatrans-dataset` (GTFS, comunidad, KML MiBus 2016) | `git clone` directo del repositorio |
| 1.3.4 / 1.3.5 | SIEC — Informe de Criminalidad 2023 (Cuadro N°13) + 12 Ejecutivos Semanales/Mensuales 2025 | PDF proporcionado por el usuario, extracción con Camelot |
| 1.3.6 | INEC — XII Censo Nacional de Población y VIII de Vivienda 2023 (Cuadro N°10) | XLS oficial proporcionado por el usuario |
| 1.3.7 | Google Places (extracción manual previa) + OpenStreetMap (Overpass API) | JSONL manual (Google) + consultas Overpass verificadas por polígono |
 
---
 
## 4. Método establecido para evitar contaminación por homónimos — aplicado desde la mitad del Feature en adelante
 
### 4.1 El problema, con evidencia cuantificada
 
Una primera consulta combinada (búsqueda por nombre sin desambiguar) devolvió, de 297 resultados, **92 (31%) fuera de Panamá** — en España, Colombia, Cuba, Ecuador, Indonesia, Brasil y Estados Unidos. Una segunda iteración, ya con `{{geocodeArea}}` calificado solo con el país, también falló por homónimos **dentro** de Panamá (existe un Distrito de San Francisco en Veraguas, distinto al corregimiento de Ciudad de Panamá).
 
Este mismo patrón de homónimo administrativo interno se confirmó, de forma independiente, en **tres fuentes distintas**:
- **OSM:** San Francisco (Veraguas) y Pedregal (David, Chiriquí).
- **SIEC:** Pedregal (Boquerón y David, Chiriquí) coexiste en el mismo Cuadro N°13 con Pedregal (Distrito de Panamá).
- **INEC:** el mismo Pedregal aparece 3 veces en el Cuadro N°10 (Boquerón, David, Distrito de Panamá) con poblaciones muy distintas (2,627 / 17,078 / 57,682).
### 4.2 El método final, validado
 
1. **Verificar antes de ejecutar completo:** correr primero `{{geocodeArea:X}}->.a; .a out;` o `relation(id); out;` en aislado, confirmar `official_name` y que el contexto administrativo (`admin_level`, distrito/provincia) sea el correcto, **antes** de correr cualquier consulta de extracción completa.
2. **Calificar el texto de búsqueda con el nivel administrativo exacto** (`"X, Distrito de Panamá, Panamá"`) cuando se usa `{{geocodeArea}}`.
3. **Usar relation ID / area ID numérico directo** cuando ya esté verificado, en vez de repetir búsquedas por nombre.
4. **Para barrios sin polígono propio** (El Cangrejo, Marbella): anidar `node["name"=X](area.padre_verificado)` dentro del polígono ya confirmado del corregimiento contenedor.
5. **Para zonas cerca de un límite administrativo** (Costa del Este/Parque Lefevre): combinar radio y polígono con doble filtro `(around:N)(area.padre)`, aceptando que esto puede reducir recall frente a otra fuente más confiable si existe.
---
 
## 5. Hallazgo estructural — 4 de 9 zonas no son corregimientos oficiales
 
Confirmado vía Wikipedia, Wikidata y registros del Municipio de Panamá: **El Cangrejo, Marbella y Obarrio son barrios dentro del corregimiento de Bella Vista**; **Costa del Este es una zona de desarrollo dentro del corregimiento de Juan Díaz** (corregimiento fuera del scope original de 9 zonas). Esto se confirmó también visualmente al superponer el polígono real de Parque Lefevre contra la ubicación de Costa del Este — una porción del territorio popularmente llamado "Costa del Este" cae administrativamente en Parque Lefevre, no en Juan Díaz.
 
**Decisión final (no reversible sin nueva discusión de equipo):** las 4 zonas no reciben polígono propio en `corregimientos.geom`, ni fila propia en dimensiones dependientes de corregimiento oficial (seguridad, socioeconómico). Heredan íntegramente los valores de su corregimiento contenedor (Bella Vista o Juan Díaz) en las 5 dimensiones del Zone Health Index. Documentado como limitación real de granularidad administrativa panameña, no como atajo de conveniencia.
 
---
 
## 6. Scripts y métodos utilizados
 
### 6.1 Overpass QL (1.3.1, 1.3.3 parcial, 1.3.7)
```
[out:json][timeout:120];
(
  relation(11385188);   // Betania
  relation(11378457);   // Pedregal
  relation(11380922);   // Parque Lefevre
  relation(11381324);   // Bella Vista
  relation(11381034);   // San Francisco
);
out geom;
```
Relation/Area IDs verificados y usados en todo el Feature:
 
| Zona | ID | Tipo |
|---|---|---|
| Betania | 11385188 | relation |
| Pedregal | 11378457 | relation |
| Parque Lefevre | 11380922 | relation |
| Bella Vista | 11381324 | relation |
| San Francisco | 11381034 | relation |
| Obarrio | 505188334 | way |
| Juan Díaz (referencia, sin polígono propio cargado) | 3611378663 | area derivada |
 
### 6.2 Python — validación geométrica (1.3.1)
`shapely` para confirmar `is_valid` y tipo de geometría de los 5 polígonos exportados (`Polygon`/`MultiPolygon`). Se detectó que San Francisco exporta como `MultiPolygon` con 3 fragmentos menores al 1% del área total (artefactos de digitalización de OSM, no exclaves reales) — documentado, no corregido, para mantener fidelidad a la fuente.
 
### 6.3 Python — cruce espacial (1.3.3)
`shapely.geometry.Point().contains()` para asignar `corregimiento_id` a las 1,150 paradas GTFS contra los 5 polígonos verificados. Campo `dentro_scope_reip_confirmado` (booleano) para separar paradas dentro del scope de las que caen en otras zonas de la ciudad.
 
### 6.4 Camelot (1.3.4, 1.3.5)
```python
camelot.read_pdf('archivo.pdf', pages='N', flavor='stream')
```
**Hallazgo del spike:** `flavor='lattice'` falla en los PDF de SIEC (no tienen bordes de celda dibujados) — captura solo 3 de 41 filas. `flavor='stream'` extrae la tabla completa con 100% de accuracy (métrica propia de Camelot). Fijado como estándar para cualquier extracción futura de SIEC.
 
### 6.5 Pandas (1.3.6)
Lectura de `Cuadro N°10` (INEC, formato `.xls`, estructura jerárquica no tabular estándar — provincia/distrito/corregimiento en columnas separadas, requiere reconstrucción de contexto por fila hacia atrás para desambiguar homónimos).
 
---
 
## 7. Documentos y archivos producidos
 
Organizados en `pipeline/data/external/` (ver estructura acordada), tras descartar 8 de 18 archivos GeoJSON generados durante el proceso (contaminados, duplicados exactos, o superados por una fuente mejor):
 
```
pipeline/data/external/
├── amenidades/
│   ├── amenidades_bella_vista_google_places.jsonl
│   ├── amenidades_san_francisco_google_places.jsonl
│   ├── amenidades_costa_del_este_google_places.jsonl
│   ├── amenidades_betania_y_barrios_bellavista_osm.geojson
│   ├── amenidades_pedregal_osm.geojson
│   └── amenidades_parque_lefevre_osm.geojson
├── corregimientos/
│   └── corregimientos_poligonos_administrativos_osm.geojson
├── metro/
│   ├── metro_linea1_oficial_raw.csv
│   ├── metro_linea2_oficial_raw.csv
│   └── metro_estaciones_final_30.jsonl
├── gtfs/
│   └── paradas_mibus_gtfs.jsonl
├── seguridad/
│   └── seguridad_homicidios_2023.jsonl
└── socioeconomico/
    └── inec_poblacion_densidad_2023.jsonl
```
 
**Acción pendiente del usuario, no ejecutada en esta sesión:** agregar excepción en `.gitignore` para `pipeline/data/external/**/*.geojson`, `*.jsonl`, `*.csv` — la excepción actual documentada en `context_log_scraping.md` §7 solo cubre `pipeline/data/raw/`.
 
---
 
## 8. Decisiones técnicas y documentativas — registro completo
 
| # | Decisión | Sub-feature | Justificación |
|---|---|---|---|
| 1 | Taxonomía de amenidades congelada en 6 categorías (`supermercado`, `farmacia`, `hospital`, `clinica`, `parque`, `colegio`), con `hospital`+`clinica` normalizados a `salud` en EDA | 1.3.7 | Taxonomías inconsistentes entre corridas iniciales impedían comparar zonas |
| 2 | Costa del Este: Google Places como fuente canónica, OSM descartado | 1.3.7 | El filtro de polígono necesario para eliminar fuga hacia Parque Lefevre redujo el conteo por debajo del ya verificado con Google Places (recall insuficiente) |
| 3 | Bella Vista y San Francisco: Google Places como fuente canónica, OSM descartado | 1.3.7 | Ya existía extracción manual verificada con metadata rica (teléfono, rating); evitar redundancia sin criterio |
| 4 | Pedregal excluido de la visualización del Zone Health Index | 1.3.7 | 12 POIs vs. promedio de 32-52 en el resto de zonas — no comparable ni defendible como score numérico |
| 5 | Metro: dataset oficial (`datosabiertos.gob.pa`) en vez de OSM | 1.3.2 | OSM solo cubría 18 de 30 estaciones reales, incluso ampliando el bounding box |
| 6 | GTFS MiBus: se preserva el archivo completo (1,150 paradas) con bandera de scope, no se descarta nada silenciosamente | 1.3.3 | Transparencia — permite auditar qué se cargó y qué no |
| 7 | Año de referencia para seguridad: 2023 (no 2024/2025) | 1.3.5 | No existen reportes anuales completos de SIEC para 2024/2025; los mensuales disponibles solo cubren ~30 corregimientos de mayor incidencia, insuficiente para las 9 zonas del scope |
| 8 | Dimensión socioeconómica reducida a población/densidad (Opción 1) | 1.3.6 | Alfabetización y composición de hogares no están disponibles a nivel de corregimiento en el Censo 2023 — solo a nivel de provincia |
| 9 | `tasa_por_100k` calculada como homicidios/población real, no usado el conteo crudo | 1.3.5 + 1.3.6 | El conteo crudo cambia el ranking de riesgo relativo entre zonas (Pedregal parecía la más peligrosa por conteo; Parque Lefevre resulta la de mayor tasa real, 21.01 vs. 15.60) |
| 10 | El Cangrejo, Marbella, Obarrio, Costa del Este: sin polígono propio, herencia total de corregimiento contenedor | 1.3.1 / 1.3.7 | Confirmado que no son corregimientos oficiales; forzar un polígono aproximado sería menos defendible que la limitación documentada |
| 11 | Carga física a Supabase trasladada a Feature 1.5 | Todas | Dependencia real no declarada en el WBS; extracción y cómputo no dependen de que la tabla exista, la carga sí |
 
---
 
## 9. Resultados numéricos clave (referencia rápida)
 
| Corregimiento | Homicidios 2023 | Población 2023 | Tasa /100k | Amenidades (POIs) | Paradas MiBus |
|---|---|---|---|---|---|
| Bella Vista | 5 | 33,710 | 14.83 | (Google Places) | 44 |
| Betania | 2 | 42,199 | 4.74 | (OSM, en archivo combinado) | 62 |
| Parque Lefevre | 9 | 42,832 | **21.01** | 52 | 44 |
| Pedregal | 9 | 57,682 | 15.60 | **12 — excluido de Zone Health** | 48 |
| San Francisco | 2 | 61,290 | 3.26 | (Google Places) | 49 |
| El Cangrejo / Marbella / Obarrio | — | — | hereda Bella Vista | (OSM, en archivo combinado) | incluidas en Bella Vista |
| Costa del Este | — | — | hereda Juan Díaz | (Google Places) | sin resolver (Juan Díaz sin polígono cargado) |
 
---
 
## 10. Aprendizajes de la sesión
 
1. **Un mismo tipo de error (homónimo administrativo interno) se repitió en 3 fuentes independientes** (OSM, SIEC, INEC). Una vez identificado el patrón en la primera fuente, verificar por contexto administrativo (no solo por nombre) se volvió el primer paso obligatorio en cada fuente nueva — y en los 3 casos, encontró el mismo tipo de problema antes de que contaminara el resultado final.
2. **Corregir contaminación geográfica puede costar recall real**, no solo ruido (caso Costa del Este). La solución correcta no siempre es "ajustar más el filtro" — a veces es reconocer que ya existe una fuente superior y dejar de insistir con la débil.
3. **Un conteo crudo y una tasa real pueden invertir el ranking de riesgo entre zonas.** Cargar el número equivocado no es solo impreciso — puede llevar a una conclusión sustantivamente distinta (Pedregal vs. Parque Lefevre como zona de mayor riesgo).
4. **El WBS puede tener dependencias reales no declaradas.** La falta de dependencia formal entre 1.3.x y 1.5.x no significa que la ejecución pueda ignorar el orden lógico real (no se puede insertar en una tabla que no existe). Vale la pena auditar el grafo de dependencias del WBS contra la lógica de ejecución antes de asumir que el orden numérico es el orden real.
5. **La estructura administrativa de un territorio es un supuesto de diseño, no un detalle de implementación.** El hallazgo de que 4 de 9 zonas no son corregimientos oficiales se originó únicamente porque las consultas de polígono fallaban de forma persistente — un fallo operativo que expuso un supuesto no cuestionado desde la fase de Pilares de Arquitectura.
6. **Verificar antes de escalar es el control de calidad más barato disponible.** Cada vez que se corrió una verificación aislada antes de la consulta completa (patrón establecido en la Sección 4), se detectó o se descartó un problema en segundos, evitando reprocesar consultas completas contaminadas.
---
 
## 11. Estado final de Feature 1.3
 
**Feature 1.3 — Carga de datos externos: EXTRACCIÓN, VERIFICACIÓN Y CÓMPUTO CERRADOS.**
 
**Pendiente, fuera del alcance de este Feature:** carga física de los 7 archivos listados en la Sección 7 a las tablas correspondientes de Supabase (`corregimientos`, `amenidades`, `scores_valuacion` o tabla auxiliar según corresponda), una vez resuelto Feature 1.5 (Esquema de base de datos). La decisión de arquitectura híbrida para las 4 zonas sin polígono propio (Sección 5) ya está cerrada y debe reflejarse en el diseño de esquema de 1.5.2/1.5.3, no requiere nueva discusión.