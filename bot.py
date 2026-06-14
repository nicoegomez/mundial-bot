"""
bot.py — Bot Mundial 2026 para X
Fuente de datos: openfootball worldcup.json (sin API key, sin límites)

Modos:
  resumen_partido  → resultado + goles + análisis de cada partido terminado
  analisis_grupo   → clasificación y escenarios del grupo de Argentina
  fixture_dia      → partidos del día
  previa_argentina → previa del próximo partido de Argentina
  dato_curioso     → dato histórico/estadístico del torneo
"""

import os
import sys
import logging
import argparse
import tweepy
from datetime import datetime, timezone, timedelta

from data_source import WorldCupData, ARGENTINA
from tweet_generator import TweetGenerator
import analisis as anl
import noticias as news
from state_manager import (
    cargar_estado, guardar_estado,
    evento_ya_procesado, marcar_evento_procesado,
    commit_estado_en_github, set_preview_mode,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

try:
    from config import (
        ANTHROPIC_API_KEY,
        X_API_KEY, X_API_SECRET,
        X_ACCESS_TOKEN, X_ACCESS_SECRET,
    )
except ImportError:
    ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
    X_API_KEY         = os.environ["X_API_KEY"]
    X_API_SECRET      = os.environ["X_API_SECRET"]
    X_ACCESS_TOKEN    = os.environ["X_ACCESS_TOKEN"]
    X_ACCESS_SECRET   = os.environ["X_ACCESS_SECRET"]

wc  = WorldCupData()
gen = TweetGenerator(ANTHROPIC_API_KEY)
x_client = tweepy.Client(
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_SECRET,
)


def recortar_tweet(texto: str, limite: int = 280) -> str:
    if len(texto) <= limite:
        return texto
    corte = texto[:limite - 1].rsplit(" ", 1)[0]
    log.warning(f"Tweet recortado de {len(texto)} a {len(corte)+1}.")
    return corte + "…"


def publicar(texto: str, preview: bool, estado: dict):
    if not texto:
        log.warning("Tweet vacío, no se publica.")
        return
    texto = recortar_tweet(texto)
    if preview:
        print(f"\n{'='*60}\n  PREVIEW ({len(texto)} chars)\n{'-'*60}\n  {texto}\n{'='*60}\n")
        return
    try:
        x_client.create_tweet(text=texto)
        estado["tweets_hoy"] = estado.get("tweets_hoy", 0) + 1
        log.info(f"Tweet publicado. Total hoy: {estado['tweets_hoy']}")
    except Exception as e:
        log.error(f"Error al publicar: {e}")


# ── MODO: RESUMEN DE PARTIDOS TERMINADOS ──────────────────────────────────────

def modo_resumen_partido(preview: bool):
    """
    Por cada partido terminado que no se haya tuiteado, publica
    resultado + goles + breve análisis. Detecta partidos nuevos vía estado.
    """
    estado = cargar_estado()
    jugados = wc.partidos_jugados()

    if not jugados:
        log.info("No hay partidos jugados todavía.")
        guardar_estado(estado)
        return

    for m in jugados:
        # ID único del partido
        mid = f"resumen_{m['date']}_{m['team1']}_{m['team2']}".replace(" ", "_")
        if evento_ya_procesado(estado, mid):
            continue

        es_arg = ARGENTINA in (m["team1"], m["team2"])
        grupo  = m.get("group", "")
        tabla  = wc.construir_tabla_grupo(grupo) if grupo else []

        datos = {
            "marcador":     wc.marcador(m),
            "goles":        wc.goles_texto(m),
            "grupo":        grupo,
            "tabla_grupo":  wc.formatear_tabla(tabla) if tabla else "",
            "es_argentina": es_arg,
            "estadio":      m.get("ground", ""),
            "fecha":        m.get("date", ""),
        }
        tweet = gen.tweet_resumen_partido(datos)
        if tweet:
            publicar(tweet, preview, estado)
            marcar_evento_procesado(estado, mid)

    guardar_estado(estado)
    commit_estado_en_github()


# ── MODO: ANÁLISIS DE GRUPO ───────────────────────────────────────────────────

def modo_analisis_grupo(preview: bool):
    """Análisis de clasificación del grupo de Argentina (1 vez al día)."""
    estado = cargar_estado()
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    aid = f"analisis_grupo_{hoy}"

    if evento_ya_procesado(estado, aid):
        log.info("Análisis de grupo ya tuiteado hoy.")
        guardar_estado(estado)
        return

    grupo = wc.grupo_de_argentina()
    if not grupo:
        log.warning("No se identificó el grupo de Argentina.")
        guardar_estado(estado)
        return

    tabla = wc.construir_tabla_grupo(grupo)
    if not tabla or all(t["pj"] == 0 for t in tabla):
        log.info("El grupo de Argentina aún no jugó. Sin análisis.")
        guardar_estado(estado)
        return

    fecha = anl.detectar_fecha(tabla)
    resumen = anl.analizar_grupo(tabla, fecha)
    datos = anl.formatear_para_claude(resumen)
    datos["grupo"] = grupo

    tweet = gen.tweet_analisis_clasificacion(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, aid)

    guardar_estado(estado)
    commit_estado_en_github()


# ── MODO: FIXTURE DEL DÍA ─────────────────────────────────────────────────────

def modo_fixture_dia(preview: bool):
    estado = cargar_estado()
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fid = f"fixture_{hoy}"

    if evento_ya_procesado(estado, fid):
        log.info("Fixture del día ya tuiteado.")
        guardar_estado(estado)
        return

    partidos = wc.partidos_de_fecha(hoy)
    if not partidos:
        log.info("No hay partidos del Mundial hoy.")
        guardar_estado(estado)
        return

    lista = []
    arg_juega = False
    for m in partidos:
        hora = wc.hora_argentina(m)
        lista.append(f"{m['team1']} vs {m['team2']} ({hora}hs AR) — {m.get('group','')}")
        if ARGENTINA in (m["team1"], m["team2"]):
            arg_juega = True

    datos = {
        "fecha": hoy,
        "cantidad": len(partidos),
        "partidos": lista,
        "argentina_juega": arg_juega,
    }
    tweet = gen.tweet_fixture_dia(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, fid)

    guardar_estado(estado)
    commit_estado_en_github()


# ── MODO: PREVIA DE ARGENTINA ─────────────────────────────────────────────────

def modo_previa_argentina(preview: bool):
    estado = cargar_estado()
    prox = wc.proximo_partido_argentina()

    if not prox:
        log.info("No hay próximo partido de Argentina.")
        guardar_estado(estado)
        return

    pid = f"previa_{prox['date']}_{prox['team1']}_{prox['team2']}".replace(" ", "_")
    if evento_ya_procesado(estado, pid):
        log.info("Previa de este partido ya tuiteada.")
        guardar_estado(estado)
        return

    rival = prox["team2"] if prox["team1"] == ARGENTINA else prox["team1"]
    grupo = prox.get("group", "")
    tabla = wc.construir_tabla_grupo(grupo) if grupo else []

    datos = {
        "rival":         rival,
        "fecha":         prox.get("date", ""),
        "hora_argentina": wc.hora_argentina(prox),
        "estadio":       prox.get("ground", ""),
        "grupo":         grupo,
        "tabla_grupo":   wc.formatear_tabla(tabla) if tabla else "",
    }
    tweet = gen.tweet_previa_argentina(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, pid)

    guardar_estado(estado)
    commit_estado_en_github()


# ── MODO: DATO CURIOSO ────────────────────────────────────────────────────────

def modo_dato_curioso(preview: bool):
    estado = cargar_estado()
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    did = f"dato_{hoy}"

    if evento_ya_procesado(estado, did):
        log.info("Dato curioso ya tuiteado hoy.")
        guardar_estado(estado)
        return

    jugados = wc.partidos_jugados()
    # Resumen de goles del torneo para dar contexto
    total_goles = 0
    for m in jugados:
        if "score" in m and "ft" in m["score"]:
            total_goles += sum(m["score"]["ft"])

    datos = {
        "partidos_jugados": len(jugados),
        "goles_totales":    total_goles,
        "promedio_goles":   round(total_goles / len(jugados), 2) if jugados else 0,
        "fecha":            hoy,
    }
    tweet = gen.tweet_dato_curioso(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, did)

    guardar_estado(estado)
    commit_estado_en_github()


def _contexto_torneo() -> dict:
    """Datos generales del torneo para los modos de contenido."""
    jugados = wc.partidos_jugados()
    total_goles = 0
    goleadores = {}  # nombre -> goles
    for m in jugados:
        if "score" in m and "ft" in m["score"]:
            total_goles += sum(m["score"]["ft"])
        for lado in ("goals1", "goals2"):
            for g in m.get(lado, []):
                nombre = g.get("name", "")
                if nombre:
                    goleadores[nombre] = goleadores.get(nombre, 0) + 1
    top = sorted(goleadores.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "partidos_jugados": len(jugados),
        "goles_totales":    total_goles,
        "promedio_goles":   round(total_goles / len(jugados), 2) if jugados else 0,
        "top_goleadores":   "\n".join(f"{n}: {g} gol(es)" for n, g in top),
    }


def modo_figura_fecha(preview: bool):
    estado = cargar_estado()
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fid = f"figura_{hoy}"
    if evento_ya_procesado(estado, fid):
        log.info("Figura de la fecha ya tuiteada hoy.")
        guardar_estado(estado)
        return

    jugados_hoy = wc.partidos_jugados_de_fecha(hoy)
    if not jugados_hoy:
        # Si no hubo partidos hoy, usar los últimos jugados
        jugados_hoy = wc.partidos_jugados()[-4:]
    if not jugados_hoy:
        log.info("No hay partidos para elegir figura.")
        guardar_estado(estado)
        return

    goles_jornada = []
    for m in jugados_hoy:
        g = wc.goles_texto(m)
        if g:
            goles_jornada.append(f"{wc.marcador(m)}:\n{g}")

    datos = {
        "partidos_jornada": [wc.marcador(m) for m in jugados_hoy],
        "goles_jornada":    "\n\n".join(goles_jornada),
    }
    tweet = gen.tweet_figura_fecha(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, fid)
    guardar_estado(estado)
    commit_estado_en_github()


def modo_debate(preview: bool):
    estado = cargar_estado()
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    did = f"debate_{hoy}"
    if evento_ya_procesado(estado, did):
        log.info("Debate ya tuiteado hoy.")
        guardar_estado(estado)
        return

    datos = _contexto_torneo()
    tweet = gen.tweet_debate(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, did)
    guardar_estado(estado)
    commit_estado_en_github()


def modo_numero_dia(preview: bool):
    estado = cargar_estado()
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nid = f"numero_{hoy}"
    if evento_ya_procesado(estado, nid):
        log.info("Número del día ya tuiteado hoy.")
        guardar_estado(estado)
        return

    datos = _contexto_torneo()
    tweet = gen.tweet_numero_dia(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, nid)
    guardar_estado(estado)
    commit_estado_en_github()


def modo_noticia(preview: bool):
    estado = cargar_estado()
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Permitimos hasta 2 noticias por día (mañana y tarde)
    hora = datetime.now(timezone.utc).hour
    franja = "am" if hora < 18 else "pm"
    nid = f"noticia_{hoy}_{franja}"

    if evento_ya_procesado(estado, nid):
        log.info("Noticia de esta franja ya tuiteada.")
        guardar_estado(estado)
        return

    combinadas = news.noticias_combinadas()
    if not combinadas["argentina"] and not combinadas["general"]:
        log.info("No se encontraron noticias.")
        guardar_estado(estado)
        return

    datos = {
        "noticias_argentina": [n["titulo"] for n in combinadas["argentina"]],
        "noticias_generales": [n["titulo"] for n in combinadas["general"]],
    }
    tweet = gen.tweet_noticia(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, nid)
    guardar_estado(estado)
    commit_estado_en_github()


MODOS = {
    "resumen_partido":  modo_resumen_partido,
    "analisis_grupo":   modo_analisis_grupo,
    "fixture_dia":      modo_fixture_dia,
    "previa_argentina": modo_previa_argentina,
    "dato_curioso":     modo_dato_curioso,
    "figura_fecha":     modo_figura_fecha,
    "debate":           modo_debate,
    "numero_dia":       modo_numero_dia,
    "noticia":          modo_noticia,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot Mundial 2026")
    parser.add_argument("modo", choices=list(MODOS.keys()))
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    set_preview_mode(args.preview)
    log.info(f"Modo={args.modo} preview={args.preview}")
    MODOS[args.modo](preview=args.preview)
    log.info("Fin.")
