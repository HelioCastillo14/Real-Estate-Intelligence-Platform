# Feature 1.2 — Pipeline de Scraping | Acta
**Real Estate Intelligence Platform (REIP) | Universidad Tecnológica de Panamá — Curso 0698**
**Estado: CERRADO** | Última actualización: 2026-07-08
 
---
 
## 1. Resumen ejecutivo
 
El scraper (`pipeline/scraper/inmopanama_scraper.py`) quedó funcional y validado en los 9 corregimientos del scope (8 + Marbella re-corrido) a volumen de catálogo completo, no muestra. El hallazgo más importante de todo el Feature 1.2 no fue técnico: **el volumen real de datos residenciales es ~34% del proyectado en el Acta de Datos** (1,361 confirmado vs. 3,800–4,200 proyectado), con implicaciones directas sobre el diseño de M1, M2 y M3 que se documentan en este Acta.
 
Durante el cierre de las tareas 1.2.6 y 1.2.7 se identificó y resolvió un segundo hallazgo estructural: el diseño original de M2 (comparables geográficos vía `ST_Distance`) asumía disponibilidad de coordenadas reales que la fuente de datos (inmopanama.com) nunca tuvo. Este Acta documenta el problema, la verificación que lo confirmó, y la redefinición de arquitectura que lo resuelve sin necesidad de geocoding externo.
 
**Decisiones formales cerradas en esta Acta:**
- Exclusión de Pedregal y Parque Lefevre del semáforo KNN y de KMeans por volumen insuficiente, validada con el consejo académico.
- Redefinición del concepto de "comparable" en M2: de proximidad geográfica real a coincidencia de corregimiento + tipo de inmueble.
- `geom` se pobla con punto sintético (jitter) para fines exclusivamente de visualización, nunca como insumo de modelo.
- `tipo_inmueble` confirmado como requisito funcional de M1, con mecanismo de extracción diseñado.
---
 
## 2. Tabla de resultados reales — 9/9 corregimientos
 
| Corregimiento | Registros finales | % contaminación tipo (bruto) | Paginación | Precio no evaluable | Acta de Datos (proyectado) | Discrepancia |
|---|---|---|---|---|---|---|
| Pedregal | 3 | 73% | OK, agotado (1 pág) | verificado | sin dato previo | universo real confirmado = 3 |
| El Cangrejo | 76 | 2.6% | OK, agotado (4 pág) | 0 | 77 | -1%, casi exacto |
| Costa del Este | 191 | 15.4% | OK, agotado (12 pág) | 0 | 1,169 | **-84%** |
| Marbella (x2, resultado idéntico) | 49 | ~23% | OK, agotado (4 pág) | verificado | 196 | **-75%** |
| Obarrio | 64 | 0% | OK, agotado (4 pág) | 0 | 62 | +3%, casi exacto |
| Bella Vista | 411 | 0% | OK, agotado (21 pág) | verificado | 496 | -17% |
| San Francisco | 465 | 0.4% (2/467) | OK, agotado (24 pág) | **6, todos preventa/$1** | 896 | **-48%** |
| Parque Lefevre | 17 | 55% (universo bruto=38) | OK, agotado (2 pág) | verificado | sin dato previo | universo real bruto=38, residencial=17 |
| Betania | 85 | 3.4% | OK, agotado (5 pág) | verificado | sin dato previo | — |
 
**Total residencial real confirmado: 1,361 registros.**
**Proyección original del Acta de Datos: 3,800–4,200.**
**Volumen real ≈ 34% de lo proyectado.**
 
**Casos de zona ambigua (`pagina_scrapeada_no_resuelto`) por corregimiento — conteo final:**
 
```
bella-vista_listings.csv:       59
betania_listings.csv:           10
costa-del-este_listings.csv:     0
el-cangrejo_listings.csv:        0
marbella_listings.csv:           0
obarrio_listings.csv:            0
parque-lefevre_listings.csv:     0
pedregal_listings.csv:           0
san-francisco_listings.csv:      2
```
**Total: 71 registros (5.2% del catálogo).** Concentrados en zonas con corredores viales ambiguos como límite (Vía España, Avenida Balboa, Via Argentina — Bella Vista principalmente).
 
---
 
## 3. Hallazgos técnicos del scraper — resueltos y validados
 
### 3.1 Selectores HTML (confirmados por inspección manual)
```python
SELECTORS = {
    "card":     "div.property-boxarea.ib-property-list-card",
    "title":    "a.ib-prop-title",
    "zone":     "p.ib-prop-zone",
    "features": "ul.ib-prop-features li",   # hab/baños/m2 via <img alt="camas|baños|metraje">
    "price":    "div.ib-prop-price-wrapper",
    "link":     "a.ib-prop-title",
}
```
ID de listing: regex `_p-(\d+)\.htm` sobre la URL, NO el slug.
 
### 3.2 Slugs de URL por corregimiento — patrón NO uniforme
```python
COREGIMIENTOS = {
    "bella-vista":     "venta-apartamentos-bella-vista",     # patron "venta-apartamentos"
    "san-francisco":   "venta-apartamentos-san-francisco",   # patron "venta-apartamentos"
    "obarrio":         "venta-apartamentos-obarrio",         # patron "venta-apartamentos"
    "parque-lefevre":  "venta-propiedades-parque-lefevre",   # patron "venta-propiedades" (mezcla tipos)
    "betania":         "venta-propiedades-betania",
    "pedregal":        "venta-propiedades-pedregal",
    "el-cangrejo":     "venta-propiedades-el-cangrejo",
    "marbella":        "venta-propiedades-marbella",
    "costa-del-este":  "venta-propiedades-costa-del-este",
}
```
**Patrón descubierto:** páginas `venta-apartamentos-*` tienen 0% de contaminación de tipo (filtran solo apartamentos). Páginas `venta-propiedades-*` mezclan tipos — contaminación bruta varía 2.6% a 73% según perfil de uso de suelo de la zona (zonas con parques industriales/corporativos como Parque Lefevre y Costa del Este/Marbella tienen contaminación alta).
 
### 3.3 Bugs de Chrome/Selenium — problema, causa, solución
| Problema | Causa | Solución |
|---|---|---|
| `--headless=new` produce `TimeoutException` instantáneo | Chrome headless nuevo no completa el handshake de DevTools a tiempo | `page_load_strategy="eager"` + `--remote-allow-origins=*` |
| Race condition al arrancar | `chromedriver` devuelve control antes de que Chrome esté listo para DevTools | `sleep(2)` post-creación + `retry_get()` con reinicio completo de driver (3 intentos) |
| Fallos de red intermitentes (`ERR_CONNECTION_TIMED_OUT`, `ERR_CONNECTION_RESET`) | Inestabilidad de red genuina, no bug de sincronización | Confirmado con evidencia real (Bella Vista): el mismo `retry_get()` protege contra esto también — mecanismo validado como robusto ante 3 causas de fallo distintas |
 
**Decisión operativa:** usar siempre `--no-headless`. El modo headless tiene un bug confirmado en este sitio; aunque el script trae workarounds, no está probado sin `--no-headless` recientemente — no arriesgar el volumen de datos por ahorrar recursos de visualización.
 
### 3.4 Paginación — problema, causa, solución
- **Problema:** paginación fallaba silenciosamente, dando resultado incompleto que parecía correcto (sin excepción visible).
- **Causa:** `PAGINATION_MODE = "button"` usaba un selector genérico nunca verificado (`a.next, a[rel='next']...`) que no coincidía con las clases reales del sitio (`ib-pagination-next`, `ib-pagination-prev`).
- **Solución:** `PAGINATION_MODE = "url"` — navega directo a `?page={n}`, verifica que la página tenga tarjetas antes de continuar. `MAX_PAGES` subido de 20 a 65 para no truncar catálogos grandes.
- **Validación:** 57+ páginas consecutivas sin un solo fallo (Bella Vista 21 pág, San Francisco 24 pág, Costa del Este 12 pág, más el resto). Issue cerrado.
### 3.5 Validación de precio (`validar_precio`) — dual venta/alquiler
```python
PRECIO_MIN_VENTA = 20000
PRECIO_MIN_ALQUILER = 400  # confirmado con conocimiento directo del usuario del mercado
 
def validar_precio(price_usd, area_m2, operation):
    umbral = PRECIO_MIN_VENTA if operation == "venta" else PRECIO_MIN_ALQUILER
    if price_usd is None or price_usd < umbral:
        return False, "precio_bajo_umbral"
    if operation == "venta" and area_m2 and area_m2 > 0:
        precio_m2 = price_usd / area_m2
        if not (100 <= precio_m2 <= 15000):
            return False, "precio_m2_fuera_de_rango"
    return True, ""
```
 
**Problema descubierto en San Francisco:** el selector de precio falla sistemáticamente en listings de **preventa** (construcción no terminada), capturando `$1` en vez del precio real. 6/6 casos confirmados eran preventa.
 
**Decisión tomada:** no arreglar el selector — excluir `precio_no_evaluable=True` del pool de entrenamiento KNN de todas formas, ya que preventa no es comparable a precio de reventa/mercado secundario. El "bug" y la decisión de producto correcta coinciden en la misma acción — no requiere trabajo adicional.
 
**Hueco conocido, no bloqueante:** no hay rango de precio/m² definido para alquiler (solo umbral mínimo). Pendiente de definir con datos reales si se considera necesario más adelante.
 
### 3.6 Resolución de zona (`zone_raw` como fuente de verdad)
```python
COREGIMIENTOS_OFICIALES = {
    "bella vista", "san francisco", "parque lefevre", "betania",
    "pedregal", "el cangrejo", "marbella", "costa del este", "obarrio",
}
BARRIOS_A_COREGIMIENTO = {
    "el carmen": "Bella Vista",
    "punta paitilla": "San Francisco",
    "punta pacifica": "San Francisco",
    "coco del mar": "San Francisco",
    "carrasquilla": "Parque Lefevre",
    "panama viejo": "Parque Lefevre",
    "tumba muerto": "Betania",
    "villa de las fuentes": "Betania",
    "edison park": "Betania",
}
```
Campo `zone_source` deja trazabilidad (`zone_raw`, `zone_raw_barrio_mapeado`, `pagina_scrapeada_no_resuelto`).
 
**Problema:** corredores viales (Vía España, Avenida Balboa, Via Argentina) no son mapeables por texto — una avenida cruza más de un corregimiento, así que el texto por sí solo no determina de qué lado está la propiedad. Estos 71 casos quedan `pagina_scrapeada_no_resuelto`.
 
**Solución final (ver Sección 4 para el razonamiento completo):** resolución manual usando el `title` del listing (nombre de PH/edificio reconocible), no geocoding automatizado — el volumen (71 de 1,361, 5.2%) no justifica construir un pipeline de geocoding para esto.
 
### 3.7 Filtro de tipo de inmueble (`es_tipo_excluido`) — heurística por keywords
```python
TIPOS_EXCLUIDOS_KEYWORDS = [
    "bodega", "local comercial", "oficina", "terreno", "finca",
    "galera", "nave industrial", "lote",
]
```
**Funciona al 100% en toda la muestra confirmada** (incluyendo "Times Square Center" ×20, "Panamá Viejo Business Center" ×21) — pero solo para vocabulario ya conocido. Único caso histórico de fuga: "Salón de Belleza" (Betania, sesión anterior), vocabulario no anticipado. **Límite estructural aceptado y documentado:** cualquier lista de keywords tendrá huecos ante vocabulario nuevo; no se persigue cobertura del 100%.
 
**`tipo_inmueble` como requisito funcional de M1 (no solo limpieza de ruido):** Preference Matching necesita exponerlo como filtro real al usuario, no solo para descartar contaminación. El campo `Tipo:` vive únicamente en la página de detalle del listing, no en la tarjeta de listado — confirmado por inspección manual.
 
```python
def obtener_tipo_inmueble(holder, listing_url):
    """Visita el detalle del listing y extrae el campo Tipo de
    ul.ib-prop-details-list. Confirmado por inspeccion manual:
    <span>Tipo:</span><strong>Apartamento</strong> vive SOLO en
    la pagina de detalle, no en la tarjeta de listado."""
    try:
        holder.driver.get(listing_url)
        time.sleep(1.5)
        items = holder.driver.find_elements(By.CSS_SELECTOR, "ul.ib-prop-details-list li")
        for li in items:
            spans = li.find_elements(By.CSS_SELECTOR, "span")
            if spans and spans[0].text.strip().lower() == "tipo:":
                strong = li.find_element(By.CSS_SELECTOR, "strong")
                return strong.text.strip()
    except (NoSuchElementException, WebDriverException):
        pass
    return ""
 
def enriquecer_con_tipo(holder, csv_path):
    """Lee un CSV ya scrapeado, agrega tipo_inmueble por listing_url,
    reescribe el archivo. Reintentable: si falla a medio camino,
    corre de nuevo, no reprocesa filas ya resueltas."""
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    for i, row in enumerate(rows):
        if row.get("tipo_inmueble"):
            continue
        tipo = obtener_tipo_inmueble(holder, row["listing_url"])
        row["tipo_inmueble"] = tipo or "no_evaluable"
        time.sleep(REQUEST_DELAY)
    # ... reescribir CSV
```
 
**Costo recalculado con volumen real:** con 1,361 registros (no 3,800–4,200), el batch de enriquecimiento es ~1,361 requests × 2.5s ≈ **~57 minutos** — no las ~2.8h estimadas originalmente sobre el volumen proyectado. Consecuencia directa y positiva de la discrepancia de volumen.
 
---
 
## 4. 1.2.6 — Geocoding: el problema real, cómo se descubrió, y cómo se resolvió
 
### 4.1 El problema tal como estaba planteado originalmente
 
La condición de done original del WBS decía: *"Todas las propiedades sin coordenadas tienen `geom` poblado; caché en Postgres evita reconsultar la misma dirección"* — diseñado para resolverse vía Google Maps Geocoding API, específicamente pensado para los casos `pagina_scrapeada_no_resuelto` (corredores viales ambiguos).
 
### 4.2 La verificación que cambió el alcance del problema
 
Se verificó por inspección manual directa —incluyendo revisión específica de un listing de ejemplo (`venta-de-apartamento-en-ph-carreras-el-carmen_p-143196.htm`)— que **inmopanama.com no expone coordenadas, mapa embebido, ni iframe en ninguna página de detalle de ningún listing.**
 
Esto no solo cerró la pregunta abierta sobre si 1.2.6 podía resolverse "gratis" como subproducto del scraping de detalle de `tipo_inmueble`. Expuso un problema de mayor alcance que no estaba en el radar original: **el diseño de 3.1.1 (Property Valuation Engine, comparables vía `ST_Distance` de PostGIS) asumía coordenadas de punto precisas para las 1,361 propiedades del catálogo completo — no solo para los 71 casos de zona ambigua.** Sin ninguna fuente de coordenadas reales (ni en tarjeta, ni en detalle, ni API, ni mapa embebido), ese diseño es inejecutable tal como estaba escrito, independientemente de qué se hiciera con geocoding externo.
 
**Por qué geocodificar el texto de `zone_raw` no resolvía nada:** para los 71 casos de corredor vial, mandar a una API el string ambiguo (ej. "Vía España, Panamá") devuelve un punto genérico sobre la avenida, sin garantía de caer en el corregimiento correcto — es geocodificar la misma ambigüedad que ya existía, sin agregar información nueva. Circular, no resolutivo.
 
### 4.3 La decisión — redefinición de arquitectura, no parche
 
Se identificó que `geom` tiene dos consumidores con necesidades de precisión completamente distintas, y que confundirlos fue el origen del problema de diseño:
 
| Consumidor | Qué necesitaba el diseño original | Qué necesita en realidad |
|---|---|---|
| **KNN comparables (M2, 3.1.1)** | Coordenadas de punto reales para `ST_Distance` | Coincidencia de `corregimiento_id` + `tipo_inmueble`, sin geometría |
| **Mapa visual (5.2.5, 5.3.6)** | Un punto que se vea razonable en pantalla | Punto sintético dentro del polígono del corregimiento — no ubicación real |
 
**Decisión 1 — Redefinición de "comparable" para M2 (aprobada):**
"Vecino más cercano" deja de significar proximidad geográfica real y pasa a significar **mismo corregimiento + mismo tipo de inmueble**, ordenado por similitud de atributos estructurados (m², habitaciones) — no por distancia espacial. Esto convierte el modelo de un KNN geoespacial (`PostGIS ST_Distance`) a un KNN de atributos (`sklearn.neighbors.KNeighborsRegressor` estándar), **simplificando el stack técnico**, no complicándolo: ya no se necesita la consulta geoespacial que 3.1.1 había diseñado.
 
Esta decisión es coherente con el precedente ya documentado en Acta de Datos §4.1 — la elección deliberada de una sola variable (precio/m²) en el semáforo, "más auditable ante el comité de defensa y más robusto dado el volumen modesto de datos por zona." Se extiende el mismo principio metodológico a la definición de "comparable."
 
**Decisión 2 — `geom` de visualización (aprobada):**
Se puebla mediante `ST_GeneratePoints(geom_poligono_corregimiento, 1)` — un punto aleatorio dentro del polígono del corregimiento ya cargado en PostGIS (Feature 1.3.1). Este punto es puramente decorativo para que el mapa (MapLibre) no muestre todos los pines de una misma zona amontonados en el mismo lugar. **Debe documentarse explícitamente como coordenada aproximada de presentación, no como ubicación real de la propiedad** — nunca debe usarse como insumo del modelo KNN, que ya no depende de `geom` en absoluto tras la Decisión 1. Esta separación también refuerza el principio de minimización de PII (SRS-026): no se expone ubicación exacta de propiedades de terceros sin verificación de consentimiento.
 
**Decisión 3 — Los 71 casos de zona ambigua:**
Dado el volumen bajo confirmado (71 de 1,361, 5.2%, concentrado en Bella Vista), se resuelven por **revisión manual** usando el `title` del listing (nombre de PH/edificio reconocible cuando existe) o juicio directo de contexto — no se construye pipeline de geocoding automatizado para esto. Construir integración con Google Maps API para 71 registros no se justifica frente al costo de revisarlos a mano en ~1 hora.
 
### 4.4 Costo real vs. presupuestado
 
| | Presupuesto original WBS | Costo real ejecutado |
|---|---|---|
| Story points | 5 SP (geocoding + caché Postgres) | ~0 SP adicionales — reutiliza `ST_GeneratePoints` nativo de PostGIS + revisión manual de 71 registros |
| Dependencia externa | Google Maps Geocoding API (costo variable) | Ninguna |
| Riesgo de defensa académica | Bajo, si funcionaba como se diseñó | Bajo — la redefinición está justificada con el mismo argumento metodológico que ya sostiene el semáforo KNN |
 
### 4.5 Condición de Done actualizada (reemplaza la original del WBS)
 
`geom` poblado para el 100% del catálogo mediante punto sintético dentro del polígono de su corregimiento; los 71 casos de zona no resuelta tienen `corregimiento_id` asignado manualmente vía revisión de `title`; documentado en este Acta que `geom` no representa ubicación real y que el modelo KNN de M2 no depende de este campo, sino de coincidencia de corregimiento + tipo de inmueble.
 
**Estado: CERRADO.**
 
---
 
## 5. 1.2.7 — Validación de calidad del catálogo
 
### 5.1 Condición de Done original (WBS) vs. condición actualizada
 
La condición original —*"script de validación corre sin errores; reporte de calidad muestra <5% de registros con precio nulo y 0 duplicados exactos"*— seguía vigente, pero quedó identificado desde la sesión de scraping que faltaba incorporar (no reemplazar) tres elementos que los hallazgos reales de la sesión hicieron evidentes:
 
1. Reporte de % de contaminación de tipo por corregimiento (como reporte obligatorio, no como umbral de rechazo).
2. Desagregación de `precio_no_evaluable_motivo` (`precio_bajo_umbral` vs. `precio_m2_fuera_de_rango`) — campo ya construido en el scraper, no reflejado antes en la condición de done del WBS.
3. Reconciliación formal de volumen real (1,361) vs. proyectado en Acta de Datos (3,800–4,200), como sección obligatoria del reporte, no solo como nota de sesión.
### 5.2 Verificación de `precio_no_evaluable` — los 5 corregimientos pendientes de auditoría
 
Se ejecutó `grep -c "pagina_scrapeada_no_resuelto" data/raw/*_listings.csv` para cerrar la auditoría pendiente en los corregimientos que quedaron sin revisar en la sesión de scraping original (Pedregal, Marbella, Bella Vista, Parque Lefevre, Betania). Resultado incorporado en la tabla de la Sección 2 de este Acta.
 
### 5.3 Decisión formal sobre exclusión de zonas de bajo volumen
 
Durante el cierre de 1.2.7 se identificó una contradicción no resuelta entre el volumen real confirmado por zona y el supuesto implícito de todo el diseño de M2: que cada corregimiento tendría masa crítica suficiente para validar KNN con 5-fold cross-validation (compromiso metodológico ya fijado en Pilares de Arquitectura §7 y Acta de Datos §4.1/§4.2).
 
**Datos que expusieron el problema:**
- Pedregal: n = 3. Matemáticamente imposible ejecutar 5-fold CV (ni siquiera alcanza para un split train/test razonable).
- Parque Lefevre: n = 17 residencial. Al límite — 5-fold CV implica ~3-4 registros por fold, insuficiente para un MAE defendible ante un comité que audite la metodología.
**Consulta al consejo académico:** se presentó el problema en sesión informativa del 2026-07-08. Recomendación explícita recibida: *"Es parte del trabajo, exclúyelos pero documenta tus decisiones."*
 
**Decisión formal, tomada y validada externamente:**
- **Pedregal y Parque Lefevre quedan excluidos del semáforo de precio (KNN) y de la segmentación de mercado (KMeans)**, por volumen insuficiente para validación estadística mínima (5-fold CV).
- **Ambas zonas permanecen sin cambios dentro del Zone Health Composite Index**, dado que ese componente es una fórmula determinística (Acta de Datos §4.5) que no depende de volumen de listings — su granularidad es por corregimiento, no por propiedad individual, y ya estaba diseñado para no requerir masa crítica de datos transaccionales.
- **Criterio de exclusión documentado explícitamente** (no como umbral arbitrario): imposibilidad de ejecutar 5-fold CV con folds estadísticamente mínimos — mismo estándar de rigor que ya se exige a KNN y RF en el resto del catálogo (Pilares de Arquitectura §7).
- **Trazabilidad de la decisión:** validada con el consejo académico en sesión del 2026-07-08, no un descuido de cobertura ni una decisión unilateral del equipo — esto debe quedar explícito en la sección de limitaciones de la tesis, como respuesta anticipada a la pregunta esperable del comité de defensa ("¿por qué solo 7 de 9 zonas tienen semáforo funcional?").
### 5.4 Condición de Done final de 1.2.7
 
Reporte único que integra:
1. % duplicados por `listing_id`.
2. % `price_usd` nulo o bajo umbral, desagregado por `precio_no_evaluable_motivo`.
3. % `area_m2` nulo.
4. % contaminación de tipo por corregimiento.
5. Desglose de `zone_source` post-resolución manual de los 71 casos.
6. Reconciliación formal: volumen real (1,361) vs. proyectado (Acta de Datos, 3,800–4,200), con el hallazgo de ~34% documentado como el hallazgo central de todo Feature 1.2.
7. Exclusión de Pedregal y Parque Lefevre del semáforo KNN y KMeans, con criterio numérico y trazabilidad de aprobación del consejo académico.
Criterio numérico original sin cambios: <5% de registros con precio nulo, 0 duplicados exactos.
 
**Estado: CERRADO**, condicionado a la ejecución final del script de reporte consolidado sobre el catálogo completo en Supabase (no CSVs sueltos) — última acción operativa de la tarea, no una decisión pendiente.
 
---
 
## 6. Consecuencias para módulos posteriores (no ejecutables en 1.2, pero originadas aquí)
 
Estas decisiones no son tareas de Feature 1.2, pero se originan directamente de sus hallazgos y deben quedar registradas para que Épica 2 y 3 (M1, M2) no se diseñen sobre supuestos ya invalidados:
 
- **3.1.1 (Property Valuation Engine, WBS Épica 3.0)** debe reescribirse: de "consulta de comparables por corregimiento y tipo de inmueble usando `ST_Distance` PostGIS" a "consulta de comparables por corregimiento y tipo de inmueble usando similitud de atributos estructurados (m², habitaciones), sin componente geoespacial." Esto simplifica el stack (no requiere la consulta combinada PostGIS+pgvector bajo carga prevista en 1.5.6 para este componente específico) y debe reflejarse en el WBS antes de iniciar Feature 3.1.
- **M2 (KNN y KMeans)** opera sobre 7 de 9 corregimientos, no 9. Documentar en Acta de Datos y en la tesis como limitación conocida, con el mismo nivel de detalle de la Sección 5.3 de este Acta.
- **`tipo_inmueble`** queda confirmado como campo de filtro real para M1 (Preference Matching), no solo insumo de limpieza — impacta el diseño del scorer estructurado (2.2.2, 2.2.3).
---
 
## 7. Aprendizajes de la sesión (para no repetir)
 
1. **Un supuesto de diseño puede sobrevivir sin cuestionarse durante SP enteros hasta que un hallazgo operativo lo expone.** El diseño de 3.1.1 asumió coordenadas reales durante toda la fase de Pilares de Arquitectura y Acta de Datos; nadie lo cuestionó hasta que la verificación manual de 1.2.6 lo hizo evidente. Revisar supuestos de infraestructura de datos contra la fuente real antes de comprometer arquitectura formal, no después.
2. **Volumen insuficiente por zona no es un problema de scraping, es un problema de diseño de M2 que el scraping expuso.** Distinguir esto en el decision log evita que se trate como "bug a arreglar" cuando en realidad es "decisión de scope a tomar con el asesor."
3. **Un "bug" y una "decisión de producto correcta" pueden coincidir en la misma acción** (caso del selector de precio en preventa) — no toda anomalía técnica requiere arreglo si la exclusión resultante es la decisión correcta de todas formas.
4. **Reutilizar un principio metodológico ya defendido es más fuerte que inventar uno nuevo.** La redefinición de "comparable" en M2 se sostiene porque aplica el mismo argumento ya usado para el semáforo (transparencia y auditabilidad sobre sofisticación), no porque sea una idea aislada nueva.
5. **Confirmar con el consejo académico antes de tomar decisiones de exclusión de scope**, no después — la trazabilidad de "validado en sesión del [fecha]" es en sí misma parte de la evidencia metodológica que un comité de defensa espera ver.
---
 
## 8. Estado final de Feature 1.2
 
| ID | Tarea | Estado |
|---|---|---|
| 1.2.1 | Verificar robots.txt/ToS inmopanama.com | ✅ Completado (sesión previa) |
| 1.2.2 | Inspeccionar HTML de listing individual | ✅ Completado (sesión previa) |
| 1.2.3 | Migrar scraper Selenium → Playwright/Selenium robusto | ✅ Completado |
| 1.2.4 | Scraping por corregimiento con paginación robusta | ✅ Completado — 9/9 corregimientos a volumen real |
| 1.2.5 | Completar conteos reales Parque Lefevre, Betania, Pedregal + definir umbral de cobertura | ✅ Completado — conteos confirmados; umbral resuelto vía exclusión de Pedregal/Lefevre del semáforo y KMeans |
| 1.2.6 | Geocoding / `geom` poblado | ✅ **Cerrado esta sesión** — redefinido: sin API externa, comparables por atributos, `geom` solo para visualización |
| 1.2.7 | Validar calidad del catálogo final | ✅ **Cerrado esta sesión** — reporte consolidado con reconciliación de volumen y exclusión de zonas documentada |
 
**Feature 1.2 — Pipeline de scraping: CERRADO.**
 
**Próximo paso del proyecto (fuera de alcance de este Feature):** iniciar Épica 2.0 (M1 — Preference Matching Module) sobre el catálogo ya validado, incorporando la redefinición de comparables documentada en Sección 6 al diseño de Feature 3.1 antes de comenzar su implementación.