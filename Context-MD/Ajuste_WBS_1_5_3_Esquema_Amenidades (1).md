# Ajuste WBS — Feature 1.5.3: Esquema de tabla `amenidades`

**Fecha:** 2026-07-15
**Estado:** Diseño aprobado — pendiente de ejecución
**Fuente de las decisiones:** `Feature_1_3_Carga_Datos_Externos_Acta.md` §7-8 + `LOG_EXTRACCION.md` + investigación de archivos reales en esta sesión + `pipeline/zone_health/cruce_espacial_corregimiento.py` (ya existente, probado, 3/3 tests)

---

## 1. Resultado de la investigación — el dato crudo sí persiste, con reservas importantes

A diferencia de `1.5.5` (donde el ground truth no existía en disco), aquí **7 archivos de datos reales sí existen** en `pipeline/data/external/amenidades/`: 3 JSONL de Google Places (San Francisco, Bella Vista, Costa del Este) y 4 GeoJSON de OSM Overpass (Betania, Parque Lefevre, Pedregal, más un archivo combinado descartado — ver §2).

**Esto cambia el carácter de la tarea** respecto a lo que el WBS anticipaba ("puede requerir re-consultar Google Places/OSM si no existe el dato intermedio") — no hace falta re-extracción, pero sí una reconciliación real antes de cargar, porque los archivos no son uniformes ni todos confiables al mismo nivel.

## 2. Decisión de fondo — exclusión del archivo combinado, no una simplificación

`amenidades_betania_obarrio_cangrejo_marbella_osm.geojson` (130 features) **se excluye por completo de la carga**, con evidencia, no por conveniencia:

- **Ninguna de las 60 claves de `properties` en el archivo indica a qué zona corresponde cada punto individualmente** — el archivo es una bolsa sin distinción interna, producto de una sola consulta Overpass con bbox único cubriendo las 4 áreas a la vez (confirmado en `LOG_EXTRACCION.md`, sin script de extracción versionado).
- **Aplicar `asignar_corregimiento()` a los 130 puntos** (lectura, sin cargar) mostró que el 95% (123/130) resuelve geométricamente a Bella Vista o San Francisco — zonas que **ya tienen fuente canónica de mayor calidad** (Google Places, con `place_id`/teléfono/rating), descartando OSM explícitamente desde Feature 1.3.7 §4.4. Solo 5 puntos caen en Betania — muy por debajo de los 104 del archivo dedicado y re-extraído específicamente para esa zona.
- **Conclusión con evidencia, no supuesto:** El Cangrejo, Marbella y Obarrio no tienen amenidades verificables en el repo — no por decisión de diseño, sino porque la extracción real nunca las capturó de forma distinguible por zona. Consistente con que estas 3 zonas ya heredan su Zone Health de Bella Vista sin usar su propia extracción de amenidades (Feature 1.4.3).

**Consecuencia:** `amenidades` cubre **6 zonas**, no 9 — las 5 oficiales + Costa del Este (Google Places canónico, pese a no ser oficial). El Cangrejo, Marbella, Obarrio quedan sin amenidades propias, documentado como limitación de datos.

## 3. Verificación geométrica — aplicada sin excepción, incluyendo archivos "dedicados"

`pipeline/zone_health/cruce_espacial_corregimiento.py` ya existe, ya está probado (3/3 tests pasan), y ya se usa en producción (`normalizacion_amenidades.py`, `normalizacion_walkability.py`) — **pero hasta ahora solo se aplicó de forma ad hoc a los archivos OSM**, no sistemáticamente a los 3 archivos de Google Places (confirmado por Claude Code: "3/18 registros mal asignados en Bella Vista Google Places, San Francisco y Costa del Este pendientes de la misma auditoría" — hallazgo ya anotado en CLAUDE.md).

**Regla operativa aplicada aquí sin excepción, cerrando esa brecha:** `asignar_corregimiento()` se corre sobre **todas** las 238 filas restantes (San Francisco 30 + Bella Vista 15 + Costa del Este 24 + Betania 104 + Parque Lefevre 53 + Pedregal 12), no solo sobre las de origen OSM. El nombre del archivo/fuente (`zona_etiquetada_origen`) se preserva junto al resultado geométrico real (`corregimiento_asignado`) — no se colapsan en un solo campo, porque pueden divergir (ya ocurrió: el registro de Parque Lefevre que en realidad es de San Francisco, migrado sin corregir el nombre del archivo).

**Nota:** Costa del Este, El Cangrejo, Marbella y Obarrio no tienen polígono en `corregimientos_5zonas_poligonos_raw_osm.geojson` (la función solo cubre las 5 zonas administrativas oficiales) — para Costa del Este, `corregimiento_asignado` será `NULL` en la mayoría de casos (la función devuelve `None` por diseño, caso esperado, no error) y `zona_etiquetada_origen = 'Costa del Este'` queda como la única fuente de verdad de zona para esas filas.

### 3.1 Hallazgo confirmado en ejecución — 13/24 filas de Costa del Este resuelven a Parque Lefevre

Al correr `asignar_corregimiento()` sin excepción sobre las 24 filas de Costa del Este, **13 resolvieron geométricamente a Parque Lefevre**, no a `NULL` como se anticipaba en el diseño original. Esto **no es un error de asignación** — es la confirmación empírica de un hallazgo ya documentado formalmente en `Feature_1_3_7_Extraccion_Amenidades_Acta.md` §5.3: una porción real del territorio que el mercado conoce como "Costa del Este" cae administrativamente dentro de Parque Lefevre (POIs como "Parque costa del este" y "The Casco School - Costa del Este" ya estaban identificados ahí como genuinamente atribuidos a Parque Lefevre, no como error de extracción).

**Distinción importante frente al caso de Parque Lefevre/San Francisco (§1 nota_auditoria, 1 fila):** ese caso es un error de extracción corregido (POI movido de archivo sin actualizar metadata). Este caso (13 filas) es geografía real documentada — no se "corrige", se carga tal cual con `corregimiento_asignado = 'Parque Lefevre'` real y `zona_etiquetada_origen = 'Costa del Este'` preservado, exactamente el mecanismo que el esquema ya provee para divergencias.

**Consecuencia aceptada, no resuelta aquí:** el Zone Health composite de Parque Lefevre (0.3765, ya cerrado y cargado en `1.5.2`) se calculó en Feature 1.4.3 usando solo `amenidades_parque_lefevre_osm.geojson` (53 features) — sin estas 13 filas, que no habían sido cruzadas geométricamente en ese momento. **No se recalcula Zone Health como parte de 1.5.3** — queda documentado como limitación conocida y evidencia disponible para una futura re-auditoría de Feature 1.4 (decisión de gobernanza, no técnica, fuera de alcance de esta tarea).

## 4. Esquema de columnas

```sql
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
```

## 5. Zonas excluidas — documentado, no oculto

**El Cangrejo, Marbella, Obarrio:** sin amenidades propias cargadas. `amenidades_betania_obarrio_cangrejo_marbella_osm.geojson` excluido por evidencia (§2), no por decisión arbitraria. Si en el futuro se requiere cobertura real para estas 3 zonas, la tarea es una re-extracción dirigida por zona (con bbox individual, no combinado) — no un ajuste de este esquema.

## 6. Checkpoint de cierre de 1.5.3

- [ ] Migración `CREATE TABLE amenidades` ejecutada contra Supabase (confirmación explícita, mismo protocolo)
- [ ] `asignar_corregimiento()` corrida sobre las 238 filas (no solo las de origen OSM) antes de o durante la carga
- [ ] 238 filas cargadas: San Francisco 30, Bella Vista 15, Costa del Este 24, Betania 104, Parque Lefevre 53, Pedregal 12
- [ ] `fuente` determinado por presencia real de `place_id`, verificado por fila, no asumido por archivo
- [ ] Costa del Este: 11/24 filas con `corregimiento_asignado = NULL`, 13/24 con `corregimiento_asignado = 'Parque Lefevre'` (geografía real documentada, Acta 1.3.7 §5.3 — no error) — todas con `zona_etiquetada_origen = 'Costa del Este'` preservado, y `nota_auditoria` citando la Acta para las 13
- [ ] Registro de Parque Lefevre con origen real Google Places cargado con `fuente = 'google_places'` (no `'osm_overpass'` solo porque estaba en ese archivo) y `nota_auditoria` poblada (caso distinto: error de extracción corregido, no geografía real)
- [ ] Consulta de prueba `ST_DWithin` responde correctamente (condición de Done original del WBS)

## 7. Pendiente explícito, fuera de alcance de 1.5.3

1. Auditoría sistemática de los 3 archivos Google Places contra `asignar_corregimiento()` — ya se hace como parte de esta carga (§3), cerrando la brecha que CLAUDE.md ya documentaba como pendiente.
2. Re-extracción dirigida de El Cangrejo/Marbella/Obarrio si se decide que el frontend necesita amenidades propias para esas zonas (Épica 5) — fuera de alcance de esquema, es trabajo de pipeline nuevo.
3. Vista o consulta que fusione `hospital`+`clinica` en `salud` para alimentar Zone Health — no se construye en 1.5.3, ya que el Zone Health Index para estas zonas ya está calculado y cargado (Feature 1.4.6 / 1.5.2); esta vista sería relevante solo si se recalcula el índice en el futuro.
