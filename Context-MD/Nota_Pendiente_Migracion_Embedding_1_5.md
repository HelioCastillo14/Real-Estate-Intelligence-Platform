# Nota pendiente — coordinar SQL de 1.5b con la construcción real de 1.5.1

**Fecha:** 2026-07-14
**Para:** quien retome 1.5.1 (creación de la tabla `propiedades`)
**Estado:** ABIERTA — no se cierra hasta que 1.5.1 se implemente coordinando con esto

---

## 1. Qué existe hoy y qué no hace todavía

`supabase/migrations/20260715032111_propiedades_embedding.sql` ya agrega la columna `embedding
vector(3072)` a `propiedades` — pero usa `alter table if exists ... add column if not exists`,
así que **no falla si se corre ahora, y tampoco hace nada**: `propiedades` todavía no existe en
Supabase (1.5.1 sigue "no iniciado", ver `CLAUDE.md`). Es un artifact de repo verificado y listo,
no una migración aplicada.

## 2. Acción obligatoria antes de escribir el `CREATE TABLE propiedades`

Cuando alguien empiece 1.5.1 (tabla completa según `DOC-05 §4.2` — documento que no está en este
repo, no se inventan sus campos aquí), debe leer este archivo **antes** de escribir el DDL
principal y elegir una de las dos opciones:

- **Opción A:** fusionar la columna `embedding vector(3072)` directamente dentro del
  `CREATE TABLE propiedades` completo, y retirar/no correr `20260715032111_propiedades_embedding.sql` por
  separado (quedaría redundante).
- **Opción B:** crear `propiedades` sin la columna `embedding` y correr
  `20260715032111_propiedades_embedding.sql` inmediatamente después, como estaba pensado originalmente.

Cualquiera de las dos es válida — lo que no es válido es no elegir ninguna.

## 3. Riesgo concreto si no se coordina

Que quien escriba el `CREATE TABLE propiedades` principal defina `embedding` con otro tipo o
dimensión (por ejemplo, copiando algún ejemplo genérico de `vector(1536)` de la documentación
pública de pgvector, o de un modelo de embeddings distinto) — duplicando o contradiciendo una
decisión ya tomada y verificada contra la API real: **3072 dimensiones, `gemini-embedding-001`**.
Si eso ocurre, el `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` de `20260715032111_propiedades_embedding.sql`
no lo corrige (la columna ya existiría con el tipo equivocado) — quedaría como una segunda fuente
de verdad contradictoria dentro del mismo repo.

## 4. Referencia cruzada

La decisión completa (modelo, dimensión, evidencia de 6.2.3, alcance exacto de lo que 1.5b cierra
y lo que no) está en `Context-MD/Feature_1_5b_Embedding_Dimension_Cierre.md`. Este archivo es
únicamente el recordatorio operativo de coordinación — no repite la evidencia ni la decisión en
sí.

---

*Esta nota se cierra (o se elimina) cuando 1.5.1 se implemente y quede claro, en el `CREATE TABLE`
resultante o en su Acta de cierre, cuál de las dos opciones del §2 se usó.*
