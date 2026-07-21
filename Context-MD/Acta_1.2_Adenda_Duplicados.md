# Feature 1.2 — Pipeline de Scraping | Adenda: duplicados cross-file

**Fecha:** 2026-07-13
**Origen:** Notebook 6.2.1 (EDA general del catálogo residencial, Feature 6.2)
**Relación con el Acta original:** esta adenda **no reemplaza ni reescribe**
`Feature 1.2 — Pipeline de scraping _ Acta.md` (Estado: CERRADO, última actualización 2026-07-08).
El Acta original queda intacta como registro histórico de lo que se sabía al cierre de Feature 1.2.
Esta adenda documenta un hallazgo posterior, encontrado al consolidar los 9 archivos de
`pipeline/data/raw/` en un solo dataset para Notebook 0 (6.2.1) — algo que Feature 1.2 no hizo
porque cada corregimiento se validó como archivo independiente, no como catálogo unificado.

---

## 1. Hallazgo

Al consolidar los 9 `*_listings.csv` en un único DataFrame, `1,361` filas contienen **184
`listing_id` duplicados**, todos cross-file (0 dentro de un mismo archivo). Se agrupan en
exactamente 3 combinaciones de archivos, sin residuo:

| Combinación de archivos | IDs duplicados |
|---|---|
| `bella-vista_listings.csv` × `el-cangrejo_listings.csv` | 71 |
| `bella-vista_listings.csv` × `obarrio_listings.csv` | 64 |
| `bella-vista_listings.csv` × `marbella_listings.csv` | 49 |
| **Total** | **184** |

Verificado con código en Notebook 0, sección 4.1.

## 2. Causa raíz

El Cangrejo, Marbella y Obarrio son las 3 zonas del scope que **no tienen `geom` propio** y
heredan Zone Health de Bella Vista (`CLAUDE.md`, sección "Zonas del scope"). Consistente con eso,
la página de categoría `venta-apartamentos-bella-vista` de inmopanama.com incluye las mismas
propiedades que aparecen en las páginas dedicadas `venta-propiedades-el-cangrejo`,
`venta-propiedades-obarrio` y `venta-propiedades-marbella` — el scraper capturó el mismo listing
físico dos veces, una por cada página de categoría que lo lista.

**Verificado, no asumido:**
- El `zone` resuelto coincide en el 100% de los 184 casos (0 conflictos) — ninguna copia quedó con
  una zona distinta a su par.
- Muestra verificada manualmente (`listing_id=143139`): título, precio, `price_raw`, `area_m2`,
  `bedrooms`, `bathrooms` y `listing_url` idénticos entre ambas copias — solo difieren
  `corregimiento_archivo` y `scraped_at`. Confirma que es el mismo listing, no una colisión de
  esquema de ID.

**Nota — no confundir con el "Marbella x2" del Acta original (§2, fila de la tabla):** el Acta
documenta que Marbella *se corrió dos veces con resultado idéntico* como verificación de
reproducibilidad del scraper (49 registros ambas corridas, consolidados en un único archivo). Ese
es un fenómeno distinto: una re-ejecución de la *misma* página de categoría dando el mismo
resultado. El hallazgo de esta adenda es un **solapamiento entre páginas de categoría distintas**
(Bella Vista vs. El Cangrejo/Obarrio/Marbella) — no tiene relación con esa nota del Acta original.

## 3. Impacto en volumen por zona (verificado, no distorsiona Bella Vista)

- Los 184 registros eliminados por deduplicación **salen exclusivamente** de
  `el-cangrejo_listings.csv` (71), `obarrio_listings.csv` (64) y `marbella_listings.csv` (49).
  **Cero** salen de `bella-vista_listings.csv` (permanece en 411 filas / 159 con
  `zone_raw == "Bella Vista"`, sin cambio antes/después del dedup).
- Volumen post-dedup por zona afectada: El Cangrejo 147→76, Obarrio 128→64, Marbella 98→49 (usando
  `zone` resuelto, antes de excluir `precio_no_evaluable`). Las tres quedan muy por encima de
  Pedregal (3) y Parque Lefevre (17) — el umbral real de exclusión de KNN/KMeans ya cerrado en el
  Acta original (§5.3). Ninguna de las tres queda en riesgo de esa misma exclusión por este hallazgo.

## 4. Cifra operativa actualizada

**1,361 → 1,177** registros para todo trabajo de modelado desde este punto en adelante
(6.2.3, 6.2.4, 6.2.5): 1,361 originales − 184 duplicados cross-file. La columna `precio_no_evaluable`
(14 filas) se mantiene como flag, no se descuenta de esta cifra — su exclusión del pool de
entrenamiento es decisión de cada notebook consumidor, no del dataset maestro.

`1,361` sigue siendo la cifra correcta y vigente para todo lo que el Acta original de Feature 1.2
ya cerró (validación de scraping, reconciliación de volumen 34% vs. proyectado, exclusión de
Pedregal/Parque Lefevre) — esos hallazgos no cambian. `1,177` es la cifra operativa nueva,
específica para el dataset consolidado que consumen los notebooks de Feature 6.2 en adelante.

## 5. Trazabilidad

Investigación completa, con código ejecutable, en `notebooks/00_eda_catalogo_residencial.ipynb`,
sección 4.1.

---

## 6. Adenda 2 (2026-07-13, misma sesión) — normalización de `corregimiento` y resolución de los 71 casos de zona ambigua

Al inspeccionar los valores únicos de la columna `corregimiento` del dataset consolidado
encontramos dos problemas adicionales, no relacionados con los duplicados cross-file de la
Sección 1-4 de esta adenda.

### 6.1 Normalización de casing — corrección directa

`"Costa Del Este"` (191 filas, único valor presente para esa zona en el catálogo) no coincidía con
la clave canónica `"Costa del Este"` que usa Zone Health (`pipeline/zone_health/composite_zone_health.py:75`,
`ZONA_SIN_SCORE = "Costa del Este"`, y las 9 claves del JSON `zone_health_composite_1_4_6.json`).
Sin esta normalización, cualquier join/groupby entre el catálogo y Zone Health habría descartado
silenciosamente las 191 filas de Costa del Este. Aplicada en Notebook 0, sección 4.3.

### 6.2 Los 71 casos de zona ambigua — resolución nunca ejecutada pese a que el Acta la da por cerrada

El Acta de Feature 1.2, §4.3 y §4.5, describe la resolución manual de los 71 registros con
`zone_source == "pagina_scrapeada_no_resuelto"` (vía nombre de PH/edificio en el título) como parte
de la condición de done ya cerrada de 1.2.6. **Buscamos evidencia de esa ejecución en todo el
historial de git** (`git log --all`, diffs de `inmopanama_scraper.py`, historial de archivo de
`bella-vista_listings.csv`) **y no encontramos ningún commit, script o archivo que la implemente.**
`bella-vista_listings.csv` solo fue tocado por el commit de scraping inicial y un re-scrape de
volumen — ninguno es una resolución manual de zona. Los 71 registros siguen, en los archivos
`pipeline/data/raw/*.csv` actuales, con el slug de página en minúscula (`bella-vista`,
`san-francisco`, `betania`) como valor de `zone`. **Mismo patrón de trazabilidad ya identificado con
`tipo_inmueble`: una decisión que el Acta da por hecha, sin implementación verificable.**

### 6.3 Metodología de resolución aplicada esta sesión

Clasificamos los 71 casos en dos niveles de confianza, verificables dentro del propio catálogo (sin
conocimiento externo del mercado panameño):

- **Alta confianza — título literal (15 casos):** el nombre de un corregimiento oficial aparece
  explícitamente en el título del listing (ej. *"...Avenida Balboa, Bella Vista"*, *"...Dos Mares,
  Betania"*).
- **Alta confianza — cross-referencia interna (3 casos):** el nombre de PH/edificio del título
  coincide con otros listings del catálogo que ya tienen zona resuelta de forma consistente (sin
  conflicto entre referencias):
  - **PH Condesa del Mar** → Bella Vista (3 referencias consistentes en el catálogo)
  - **PH Rivage** → Bella Vista (4 referencias consistentes)
  - **PH Mirador del Golf** → San Francisco (referencia directa con `zone_raw = "San Francisco"`)

**Total resueltos en alta confianza: 18 / 71.**

**Casos descartados de resolución automática por señal contradictoria o insuficiente** (quedan en
la lista de pendientes, no se resolvieron "a medias"):
- **PH Torres de Castilla:** aparece en el catálogo resuelto tanto a Bella Vista como a Parque
  Lefevre (Carrasquilla) en registros distintos — nombre no unívoco, posible colisión entre dos
  edificios distintos con nombre similar. No resuelto.
- **PH Metro Towers:** una sola referencia resuelta (Parque Lefevre, vía Carrasquilla), nombre
  genérico, sin segunda confirmación independiente. No resuelto.
- **PH The Edge:** una sola referencia resuelta cuyo propio título contiene la palabra "marbella"
  de forma ambigua (`"Se vende apartamento en The edge marbella"`, con `zone_raw = "Bella Vista"`)
  — señal internamente contradictoria. No resuelto.
- Todos los demás candidatos de PH (Plaza Valencia/Valencia Plaza, PH Destiny, PH The Sands, PH San
  Roque, PH YOO, PH Belle View) no tuvieron ninguna coincidencia en el resto del catálogo. No
  resueltos.

### 6.4 Los 53 casos pendientes — lista completa para revisión manual

Quedan marcados como `corregimiento = "zona_no_determinada"` en
`catalogo_residencial_limpio_6_2_1.csv` — **no se excluyen del catálogo, pero no se asignan a
ninguna zona por inferencia.** Ningún notebook de Feature 6.2 debe agruparlos por corregimiento
hasta que se resuelvan.

| listing_id | archivo de origen | zone_raw | título | URL |
|---|---|---|---|---|
| 136780 | bella-vista | Avenida Balboa | Apartamento en Venta  Avenida Balboa | https://www.inmopanama.com/apartamento-en-venta-avenida-balboa_p-136780.htm |
| 136317 | bella-vista | Avenida Balboa | Apartamento en venta en Avenida Balboa, Panamá | https://www.inmopanama.com/apartamento-en-venta-en-avenida-balboa-panama_p-136317.htm |
| 135942 | bella-vista | Avenida Balboa | Penthouse en Venta en Avenida Balboa | https://www.inmopanama.com/penthouse-en-venta-en-avenida-balboa_p-135942.htm |
| 143394 | bella-vista | Vía España | Apartamento en Venta Vía Argentina | https://www.inmopanama.com/apartamento-en-venta-via-argentina_p-143394.htm |
| 136783 | bella-vista | Vía España | Venta de Apartamento en PH Plaza Valencia, Vía España, Panamá | https://www.inmopanama.com/venta-de-apartamento-en-ph-plaza-valencia-via-espana-panama_p-136783.htm |
| 143401 | bella-vista | Vía España | Apartamento en Venta Vía Argentina | https://www.inmopanama.com/apartamento-en-venta-via-argentina_p-143401.htm |
| 143400 | bella-vista | Vía España | Apartamento en Venta Vía Argentina | https://www.inmopanama.com/apartamento-en-venta-via-argentina_p-143400.htm |
| 143399 | bella-vista | Vía España | Apartamento en Venta Vía Argentina | https://www.inmopanama.com/apartamento-en-venta-via-argentina_p-143399.htm |
| 143392 | bella-vista | Vía España | Apartamento en Venta Vía Argentina | https://www.inmopanama.com/apartamento-en-venta-via-argentina_p-143392.htm |
| 143393 | bella-vista | Vía España | Apartamento en Venta Vía Argentina | https://www.inmopanama.com/apartamento-en-venta-via-argentina_p-143393.htm |
| 136770 | bella-vista | Vía España | Venta apartamento PH Plaza Valencia,Via España | https://www.inmopanama.com/venta-apartamento-ph-plaza-valencia-via-espana_p-136770.htm |
| 140887 | bella-vista | La Cresta | Apartamento nuevo en venta en La Cresta | https://www.inmopanama.com/apartamento-nuevo-en-venta-en-la-cresta_p-140887.htm |
| 140888 | bella-vista | La Cresta | Apartamento nuevo en venta en La Cresta | https://www.inmopanama.com/apartamento-nuevo-en-venta-en-la-cresta_p-140888.htm |
| 140889 | bella-vista | La Cresta | Apartamento nuevo en venta en La Cresta | https://www.inmopanama.com/apartamento-nuevo-en-venta-en-la-cresta_p-140889.htm |
| 140987 | bella-vista | Calle 50 | Apartamento en venta, Calle 50 | https://www.inmopanama.com/apartamento-en-venta-calle-50_p-140987.htm |
| 142102 | bella-vista | La Cresta | Apartamento nuevo en venta en La Cresta | https://www.inmopanama.com/apartamento-nuevo-en-venta-en-la-cresta_p-142102.htm |
| 142103 | bella-vista | La Cresta | Apartamento nuevo en venta en La Cresta | https://www.inmopanama.com/apartamento-nuevo-en-venta-en-la-cresta_p-142103.htm |
| 142104 | bella-vista | La Cresta | Apartamento nuevo en venta en La Cresta | https://www.inmopanama.com/apartamento-nuevo-en-venta-en-la-cresta_p-142104.htm |
| 142207 | bella-vista | Calle 50 | Apartamento en venta, Calle 50 | https://www.inmopanama.com/apartamento-en-venta-calle-50_p-142207.htm |
| 143426 | bella-vista | Avenida Balboa | Apartamento en venta Av Balboa - PH Destiny | https://www.inmopanama.com/apartamento-en-venta-av-balboa-ph-destiny_p-143426.htm |
| 143420 | bella-vista | Vía España | Apartamento en Venta en Via España - PH Torres de Castilla | https://www.inmopanama.com/apartamento-en-venta-en-via-espana-ph-torres-de-castilla_p-143420.htm |
| 143414 | bella-vista | Vía España | Apartamento en venta PH Plaza Valencia - Via España | https://www.inmopanama.com/apartamento-en-venta-ph-plaza-valencia-via-espana_p-143414.htm |
| 143413 | bella-vista | Vía España | Venta de apartamento en PH Valencia Plaza | https://www.inmopanama.com/venta-de-apartamento-en-ph-valencia-plaza_p-143413.htm |
| 143307 | bella-vista | Via Argentina | Venta de Apartamento en Via Argentina, Panamá | https://www.inmopanama.com/venta-de-apartamento-en-via-argentina-panama_p-143307.htm |
| 143411 | bella-vista | Vía España | Vía España Apartamento en venta | https://www.inmopanama.com/via-espana-apartamento-en-venta_p-143411.htm |
| 142805 | bella-vista | Vista Hermosa | Apartamento en venta PH Plaza Valencia - Via España | https://www.inmopanama.com/apartamento-en-venta-ph-plaza-valencia-via-espana_p-142805.htm |
| 143409 | bella-vista | Vía España | Venta de apartamento en PH Metro Towers | https://www.inmopanama.com/venta-de-apartamento-en-ph-metro-towers_p-143409.htm |
| 143407 | bella-vista | Vía España | Venta de apartamento en PH Valencia Plaza | https://www.inmopanama.com/venta-de-apartamento-en-ph-valencia-plaza_p-143407.htm |
| 143406 | bella-vista | Vía España | Venta Apartamento amoblado en PH San Roque, Via España | https://www.inmopanama.com/venta-apartamento-amoblado-en-ph-san-roque-via-espana_p-143406.htm |
| 139881 | bella-vista | Vista Hermosa | Se Vende apartamento en Vista Hermosa. | https://www.inmopanama.com/se-vende-apartamento-en-vista-hermosa_p-139881.htm |
| 136721 | bella-vista | Avenida Balboa | Venta de apartamento en avenida balboa | https://www.inmopanama.com/venta-de-apartamento-en-avenida-balboa_p-136721.htm |
| 136309 | bella-vista | Avenida Balboa | Se vende apartamento en Avenida Balboa, Panamá | https://www.inmopanama.com/se-vende-apartamento-en-avenida-balboa-panama_p-136309.htm |
| 143042 | bella-vista | Avenida Balboa | VENTA DE APARTAMENTO EN SKY AVE BALBOA | https://www.inmopanama.com/venta-de-apartamento-en-sky-ave-balboa_p-143042.htm |
| 138305 | bella-vista | Avenida Balboa | Hermoso Apartamento con Vista al Mar en Venta/Beautiful Apartment for ... | https://www.inmopanama.com/hermoso-apartamento-con-vista-al-mar-en-venta-beautiful-apartment-for-sale-with-ocean-view_p-138305.htm |
| 136558 | bella-vista | Avenida Balboa | Venta de apartamentos, PH The Sands, Avenida Balboa, Panamá | https://www.inmopanama.com/venta-de-apartamentos-ph-the-sands-avenida-balboa-panama_p-136558.htm |
| 137619 | bella-vista | Avenida Balboa | Venta de Apartamento en Torre Aqua de Costanera Ave Balboa | https://www.inmopanama.com/venta-de-apartamento-en-torre-aqua-de-costanera-ave-balboa_p-137619.htm |
| 137297 | bella-vista | Avenida Balboa | Venta de Apartamento en la Avenida Balboa | https://www.inmopanama.com/venta-de-apartamento-en-la-avenida-balboa_p-137297.htm |
| 136609 | bella-vista | Avenida Balboa | Venta de apartamentos, Proyecto PH The Edge, Ave. Balboa, Panamá | https://www.inmopanama.com/venta-de-apartamentos-proyecto-ph-the-edge-ave-balboa-panama_p-136609.htm |
| 136530 | bella-vista | Avenida Balboa | Venta de Apartamento Reposeído en Avenida Balboa, PH Belle View | https://www.inmopanama.com/venta-de-apartamento-reposeido-en-avenida-balboa-ph-belle-view_p-136530.htm |
| 136305 | bella-vista | Avenida Balboa | Venta de apartamento amoblado en Avenida Balboa, Panamá | https://www.inmopanama.com/venta-de-apartamento-amoblado-en-avenida-balboa-panama_p-136305.htm |
| 136304 | bella-vista | Avenida Balboa | Venta de apartamento en Avenida Balboa, Panamá | https://www.inmopanama.com/venta-de-apartamento-en-avenida-balboa-panama_p-136304.htm |
| 135741 | bella-vista | Avenida Balboa | Alquiler de Apartamento en Avenida Balboa | https://www.inmopanama.com/alquiler-de-apartamento-en-avenida-balboa_p-135741.htm |
| 135721 | bella-vista | Vía España | Venta de Apartamento en Vía España | https://www.inmopanama.com/venta-de-apartamento-en-via-espana_p-135721.htm |
| 139321 | bella-vista | Avenida Balboa | Venta de apartamento en Avenida Balboa | https://www.inmopanama.com/venta-de-apartamento-en-avenida-balboa_p-139321.htm |
| 137151 | bella-vista | Avenida Balboa | Se Vende Apartamento | https://www.inmopanama.com/se-vende-apartamento_p-137151.htm |
| 137017 | bella-vista | Avenida Balboa | PH YOO  VENTA DE EXCLUSIVO APARTAMENTO DE LUJO EN AVENIDA BALBOA | https://www.inmopanama.com/ph-yoo-venta-de-exclusivo-apartamento-de-lujo-en-avenida-balboa_p-137017.htm |
| 143028 | bella-vista | Vía España | Se vende edificio | https://www.inmopanama.com/se-vende-edificio_p-143028.htm |
| 137311 | betania | La Alameda | Se vende casa en La Alameda | https://www.inmopanama.com/se-vende-casa-en-la-alameda_p-137311.htm |
| 140965 | betania | La Alameda | Se vende casa en Urbanización La Alameda | https://www.inmopanama.com/se-vende-casa-en-urbanizacion-la-alameda_p-140965.htm |
| 142182 | betania | La Alameda | Se vende casa en Urbanización La Alameda | https://www.inmopanama.com/se-vende-casa-en-urbanizacion-la-alameda_p-142182.htm |
| 137348 | betania | Camino De Cruces | Alquile de casa en Camino de Cruces | https://www.inmopanama.com/alquile-de-casa-en-camino-de-cruces_p-137348.htm |
| 137483 | betania | El Dorado | EL DORADO APARTMENT FOR SALE | https://www.inmopanama.com/el-dorado-apartment-for-sale_p-137483.htm |
| 143467 | betania | El Dorado | Commercial Space for Sale in Dorado Mall | https://www.inmopanama.com/commercial-space-for-sale-in-dorado-mall_p-143467.htm |

**Nota aparte, encontrada al armar esta lista, sin relación con la resolución de zona:** el listing
143467 (*"Commercial Space for Sale in Dorado Mall"*) parece ser un tipo de inmueble no residencial
que el filtro `TIPOS_EXCLUIDOS_KEYWORDS` no capturó porque el filtro solo tiene palabras clave en
español y este título está en inglés (*"Commercial Space"*, no *"local comercial"*). No se corrigió
en esta sesión — se deja documentado para que quien revise la lista de pendientes lo tenga en
cuenta, y como posible hueco de cobertura del filtro de tipo de inmueble a evaluar por separado.

### 6.5 Cambios aplicados al scraper para corridas futuras

Agregamos `PH_A_COREGIMIENTO` a `pipeline/scraper/inmopanama_scraper.py` (deliberadamente separado
de `BARRIOS_A_COREGIMIENTO`, que se compara contra `zone_raw`; `PH_A_COREGIMIENTO` se compara contra
el título del listing, un campo distinto) con los 3 mapeos de alta confianza verificados en 6.3, y
un nuevo paso de resolución en `parse_card()` que consulta ese diccionario cuando `zone_raw` no
resuelve — con `zone_source = "titulo_ph_mapeado"` para mantener trazabilidad. Los 15 casos
resueltos por título literal (6.3) **no** tienen un mecanismo equivalente en el scraper todavía —
resolverlos automáticamente requeriría un parser de texto de título más general, que no se
implementó en esta sesión por ser una decisión de alcance mayor.

### 6.6 Cifra operativa sin cambios

La deduplicación cross-file (1,361 → 1,177) no se ve afectada por esta segunda adenda — son
correcciones independientes sobre la misma columna `corregimiento`, aplicadas en el mismo notebook.
`catalogo_residencial_limpio_6_2_1.csv` (1,177 filas) queda con: `Costa Del Este` normalizado,
18 de los 71 casos de zona ambigua resueltos, y 53 marcados `zona_no_determinada`.

## 7. Trazabilidad

Investigación e implementación completas, con código ejecutable, en
`notebooks/00_eda_catalogo_residencial.ipynb`, secciones 4.1-4.3. Cambio de scraper en
`pipeline/scraper/inmopanama_scraper.py`. Dataset exportado:
`pipeline/data/processed/catalogo_residencial_limpio_6_2_1.csv` (1,177 filas).

## 8. Adenda 3 (2026-07-13, misma sesión) — verificación de contaminación residual en inglés y n efectivo por tipo de uso

**Verificación de contaminación residual:** corrimos un grep de palabras clave en inglés
(`commercial`, `office`, `warehouse`, `retail`, `mall`, `space for`, `land for`, `lot for`,
`industrial`, `storage`) sobre el título de las 1,177 filas del catálogo consolidado. Resultado:
**1 sola coincidencia — el ya conocido `listing_id=143467`** ("Commercial Space for Sale in Dorado
Mall", §6.4). No aparecieron casos adicionales. Bajo el umbral que ameritaría bloquear o expandir
`TIPOS_EXCLUIDOS_KEYWORDS` en esta sesión — queda documentado, no bloqueante.

**Volumen efectivo por tipo de uso — no citar 1,177 como n para modelos dependientes de
corregimiento:** `catalogo_residencial_limpio_6_2_1.csv` tiene **1,177 filas totales**, pero
**1,124** (1,177 − 53 `zona_no_determinada`) es el **n real para cualquier modelo o join que
dependa de `corregimiento`** — KNN semáforo de precio, Random Forest, KMeans de segmentación, y
cualquier cruce con Zone Health (6.2.4, 6.2.5, y el eje evaluativo de 6.2.2). Los 53 registros
`zona_no_determinada` permanecen en el catálogo maestro para no perder el dato, pero deben
excluirse explícitamente de cualquier agrupación por zona hasta que se resuelvan (§6.4).

---

## 9. Adenda 4 (2026-07-13, misma sesión) — enriquecimiento de `tipo_inmueble` + `descripcion`, ejecutado por primera vez

### 9.1 Qué estaba documentado vs. qué existía realmente

El Acta de Feature 1.2, §3.7, documenta una función `obtener_tipo_inmueble()` diseñada para
visitar la página de detalle de cada listing y extraer el campo `Tipo:` desde el selector
`ul.ib-prop-details-list`. Verificamos, contra el repositorio real (no contra la documentación),
que:

1. **`obtener_tipo_inmueble()` nunca se implementó** en `pipeline/scraper/inmopanama_scraper.py` —
   no existe ninguna función con ese nombre, ni una equivalente, en el scraper actual.
2. **El selector documentado, `ul.ib-prop-details-list`, está obsoleto.** Confirmado contra 3
   páginas de detalle reales (una por cada patrón de contaminación conocido): 0 coincidencias en
   las 3. El HTML real del sitio cambió desde que se escribió esa sección del Acta.

Mismo patrón de trazabilidad ya identificado con la cita inventada "Feature 1.4.6" (Acta de
Feature 1.4, corregida en su momento) y con los 71 casos de zona ambigua (§6 de esta adenda): una
decisión o mecanismo documentado como diseñado no implica que se haya ejecutado o que siga siendo
válido contra el estado real del sitio — se verifica de nuevo, no se asume.

### 9.2 Selectores reales, verificados contra el HTML vigente

- **`tipo_inmueble`:** `ol.nb-breadcrumb-list` → se filtran los separadores `›` → se toma el ítem
  en posición 2 (0-indexed), tras `Home` y la operación (`En Venta`/`En Alquiler`). Verificado que
  varía genuinamente por tipo real: un listing de la categoría `venta-apartamentos-*` devuelve
  `"Apartamentos"`, un listing de `venta-propiedades-pedregal` (categoría mixta, ya excluido de
  nuestro catálogo por el filtro de título) devuelve `"Casas"` — no es un valor constante.
  Verificado además contra un listing de cada uno de los 7 archivos de origen
  `venta-propiedades-*` (betania, costa-del-este, el-cangrejo, marbella, obarrio, parque-lefevre,
  pedregal): los 6 adicionales probados devolvieron `"Apartamentos"` de forma consistente
  (esperado, ya que nuestro catálogo ya está filtrado a tipo residencial por
  `TIPOS_EXCLUIDOS_KEYWORDS`).
- **`descripcion`:** `.nb-desc-full-content` (párrafo completo, ~280-300 palabras en las muestras
  verificadas, contenido cualitativo real — proximidad, ambiente, audiencia objetivo, no solo
  repetición de atributos estructurados). Cuando ese bloque no existe, hacemos fallback a
  `.nb-desc-preview` (texto corto, a veces solo el nombre del PH/edificio). Cuando ninguno de los
  dos tiene texto, la página confirma explícitamente *"Esta propiedad no tiene descripción
  disponible"* — no es un fallo de scraping, es un estado real del listing en el sitio.

### 9.3 Ejecución

Script: `pipeline/scraper/enriquecer_detalle.py`. Visita cada `listing_url` **una sola vez**,
extrae `tipo_inmueble` y `descripcion` en la misma visita (no duplica requests). Retomable por
diseño: una fila con `tipo_inmueble` y `descripcion` ya poblados no se reprocesa en una corrida
posterior — mismo patrón que `enriquecer_con_tipo()` del Acta original. Cortesía de scraping:
2.5s entre requests, misma convención que `inmopanama_scraper.py`.

Se ejecutó en dos pasadas sobre las 1,177 filas del catálogo maestro:
1. **Pasada completa** (todas las filas, selector de descripción solo `.nb-desc-full-content`):
   1,137 filas con ambos campos poblados, 40 con `tipo_inmueble` poblado pero `descripcion` vacía
   (`sin_descripcion`), 0 fallos de red.
2. **Pasada de retoma** (solo las 40 pendientes, con el fallback a `.nb-desc-preview` ya agregado):
   31 resueltas vía preview, 9 confirmadas sin ninguna descripción disponible (verificado
   directamente contra la página real en cada uno de los 9 casos — no un supuesto).

**Resultado final, `descripcion_fuente` sobre las 1,177 filas:**

| descripcion_fuente | n | % |
|---|---|---|
| completa | 1,137 | 96.60% |
| preview | 31 | 2.63% |
| ninguna | 9 | 0.76% |

`ninguna` queda muy por debajo del 5% del catálogo — no concentrado en ninguna zona en particular,
verificado caso por caso (9 listings, cada uno con causa confirmada: o la página declara
explícitamente que no hay descripción, o el bloque de preview existe en el DOM pero está vacío).

**Fallos de red en toda la ejecución (ambas pasadas, 1,177 + 40 requests): 0.**

### 9.4 Consecuencia directa: redefinición de "comparable" ya no degradada

Con `tipo_inmueble` poblado para prácticamente todo el catálogo (1,168 / 1,177 con `enriquecimiento_estado == "ok"`),
la redefinición de "comparable" documentada en el Acta original (decisión #4: de `ST_Distance` a
`corregimiento + tipo_inmueble`) deja de estar degradada a solo `corregimiento` — se aplica tal
como se diseñó originalmente. Actualizado en Notebook 6.2.1 (`notebooks/00_eda_catalogo_residencial.ipynb`),
sección de redefinición de comparable.

### 9.5 Trazabilidad

Script: `pipeline/scraper/enriquecer_detalle.py`. Ejecución documentada con código en
`notebooks/00_eda_catalogo_residencial.ipynb`. Backups del catálogo antes/después de cada pasada:
`/tmp/catalogo_residencial_limpio_6_2_1_backup_pre_enriquecimiento.csv`,
`/tmp/catalogo_backup_post_13200.csv` (no versionados en git, solo referencia local de la sesión).
