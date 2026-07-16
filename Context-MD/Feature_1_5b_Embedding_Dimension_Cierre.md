# Feature 1.5b — Dimensión de embedding en el esquema derivado — Cierre

**Fecha de cierre:** 2026-07-14
**Estado:** CERRADO (alcance acotado — ver §4)

---

## 1. Qué era "1.5b"

No es un ID formal del WBS (`REIP_WBS.xlsx` solo tiene 1.5.1–1.5.6). Es la sub-decisión, dentro de
la Condición de Done de **1.5.1** ("Implementar tabla `propiedades` con columna `geom` ... y
`embedding` (vector/pgvector) + índice GiST y HNSW"), que quedó pospuesta porque el modelo de
embeddings y su dimensión no estaban confirmados contra la API real. Referenciada explícitamente
en `Context-MD/Feature_6.2_Contexto_Ejecucion_v2.md` §4: *"modelo de embeddings y dimensión
documentados con precisión (desbloquea 1.5b a futuro)"*.

## 2. Por qué ya no aplica la pausa

`Context-MD/Feature_6_2_3_M1_Preference_Matching_Cierre.md` §2 confirma, contra la API real (no
asumido de documentación): **`gemini-embedding-001`, 3072 dimensiones**. `text-embedding-004`
(nombre de versiones anteriores de la documentación pública de Gemini) ya no existe en esta API.
Los artifacts de 6.2.3 (`pipeline/models/embeddings_catalogo_6_2_3_raw.pkl`,
`embeddings_perfiles_6_2_3_raw.pkl`) son vectores de 3072-dim reales, no una cifra teórica.

`CLAUDE.md` documenta la misma confirmación como decisión de repo vigente.

## 3. Decisión

`propiedades.embedding` se define como **`vector(3072)`** (extensión `pgvector`, ya habilitada
por 1.1.1) en el esquema de Supabase. DDL de referencia en
`supabase/migrations/20260715032111_propiedades_embedding.sql`.

## 4. Alcance de este cierre — qué NO resuelve

Este cierre resuelve **únicamente** la dimensión del vector, que era el único motivo documentado
de la pausa. No resuelve el resto de 1.5.1:

- La Condición de Done de 1.5.1 remite a `DOC-05 §4.2` para el resto del esquema de `propiedades`
  (campos, tipos, constraints más allá de `embedding`). Ese documento no está en este repo — no se
  inventa aquí el resto de la tabla. Falta esa fuente para cerrar 1.5.1 completo.
- Los índices GiST (sobre `geom`) y HNSW (sobre `embedding`) siguen sin implementarse.
- **1.5.1 permanece "no iniciado"** en el WBS; solo su sub-bloqueo de dimensión queda cerrado.
- No se ejecutó ninguna migración contra el Supabase real del proyecto — el DDL de §3 es un
  artifact de repo, pendiente de aplicar cuando el resto de 1.5.1 esté especificado y se decida
  correrlo (acción sobre infraestructura compartida, requiere confirmación explícita aparte).

## 5. Estado de 2.1.3 tras este cierre

2.1.3 ("Ejecutar batch de embeddings sobre todo el catálogo y almacenar en `propiedades.embedding`")
depende de `2.1.2, 1.5.1, 1.2.7` (WBS, hoja `2.0 M1 Preference Matching`).

- **1.2.7:** Completado.
- **1.5.1:** el único motivo de bloqueo *documentado como decisión pendiente* (dimensión de
  embedding) queda resuelto por este cierre. El resto de 1.5.1 (creación real de la tabla, índices)
  sigue siendo trabajo de implementación ordinario "no iniciado", no una decisión abierta.
- **2.1.2** (`generar_embedding(texto) → vector`): sigue "no iniciado" — no implementado en este
  repo todavía.

**Conclusión:** 2.1.3 ya no tiene ninguna decisión de diseño pendiente que lo bloquee — el target
de columna (`vector(3072)`) es conocido y estable. Pero **no puede ejecutarse todavía**: sigue
esperando la implementación real de 1.5.1 (tabla creada en Supabase) y 2.1.2 (función de
embeddings). "Desbloqueado en diseño" ≠ "listo para ejecutar".

---

*Fuente de verdad: `Context-MD/Feature_6_2_3_M1_Preference_Matching_Cierre.md` (dimensión),
`Context-MD/Feature_6.2_Contexto_Ejecucion_v2.md` (referencia original a 1.5b),
`Context-MD/REIP_WBS.xlsx` hojas `1.0 Infraestructura y Datos` y `2.0 M1 Preference Matching`
(IDs y dependencias, no tocado).*
