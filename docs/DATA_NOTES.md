# Notas sobre datos y PII

Auditoría de PII sin enmascarar sobre `pipeline/data/`, notebooks y artifacts de
modelo, hecha antes del merge `dev` → `main` (2026-07-21).

## Redactado

- **`pipeline/data/processed/catalogo_residencial_limpio_6_2_1.csv`** — columna
  `descripcion`, 7 filas (`listing_id` 136553, 136835, 137007, 137102, 143051, 143055,
  143140) tenían bloque de contacto de agente inmobiliario (teléfono/email personal)
  pegado en el texto libre por el enriquecimiento de detalle. Reemplazado por
  `[contacto removido]`, filas conservadas.
  **Nota:** este archivo está en `.gitignore` (`pipeline/data/processed/*`) y nunca
  estuvo en el historial de git — la redacción es higiene del dataset local, no un
  fix de exposición en el repo.
  **Estos son los mismos 7 `listing_id` que `frontend/lib/sanitize-pii.ts` ya
  sanitizaba en el Server Component desde Feature 7.2.2** (`Context-MD/Feature_7_2_2_Auditoria_PII_Cierre.md`)
  — confirma que ese fix era solo de capa de presentación: nunca tocó el dato fuente,
  que siguió con la PII cruda disponible para cualquier proceso que leyera la columna
  directo (M1 embeddings, M2 Quality Scorer).
- **`pipeline/data/external/amenidades/amenidades_betania_obarrio_cangrejo_marbella_osm.geojson`**
  — campo `email` de un nodo OSM (`tats85@hotmail.com`, escuela de baile), dominio de
  correo personal, no corporativo. Reemplazado por `[contacto removido]`.

## Dejado tal cual — contacto público de negocio, no PII sensible

- `cliente@superxtra.com` (`amenidades_pedregal_osm.geojson`,
  `amenidades_betania_obarrio_cangrejo_marbella_osm.geojson`,
  `amenidades_parque_lefevre_osm.geojson`) — email corporativo de cadena de
  supermercados, publicado por el propio negocio en OSM.
- Teléfonos en `amenidades_*_google_places.jsonl` (Costa del Este, Bella Vista, San
  Francisco) — campo `telefono` de negocios (supermercados, comercios), dato de Google
  Places, público por diseño de la fuente.

Estas son entidades (negocios), no personas físicas — no se tratan como PII a
redactar.
