# Vendorización de artifacts en `backend/` — por qué existen 2 copias

**Fecha:** 2026-07-16. Sesión de diagnóstico de `/search/nlp` y `/valuation/transparencia`
devolviendo 500 en Railway (producción) mientras funcionaban en local.

## Causa raíz

Railway tiene el servicio backend configurado con **Root Directory = `backend/`**
(Settings → confirmado por Besto). Esto significa que Railway construye el contenedor
**solo** con el contenido de `backend/` — `pipeline/` (hermano de `backend/` en el
monorepo) **nunca llega al filesystem del contenedor**, sin importar si los archivos
están commiteados en git o no.

`comparables_knn.py` y `transparencia_valuacion.py` calculaban su ruta de artifact con
`Path(__file__).resolve().parents[3]`, asumiendo que `pipeline/` era alcanzable subiendo
3 niveles desde el archivo — cierto en el checkout local completo del monorepo, falso en
el contenedor de Railway (que solo tiene `backend/`). El traceback en producción mostraba
la ruta calculada como `/pipeline/models/knn_semaforo_precio_6_2_4.pkl` (un solo slash
inicial) — la prueba de que `parents[3]` resolvía a la raíz del filesystem del
contenedor, no a la raíz del monorepo.

**Primer intento de fix (commit `032bbfc`), insuficiente:** sacar los 4 artifacts del
`.gitignore` y commitearlos en sus rutas originales dentro de `pipeline/`. El build de
Railway fue exitoso ("Active"/"successful"), pero los endpoints seguían fallando —
confirmando que el problema nunca fue que los archivos no estuvieran en git, sino que
`pipeline/` completo está fuera del build context de Railway por el Root Directory.

## Fix real — vendorización dentro de `backend/`

Los 4 artifacts se copiaron a:
- `backend/models/knn_semaforo_precio_6_2_4.pkl`
- `backend/models/escalador_knn_6_2_4.pkl`
- `backend/models/knn_semaforo_precio_6_2_4_listing_ids_train.pkl`
- `backend/data/conjunto_test_semaforo_knn_3_5_1.csv`

`comparables_knn.py`/`transparencia_valuacion.py` ahora calculan `BACKEND_ROOT =
Path(__file__).resolve().parents[2]` (sube hasta `backend/`, no hasta la raíz del
monorepo) y leen desde ahí.

## Por qué hay 2 copias — no es un descuido, es intencional

- **`pipeline/models/` y `pipeline/data/processed/`** siguen siendo la **fuente de
  verdad** para el pipeline de entrenamiento — los notebooks (`02_m2_knn_semaforo_rf.ipynb`,
  scripts de `pipeline/scripts/`) exportan y leen de ahí. Esta copia sigue en el
  filesystem local (y en git, ya no bajo excepción de `.gitignore` — ver abajo), **nunca
  se borra**.
- **`backend/models/` y `backend/data/`** son una **copia de despliegue**, de solo
  lectura desde la perspectiva del backend en producción. Existen únicamente porque
  Railway no puede ver `pipeline/`.

**Consecuencia operativa que el equipo debe recordar:** si el modelo KNN se reentrena
(nuevo pickle en `pipeline/models/`), o si se regenera el CSV de test
(`pipeline/scripts/exportar_conjunto_test_semaforo_knn_3_5_1.py`), **hay que copiar
manualmente el artifact actualizado a `backend/models/`/`backend/data/` y volver a
commitear** — no hay ningún mecanismo automático de sincronización entre las 2 copias.
Un artifact desactualizado en `backend/` después de un reentrenamiento sería un bug
silencioso (el backend serviría predicciones del modelo viejo sin ningún error), no
detectable por los tests actuales.

## `.gitignore` — estado final

Las excepciones puntuales que vivían bajo `pipeline/models/`/`pipeline/data/processed/`
se revirtieron (ya no hacen falta ahí — esos 4 archivos volvieron a ser ignorados en sus
rutas de `pipeline/`, consistentes con el resto de artifacts de ese directorio). Las
excepciones equivalentes ahora viven bajo `backend/models/`/`backend/data/`. El patrón
global `*.pkl` sigue intacto — los archivos grandes de `pipeline/models/`
(`embeddings_catalogo_2_1_3_completo.pkl` 28M, `embeddings_catalogo_6_2_3_raw.pkl` 26M,
`random_forest_6_2_4.pkl` 10M) siguen excluidos, nunca los necesita el backend en
runtime.
