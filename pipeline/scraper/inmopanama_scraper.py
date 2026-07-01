#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inmopanama_scraper.py
=====================
Scraper Selenium para listings de venta de apartamentos en inmopanama.com,
parametrizado por corregimiento.

CONTEXTO LEGAL (verificado 2026):
  - robots.txt de inmopanama: "User-agent: * / Disallow:" -> permite rastreo completo.
  - robots.txt NO es lo mismo que los Terminos de Servicio. Revisa los ToS una vez
    antes de uso en produccion. Para REIP academico con datos etiquetados, estas cubierto.
  - Usa rate-limiting respetuoso (este script lo hace por defecto). No martilles el sitio.

DECISION DE DISEÑO -- ZONA (registrar en decision log, sesion REIP):
  El campo "zone" se asigna por la URL/pagina scrapeada (autoridad de pagina), NO por
  el texto individual de cada listing. Se confirmo con muestra real (n=10, Bella Vista)
  que 5/10 registros traen "zone_raw" distinto de la zona de la pagina. Se decide GUARDAR
  zone_raw sin usarlo aun para resegmentar -- la resegmentacion real se hace como parte
  de 1.2.7 (validacion de calidad del catalogo), ANTES de que el catalogo alimente
  1.4 (Zone Health Index) y 3.1 (KNN comparables).

ESTADO DE SELECTORES (confirmados por inspeccion manual de HTML real, sesion REIP):
    - Titulo y link:  a.ib-prop-title (dentro de div.content-area)
    - Zona/barrio:    p.ib-prop-zone
    - Features:       ul.ib-prop-features > li  (cada li tiene un <img alt="camas|baños|metraje">
                       seguido de texto suelto, ej. "x2", "84 m²")
    - Precio:         div.ib-prop-price-wrapper
    - ID de listing:  numero despues de "_p-" en el href, ej. "..._p-143196.htm" -> "143196"

  Si esto deja de funcionar (inmopanama cambio su HTML), corre el modo descubrimiento:
      python inmopanama_scraper.py --corregimiento bella-vista --discover --no-headless

  BUGS CONOCIDOS Y FIXES APLICADOS (Chrome 149 / Selenium 4.45 / macOS, sesion REIP):
  1. --headless=new produce TimeoutException instantaneo. Fix: page_load_strategy="eager"
     + flag --remote-allow-origins=*.
  2. Race condition al arrancar: chromedriver devuelve control antes de que el proceso
     Chrome este listo para recibir comandos DevTools -- el primer driver.get() falla con
     "Timed out receiving message from renderer: -0.00X" (tiempo NEGATIVO = fallo casi
     instantaneo, no timeout real de 45s). Sintoma visible: la ventana de Chrome abre en
     blanco mostrando "data:" (pagina inicial por defecto) y nunca navega. Fix: sleep(2)
     tras crear el driver, antes del primer comando. Ademas: retry_get() con reinicio
     completo de driver como red de seguridad si el sleep no es suficiente (ver mas abajo).

DEPENDENCIAS:
  pip install selenium webdriver-manager
"""

import argparse
import csv
import json
import re
import time
from collections import Counter
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)

from webdriver_manager.chrome import ChromeDriverManager

# ----------------------------------------------------------------------------
# CONFIGURACION POR COREGIMIENTO
# ----------------------------------------------------------------------------
BASE_URL = "https://www.inmopanama.com"

COREGIMIENTOS = {
    "bella-vista":     "venta-apartamentos-bella-vista",       # CONFIRMADO
    "san-francisco":   "venta-apartamentos-san-francisco",     # <- VERIFICAR ANTES DE USAR
    "parque-lefevre":  "venta-apartamentos-parque-lefevre",    # <- VERIFICAR ANTES DE USAR
    "betania":         "venta-apartamentos-betania",           # <- VERIFICAR ANTES DE USAR
    "pedregal":        "venta-apartamentos-pedregal",          # <- VERIFICAR ANTES DE USAR
    "el-cangrejo":     "venta-apartamentos-el-cangrejo",       # <- VERIFICAR ANTES DE USAR
    "marbella":        "venta-apartamentos-marbella",          # <- VERIFICAR ANTES DE USAR
    "costa-del-este":  "venta-apartamentos-costa-del-este",    # <- VERIFICAR ANTES DE USAR
    "obarrio":         "venta-apartamentos-obarrio",           # <- VERIFICAR ANTES DE USAR
}

REQUEST_DELAY = 2.5          # segundos entre paginas (cortesia, evita rate-limit)
PAGE_LOAD_TIMEOUT = 45       # timeout de carga de pagina
WAIT_TIMEOUT = 15            # espera explicita por elementos
MAX_PAGES = 20               # tope de paginas a recorrer (cinturon de seguridad)
MAX_GET_RETRIES = 3          # reintentos de driver.get() con reinicio de driver ante timeout
DRIVER_STARTUP_DELAY = 2     # segundos de espera tras crear el driver, antes del primer comando

SELECTORS = {
    "card":     "div.property-boxarea.ib-property-list-card",
    "title":    "a.ib-prop-title",
    "zone":     "p.ib-prop-zone",
    "features": "ul.ib-prop-features li",
    "price":    "div.ib-prop-price-wrapper",
    "link":     "a.ib-prop-title",
}

COREGIMIENTOS_OFICIALES = {
    "bella vista", "san francisco", "parque lefevre", "betania",
    "pedregal", "el cangrejo", "marbella", "costa del este", "obarrio",
}
# Barrios reconocidos DENTRO de un corregimiento oficial -- mapeo explícito,
# no adivinanza. "El Carmen" es un barrio de Bella Vista, no un corregimiento propio.
BARRIOS_A_COREGIMIENTO = {
    "el carmen": "Bella Vista",
}


LISTING_ID_RE = re.compile(r"_p-(\d+)\.htm")

PAGINATION_MODE = "button"
NEXT_BUTTON_SELECTOR = "a.next, a[rel='next'], .pagination a:last-child"


# ----------------------------------------------------------------------------
# DRIVER
# ----------------------------------------------------------------------------
def setup_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--remote-allow-origins=*")
    opts.add_argument("--window-size=1366,900")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.page_load_strategy = "eager"

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )

    # Fix de race condition: el proceso Chrome puede no estar listo para recibir
    # comandos DevTools justo al terminar webdriver.Chrome(). Sin esto, el primer
    # driver.get() puede fallar con TimeoutException casi instantaneo (tiempo negativo).
    time.sleep(DRIVER_STARTUP_DELAY)

    return driver


class DriverHolder:
    """Envoltorio simple para poder reemplazar el objeto driver desde dentro
    de retry_get() sin perder la referencia en el codigo que la llama."""
    def __init__(self, headless):
        self.headless = headless
        self.driver = setup_driver(headless=headless)

    def restart(self):
        try:
            self.driver.quit()
        except Exception:
            pass
        time.sleep(2)
        self.driver = setup_driver(headless=self.headless)


def retry_get(holder: DriverHolder, url: str, max_retries: int = MAX_GET_RETRIES):
    """
    Intenta holder.driver.get(url). Si falla por TimeoutException/WebDriverException,
    reinicia el driver completo (proceso Chrome nuevo) y reintenta. Es la red de
    seguridad final ante la condicion de carrera de arranque -- necesaria porque el
    sleep() en setup_driver reduce la probabilidad de fallo pero no la elimina al 100%.
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            holder.driver.get(url)
            return
        except (TimeoutException, WebDriverException) as e:
            last_error = e
            print(f"[retry] Fallo en intento {attempt}/{max_retries} navegando a {url}: {e}")
            if attempt < max_retries:
                print("[retry] Reiniciando driver completo antes de reintentar...")
                holder.restart()
    raise TimeoutException(f"Fallo persistente tras {max_retries} intentos en {url}") from last_error


def accept_cookies(driver):
    """Best-effort: cierra banner de cookies si existe. No falla si no lo hay."""
    for xp in [
        "//button[contains(translate(.,'ACEPTAR','aceptar'),'aceptar')]",
        "//button[contains(.,'OK')]",
        "//*[contains(@id,'cookie')]//button",
    ]:
        try:
            driver.find_element(By.XPATH, xp).click()
            time.sleep(0.5)
            return
        except (NoSuchElementException, WebDriverException):
            continue


# ----------------------------------------------------------------------------
# MODO DESCUBRIMIENTO -> usar solo si los selectores confirmados dejan de funcionar
# ----------------------------------------------------------------------------
def discover(holder: DriverHolder, start_url):
    print(f"[discover] Abriendo {start_url} ...")
    retry_get(holder, start_url)
    accept_cookies(holder.driver)
    time.sleep(4)

    with open("inmopanama_page.html", "w", encoding="utf-8") as f:
        f.write(holder.driver.page_source)
    print("[discover] HTML guardado en inmopanama_page.html (inspeccionalo en el navegador).")

    elements = holder.driver.find_elements(By.CSS_SELECTOR, "div, article, li")
    class_counter = Counter()
    for el in elements:
        cls = (el.get_attribute("class") or "").strip()
        if cls:
            class_counter[cls] += 1

    print("\n[discover] Clases mas repetidas (candidatas a 'card'):")
    print("  count | longitud_texto_muestra | clase")
    for cls, count in class_counter.most_common(25):
        if 5 <= count <= 60:
            try:
                sample = holder.driver.find_element(By.CSS_SELECTOR, "." + cls.split()[0])
                tlen = len(sample.text.strip())
            except Exception:
                tlen = 0
            print(f"  {count:5d} | {tlen:5d} chars | .{cls}")

    print("\n[discover] Toma la clase con count razonable Y texto largo, ponla en")
    print("           SELECTORS['card'] y vuelve a inspeccionar el HTML para los demas campos.")


# ----------------------------------------------------------------------------
# EXTRACCION
# ----------------------------------------------------------------------------
def _txt(card, css):
    for sel in css.split(","):
        try:
            return card.find_element(By.CSS_SELECTOR, sel.strip()).text.strip()
        except (NoSuchElementException, WebDriverException):
            continue
    return ""


def _num(text):
    if not text:
        return None
    m = re.search(r"[\d.,]+", text.replace(".", "").replace(",", ""))
    return int(m.group()) if m else None


def _feature_by_icon_alt(card, alt_value):
    try:
        items = card.find_elements(By.CSS_SELECTOR, SELECTORS["features"])
    except (NoSuchElementException, WebDriverException):
        return ""
    for li in items:
        try:
            icon = li.find_element(By.CSS_SELECTOR, "img")
            if (icon.get_attribute("alt") or "").strip().lower() == alt_value:
                return li.text.strip()
        except (NoSuchElementException, WebDriverException):
            continue
    return ""


def parse_card(card, zone_label):
    link = ""
    try:
        link = card.find_element(By.CSS_SELECTOR, SELECTORS["link"]).get_attribute("href")
        link = urljoin(BASE_URL, link) if link else ""
    except (NoSuchElementException, WebDriverException):
        pass

    id_match = LISTING_ID_RE.search(link) if link else None
    listing_id = id_match.group(1) if id_match else ""

    price_raw = _txt(card, SELECTORS["price"])
    zone_raw_text = _txt(card, SELECTORS["zone"])
    zone_raw_norm = zone_raw_text.strip().lower()

    if zone_raw_norm in BARRIOS_A_COREGIMIENTO:
        zone_final = BARRIOS_A_COREGIMIENTO[zone_raw_norm]
        zone_source = "zone_raw_barrio_mapeado"
    elif zone_raw_norm in COREGIMIENTOS_OFICIALES:
        zone_final = zone_raw_text.strip()
        zone_source = "zone_raw"
    else:
        zone_final = zone_label
        zone_source = "pagina_scrapeada_no_resuelto"
        
    return {
        "listing_url": link,
        "listing_id": listing_id,
        "title": _txt(card, SELECTORS["title"]),
        "zone_raw": zone_raw_text,
        "zone": zone_final,
        "zone_source": zone_source,
        "price_raw": price_raw,
        "price_usd": _num(price_raw),
        "bedrooms": _num(_feature_by_icon_alt(card, "camas")),
        "bathrooms": _num(_feature_by_icon_alt(card, "baños")),
        "area_m2": _num(_feature_by_icon_alt(card, "metraje")),
        "operation": "venta",
        "source": "inmopanama.com",
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_cards(driver):
    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS["card"].split(",")[0].strip()))
        )
    except TimeoutException:
        print("[warn] No aparecieron tarjetas con el selector actual. Corre --discover.")
    return driver.find_elements(By.CSS_SELECTOR, SELECTORS["card"])


def go_next_page(driver, page_num, page_url_template):
    if PAGINATION_MODE == "url":
        driver.get(page_url_template.format(n=page_num + 1))
        return True
    try:
        btn = driver.find_element(By.CSS_SELECTOR, NEXT_BUTTON_SELECTOR)
        if btn.is_enabled() and btn.is_displayed():
            driver.execute_script("arguments[0].click();", btn)
            return True
    except (NoSuchElementException, WebDriverException):
        pass
    return False


# ----------------------------------------------------------------------------
# MAIN SCRAPE
# ----------------------------------------------------------------------------
def scrape(holder: DriverHolder, max_records, start_url, zone_label):
    print(f"[scrape] Abriendo {start_url} ...")
    retry_get(holder, start_url)
    accept_cookies(holder.driver)

    page_url_template = start_url + "?page={n}"
    records, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        time.sleep(REQUEST_DELAY)
        cards = get_cards(holder.driver)
        print(f"[scrape] Pagina {page}: {len(cards)} tarjetas encontradas.")

        for card in cards:
            try:
                rec = parse_card(card, zone_label)
            except Exception as e:
                print(f"  [skip] error parseando tarjeta: {e}")
                continue
            key = rec["listing_id"] or rec["listing_url"] or rec["title"]
            if key and key not in seen:
                seen.add(key)
                records.append(rec)

        print(f"[scrape] Acumulados: {len(records)}")
        if len(records) >= max_records:
            break
        if not go_next_page(holder.driver, page, page_url_template):
            print("[scrape] No hay mas paginas.")
            break

    return records[:max_records]


def save(records, zone_slug):
    if not records:
        print("[save] 0 registros. Verifica selectores con --discover.")
        return
    out_json = f"{zone_slug}_listings.json"
    out_csv = f"{zone_slug}_listings.csv"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)
    print(f"[save] {len(records)} registros -> {out_csv} / {out_json}")


def main():
    ap = argparse.ArgumentParser(description="Scraper inmopanama por corregimiento (venta).")
    ap.add_argument("--corregimiento", required=True, choices=list(COREGIMIENTOS.keys()),
                     help="Corregimiento a scrapear (define URL y etiqueta de zona).")
    ap.add_argument("--discover", action="store_true",
                     help="Modo descubrimiento de selectores (solo si los actuales fallan).")
    ap.add_argument("--max", type=int, default=50, help="Maximo de registros (default 50).")
    ap.add_argument("--no-headless", action="store_true",
                     help="Mostrar el navegador.")
    args = ap.parse_args()

    slug = COREGIMIENTOS[args.corregimiento]
    start_url = f"{BASE_URL}/{slug}"

    holder = DriverHolder(headless=not args.no_headless)
    try:
        if args.discover:
            discover(holder, start_url)
        else:
            save(scrape(holder, args.max, start_url, args.corregimiento), args.corregimiento)
    finally:
        try:
            holder.driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()