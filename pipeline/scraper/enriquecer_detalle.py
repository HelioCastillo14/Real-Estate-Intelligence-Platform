#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enriquecer_detalle.py
======================
Enriquecimiento de tipo_inmueble + descripcion visitando la pagina de detalle
de cada listing UNA sola vez (ambos campos en la misma visita, no se duplican
requests).

CONTEXTO -- por que existe este script:
  Acta 1.2 SS3.7 documenta una funcion `obtener_tipo_inmueble()` con el
  selector `ul.ib-prop-details-list` como diseno para extraer tipo_inmueble
  de la pagina de detalle -- pero esa funcion nunca se implemento en
  inmopanama_scraper.py (verificado contra el repo, no un supuesto), y el
  selector documentado ya no existe en el HTML real de la pagina (confirmado
  contra 3 paginas de detalle reales: 0 coincidencias). Este script reemplaza
  ese diseno con selectores verificados contra el HTML real vigente:

  - tipo_inmueble: `ol.nb-breadcrumb-list` -- se filtran los separadores '>'
    y se toma el item en posicion 2 (0-indexed, tras 'Home' y la operacion
    'En Venta'/'En Alquiler'). Verificado que varia genuinamente por tipo real
    (probado contra un listing de "Apartamentos" y uno de "Casas", valores
    distintos confirmados) -- no es un valor constante.
  - descripcion: `.nb-desc-full-content` -- parrafo de texto libre, ~280-300
    palabras en las 3 muestras verificadas, con contenido cualitativo real
    (proximidad, ambiente, audiencia objetivo), no solo repeticion de
    atributos estructurados.

RETOMABLE: si el proceso se interrumpe a medio camino, correrlo de nuevo NO
reprocesa filas que ya tienen tipo_inmueble Y descripcion pobladas en el CSV
de salida -- mismo patron que `enriquecer_con_tipo()` de Acta 1.2 SS3.7.

USO:
  python pipeline/scraper/enriquecer_detalle.py
"""

import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ENTRADA = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "catalogo_residencial_limpio_6_2_1.csv"
)

REQUEST_DELAY = 2.5  # segundos entre requests -- misma cortesia que inmopanama_scraper.py
TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

CAMPOS_NUEVOS = ["tipo_inmueble", "descripcion", "descripcion_fuente", "enriquecimiento_estado"]


def extraer_tipo_y_descripcion(html: str) -> tuple[str, str, str, str]:
    """Devuelve (tipo_inmueble, descripcion, descripcion_fuente, estado).

    descripcion_fuente in {"completa", "preview", "ninguna"} -- algunos
    listings no tienen bloque de descripcion completa (.nb-desc-full-content),
    solo un preview de una linea (.nb-desc-preview, ej. "PH Miyaki  Obarrio").
    Confirmado con un caso real (listing_id=143139): la pagina existe, carga
    bien (200), tiene tipo_inmueble valido, pero genuinamente no tiene bloque
    de descripcion completa -- no es un fallo de red. En vez de dejar
    descripcion vacia para estos casos, capturamos el preview y marcamos la
    fuente, para que 6.2.3 pueda ponderar distinto un listing con descripcion
    completa vs. solo preview vs. ninguna, en vez de tratarlos igual.

    estado in {"ok", "sin_breadcrumb", "sin_descripcion", "sin_ambos"}.
    "ok" ahora cubre tanto descripcion completa como preview -- el detalle
    de cual fue vive en descripcion_fuente, no en estado.
    """
    soup = BeautifulSoup(html, "html.parser")

    tipo = ""
    bc = soup.select_one("ol.nb-breadcrumb-list")
    if bc:
        items = [
            li.get_text(strip=True)
            for li in bc.select("li")
            if li.get_text(strip=True) not in ("", "›", ">", "›")
        ]
        # items esperados: [Home, Operacion, Tipo, Zona, Titulo, ...]
        if len(items) >= 3:
            tipo = items[2]

    descripcion = ""
    descripcion_fuente = "ninguna"
    desc_full = soup.select_one(".nb-desc-full-content")
    desc_preview = soup.select_one(".nb-desc-preview")
    if desc_full and desc_full.get_text(strip=True):
        descripcion = desc_full.get_text(" ", strip=True)
        descripcion_fuente = "completa"
    elif desc_preview and desc_preview.get_text(strip=True):
        descripcion = desc_preview.get_text(" ", strip=True)
        descripcion_fuente = "preview"

    if tipo and descripcion:
        estado = "ok"
    elif not tipo and not descripcion:
        estado = "sin_ambos"
    elif not tipo:
        estado = "sin_breadcrumb"
    else:
        estado = "sin_descripcion"

    return tipo, descripcion, descripcion_fuente, estado


def cargar_filas(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def guardar_filas(ruta: Path, filas: list[dict], fieldnames: list[str]) -> None:
    tmp = ruta.with_suffix(".tmp.csv")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filas)
    tmp.replace(ruta)


def main() -> None:
    filas = cargar_filas(ENTRADA)
    fieldnames = list(filas[0].keys())
    for campo in CAMPOS_NUEVOS:
        if campo not in fieldnames:
            fieldnames.append(campo)
        for fila in filas:
            fila.setdefault(campo, "")

    pendientes = [
        i for i, fila in enumerate(filas)
        if not (fila.get("tipo_inmueble") and fila.get("descripcion"))
    ]
    print(f"Total filas: {len(filas)}. Pendientes de enriquecer: {len(pendientes)}.")

    exitos = 0
    fallos_red = 0
    fallos_parcial = 0

    for n, i in enumerate(pendientes, start=1):
        fila = filas[i]
        url = fila.get("listing_url", "")
        if not url:
            fila["enriquecimiento_estado"] = "sin_url"
            fallos_parcial += 1
            continue

        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
        except requests.RequestException as e:
            fila["enriquecimiento_estado"] = f"error_red:{type(e).__name__}"
            fallos_red += 1
            time.sleep(REQUEST_DELAY)
            continue

        tipo, descripcion, descripcion_fuente, estado = extraer_tipo_y_descripcion(r.text)
        fila["tipo_inmueble"] = tipo
        fila["descripcion"] = descripcion
        fila["descripcion_fuente"] = descripcion_fuente
        fila["enriquecimiento_estado"] = estado

        if estado == "ok":
            exitos += 1
        else:
            fallos_parcial += 1

        if n % 25 == 0:
            guardar_filas(ENTRADA, filas, fieldnames)
            print(f"  progreso: {n}/{len(pendientes)} (checkpoint guardado)")

        time.sleep(REQUEST_DELAY)

    guardar_filas(ENTRADA, filas, fieldnames)

    print(f"\nCompletado.")
    print(f"  Éxitos (tipo_inmueble y descripcion poblados): {exitos}")
    print(f"  Fallos de red: {fallos_red}")
    print(f"  Fallos parciales (uno de los dos campos vacío): {fallos_parcial}")
    print(f"  Escrito: {ENTRADA}")


if __name__ == "__main__":
    main()
