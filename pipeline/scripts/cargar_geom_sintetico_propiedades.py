"""Puebla `propiedades.geom` con un punto sintético (jitter) dentro del polígono real de
su corregimiento — nunca la coordenada real del listing (`inmopanama.com` no la expone).

Requiere `corregimientos.geom` ya poblado para los 5 oficiales
(`cargar_geom_corregimientos.py`, ejecutado en sesión anterior) y la columna
`propiedades.ubicacion_aproximada` (migración `20260716005446`, ya aplicada).

## Resolución del polígono fuente — una sola query, sin casos especiales en Python

Para cada propiedad, el polígono fuente es:
- El propio corregimiento, si es uno de los 5 oficiales (San Francisco, Bella Vista,
  Parque Lefevre, Betania, Pedregal) — `ubicacion_aproximada = false`.
- El polígono del padre (`hereda_de`), si es una de las 3 zonas heredadas de Bella Vista
  (El Cangrejo, Marbella, Obarrio) — `ubicacion_aproximada = true`.
- Ninguno, si es Costa del Este (sin padre y sin `geom` propio — su propio polígono
  fuente resuelve a sí misma, que tiene `geom IS NULL`) o `zona_no_determinada` (no es
  una fila de `corregimientos`, el JOIN no encuentra match).

Estas exclusiones **no están hardcodeadas como casos especiales** — salen solas del
`INNER JOIN` + `WHERE poly.geom IS NOT NULL` de `SQL_BASE` de abajo: Costa del Este y
zona_no_determinada quedan fuera porque no hay ninguna fila de `corregimientos` con
`geom` no nulo que les corresponda, no porque el script las excluya por nombre. Esto es
deliberado: si en el futuro Costa del Este consigue un polígono real, esta query empieza
a incluirla automáticamente sin tocar el script.

## Punto único, no MultiPoint

`ST_GeneratePoints(poligono, 1)` devuelve un `MultiPoint` de 1 elemento — la columna
`propiedades.geom` es `geometry(Point, 4326)` estricto (mismo tipo de error que ya
falló con `MultiPolygon` en `corregimientos.geom`). Se extrae el punto único vía
`(ST_Dump(ST_GeneratePoints(poligono, 1))).geom`.

## Dry-run vs. ejecución real — los puntos generados NO son idénticos entre ambos

`ST_GeneratePoints` es aleatorio por diseño (sin seed fija) — el dry-run genera una
vista previa real (mismo query, mismo `ST_GeneratePoints`) pero los puntos exactos de
la corrida final serán distintos. Es el comportamiento esperado para un jitter de
visualización, no un problema de reproducibilidad — nunca es insumo de modelo.

Protocolo de ejecución: por defecto SOLO dry-run (conteo por corregimiento + muestra de
2-3 filas con coordenadas por corregimiento). Ejecutar de verdad requiere `--ejecutar`.
"""
import argparse
import os

import psycopg2
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

MUESTRAS_POR_ZONA = 3

# JOIN doble: primero al propio corregimiento del listing (para leer hereda_de), luego
# al polígono fuente real (el mismo si es oficial, el padre si hereda). El WHERE
# poly.geom IS NOT NULL es lo único que decide inclusión/exclusión — sin nombres de zona
# hardcodeados en la lógica de filtrado.
SQL_BASE = """
    from propiedades p
    join corregimientos c on c.nombre = p.corregimiento
    join corregimientos poly on poly.nombre = coalesce(c.hereda_de, c.nombre)
    where poly.geom is not null
"""

SQL_DRY_RUN_CONTEO = f"""
    select p.corregimiento, (poly.nombre <> p.corregimiento) as heredado, count(*)
    {SQL_BASE}
    group by p.corregimiento, heredado
    order by count(*) desc
"""

SQL_DRY_RUN_MUESTRA = f"""
    select
        p.listing_id,
        p.corregimiento,
        poly.nombre as poligono_fuente,
        (poly.nombre <> p.corregimiento) as heredado,
        ST_AsText((ST_Dump(ST_GeneratePoints(poly.geom, 1))).geom) as punto_wkt
    {SQL_BASE}
    and p.corregimiento = %(corregimiento)s
    order by random()
    limit %(n)s
"""

SQL_UPDATE = f"""
    update propiedades p
    set
        geom = sub.punto,
        ubicacion_aproximada = sub.heredado
    from (
        select
            p.listing_id,
            (poly.nombre <> p.corregimiento) as heredado,
            (ST_Dump(ST_GeneratePoints(poly.geom, 1))).geom as punto
        {SQL_BASE}
    ) sub
    where p.listing_id = sub.listing_id
"""

SQL_ZONAS_EXCLUIDAS_CONTEO = """
    select corregimiento, count(*)
    from propiedades
    where corregimiento not in (
        select distinct p.corregimiento
        from propiedades p
        join corregimientos c on c.nombre = p.corregimiento
        join corregimientos poly on poly.nombre = coalesce(c.hereda_de, c.nombre)
        where poly.geom is not null
    )
    group by corregimiento
    order by count(*) desc
"""


def dry_run(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(SQL_DRY_RUN_CONTEO)
        conteos = cur.fetchall()

        print("Dry-run — conteo de filas a actualizar por corregimiento:\n")
        total = 0
        for corregimiento, heredado, n in conteos:
            etiqueta = " (heredado, ubicacion_aproximada=true)" if heredado else " (oficial, ubicacion_aproximada=false)"
            print(f"  {corregimiento:20s}{etiqueta:45s} {n}")
            total += n
        print(f"\n  TOTAL a actualizar: {total}")

        cur.execute(SQL_ZONAS_EXCLUIDAS_CONTEO)
        excluidas = cur.fetchall()
        print(f"\nExcluidas explícitamente (geom queda NULL):")
        total_excluidas = 0
        for corregimiento, n in excluidas:
            print(f"  {corregimiento:20s} {n}")
            total_excluidas += n
        print(f"\n  TOTAL excluidas: {total_excluidas}")
        print(f"  TOTAL general:   {total + total_excluidas} (debe ser 1,177)")

        print(f"\nMuestra de {MUESTRAS_POR_ZONA} filas por corregimiento (puntos de vista previa — no serán idénticos en la corrida real, ST_GeneratePoints es aleatorio):\n")
        zonas = sorted({c for c, _, _ in conteos})
        for zona in zonas:
            cur.execute(SQL_DRY_RUN_MUESTRA, {"corregimiento": zona, "n": MUESTRAS_POR_ZONA})
            print(f"  {zona}:")
            for listing_id, corregimiento, poligono_fuente, heredado, wkt in cur.fetchall():
                nota = f" (polígono de {poligono_fuente})" if heredado else ""
                print(f"    listing_id={listing_id}{nota}: {wkt}")
            print()

    return total


def ejecutar_update(conn) -> None:
    with conn:
        with conn.cursor() as cur:
            cur.execute(SQL_UPDATE)
            print(f"{cur.rowcount} filas de propiedades actualizadas con geom sintético.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ejecutar",
        action="store_true",
        help="Ejecuta el UPDATE contra Supabase de verdad. Sin este flag, solo dry-run.",
    )
    args = parser.parse_args()

    database_url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(database_url)
    try:
        total = dry_run(conn)
        assert total == 933, f"esperaba 933 filas a actualizar, la query encontró {total}"

        if not args.ejecutar:
            print("\nDry-run únicamente — nada se ejecutó contra Supabase. Correr con --ejecutar para aplicar de verdad.")
            return

        ejecutar_update(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
