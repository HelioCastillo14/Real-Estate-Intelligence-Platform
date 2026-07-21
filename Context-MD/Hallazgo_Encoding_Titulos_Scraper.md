# Hallazgo — bytes C1 de Windows-1252 sin decodificar en `title`/`descripcion`

**Fecha:** 2026-07-16

## Qué se encontró

`propiedades.title` y `propiedades.descripcion` contienen bytes de control C1
(`\x80`-`\x9f`) crudos, sin decodificar — específicamente `\x91`, `\x92`, `\x93`, `\x94`
(comillas/apóstrofes curvos de Windows-1252) y `\x96`/`\x97` (guion medio/largo). Se
verificó contra la base real:

- **44 filas** con el defecto en `title`.
- **220 filas** con el defecto en `descripcion`.
- **256 filas distintas** en total (unión de ambos conjuntos).

**Corrección de cifra:** una primera revisión con `LIMIT 10` había reportado "10 filas" —
esa cifra era un artefacto del `LIMIT` de la consulta de muestra, no el total real. Las
cifras de arriba son el conteo completo (`count(*)`, sin `LIMIT`), verificado dos veces.

Ejemplo real (`listing_id=136217`):
```
título en DB (crudo):     'VENTA DE APARTAMENTOS \x96 PROYECTO ARMONÍA, BELLA VISTA'
debería decir:             'VENTA DE APARTAMENTOS – PROYECTO ARMONÍA, BELLA VISTA'
```

## Causa raíz probable

El patrón (bytes 0x91-0x94, 0x96-0x97 específicamente, que en Windows-1252 son comillas
curvas y guiones) es característico de texto que se codificó originalmente en
Windows-1252/CP1252 (probable en una fuente de datos de Panamá/Latinoamérica) y se
decodificó como si fuera Latin-1 o se transcodificó incorrectamente a UTF-8 en algún
punto entre el scraper y la carga a Supabase. **No se investigó en esta sesión en qué
paso exacto del pipeline se introduce el defecto** — pudo ser en el scraping mismo
(`pipeline/scraper/`), en un paso de limpieza/enriquecimiento, o en la carga a la tabla
`propiedades`.

## Qué se corrigió y qué no

**Corregido solo a nivel de display (frontend):** `frontend/lib/sanitize-text.ts`
reemplaza los bytes conocidos por su carácter UTF-8 correcto (`'`, `'`, `"`, `"`, `–`,
`—`) antes de renderizar `title`/`descripcion` en `PropertyCard.tsx` y
`PropertyDetail.tsx`. Es un parche cosmético — la fila en Supabase sigue con el byte
crudo sin modificar.

**Pendiente:** corregir en origen (pipeline de scraping o un `UPDATE` puntual sobre las
256 filas ya identificadas en la DB) para que el defecto no se repita en futuros
re-scrapes, y para que cualquier otro consumidor de `title`/`descripcion` que no pase por
`sanitizeText()` (por ejemplo, el LLM Quality Scorer, que ya evaluó las 220 filas de
`descripcion` afectadas con el byte crudo, antes de que existiera este fix) no herede el
mismo defecto. **El fix de esta sesión no cambia el dato que el Quality Scorer ya
evaluó** — solo corrige cómo se muestra en el navegador, no lo que hay en la base.
