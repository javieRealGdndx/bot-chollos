#!/usr/bin/env python3
"""
Bot de chollos / errores de precio de Amazon -> Telegram.

Instalación:
    pip install requests feedparser

Configuración (variables de entorno o edita abajo):
    TELEGRAM_TOKEN   token que te da @BotFather
    TELEGRAM_CHAT_ID tu chat id (escribe a @userinfobot para saberlo)
    KEEPA_KEY        (opcional) solo si tienes la API de pago

Uso:
    python bot_chollos.py
"""
import json
import os
import re
import time
from pathlib import Path

import feedparser
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "PON_AQUI_TU_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "PON_AQUI_TU_CHAT_ID")
KEEPA_KEY = os.getenv("KEEPA_KEY", "")  # opcional

# Feeds RSS de ofertas. Comprueba en el sitio la URL exacta del RSS que
# quieras (suele haber un icono RSS en cada categoría o búsqueda).
FEEDS = [
    "https://www.chollometro.com/rss/nuevos",
    # "https://www.chollometro.com/rss/busqueda?q=amazon+error+precio",
]

INTERVALO_SEGUNDOS = 120
SEEN_FILE = Path("seen.json")

# Solo avisa si el chollo menciona Amazon...
EXIGE_AMAZON = True
# ...y cumple al menos una de estas condiciones:
PALABRAS_CLAVE = ["error de precio", "error precio", "precio error", "glitch", "fallo de precio"]
DESCUENTO_MINIMO = 85  # % de descuento detectado en el título


def cargar_vistos() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def guardar_vistos(vistos: set) -> None:
    SEEN_FILE.write_text(json.dumps(list(vistos)[-2000:]))


def enviar_telegram(texto: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(
        url,
        data={"chat_id": TELEGRAM_CHAT_ID, "text": texto, "disable_web_page_preview": False},
        timeout=15,
    )
    if not r.ok:
        print("Error Telegram:", r.text)


def descuento_en_texto(texto: str):
    m = re.search(r"-?\s?(\d{2,3})\s?%", texto)
    if m:
        return int(m.group(1))
    precios = []
    for p in re.findall(r"(\d[\d.]*(?:,\d+)?)\s?€", texto):
        try:
            precios.append(float(p.replace(".", "").replace(",", ".")))
        except ValueError:
            pass
    if len(precios) >= 2 and max(precios) > 0:
        return round((1 - min(precios) / max(precios)) * 100)
    return None


def es_interesante(titulo: str, resumen: str) -> bool:
    t = f"{titulo} {resumen}".lower()
    if EXIGE_AMAZON and "amazon" not in t:
        return False
    if any(p in t for p in PALABRAS_CLAVE):
        return True
    d = descuento_en_texto(titulo)
    return d is not None and d >= DESCUENTO_MINIMO


# ---------- Opcional: Keepa (requiere API de pago) ----------
def precio_keepa(asin: str, dominio: int = 9):
    """Devuelve (precio_actual, media_90d) en euros. dominio 9 = amazon.es."""
    if not KEEPA_KEY:
        return None
    r = requests.get(
        "https://api.keepa.com/product",
        params={"key": KEEPA_KEY, "domain": dominio, "asin": asin, "stats": 90},
        timeout=20,
    )
    p = r.json()["products"][0]
    actual = p["stats"]["current"][0]  # 0 = precio vendido por Amazon
    media = p["stats"]["avg90"][0]
    if actual in (-1, None) or media in (-1, None):
        return None
    return actual / 100, media / 100


# ------------------------------------------------------------
def revisar_feeds(vistos: set) -> None:
    for feed_url in FEEDS:
        feed = feedparser.parse(feed_url)
        for e in feed.entries:
            uid = e.get("id") or e.get("link")
            if uid in vistos:
                continue
            vistos.add(uid)
            if es_interesante(e.get("title", ""), e.get("summary", "")):
                enviar_telegram(f"🔥 {e.title}\n{e.link}")
                print("Enviado:", e.title)


def main() -> None:
    vistos = cargar_vistos()
    primera_vez = not vistos
    while True:
        try:
            if primera_vez:
                # Marca lo existente como visto para no inundarte al arrancar
                for f in FEEDS:
                    for e in feedparser.parse(f).entries:
                        vistos.add(e.get("id") or e.get("link"))
                primera_vez = False
            else:
                revisar_feeds(vistos)
            guardar_vistos(vistos)
        except Exception as ex:
            print("Error:", ex)
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    main()
