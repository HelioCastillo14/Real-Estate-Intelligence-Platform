-- 1.5.1 — CREATE TABLE propiedades (esquema aprobado)
-- Fuente de la decisión: Context-MD/Ajuste_WBS_1_5_1_Esquema_Propiedades.md (versión final,
-- aprobada 2026-07-15) — reemplaza formalmente la Condición de Done original de 1.5.1, que remitía
-- a `DOC-05 §4.2` (documento inexistente en este repo, confirmado sin resultado). Ver también
-- Context-MD/Gobernanza_WBS_vs_Feature_6_2.md, entrada "1.5.1" en la sección 3.
--
-- NO EJECUTADA CONTRA SUPABASE. Acción sobre infraestructura compartida — requiere confirmación
-- explícita del usuario en el momento de aplicarla (no basta con este archivo existiendo en el
-- repo). Preparada para revisión, no para correr automáticamente.
--
-- Requiere las extensiones pgvector (1.1.1) y PostGIS ya habilitadas.
--
-- Actualización 2026-07-15 (post-corrida de imágenes): se fusiona `imagenes text[]` (§2.4).
-- 1 fila (listing_id 137025) quedó sin `imagenes` por un fallo de red aislado durante esa
-- corrida — ver comentario de la columna más abajo. No bloqueante para este CREATE TABLE.

-- Opción elegida para la columna `embedding` (Ajuste_WBS_1_5_1_Esquema_Propiedades.md §5):
-- OPCIÓN A — `embedding vector(3072)` se fusiona directamente en este CREATE TABLE. La migración
-- `20260715032111_propiedades_embedding.sql` (Feature 1.5b, `ALTER TABLE ... ADD COLUMN IF NOT
-- EXISTS`) queda redundante una vez esta migración corra — no se retira el archivo (registro
-- histórico de la decisión de dimensión), pero no debe ejecutarse después de esta migración: al
-- correr después de este CREATE TABLE, su `ADD COLUMN IF NOT EXISTS embedding` sería un no-op
-- (la columna ya existiría con el tipo correcto), así que es inofensiva pero innecesaria.

create table if not exists propiedades (
    -- Identidad (Ajuste_WBS_1_5_1_Esquema_Propiedades.md §3 — PK = listing_id, no listing_url)
    listing_id                   bigint primary key,
    listing_url                  text not null unique,

    -- Columnas derivadas del catálogo real (§2.1) — catalogo_residencial_limpio_6_2_1.csv,
    -- 1,177 filas, header y nulls verificados contra el archivo real el 2026-07-15.
    title                        text not null,
    zone_raw                     text not null,
    corregimiento                text not null,
    zone_source                  text not null
        check (zone_source in ('zone_raw', 'zone_raw_barrio_mapeado', 'pagina_scrapeada_no_resuelto')),
    price_raw                    text not null,
    price_usd                    integer not null,
    precio_no_evaluable          boolean not null default false,
    precio_no_evaluable_motivo   text,
    bedrooms                     smallint,
    bathrooms                    smallint,
    area_m2                      numeric,
    operation                    text not null
        check (operation in ('venta', 'alquiler')),
    source                       text not null,
    scraped_at                   timestamp not null,
    corregimiento_archivo        text not null,
    tipo_inmueble                text not null
        check (tipo_inmueble in ('Apartamentos', 'Casas', 'Edificios', 'Locales', 'Terrenos')),
    descripcion                  text,
    descripcion_fuente           text not null
        check (descripcion_fuente in ('completa', 'preview', 'ninguna')),
    -- 4 categorias fijas -- normalizado 2026-07-15 para que este CHECK no dependa del
    -- nombre de una excepcion de Python ni de cual de dos variantes de "faltaba
    -- contenido" ocurrio (antes 'error_red:ConnectionError' rompia cualquier lista de
    -- valores fijos; 'sin_breadcrumb'/'sin_ambos' de enriquecer_detalle.py tampoco
    -- estaban cubiertos -- 0 ocurrencias en el catalogo actual, pero el codigo del
    -- scraper puede producirlos, asi que se cierran preventivamente aqui antes de que
    -- ocurran, no despues). El detalle especifico de cada caso vive en
    -- enriquecimiento_error_detalle (sin CHECK, texto libre), no aqui:
    --   'ok'              -> caso normal, sin detalle
    --   'sin_descripcion' -> detalle '' | 'sin_breadcrumb' | 'sin_ambos'
    --   'error_red'       -> detalle = nombre de la excepcion (ej. 'ConnectionError')
    --   'sin_url'         -> falta listing_url en el CSV, la pagina nunca se visito
    --                        (categoria distinta de 'sin_descripcion' -- no es la misma
    --                        causa, no se normaliza junto con esa)
    enriquecimiento_estado       text not null
        check (enriquecimiento_estado in ('ok', 'sin_descripcion', 'error_red', 'sin_url')),
    -- Poblada solo cuando enriquecimiento_estado in ('sin_descripcion', 'error_red') --
    -- ver mapeo arriba. Sin CHECK a proposito -- no tiene sentido restringir un
    -- conjunto cerrado de nombres de excepciones de red, que puede crecer sin previo
    -- aviso.
    enriquecimiento_error_detalle text,

    -- §7 — CHECK inmediato sobre corregimiento (9 zonas de scope + zona_no_determinada),
    -- lista verificada carácter por carácter contra CLAUDE.md y el catálogo real. FK contra
    -- corregimientos(nombre) queda condicionada al número de filas que defina 1.5.2 — ver
    -- Ajuste_WBS_1_5_1_Esquema_Propiedades.md §7.1. No se agrega aquí porque 1.5.2 no existe
    -- todavía en este repo.
    constraint chk_propiedades_corregimiento check (
        corregimiento in (
            'San Francisco', 'Bella Vista', 'Parque Lefevre', 'Betania', 'Pedregal',
            'El Cangrejo', 'Marbella', 'Obarrio', 'Costa del Este',
            'zona_no_determinada'
        )
    ),

    -- §2.2 — Feature 1.5b, dimensión verificada contra la API real (gemini-embedding-001).
    embedding                    vector(3072),

    -- §2.3 — Point/PostGIS. APROXIMACIÓN SINTÉTICA PARA VISUALIZACIÓN, NO LA COORDENADA REAL DEL
    -- LISTING (inmopanama.com no expone coordenadas reales — misma razón por la que 3.1.1
    -- descarta ST_Distance para comparables de M2). Nunca usar como insumo de modelo.
    geom                          geometry(Point, 4326),

    -- §2.4 — Arquitectura hotlink (Opción A, decisión cerrada 2026-07-15): solo se guarda la URL
    -- de cada imagen, nunca el archivo. Nullable porque la corrida de enriquecer_detalle.py que
    -- pobló esta columna (2026-07-15) dejó 1 fila (listing_id 137025) sin imagenes por un fallo
    -- de red aislado durante esa corrida — NO bloqueante para crear la tabla, pendiente de una
    -- corrida adicional del script (su filtro de `pendientes` ya la recogerá automáticamente, sin
    -- reprocesar las filas que ya tienen imagenes poblado). Ver
    -- Ajuste_WBS_1_5_1_Esquema_Propiedades.md §2.4.
    imagenes                      text[]
);

comment on column propiedades.geom is
    'Aproximación sintética (ST_GeneratePoints o equivalente) para visualización en mapa. '
    'NO es la coordenada real del listing — inmopanama.com no la expone. Nunca usar como insumo '
    'de modelo (M1/M2/M3). Ver Ajuste_WBS_1_5_1_Esquema_Propiedades.md §2.3.';

comment on column propiedades.embedding is
    'gemini-embedding-001, 3072 dimensiones. Verificado contra la API real en 6.2.3. '
    'Ver Feature_1_5b_Embedding_Dimension_Cierre.md.';

comment on column propiedades.imagenes is
    'URLs de imagen extraídas de .ib-prop-gallery-main .swiper-slide img en la página de detalle '
    '(hotlink, Opción A — nunca se descarga ni almacena el archivo). Orden preservado por '
    'posición del array (orden real del carrusel). Nullable: listing_id 137025 quedó sin poblar '
    'por un fallo de red aislado en la corrida de 2026-07-15 (enriquecimiento_estado = '
    '''error_red'', enriquecimiento_error_detalle = ''ConnectionError'' para esa fila) — '
    'requiere una corrida adicional de enriquecer_detalle.py antes de considerarse completo, '
    'pero no bloquea el CREATE TABLE. '
    'Carga de datos: el CSV serializa esta columna como JSON-string (json.dumps) — requiere '
    'json.loads() explícito antes de insertar como text[], nunca reconstrucción manual de '
    'string. Ver Ajuste_WBS_1_5_1_Esquema_Propiedades.md §2.4, §2.4.1, §2.4.2.';

comment on column propiedades.enriquecimiento_error_detalle is
    'Detalle de caso, poblado solo cuando enriquecimiento_estado no es ''ok'' ni ''sin_url'': '
    'nombre de la excepción de red (ej. "ConnectionError") si enriquecimiento_estado = '
    '''error_red''; ''sin_breadcrumb'' o ''sin_ambos'' si enriquecimiento_estado = '
    '''sin_descripcion'' y se quiere distinguir cuál de las dos variantes ocurrió (ambas '
    '0 ocurrencias en el catálogo actual, cerradas preventivamente en el CHECK antes de '
    'que ocurran). NULL/vacío en cualquier otro caso. Sin CHECK a propósito — texto '
    'libre, no un conjunto cerrado de valores. Ver Ajuste_WBS_1_5_1_Esquema_Propiedades.md §2.1.';

-- §4.1 — Índice GiST sobre geom, parte de la verificación inmediata de 1.5.1.
create index if not exists idx_propiedades_geom
    on propiedades using gist (geom);

-- §4.2 — Índice HNSW sobre embedding: DIFERIDO a después de 1.5.6 (spike de rendimiento bajo
-- volumen real). No se crea en esta migración — no es condición de Done de 1.5.1.
-- create index if not exists idx_propiedades_embedding_hnsw
--     on propiedades using hnsw (embedding vector_cosine_ops)
--     with (m = ..., ef_construction = ...);  -- parámetros a determinar por 1.5.6
