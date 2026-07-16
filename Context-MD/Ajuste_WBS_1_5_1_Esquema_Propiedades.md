# Ajuste WBS 1.5.1 — Esquema de la tabla `propiedades` (propuesta, sin ejecutar)

**Fecha:** 2026-07-15
**Estado:** PROPUESTA — pendiente de aprobación. No modifica `REIP_WBS.xlsx` (queda intacto como
registro histórico, consistente con `Context-MD/Gobernanza_WBS_vs_Feature_6_2.md`). No se ejecutó
ninguna migración contra Supabase como parte de este documento.

---

## 1. El problema

La Condición de Done original de **1.5.1** (`REIP_WBS.xlsx`, hoja `1.0 Infraestructura y Datos`)
dice: *"Implementar tabla `propiedades` con columna `geom` (Point/PostGIS) y `embedding`
(vector/pgvector) + índice GiST y HNSW"*, y remite a **`DOC-05 §4.2`** para el resto de los
campos de la tabla (tipos, constraints, más allá de `geom`/`embedding`).

`DOC-05` no existe en este repo. Ya se buscó explícitamente y no dio resultado (confirmado antes
de escribir este documento — no se repite la búsqueda aquí). Esto ya está documentado como
bloqueo abierto en `Context-MD/Feature_1_5b_Embedding_Dimension_Cierre.md` §4 y en
`Context-MD/WBS_Pendiente_Epicas_2_3_4.md` línea 84.

Tal como está escrita, la tarea depende de una fuente que no existe en el repo — no se puede
cerrar nunca por esa vía. Este documento propone un esquema derivado de fuentes que sí existen y
están verificadas, para que el equipo decida si sustituye a `DOC-05 §4.2` como base de 1.5.1.

---

## 2. Esquema propuesto para `propiedades`

Tres fuentes, cada una citada. No se inventa ningún campo fuera de estas tres.

### 2.1 Columnas derivadas del catálogo real

Fuente: `pipeline/data/processed/catalogo_residencial_limpio_6_2_1.csv`, header y tipos leídos
directamente del archivo el 2026-07-15 (1,177 filas, no de memoria de ninguna conversación
anterior). Tipo inferido por pandas (`dtype`) a la izquierda, tipo SQL propuesto a la derecha.

| Columna CSV | dtype pandas | nulls (de 1177) | Tipo SQL propuesto | Nota |
|---|---|---|---|---|
| `listing_url` | str | 0 | `text` | 1,177 valores únicos — candidato natural a `UNIQUE` |
| `listing_id` | int64 | 0 | `bigint` | 1,177 valores únicos — candidato natural a `PRIMARY KEY` o `UNIQUE` |
| `title` | str | 0 | `text` | |
| `zone_raw` | str | 0 | `text` | Zona tal como apareció en el listing original (30 valores distintos, incluye barrios como "El Carmen") |
| `corregimiento` | str | 0 | `text` | Corregimiento resuelto (10 valores — las 9 zonas de scope + posible residual de mapeo; verificar contra Acta 1.2 antes de fijar `CHECK`) |
| `zone_source` | str | 0 | `text` | Método de resolución de zona (3 valores, ej. `zone_raw_barrio_mapeado`) — trazabilidad de Acta 1.2 |
| `price_raw` | str | 0 | `text` | Precio como texto original (`"$200,000"`) — preservar para auditoría |
| `price_usd` | int64 | 0 | `integer` o `numeric` | Precio numérico parseado |
| `precio_no_evaluable` | bool | 0 | `boolean` | |
| `precio_no_evaluable_motivo` | str | 1163 | `text`, nullable | Solo 14 filas no-nulas — motivo cuando `precio_no_evaluable=True` |
| `bedrooms` | float64 | 1 | `numeric` o `smallint` (evaluar si siempre es entero pese al dtype float) | |
| `bathrooms` | float64 | 1 | `numeric` o `smallint` (idem) | |
| `area_m2` | float64 | 29 | `numeric` | |
| `operation` | str | 0 | `text` | 2 valores (venta / alquiler, verificar valores exactos antes de `CHECK`) |
| `source` | str | 0 | `text` | 1 valor único (`inmopanama.com`) — confirmar si vale la pena una columna o es constante de fase actual |
| `scraped_at` | str | 0 | `timestamp` (parsear desde texto `"2026-07-03 00:06:23"`) | |
| `corregimiento_archivo` | str | 0 | `text` | Corregimiento según el archivo de origen del scraper (7 valores) — distinto de `corregimiento` resuelto, mantener ambos por trazabilidad (Acta 1.2 Adenda Duplicados) |
| `tipo_inmueble` | str | 0 | `text` | 5 valores — insumo directo de comparables M2 (`corregimiento + tipo_inmueble`, decisión cerrada §4 de `CLAUDE.md`) |
| `descripcion` | str | 9 | `text`, nullable | Insumo de embeddings (M1) y Quality Scorer (M2) — 9 filas sin descripción ya conocidas y manejadas en 6.2.3/6.2.6 |
| `descripcion_fuente` | str | 0 | `text` | 3 valores (ej. `completa`, `ninguna`) — flag de calidad del insumo de `descripcion` |
| `enriquecimiento_estado` | str | 0 | `text` | **4 valores fijos** (normalizado 2026-07-15): `ok` (1167), `sin_descripcion` (9), `error_red` (1), `sin_url` (0) — resultado de `pipeline/scraper/enriquecer_detalle.py` (Feature 6.2.1). Antes de esta normalización, el fallo de red producía un string compuesto (`error_red:ConnectionError`), incompatible con un `CHECK` de valores fijos en Postgres — corregido a 4 categorías cerradas, con el detalle específico de cada caso movido a la columna nueva `enriquecimiento_error_detalle` |
| `enriquecimiento_error_detalle` | str | 1176 | `text`, nullable | Columna nueva (2026-07-15), sin `CHECK` a propósito (texto libre). Poblada cuando `enriquecimiento_estado` es `error_red` (nombre de la excepción, ej. `ConnectionError` — 1 fila no-nula, `listing_id` 137025) o `sin_descripcion` con una variante específica (`sin_breadcrumb`/`sin_ambos` — **0 ocurrencias en el catálogo actual, cubiertas preventivamente en el `CHECK` de `enriquecimiento_estado` antes de que ocurran, no después**, mismo criterio ya aplicado a `error_red`). `sin_url` (falta `listing_url` en el CSV, la página nunca se visitó) es intencionalmente **distinto** de `sin_descripcion` — no se normaliza junto con esa categoría porque la causa es otra (ausencia de URL de origen, no ausencia de contenido en una página visitada) |

**No se decide aquí** cuáles de estos campos llevan `NOT NULL`, `CHECK`, o índices secundarios —
eso es trabajo de implementación de 1.5.1 propiamente, no de este documento de esquema.

### 2.2 `embedding vector(3072)`

Ya decidido y verificado contra la API real — no se reabre aquí (Feature 1.5b, CERRADA):
`gemini-embedding-001`, 3072 dimensiones. Migración de referencia ya existe en
`supabase/migrations/20260715032111_propiedades_embedding.sql`, con el `alter table if exists ...
add column if not exists` — no ejecutada todavía contra Supabase real. Ver §4 de este documento
para cómo se coordina con el `CREATE TABLE` principal.

### 2.3 `geom` (Point/PostGIS)

**Nota explícita, no opcional:** esta columna almacena una **aproximación sintética para
visualización**, generada con el mismo mecanismo (`ST_GeneratePoints` o equivalente) ya usado en
el mapa de Zone Health — **no** la coordenada real del listing. `inmopanama.com` no expone
coordenadas reales de las propiedades scrapeadas; esta es la misma razón documentada por la que
3.1.1 (comparables de M2) descartó `ST_Distance` geográfico en favor de `corregimiento +
tipo_inmueble` (`CLAUDE.md`, decisión formal cerrada #4). Cualquier consumidor futuro de `geom`
en `propiedades` (mapa del frontend, queries espaciales) debe tratar este campo como dato de
presentación, nunca como insumo de modelo — igual que el `geom` sintético ya existente para
propiedades en el resto del pipeline (`CLAUDE.md`, sección "Estado del pipeline de datos": *"`geom`
de propiedades es sintético (jitter), solo para visualización — nunca insumo de modelo"*).

Tipo SQL propuesto: `geometry(Point, 4326)` (PostGIS), consistente con el resto del proyecto.

### 2.4 `imagenes` — arquitectura hotlink (Opción A, decisión cerrada 2026-07-15)

**Decisión: hotlink, no descarga.** `propiedades.imagenes` almacena únicamente las URLs de imagen
extraídas del HTML de la página de detalle — nunca se descarga ni almacena el archivo `.jpg` en
Supabase (evita cualquier problema de espacio en el free tier). Verificado contra 3 páginas de
detalle reales (IDs 143475, 136451, 140502) antes de esta decisión:

- Selector: `.ib-prop-gallery-main .swiper-slide img` (atributo `src`), dentro de `.nb-gallery-wrap`
  — mismo bloque cuyo contador `.nb-gallery-counter` ("N fotos") coincide exactamente con el número
  de imágenes encontradas en las 3 muestras (6, 14 y 7 fotos respectivamente).
- URLs directas al propio dominio (`https://www.inmopanama.com/files/props/{id}/{nombre}.jpg`), sin
  CDN externo, sin sesión ni token — verificado con `curl -I` sin cookies: `200 OK` en las 3
  muestras, `Cache-Control: max-age=31536000`. El nombre de archivo no es reconstruible solo con el
  `listing_id` (varía entre numérico y slug del título) — debe extraerse del HTML en cada visita, no
  generarse por convención.
- `robots.txt` no restringe `/files/props/` (solo bloquea `/adm/`, `/account/`, `/sesion/`,
  `/cuenta/`, `/includes/`, `/sync/`, `/_diag_db.php`) — nada distinto de lo ya verificado para
  scraping de texto. No existe una página de ToS real en el sitio (las rutas candidatas devuelven
  `200` pero resuelven al home, ruta catch-all sin contenido propio) — no hay restricción específica
  de imágenes que consultar.

**Tipo SQL propuesto: `text[]`, no `jsonb`.** Un array de Postgres ya preserva el orden por posición
(la galería es un carrusel ordenado, orden 1..N tal como aparece en `.swiper-wrapper`) — no hay
metadata adicional por imagen que justifique `jsonb` (no hay caption, no hay dimensiones, no hay
`alt` distinto por imagen en las muestras verificadas). Si en el futuro se necesita metadata por
imagen, se puede migrar a `jsonb` entonces; no se anticipa aquí sin necesidad concreta.

| Columna CSV | Estado en catálogo actual | Tipo SQL propuesto | Nota |
|---|---|---|---|
| `imagenes` | No existe aún en `catalogo_residencial_limpio_6_2_1.csv` — requiere nueva pasada de `enriquecer_detalle.py` (ver script) | `text[]` | URLs completas extraídas de `.ib-prop-gallery-main .swiper-slide img` en la página de detalle, mismo mecanismo de visita que `tipo_inmueble`/`descripcion` (Feature 6.2.1) |

#### 2.4.1 Verificación: comas sin escapar dentro de una URL individual

Riesgo evaluado antes de lanzar la corrida completa: la sintaxis literal de `text[]` en Postgres es
`{url1,url2,...}` — una coma *dentro* de una URL individual (no como separador) rompería el parseo
al insertar si el array se construye como string manual.

**Verificado sobre las 27 URLs de las 3 muestras de detalle (IDs 143475, 136451, 140502): 0 con
coma.** Los nombres de archivo son o bien numéricos (`143475-6.jpg`) o un slug del título con
espacios/caracteres especiales ya convertidos a guiones por el propio `inmopanama.com`
(`se-vende-casa-en-paseo-ddl-dorado-condado-del-rey_1.jpg`) — el mecanismo de generación de slugs
del sitio no deja comas en el nombre de archivo en ninguna de las muestras observadas.

Esto es una observación sobre 27 URLs, no una garantía sobre las ~1,177 filas del catálogo
completo — **no se debe construir el literal `{url1,url2}` a mano como string por eso**. La forma
correcta y ya defendida contra este riesgo (aparezca o no una coma) es que el script de carga
(1.2.4/2.1.3) pase la lista de URLs como un objeto Python nativo (`list[str]`) al driver de
Postgres (`psycopg2`/`psycopg3`/`asyncpg`), que adapta un `list` a `text[]` con el escapado correcto
automáticamente — nunca formatear el string `{...}` manualmente ni con `str.join(",")`.

#### 2.4.2 Nota obligatoria: el CSV NO usa la sintaxis de Postgres — conversión explícita requerida

`enriquecer_detalle.py` guarda `imagenes` en el CSV intermedio como **JSON-string** (formato
`json.dumps(...)`, ej. `["https://.../143475-1.jpg", "https://.../143475-2.jpg"]`), consistente con
cómo el resto del pipeline serializa estructuras en columnas de CSV. **Esto no es la sintaxis nativa
de un `text[]` de Postgres** (`{https://.../143475-1.jpg,https://.../143475-2.jpg}`) — son dos
formatos de texto distintos que se ven superficialmente similares (ambos son "una lista entre
corchetes/llaves") pero no son intercambiables carácter por carácter.

**Acción obligatoria para quien implemente la carga de datos a `propiedades` (1.2.4/2.1.3 o el
script que finalmente puebla la tabla):** el campo `imagenes` del CSV debe pasar por
`json.loads(...)` para obtener un `list[str]` de Python antes de insertarlo — nunca insertarse tal
cual como string crudo del CSV, y nunca reconstruirse a mano con `.replace("[", "{")` o
transformaciones de string equivalentes. Se documenta aquí explícitamente para que esto no se
descubra como error de carga a mitad de la implementación de 1.5.1/1.5.2, sino que quede resuelto
de antemano con el mismo patrón de conversión segura de §2.4.1 (pasar el `list[str]` ya parseado al
driver, no construir el literal de Postgres como string).

---

## 3. Decisión: PRIMARY KEY de `propiedades`

Dos candidatos naturales, ambos con 1,177 valores únicos y 0 nulos en el catálogo real (§2.1):
`listing_id` (`bigint`) y `listing_url` (`text`).

**Decisión: `listing_id` (`bigint`) es la PRIMARY KEY de `propiedades`.**

Razones:

- **Tamaño e indexación:** una PK `bigint` produce un índice más compacto y comparaciones más
  baratas que una PK `text` sobre URLs largas (`https://www.inmopanama.com/venta-de-apartamento-...`,
  observado >60 caracteres en la muestra de §2.1) — relevante para cualquier FK que la referencie
  (ver §6) y para joins de M1/M2/M3 contra `propiedades`.
- **Estabilidad frente a cambios de URL:** `listing_id` es el identificador interno del listing en
  `inmopanama.com` (el número que aparece al final de la URL, ej. `_p-143196.htm`); es más estable
  que la URL completa, que podría cambiar de slug (título, zona) sin cambiar de listing — el CSV ya
  trata `listing_id` como el identificador canónico (nombre de columna sin sufijo `_raw`, a
  diferencia de `price_raw`/`price_usd`).
- **`listing_url` no se descarta:** se mantiene como columna con constraint `UNIQUE` (§2.1) — sigue
  siendo la referencia legible/auditable hacia el listing original, solo no es la PK.

No se decide aquí si `listing_id` lleva un `GENERATED ALWAYS AS IDENTITY` adicional o cualquier
otra columna técnica de PK — la decisión de este documento es únicamente **cuál columna existente
del catálogo hace de PK**, no la implementación física final.

---

## 4. Condición de Done ajustada — dos verificaciones separadas

El original mezclaba la creación de la tabla con el índice HNSW en una sola condición. Se separan:

### 4.1 Al crear la tabla (verificación inmediata de 1.5.1)

- Migración `CREATE TABLE propiedades` ejecutada contra Supabase con el esquema de §2 de este
  documento (no el de `DOC-05 §4.2`, que no existe en este repo).
- `\d propiedades` en `psql` muestra exactamente las columnas de §2.1 + `embedding vector(3072)`
  (§2.2) + `geom geometry(Point, 4326)` (§2.3) — ninguna columna adicional no listada aquí, ninguna
  faltante.
- Índice GiST sobre `geom` creado y verificado con `\di` (ej.
  `CREATE INDEX idx_propiedades_geom ON propiedades USING GIST (geom);`).

### 4.2 DIFERIDO — después de 1.5.6 (spike de rendimiento bajo volumen real)

- Índice **HNSW** sobre `embedding` — **no se exige como parte del cierre de 1.5.1**. La propia
  migración de Feature 1.5b (`supabase/migrations/20260715032111_propiedades_embedding.sql`) tiene
  el `CREATE INDEX ... USING hnsw` comentado a propósito, esperando los parámetros (`m`,
  `ef_construction`) que 1.5.6 debe determinar con volumen real de catálogo cargado. Cerrar 1.5.1
  sin este índice es válido y esperado; no es una condición de Done pendiente de 1.5.1 sino de una
  fase posterior.

---

## 5. Coordinación cruzada con `Nota_Pendiente_Migracion_Embedding_1_5.md`

Ese archivo ya documenta el riesgo: si el `CREATE TABLE propiedades` de 1.5.1 se escribe sin
coordinar con la migración de embedding ya existente, alguien podría redefinir `embedding` con
otro tipo/dimensión por accidente (ej. copiando un ejemplo genérico de `vector(1536)` de la
documentación pública de pgvector), contradiciendo la decisión ya verificada de Feature 1.5b.

Cuando se ejecute el `CREATE TABLE` ajustado de este documento, se debe elegir explícitamente una
de las dos opciones ya planteadas en `Nota_Pendiente_Migracion_Embedding_1_5.md` §2 — **no** dejar
`20260715032111_propiedades_embedding.sql` como `ALTER TABLE` separado sin decisión:

- **Opción A:** fusionar `embedding vector(3072)` directamente dentro del `CREATE TABLE
  propiedades` completo (el de este documento) y retirar/no correr la migración de 1.5b por
  separado (quedaría redundante).
- **Opción B:** crear `propiedades` sin `embedding` y correr
  `20260715032111_propiedades_embedding.sql` inmediatamente después, como estaba pensado
  originalmente.

`Nota_Pendiente_Migracion_Embedding_1_5.md` permanece ABIERTA hasta que se elija una de las dos y
quede registrado en el `CREATE TABLE` resultante o en el Acta de cierre de 1.5.1.

---

## 6. Coordinación cruzada con 1.5.4 (`scores_valuacion`)

Mismo tipo de riesgo que §5, aplicado hacia adelante en vez de hacia atrás: 1.5.4 (tabla
`scores_valuacion`, resultados de M2) todavía no está implementada en este repo — no se inventa su
esquema completo aquí, pero su relación con `propiedades` sí queda fijada por la decisión de §3.

**Regla obligatoria para cuando se implemente 1.5.4:** `scores_valuacion` debe referenciar
propiedades vía **`listing_id` (`bigint`)**, con una FK explícita —

```sql
listing_id bigint REFERENCES propiedades(listing_id)
```

— **no** una FK contra `listing_url`, ni una columna de texto libre que duplique la URL o el título
del listing para "identificarlo" de forma paralela. Motivo: es exactamente el mismo tipo de
desalineación que ya se previno en §5 para `embedding` — si quien implemente 1.5.4 elige otra
columna como referencia (por comodidad, por copiar un ejemplo, o por no revisar este documento),
`scores_valuacion` quedaría con una segunda forma de identificar una propiedad, contradictoria con
la PK real de `propiedades`, y los joins de M2/M3 contra ambas tablas se volverían ambiguos o
requerirían normalización posterior no planeada.

Cualquier otra tabla futura que referencie `propiedades` (ej. resultados de M1 si se persisten
fuera de `propiedades.embedding`) debe seguir la misma regla: FK contra `listing_id`, nunca contra
`listing_url` ni una columna derivada.

---

## 7. Coordinación cruzada con 1.5.2 (`corregimientos`) — `propiedades.corregimiento`

Tercer punto simétrico a §5 y §6, mismo motivo: sin una regla explícita aquí, quien implemente
1.5.2 (tabla `corregimientos`) podría nombrar las zonas de forma ligeramente distinta a como ya
existen en el catálogo real — mayúsculas, tildes, orden de palabras — y el join
`propiedades.corregimiento ↔ corregimientos` se rompería en silencio (sin error de FK, solo filas
que dejan de matchear).

**Valores reales verificados** (no asumidos), leídos de
`pipeline/data/processed/catalogo_residencial_limpio_6_2_1.csv` el 2026-07-15, columna
`corregimiento`, 10 valores distintos sobre 1,177 filas:

| Valor exacto | Filas | Tipo (según `CLAUDE.md`, sección "Zonas del scope") |
|---|---|---|
| `San Francisco` | 466 | corregimiento real |
| `Costa del Este` | 191 | zona sin `geom` propio, sin herencia (no recibe score compuesto) |
| `Bella Vista` | 178 | corregimiento real |
| `Betania` | 79 | corregimiento real |
| `El Cangrejo` | 77 | zona sin `geom` propio, hereda de Bella Vista |
| `Obarrio` | 64 | zona sin `geom` propio, hereda de Bella Vista |
| `zona_no_determinada` | 53 | residual de resolución de zona, no es una de las 9 (Acta 1.2 Adenda Duplicados) |
| `Marbella` | 49 | zona sin `geom` propio, hereda de Bella Vista |
| `Parque Lefevre` | 17 | corregimiento real |
| `Pedregal` | 3 | corregimiento real |

Los 9 nombres de zona coinciden exactamente, carácter por carácter, con los listados en
`CLAUDE.md` ("Zonas del scope"). `zona_no_determinada` es el décimo valor — no es una zona de
scope, es la etiqueta de las 53 filas sin `corregimiento` resuelto (documentadas en Acta 1.2).

### 7.1 Decisión: CHECK inmediato, FK condicionada al alcance real de 1.5.2

**`propiedades.corregimiento` lleva, desde el `CREATE TABLE` de 1.5.1, un `CHECK` con la lista
exacta y cerrada de los 10 valores de la tabla anterior:**

```sql
corregimiento text NOT NULL CHECK (
    corregimiento IN (
        'San Francisco', 'Bella Vista', 'Parque Lefevre', 'Betania', 'Pedregal',
        'El Cangrejo', 'Marbella', 'Obarrio', 'Costa del Este',
        'zona_no_determinada'
    )
)
```

Este `CHECK` **no depende de que 1.5.2 esté implementada** — se puede (y debe) aplicar en el
`CREATE TABLE` de 1.5.1 tal cual, usando la lista ya verificada arriba, exactamente como está
escrita en `CLAUDE.md` (misma capitalización, mismos tildes, mismo orden de palabras). Cierra el
riesgo de desalineación de inmediato, sin esperar a 1.5.2.

**La FK contra `corregimientos(nombre)` (o el campo equivalente que use esa tabla) queda
condicionada, no descartada:** `CLAUDE.md` no especifica todavía si la tabla `corregimientos` de
1.5.2 va a tener **9 filas** (una por cada zona de scope, incluyendo las 4 que heredan Zone Health
sin `geom` propio) o **5 filas** (solo los corregimientos administrativos reales, que sí tienen
`geom` y cómputo directo de las 5 dimensiones). Esa decisión no está cerrada en ningún documento de
este repo — no se inventa aquí.

- Si 1.5.2 define `corregimientos` con **9 filas** (una por zona de scope, con las 4 zonas
  heredadas marcadas de alguna forma como "sin `geom` propio, hereda de X"): la FK
  `corregimiento text REFERENCES corregimientos(nombre)` es directa y **se recomienda agregarla**
  en cuanto 1.5.2 exista, reemplazando o complementando el `CHECK` de arriba (`zona_no_determinada`
  seguiría sin match — decidir en ese momento si se permite `NULL` en vez de esa etiqueta, o si se
  mantiene como fila adicional de "cobertura pendiente").
- Si 1.5.2 define `corregimientos` con **solo 5 filas** (los corregimientos administrativos
  reales): la FK **no se puede aplicar tal cual** — `El Cangrejo`, `Marbella`, `Obarrio` y
  `Costa del Este` (381 filas de `propiedades`, casi un tercio del catálogo) no tendrían fila que
  matchear, y el `INSERT`/`UPDATE` fallaría en masa. En ese caso el `CHECK` de §7.1 permanece como
  única validación de `propiedades.corregimiento`, y cualquier mapeo hacia el corregimiento
  contenedor (para heredar Zone Health) se resuelve en código de aplicación o en una columna/tabla
  de mapeo aparte — no en una FK directa.

**Acción obligatoria para quien implemente 1.5.2:** antes de decidir el número de filas de
`corregimientos`, revisar esta sección y registrar explícitamente en el Acta de cierre de 1.5.2
cuál de las dos opciones de arriba se usó, y si la FK de `propiedades.corregimiento` se agregó o si
el `CHECK` de §7.1 se mantiene como única validación — mismo patrón de coordinación explícita que
§5 (embedding) y §6 (`scores_valuacion`), para no repetir el mismo tipo de desalineación silenciosa
una tercera vez.

---

*Este documento no reemplaza una Acta de cierre de 1.5.1 — es la propuesta de esquema para
aprobación. Si se aprueba, el cierre formal de 1.5.1 debe citar este archivo y registrar cuál
opción del §5 se usó, y el cierre de 1.5.2 debe registrar cuál opción del §7 se usó.*
