# Feature 7.2.2 — Auditoría PII: cierre

**Fecha:** 2026-07-16. Sesión de Épica 7 (frontend), a partir de la conexión de
`GET /propiedades/{id}` al Detalle y de la decisión ya cerrada de mostrar `descripcion`
"tal cual, sin editar" (insumo del Quality Scorer).

## 1. Clasificación de columnas de `propiedades`

| Clasificación | Columnas |
|---|---|
| Público (visible en el anuncio de inmopanama.com) | `listing_url`, `title`, `price_raw`/`price_usd`, `bedrooms`, `bathrooms`, `area_m2`, `operation`, `tipo_inmueble`, `imagenes` |
| Derivado/interno (nuestro, no visible en el anuncio) | `zone_raw`, `corregimiento`, `zone_source`, `corregimiento_archivo`, `precio_no_evaluable`, `precio_no_evaluable_motivo`, `source`, `scraped_at`, `descripcion_fuente`, `enriquecimiento_estado`, `enriquecimiento_error_detalle`, `embedding`, `geom` (sintético), `ubicacion_aproximada` |
| **Potencialmente sensible** | **`descripcion`** — ver §2 |

## 2. `listing_url` — confirmado seguro

Apunta al anuncio público original en `inmopanama.com` (ej.
`https://www.inmopanama.com/lujoso-loft-frente-al-mar-avenida-balboa_p-143181.htm`).
Verificado en vivo: HTTP 200 sin autenticación, contenido completo (no hay muro de
login). La propia página destino ya expone públicamente el teléfono/WhatsApp del
anunciante — el botón "Contactar anunciante" (implementado en este cierre, enlace
directo con `target="_blank"`) no crea exposición nueva, replica lo que
inmopanama.com ya muestra en esa misma URL.

## 3. Hallazgo — PII incrustada en `descripcion`

Escaneo completo de las 1,168 filas con `descripcion` no nula (no solo una muestra):

- **7/1,168 filas (0.6%) con teléfono panameño real** incrustado en el texto libre,
  11 coincidencias totales (algunas filas tienen 2 números).
- **1/1,168 filas con email real** (`moi.camen@kwpanama.com`, listing_id=136553).
- Al menos 2 filas incluyen nombre propio de agente inmobiliario junto al contacto
  (Diego Cantón en 136553, Elisia Motta en 143051).
- Formatos vistos: `6XXX-XXXX`, `+507 6XXX-XXXX`, `+ 507 6XXX-XXXX` (espacio entre "+"
  y "507"), `+50763710895` (sin separadores).
- `listing_id` afectados: 136553, 143051, 136835, 137007, 137102, 143055, 143140.

Como `descripcion` ya se decidió mostrar sin editar (insumo del Quality Scorer), esta
PII ya estaba expuesta en el Detalle antes de esta auditoría, sin que el frontend lo
supiera.

## 4. Decisión tomada

- **Botón "Contactar anunciante"**: enlaza directo a `listing_url`, sin lógica
  adicional — la página destino ya expone el contacto públicamente (§2).
  `backend/app/routers/propiedades.py` ahora expone `listing_url` en
  `GET /propiedades/{id}` (no estaba antes de este cierre).
- **Sanitización de `descripcion`**: `frontend/lib/sanitize-pii.ts` — regex de
  teléfono panameño + email, reemplazo por `"[contacto de terceros removido]"`.
  Verificado contra las 1,168 filas reales: 11 coincidencias de teléfono en 7 filas, 1
  de email, **cero falsos positivos** (no confunde `area_m2`/precio con teléfono).
  **La columna en Supabase NO se toca** — mismo criterio que el fix de encoding
  Windows-1252 (`sanitizeText()`), M2/Quality Scorer siguen leyendo el dato crudo
  directo de la DB, nunca de este objeto de frontend.

### Hallazgo secundario durante la implementación — sanitizar solo en el render no bastaba

La primera implementación aplicaba `sanitizePii()` dentro de `PropertyDetail.tsx`
("use client") en el momento de renderizar. Verificado en vivo (`curl` sobre el HTML
servido de `/propiedad/136553`) que el teléfono/email **crudos seguían presentes** en
el payload de hidratación de Next.js (`<script>` de RSC), aunque el DOM visible ya
mostraba el texto sanitizado — un "ver código fuente" del navegador exponía igual el
dato crudo. Corregido moviendo `sanitizePii()` a `frontend/lib/propiedades.ts`
(`obtenerPropiedadPorId`), que corre en el Server Component antes de que el objeto
cruce el límite servidor→cliente — ahí es la única forma real de que el string crudo
nunca llegue al navegador. Reverificado tras el fix: 0 ocurrencias de los 11 números/1
email reales en el HTML servido, para los 7 `listing_id` afectados.

## Verificación final (evidencia)

Antes/después sobre los 7 casos reales (ejemplo, listing_id=136553):

```
ANTES:   "Cel: +507 6371-0895"
DESPUÉS: "Cel: [contacto de terceros removido]"
ANTES:   "Email: moi.camen@kwpanama.com"
DESPUÉS: "Email: [contacto de terceros removido]"
```

`tsc --noEmit` y `next lint` limpios. Páginas de detalle de los 7 `listing_id`
verificadas en vivo contra backend local real — 0 PII cruda en el HTML servido
(DOM ni payload de hidratación) en los 7 casos.
