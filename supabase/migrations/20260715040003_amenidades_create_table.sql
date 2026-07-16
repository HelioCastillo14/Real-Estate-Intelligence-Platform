-- 1.5.3 — CREATE TABLE amenidades (esquema aprobado)
-- Fuente de la decisión: Context-MD/Ajuste_WBS_1_5_3_Esquema_Amenidades.md §4 (diseño aprobado
-- 2026-07-15, pendiente de ejecución).
--
-- NO EJECUTADA CONTRA SUPABASE. Acción sobre infraestructura compartida — requiere confirmación
-- explícita del usuario en el momento de aplicarla (no basta con este archivo existiendo en el
-- repo). Mismo protocolo que 20260715040000_propiedades_create_table.sql (1.5.1),
-- 20260715040001_corregimientos_create_table.sql (1.5.2) y
-- 20260715040002_perfiles_lifestyle_y_conjunto_referencia_m1.sql (1.5.5).
--
-- Decisión de fondo (§2): amenidades_betania_obarrio_cangrejo_marbella_osm.geojson (130
-- features) EXCLUIDO de la carga con evidencia — ninguna de sus 60 claves de properties indica
-- zona por punto individual (bbox único de una sola consulta Overpass cubriendo 4 zonas a la
-- vez). Cobertura real de esta tabla: 6 zonas (5 corregimientos oficiales + Costa del Este), no
-- las 9 del scope de negocio — El Cangrejo/Marbella/Obarrio quedan sin amenidades propias,
-- documentado como limitación de datos, no como omisión silenciosa.
--
-- Requiere la extensión PostGIS ya habilitada (compartida con propiedades.geom/corregimientos.geom)
-- y la tabla corregimientos (1.5.2) ya creada — corregimiento_asignado la referencia.

create table if not exists amenidades (
    id                        bigserial primary key,

    categoria                 text not null
        check (categoria in ('supermercado', 'farmacia', 'hospital', 'clinica', 'parque', 'colegio')),
    -- 6 categorías CRUDAS, sin fusionar. La fusión hospital+clinica -> "salud" es
    -- cómputo de Zone Health (Feature 1.4.3), no propiedad del dato fuente — se
    -- aplica en la consulta/vista que alimenta el composite, no aquí.

    nombre                    text,

    geom                      geometry(Point, 4326) not null,
    geom_tipo_origen          text not null
        check (geom_tipo_origen in ('point', 'polygon_centroid')),
    -- OSM mezcla Point (nodos) y Polygon (ways/edificios) — Pedregal y otros. Todo
    -- se normaliza a Point; polygon_centroid deja explícito cuándo la coordenada es
    -- una aproximación (centroide), no la ubicación exacta del POI.

    fuente                    text not null
        check (fuente in ('google_places', 'osm_overpass')),
    -- Determinado por presencia real de place_id, NUNCA asumido por el nombre del
    -- archivo — el caso de Parque Lefevre (1 registro Google Places dentro de un
    -- archivo "OSM") es evidencia directa de por qué esto importa.

    zona_etiquetada_origen    text not null,
    -- Nombre de la zona según el archivo/consulta de origen (San Francisco, Bella
    -- Vista, Costa del Este, Betania, Parque Lefevre, Pedregal). Preservado incluso
    -- cuando diverge del resultado geométrico real.

    corregimiento_asignado    text references corregimientos(nombre),
    -- Resultado REAL de asignar_corregimiento() — aplicado a las 238 filas sin
    -- excepción, no solo a las de origen OSM. NULL para Costa del Este (fuera de
    -- las 5 zonas que cubre la función) — caso esperado, no error.

    place_id                  text,
    telefono                  text,
    rating                    numeric,
    -- Solo poblados cuando fuente = 'google_places'.

    propiedades_raw           jsonb not null,
    -- Preserva las ~60 claves inconsistentes de OSM (amenity/shop/leisure,
    -- healthcare:speciality, contact:*, wikidata, etc.) sin forzar columnas
    -- individuales para cada una. Para Google Places, preserva el objeto JSONL
    -- completo tal cual.

    nota_auditoria             text
    -- Texto libre, sin CHECK. Poblado cuando la fila tiene una limitación conocida
    -- documentada (ej. Costa del Este clinica=0 sesgo de extracción no corregido,
    -- Parque Lefevre registro migrado de otra zona).
);

comment on column amenidades.corregimiento_asignado is
    'Resultado real de pipeline/zone_health/cruce_espacial_corregimiento.py::'
    'asignar_corregimiento(), aplicado sin excepción a las 6 fuentes cargadas. '
    'NULL para Costa del Este — fuera de las 5 zonas que cubre la función (no tiene '
    'polígono administrativo oficial). zona_etiquetada_origen es la fuente de verdad '
    'de zona en ese caso.';

comment on column amenidades.zona_etiquetada_origen is
    'Zona según el archivo/consulta de origen. Puede divergir de '
    'corregimiento_asignado — no colapsar ambos campos en uno solo. Ejemplo real: '
    'un registro en amenidades_parque_lefevre_osm.geojson es en realidad de San '
    'Francisco (migración documentada en el propio archivo, nota_auditoria).';

create index if not exists idx_amenidades_geom on amenidades using gist (geom);
