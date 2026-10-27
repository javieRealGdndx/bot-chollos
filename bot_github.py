"""Una sola pasada del bot (para GitHub Actions). Reutiliza bot_chollos.py."""
import feedparser

from bot_chollos import FEEDS, SEEN_FILE, cargar_vistos, guardar_vistos, revisar_feeds


def main() -> None:
    primera_vez = not SEEN_FILE.exists()
    vistos = cargar_vistos()
    if primera_vez:
        # Primera ejecución: marca lo existente como visto, sin avisar
        for f in FEEDS:
            for e in feedparser.parse(f).entries:
                vistos.add(e.get("id") or e.get("link"))
    else:
        revisar_feeds(vistos)
    guardar_vistos(vistos)


if __name__ == "__main__":
    main()