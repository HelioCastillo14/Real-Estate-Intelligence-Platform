#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enriquecer_detalle.py
======================
Enriquecimiento de tipo_inmueble + descripcion + imagenes visitando la pagina
de detalle de cada listing UNA sola vez (los tres campos en la misma visita,
no se duplican requests).

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

  - imagenes: `.ib-prop-gallery-main .swiper-slide img` (atributo `src`) --
    URLs completas del carrusel de fotos principal de la pagina de detalle,
    resueltas a absolutas con la URL de la pagina. Verificado contra 3
    paginas de detalle reales: el conteo de <img> del bloque coincide
    exactamente con el contador `.nb-gallery-counter` ("N fotos") en las 3
    muestras. Arquitectura hotlink (Opcion A, decision cerrada 2026-07-15,
    ver `Context-MD/Ajuste_WBS_1_5_1_Esquema_Propiedades.md` SS2.4): solo se
    guarda la URL, nunca se descarga el archivo.

enriquecimiento_estado / enriquecimiento_error_detalle: `enriquecimiento_estado`
usa 4 categorias fijas -- 'ok', 'sin_descripcion', 'error_red', 'sin_url' --
para poder tener un CHECK cerrado en el CREATE TABLE de Postgres (1.5.1).
Ningun detalle especifico de un caso (nombre de excepcion de Python, o cual
de las dos variantes de "faltaba contenido" ocurrio) va dentro de
`enriquecimiento_estado` -- vive en `enriquecimiento_error_detalle`, columna
de texto libre sin CHECK. Mapeo completo (normalizado 2026-07-15, ver
Ajuste_WBS_1_5_1_Esquema_Propiedades.md SS2.1):

  - "ok"            -> estado='ok',            detalle=''
  - "sin_descripcion" (extraer_tipo_y_descripcion) -> estado='sin_descripcion', detalle=''
  - "sin_breadcrumb" (extraer_tipo_y_descripcion) -> estado='sin_descripcion', detalle='sin_breadcrumb'
  - "sin_ambos"      (extraer_tipo_y_descripcion) -> estado='sin_descripcion', detalle='sin_ambos'
  - excepcion de red (ej. ConnectionError)        -> estado='error_red',       detalle=<nombre de la excepcion>
  - listing_url vacia en el CSV                   -> estado='sin_url',         detalle=''

`sin_breadcrumb`/`sin_ambos` se normalizan a `sin_descripcion` porque son el
mismo fenomeno conceptual (la pagina se descargo pero le faltaba el
contenido esperado) -- cual de los dos ocurrio se preserva en
`enriquecimiento_error_detalle`, no se pierde. `sin_url` NO se normaliza a
`sin_descripcion`: es una categoria distinta (falta la URL de origen en el
CSV, la pagina nunca se visito), por eso es un cuarto valor propio del
CHECK en vez de una variante de "sin_descripcion".

RETOMABLE: si el proceso se interrumpe a medio camino, correrlo de nuevo NO
reprocesa filas que ya tienen tipo_inmueble, descripcion E imagenes pobladas
en el CSV de salida -- mismo patron que `enriquecer_con_tipo()` de Acta 1.2
SS3.7. Como `imagenes` es un campo nuevo, la primera corrida tras agregar
este campo SI revisita las ~1,177 filas ya enriquecidas (solo para
completar `imagenes`; `tipo_inmueble`/`descripcion` se recalculan de la
misma respuesta HTTP, sin costo adicional de red).

USO:
  python pipeline/scraper/enriquecer_detalle.py
"""

import csv
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

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

CAMPOS_NUEVOS = [
    "tipo_inmueble",
    "descripcion",
    "descripcion_fuente",
    "imagenes",
    "enriquecimiento_estado",
    "enriquecimiento_error_detalle",
]


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


def normalizar_estado(estado_bruto: str) -> tuple[str, str]:
    """Mapea el estado bruto de extraer_tipo_y_descripcion a (estado, detalle)
    dentro de las 4 categorias fijas del CHECK de Postgres. Ver mapeo
    completo en el docstring del modulo.
    """
    if estado_bruto in ("sin_breadcrumb", "sin_ambos"):
        return "sin_descripcion", estado_bruto
    return estado_bruto, ""


def extraer_imagenes(html: str, base_url: str) -> list[str]:
    """URLs completas del carrusel principal de fotos (`.ib-prop-gallery-main`).

    Resuelve rutas relativas (`/files/props/...`) a absolutas con `base_url`
    -- las URLs ya observadas en el sitio son absolutas en el HTML, pero se
    resuelve igual por seguridad ante variaciones entre listings.
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for img in soup.select(".ib-prop-gallery-main .swiper-slide img"):
        src = img.get("src")
        if src:
            urls.append(urljoin(base_url, src))
    return urls


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
        if not (fila.get("tipo_inmueble") and fila.get("descripcion") and fila.get("imagenes"))
    ]
    print(f"Total filas: {len(filas)}. Pendientes de enriquecer: {len(pendientes)}.")

    exitos = 0
    fallos_red = 0
    fallos_parcial = 0
    total_imagenes = 0

    for n, i in enumerate(pendientes, start=1):
        fila = filas[i]
        url = fila.get("listing_url", "")
        if not url:
            fila["enriquecimiento_estado"] = "sin_url"
            fila["enriquecimiento_error_detalle"] = ""
            fallos_parcial += 1
            continue

        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
        except requests.RequestException as e:
            # enriquecimiento_estado se mantiene en 3 categorias fijas ('ok',
            # 'sin_descripcion', 'error_red') para que el CHECK de Postgres
            # (CREATE TABLE propiedades) no dependa del nombre de la excepcion
            # de Python -- el detalle especifico va en una columna separada,
            # sin CHECK, texto libre. Ver Ajuste_WBS_1_5_1_Esquema_Propiedades.md SS2.1.
            fila["enriquecimiento_estado"] = "error_red"
            fila["enriquecimiento_error_detalle"] = type(e).__name__
            fallos_red += 1
            time.sleep(REQUEST_DELAY)
            continue

        tipo, descripcion, descripcion_fuente, estado_bruto = extraer_tipo_y_descripcion(r.text)
        imagenes = extraer_imagenes(r.text, url)
        estado, detalle = normalizar_estado(estado_bruto)
        fila["tipo_inmueble"] = tipo
        fila["descripcion"] = descripcion
        fila["descripcion_fuente"] = descripcion_fuente
        fila["imagenes"] = json.dumps(imagenes, ensure_ascii=False)
        fila["enriquecimiento_estado"] = estado
        fila["enriquecimiento_error_detalle"] = detalle  # limpia un error_red/sin_url previo si esta fila se reprocesa y ahora tiene otro resultado
        total_imagenes += len(imagenes)

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
    print(f"  Imagenes capturadas: {total_imagenes} en {len(pendientes)} filas procesadas")
    print(f"  Escrito: {ENTRADA}")


if __name__ == "__main__":
    main()
