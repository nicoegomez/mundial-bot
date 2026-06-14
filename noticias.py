"""
noticias.py — Lee titulares del Mundial desde RSS de Google News.
Sin API key, sin límites. El bot comenta/resume los titulares (sin links).
"""

import logging
import feedparser
from urllib.parse import quote

log = logging.getLogger(__name__)

# Feeds de Google News en español, ordenados por prioridad
FEEDS = {
    "argentina": "https://news.google.com/rss/search?q={q}&hl=es-419&gl=AR&ceid=AR:es-419",
}

QUERIES = {
    "argentina": "Selección Argentina Mundial 2026",
    "general":   "Mundial 2026",
}


def _leer_feed(query: str, limite: int = 10) -> list:
    """Lee un feed de Google News y devuelve lista de titulares."""
    url = FEEDS["argentina"].format(q=quote(query))
    try:
        feed = feedparser.parse(url)
        titulares = []
        for entry in feed.entries[:limite]:
            titulares.append({
                "titulo": entry.title,
                "fuente": entry.get("source", {}).get("title", "") if hasattr(entry, "source") else "",
                "fecha":  entry.get("published", ""),
            })
        log.info(f"Noticias '{query}': {len(titulares)} titulares")
        return titulares
    except Exception as e:
        log.error(f"Error leyendo feed '{query}': {e}")
        return []


def noticias_argentina(limite: int = 8) -> list:
    return _leer_feed(QUERIES["argentina"], limite)


def noticias_generales(limite: int = 8) -> list:
    return _leer_feed(QUERIES["general"], limite)


def noticias_combinadas() -> dict:
    """Devuelve noticias de Argentina y generales para que Claude elija."""
    return {
        "argentina": noticias_argentina(8),
        "general":   noticias_generales(6),
    }
