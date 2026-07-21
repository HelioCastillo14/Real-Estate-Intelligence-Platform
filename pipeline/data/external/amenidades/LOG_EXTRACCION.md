# Log de extracción — `pipeline/data/external/amenidades/`

Este log no existía antes de la auditoría de Feature 1.4.3 (2026-07-09). Se crea para
que el próximo sesgo de extracción se detecte revisando este archivo, no re-derivando
todo desde cero como se tuvo que hacer ahora.

## Limitación de esta reconstrucción

Los 6 archivos originales (3 Google Places + 3 OSM) **no tienen script de extracción
ni log de queries en el repo**. Se buscó (`grep` sobre `pipeline/`, `find` de logs) y
no existe ningún `.py` de scraping de Google Places ni un registro de qué términos de
búsqueda se usaron por zona. Los únicos logs de extracción que existen en
`pipeline/data/raw/*_pagination_log.csv` son del scraping de **listings**, no de
amenidades.

Por eso, lo que sigue es metadata **reconstruida post-hoc** a partir de los archivos
mismos (conteo por categoría) y del filesystem/git — no reconstruye las queries
originales, esa información ya se perdió. El timestamp de filesystem tampoco es
confiable como "fecha de extracción real": todos los archivos muestran el mismo
checkout de git (`git log` muestra que entraron al repo en los commits `5616809` y
`93009ea`, 2026-07-09, como parte de una reorganización de rutas — no en el momento
en que se extrajeron de Google Places / OSM originalmente).

## Baseline por archivo (reconstruido 2026-07-09)

### Google Places (búsqueda manual por categoría, sin script versionado)

| Archivo | Zona | Total | supermercado | farmacia | colegio | parque | clinica | hospital |
|---|---|---|---|---|---|---|---|---|
| `amenidades_san_francisco_google_places.jsonl` | San Francisco | 34 | 6 | 8 | 8 | 4 | 6 | 2 |
| `amenidades_bella_vista_google_places.jsonl` | Bella Vista | 17→18* | 2 | 4 | 7 | 3 | 1 | 0→1* |
| `amenidades_costa_del_este_google_places.jsonl` | Costa del Este | 24 | 7 | 8 | 4 | 4 | 0 | 1 |

\* Actualizado por la re-extracción del 2026-07-09 documentada abajo.

**Lectura de sesgo (método):** en extracciones por texto tipo Google Places, cada
categoría es una búsqueda independiente ("hospital cerca de...", "clinica cerca
de..."). Si una zona tiene 0 resultados en una sola subcategoría de salud mientras
las demás categorías tienen volumen normal, y una zona comparable sí tiene ambos
subtipos, es señal de que esa búsqueda específica nunca se ejecutó (bug de cobertura),
no de que la zona carezca genuinamente de esa amenidad. Así se detectó originalmente
Costa del Este (Acta 1.3.7 §7, `hospital`=1 pero `clinica`=0) y así se detectó ahora
Bella Vista (`clinica`=1 pero `hospital`=0 antes de la corrección).

### OSM (extracción por bounding box / polígono, todos los tags `amenity`/`shop`/`leisure` de una vez)

| Archivo | Zona(s) | Total features | school | pharmacy | clinic | hospital | shop=supermarket | leisure=park |
|---|---|---|---|---|---|---|---|---|
| `amenidades_betania_obarrio_cangrejo_marbella_osm.geojson` | Betania + Obarrio + Cangrejo + Marbella | 130 | 19 | 28 | 16 | 2 | (ver nota) | (ver nota) |
| `amenidades_parque_lefevre_osm.geojson` | Parque Lefevre | 52 | 12 | 5 | 3 | 1 | (ver nota) | (ver nota) |
| `amenidades_pedregal_osm.geojson` | Pedregal | 12 | 4 | 1 | 2 | 0 | 2 | 3 |

Nota: los archivos OSM mezclan tags `amenity`, `shop` y `leisure` en la misma
propiedad (no hay una columna `categoria` uniforme como en los Google Places). El
conteo de `supermercado`/`parque` de Betania y Parque Lefevre no se desglosó en esta
tabla — el cómputo de 1.4.3 (pendiente de aprobación para avanzar al Paso 2) deberá
parsear `amenity`/`shop`/`leisure` por zona directamente de estos `.geojson`.

**Por qué el sesgo de "búsqueda por categoría" es estructuralmente menos probable en
OSM:** la extracción de Pedregal (verificada contra el caso de prueba conocido:
colegio=4, parque=3, supermercado=2, clinica=2, farmacia=1, hospital=0) trae *todos*
los tags de amenidad de una sola consulta por polígono, no una consulta por
categoría — no hay "búsqueda de hospital" que se pueda omitir independientemente de
"búsqueda de clinica". Este tipo de sesgo es específico del método de extracción por
texto de Google Places, no de OSM.

---

## Re-extracciones

### 2026-07-09 — Bella Vista, categoría `hospital`

- **Motivo:** auditoría de Feature 1.4.3 (Paso 1) detectó que
  `amenidades_bella_vista_google_places.jsonl` tenía `hospital=0` mientras
  `clinica=1` y las demás categorías tenían volumen normal (2-7 registros), el mismo
  patrón de sesgo por búsqueda incompleta ya documentado para Costa del Este
  (Acta 1.3.7 §7). Confirmado externamente por el usuario (no asumido por el agente)
  que Bella Vista sí tiene hospitales reales dentro del polígono administrativo.
- **Método:** el archivo original no tiene script de extracción versionado (ver
  limitación arriba), así que no hay una "llamada a la API de Google Places" que
  repetir de forma idéntica. En esta sesión **no hay acceso a la API de Google
  Places** (no hay credencial/tool disponible), por lo que la re-extracción se hizo
  por **investigación manual vía búsqueda web**, cruzando cada candidato contra el
  límite del corregimiento Bella Vista en Mapcarta/OSM antes de aceptarlo. Esto es
  un método distinto y menos automatizado que el original — se documenta así
  explícitamente en cada registro nuevo (campo `metodo` y `fuente`) para que sea
  auditable y diferenciable de los registros originales de Google Places (que sí
  traen `place_id` real).
- **Verificación programática (2026-07-09, segunda pasada):** la primera versión de
  esta re-extracción aceptó candidatos por *descripción* de límites (Mapcarta,
  colindancias en texto). A pedido explícito del usuario, se corrió
  `pipeline/zone_health/cruce_espacial_corregimiento.py`
  (`asignar_corregimiento(lat, lng, poligonos)`, shapely `Point().contains()`) contra
  `corregimientos_5zonas_poligonos_raw_osm.geojson` — el mismo cruce punto-en-polígono
  que ya se usa para el resto del pipeline (metro, etc.) — para confirmar cada
  candidato programáticamente en vez de por descripción textual. Resultado:
  - **Hospital Nacional** (8.9706, -79.5336) → `asignar_corregimiento` devuelve
    `None`. El punto queda ~0.0042° (≈470 m) al sur del límite inferior del polígono
    de Bella Vista (`bounds` mínimo de latitud 8.9711276) — geográficamente en o cerca
    de Calidonia, no Bella Vista. **Descartado**, pese a que la descripción textual de
    "Av. Cuba entre Calle 38 y 39" sonaba plausible — la verificación programática la
    contradice y tiene prioridad.
  - **Complejo Hospitalario Dr. Arnulfo Arias Madrid** (8.98083, -79.53563, conversión
    corregida de 8°58'50.790"N 79°32'8.261"W) → `asignar_corregimiento` devuelve
    `'Bella Vista'`. **Confirmado, se mantiene.**
  - Se buscaron reemplazos para el hueco dejado por Hospital Nacional. Se evaluaron
    programáticamente **Hospital San Fernando** (Pueblo Nuevo, descartado antes de
    verificar por dirección conocida) y los dos polígonos de **Hospital Paitilla** /
    **Centro Médico Paitilla** ya presentes en
    `amenidades_betania_obarrio_cangrejo_marbella_osm.geojson`
    (`way/146689569`, `way/1287207332`, centroides ≈8.9777/8.9786, -79.518) — ambos
    devuelven `'San Francisco'`, no Bella Vista. **No se encontró un segundo hospital
    real dentro del polígono confirmado de Bella Vista.** Esto no se trata como un
    sesgo de búsqueda: la evidencia geográfica es consistente (los 3 hospitales grandes
    de la zona — Hospital Nacional, Hospital Paitilla, Hospital San Fernando — caen
    justo fuera del polígono de Bella Vista, en Calidonia, San Francisco/Punta Paitilla
    y Pueblo Nuevo respectivamente), no un artefacto de la extracción.
  - **Hospital Geriátrico 31 de Marzo** — descartado antes de la verificación
    geométrica: ubicado en Pueblo Nuevo según fuente directa, ni se intentó.
- **Conteo final:** `hospital` en Bella Vista pasa de **0 a 1** (no a 2 — la primera
  versión de este log sobreestimó el conteo antes de la verificación programática;
  corregido aquí). Total del archivo pasa de 17 a 18 registros.
- **No se tocaron** las categorías `supermercado`, `parque`, `farmacia`, `colegio` de
  Bella Vista — solo se agregó 1 registro de `hospital`.

---

## Paso 4 — Verificación cruzada de cobertura hospital/clinica

| Zona | hospital | clinica | ¿Ambos tipos targeteados? |
|---|---|---|---|
| San Francisco | 2 | 6 | Sí — confirmado, sin acción necesaria |
| Bella Vista | 2 (post-fix) | 1 | Corregido en esta sesión |
| Costa del Este | 1 | 0 | **Sigue pendiente.** Mismo patrón de sesgo (Acta 1.3.7 §7), no corregido. |

**Costa del Este NO se corrigió en esta sesión** — por decisión ya cerrada en
CLAUDE.md (Costa del Este no recibe score compuesto, 4/5 dimensiones sin insumo
estructural), no entra al cálculo de 1.4.3 de todas formas. Se deja documentado aquí
como deuda pendiente por si en el futuro cambia el alcance de Costa del Este o se usa
esta tabla de amenidades para otro propósito (ej. dato descriptivo). No se debe
asumir que `clinica=0` en Costa del Este es un resultado geográfico real.

---

### 2026-07-09 — Betania, hueco de cobertura espacial (las 5 categorías)

- **Motivo:** al ejecutar el Paso 2 del cómputo de 1.4.3, el cruce punto-en-polígono
  de `amenidades_betania_obarrio_cangrejo_marbella_osm.geojson` contra el polígono
  real de Betania devolvió conteos anómalamente bajos: `supermercado=0`,
  `farmacia=0`, `salud=0`, `parque=1`, `colegio=4` — 3 de 5 categorías en cero,
  cuando ninguna otra zona (ni Pedregal, la más pequeña) tiene ceros. Diagnóstico: el
  polígono real de Betania cubre lat 8.9886–9.0364, pero los puntos del archivo
  original solo llegan hasta lat 9.0009 — la consulta OSM original nunca cubrió
  ~74% de la extensión norte-sur de Betania. El nombre del archivo
  ("betania_obarrio_cangrejo_marbella") sugiere que la caja de búsqueda se centró en
  la zona de El Cangrejo/Marbella/Obarrio (que administrativamente pertenecen al
  polígono de Bella Vista, no al de Betania) y solo alcanzó el borde sur de Betania
  de forma incidental. Esto es un hueco de **cobertura espacial** (bbox insuficiente),
  no una omisión de subcategoría como el caso de Bella Vista/hospital arriba, pero
  con el mismo efecto: sesga el score de la zona si se calcula sin corregir.
- **Decisión del usuario:** re-extraer OSM para el polígono completo de Betania antes
  de calcular 1.4.3 (opción explícitamente elegida sobre "calcular igual con
  limitación documentada" o "pausar 1.4.3").
- **Método:** consulta a Overpass API (`https://overpass-api.de/api/interpreter`,
  acceso confirmado disponible en esta sesión vía `curl`) acotada al bounding box
  exacto del polígono real de Betania (`poligonos['Betania'].bounds` =
  `8.9886275, -79.5418181, 9.0364299, -79.5095706`), pidiendo
  `amenity~"^(hospital|clinic|pharmacy|school)$"`, `shop=supermarket`,
  `leisure=park` (nodos y ways, `out center tags`). 217 elementos devueltos por el
  bbox completo. Cada elemento se filtró de nuevo con
  `asignar_corregimiento()` contra el polígono real (no basta con el bbox, que es un
  rectángulo — el polígono de Betania no lo es) — de los 217, 104 caen efectivamente
  dentro del polígono de Betania; 25 caen en Bella Vista, 16 en San Francisco
  (probablemente El Cangrejo/Marbella/Obarrio/zonas colindantes) y 72 quedan fuera de
  las 5 zonas reales. Solo los 104 confirmados dentro de Betania se guardaron.
- **Archivo nuevo:** `amenidades_betania_osm.geojson` (104 features, ya filtrado y
  confirmado dentro del polígono de Betania — mismo criterio de "archivo dedicado
  y limpio" que ya se usa para `amenidades_pedregal_osm.geojson` y
  `amenidades_parque_lefevre_osm.geojson`). **Es el archivo que consume el cómputo de
  1.4.3 para Betania.**
- **El archivo original `amenidades_betania_obarrio_cangrejo_marbella_osm.geojson`
  NO se modificó ni se borró** — queda como está, fuera de alcance de esta sesión.
  Ver corrección de referencia de feature más abajo (§ "Corrección de referencia de
  feature") y hallazgo de cobertura para El Cangrejo/Obarrio/Marbella en la sección
  siguiente.
- **Conteo final Betania (post-fix), vs. el conteo truncado original:**

  | Categoría | Original (bbox truncado) | Corregido (bbox completo) |
  |---|---|---|
  | supermercado | 0 | 12 |
  | farmacia | 0 | 19 |
  | salud (clinic+hospital) | 0 | 20 |
  | parque | 1 | 29 |
  | colegio | 4 | 24 |

- **No se tocaron** las fuentes de las otras 4 zonas reales.

---

## Verificación de cobertura: El Cangrejo, Marbella, Obarrio (2026-07-09)

**No bloquea 1.4.3** — estas 3 zonas no son corregimientos administrativos reales
(heredan Zone Health de Bella Vista, CLAUDE.md), así que no entran al cómputo de
1.4.3. Se investiga aquí únicamente porque puede afectar visualización de
amenidades más adelante (ver nota de alcance abajo).

**Limitación del método:** a diferencia de Betania, San Francisco, Bella Vista,
Parque Lefevre y Pedregal, El Cangrejo/Marbella/Obarrio **no son corregimientos
administrativos** y por lo tanto no tienen un polígono de límite en
`corregimientos_5zonas_poligonos_raw_osm.geojson` — ese archivo solo tiene los 5
polígonos reales. Se buscaron límites alternativos en OSM (`place=suburb` /
`place=neighbourhood` / `place=quarter`):

- **El Cangrejo**: existe un polígono real (way `444837940`, 112 nodos, límite
  cerrado). Se pudo verificar con el mismo método que Betania.
- **Obarrio**: existe un polígono real (way `505188334`, 54 nodos, límite cerrado).
  Se pudo verificar.
- **Marbella**: solo existe un nodo-punto (`place=neighbourhood`, sin polígono de
  límite en OSM). **No se pudo verificar con el mismo rigor** — no hay un polígono
  contra el cual filtrar, así que cualquier conclusión sobre Marbella es
  necesariamente más débil que la de las otras 2 zonas de herencia.

**Resultado (Overpass fresco sobre el bbox combinado de El Cangrejo+Obarrio,
filtrado por el polígono real de cada uno, comparado contra el archivo ya existente
en el repo filtrado por esos mismos polígonos):**

| Zona | Categoría | Repo (archivo actual) | Ground truth (Overpass fresco) | Diferencia |
|---|---|---|---|---|
| El Cangrejo | todas | 20 (colegio 8, farmacia 6, salud 3, supermercado 2, parque 1) | 20 (idéntico) | Ninguna |
| Obarrio | farmacia | 3 | 4 | -1 |
| Obarrio | parque | 0 | 2 (Parque Harry Strunz, Park and Padel Panama) | **-2 (100% faltante)** |
| Obarrio | salud, supermercado | 4, 3 | 4, 3 | Ninguna |

**Conclusión:**
- **El Cangrejo: sin problema de cobertura.** El bbox original capturó el 100% de
  lo que existe dentro de su polígono real.
- **Obarrio: problema de cobertura parcial**, mucho más leve que el de Betania (que
  perdía 3 de 5 categorías por completo). Aquí falta 1 farmacia y, más
  significativo, el 100% de los parques (2 de 2). Si se usa este archivo para
  mostrar amenidades de Obarrio en frontend, los parques quedarían invisibles.
- **Marbella: no verificable con este método** (sin polígono real disponible). No
  se puede afirmar ni descartar un problema de cobertura ahí con la misma
  confianza que en los otros casos.

**No se corrige nada de esto en esta sesión** — queda documentado para quien
trabaje la visualización de amenidades en frontend (posiblemente Feature 5.3.6,
"mapa de servicios cercanos" — ver corrección de referencia abajo sobre por qué no
se afirma esto como confirmado).

---

## Corrección de referencia de feature (2026-07-09)

Las 3 primeras versiones de este log, y los docstrings de
`normalizacion_seguridad.py`, `normalizacion_transporte.py` y
`normalizacion_amenidades.py`, decían que El Cangrejo/Marbella/Obarrio/Costa del
Este "se resuelven en Feature 1.4.6". **Esa referencia es incorrecta y no estaba
verificada** — se copió de un archivo a otro sin comprobarla contra ninguna fuente.
Se buscó en el repo (`grep -rn "1.4.6"`) y **"Feature 1.4.6" no aparece definida en
ningún lugar** — ni en CLAUDE.md, ni en ningún Acta local. CLAUDE.md solo confirma
que Feature 1.4 es el "Zone Health Composite Index", sin desglosar sub-features
más allá de 1.4.1–1.4.4 (normalización) y menciona explícitamente que la fuente de
verdad completa de las Actas está en Notion, no en este repo.

**Corrección aplicada:** se removió la afirmación "Feature 1.4.6" de los 3
docstrings y de este log, reemplazada por una descripción sin número de feature
inventado (ver diffs de esta sesión). Sobre el archivo combinado
`amenidades_betania_obarrio_cangrejo_marbella_osm.geojson`: **no se puede confirmar
desde este repo qué feature lo consume.** La hipótesis más plausible, dado que
contiene POIs crudos de El Cangrejo/Marbella/Obarrio (zonas sin score compuesto
propio, solo con datos descriptivos), es una feature de visualización de
amenidades en el frontend — el usuario sugirió Feature 5.3.6 ("mapa de servicios
cercanos") como candidato, pero **ese número tampoco está verificado en este
repo** y no se debe tratar como confirmado hasta que se corrobore contra el Acta
correspondiente en Notion. No se repite aquí el mismo error de propagar un número
sin verificar.
