"""
bot.py — Orquestador principal del Bot Mundial 2026

Modos de ejecución:
  python bot.py en_vivo          → monitorea partidos en curso (corre c/5min en GA)
  python bot.py fixture_dia      → publica el fixture del día
  python bot.py tabla_grupo      → publica tabla del grupo de Argentina
  python bot.py dato_curioso     → publica un dato/stat llamativo del torneo
  python bot.py recordatorio     → recordatorio del próximo partido de Argentina
  
  Agregar --preview a cualquier modo para ver sin publicar.
"""

import os
import sys
import logging
import argparse
import tweepy
from datetime import datetime, timezone, timedelta

from football_api import FootballAPI, ARGENTINA_ID
from tweet_generator import TweetGenerator
from state_manager import (
    cargar_estado, guardar_estado,
    evento_ya_procesado, marcar_evento_procesado,
    generar_evento_id, generar_id_entretiempo, generar_id_final,
    generar_id_fixture_dia, generar_id_tabla, generar_id_dato_curioso,
    commit_estado_en_github,
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
        FOOTBALL_API_KEY,
    )
except ImportError:
    ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
    X_API_KEY          = os.environ["X_API_KEY"]
    X_API_SECRET       = os.environ["X_API_SECRET"]
    X_ACCESS_TOKEN     = os.environ["X_ACCESS_TOKEN"]
    X_ACCESS_SECRET    = os.environ["X_ACCESS_SECRET"]
    FOOTBALL_API_KEY   = os.environ["FOOTBALL_API_KEY"]

api      = FootballAPI(FOOTBALL_API_KEY)
gen      = TweetGenerator(ANTHROPIC_API_KEY)
x_client = tweepy.Client(
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_SECRET,
)


def publicar(texto: str, preview: bool, estado: dict):
    if not texto:
        log.warning("Tweet vacío, no se publica.")
        return
    if preview:
        print(f"\n{'='*60}")
        print(f"  PREVIEW ({len(texto)} chars)")
        print(f"{'─'*60}")
        print(f"  {texto}")
        print(f"{'='*60}\n")
        return
    try:
        x_client.create_tweet(text=texto)
        estado["tweets_hoy"] = estado.get("tweets_hoy", 0) + 1
        log.info(f"Tweet publicado. Total hoy: {estado['tweets_hoy']}")
    except Exception as e:
        log.error(f"Error al publicar: {e}")


def modo_en_vivo(preview: bool):
    estado   = cargar_estado()
    partidos = api.get_partidos_en_vivo()

    if not partidos:
        log.info("No hay partidos en vivo.")
        guardar_estado(estado)
        return

    log.info(f"Partidos en vivo: {len(partidos)}")

    for fixture in partidos:
        fixture_id = fixture["fixture"]["id"]
        local      = fixture["teams"]["home"]["name"]
        visitante  = fixture["teams"]["away"]["name"]
        marcador   = api.formatear_marcador(fixture)
        status     = fixture["fixture"]["status"]["short"]
        es_arg     = (
            fixture["teams"]["home"]["id"] == ARGENTINA_ID or
            fixture["teams"]["away"]["id"] == ARGENTINA_ID
        )

        log.info(f"Procesando: {marcador} [{status}]")
        eventos = api.get_eventos(fixture_id)

        for evento in eventos:
            tipo    = evento.get("type", "")
            detalle = evento.get("detail", "")
            minuto  = evento.get("time", {}).get("elapsed", 0)
            jugador = evento.get("player", {}) or {}
            equipo  = evento.get("team", {}) or {}
            eid     = generar_evento_id(fixture_id, evento)

            if evento_ya_procesado(estado, eid):
                continue

            tweet = ""

            if tipo == "Goal" and detalle not in ("Missed Penalty", "Penalty missed"):
                stats_j = {}
                pid = jugador.get("id")
                if pid:
                    stats_j = api.get_stats_jugador_torneo(pid)
                datos = {
                    "evento": "GOL",
                    "marcador": marcador,
                    "minuto": minuto,
                    "goleador": jugador.get("name", ""),
                    "asistidor": (evento.get("assist") or {}).get("name", ""),
                    "equipo": equipo.get("name", ""),
                    "stats_goleador": stats_j,
                    "estadisticas_partido": api.get_estadisticas(fixture_id),
                    "es_argentina": es_arg,
                    "local": local,
                    "visitante": visitante,
                }
                tweet = gen.tweet_gol(datos)

            elif tipo == "Goal" and "Penalty" in detalle and detalle != "Missed Penalty":
                datos = {
                    "evento": "PENAL CONVERTIDO",
                    "marcador": marcador,
                    "minuto": minuto,
                    "ejecutor": jugador.get("name", ""),
                    "equipo": equipo.get("name", ""),
                    "resultado": "convertido",
                    "es_argentina": es_arg,
                }
                tweet = gen.tweet_penal(datos)

            elif tipo == "Goal" and detalle in ("Missed Penalty", "Penalty missed"):
                datos = {
                    "evento": "PENAL ERRADO",
                    "marcador": marcador,
                    "minuto": minuto,
                    "ejecutor": jugador.get("name", ""),
                    "equipo": equipo.get("name", ""),
                    "resultado": "errado",
                    "es_argentina": es_arg,
                }
                tweet = gen.tweet_penal(datos)

            elif tipo == "Card" and "Red" in detalle:
                datos = {
                    "evento": "TARJETA ROJA",
                    "marcador": marcador,
                    "minuto": minuto,
                    "jugador_expulsado": jugador.get("name", ""),
                    "equipo": equipo.get("name", ""),
                    "es_segunda_amarilla": "Yellow" in detalle,
                    "estadisticas": api.get_estadisticas(fixture_id),
                    "es_argentina": es_arg,
                }
                tweet = gen.tweet_tarjeta_roja(datos)

            elif tipo == "VAR":
                datos = {
                    "evento": "VAR",
                    "marcador": marcador,
                    "minuto": minuto,
                    "que_se_reviso": detalle,
                    "decision": evento.get("comments", ""),
                    "equipo": equipo.get("name", ""),
                    "jugador": jugador.get("name", ""),
                    "es_argentina": es_arg,
                }
                tweet = gen.tweet_var(datos)

            elif tipo == "subst" and detalle == "Injury":
                pid = jugador.get("id")
                stats_j = api.get_stats_jugador_torneo(pid) if pid else {}
                if not api.es_figura(jugador.get("name", ""), fixture) and not es_arg:
                    marcar_evento_procesado(estado, eid)
                    continue
                datos = {
                    "evento": "LESION",
                    "marcador": marcador,
                    "minuto": minuto,
                    "jugador_lesionado": jugador.get("name", ""),
                    "equipo": equipo.get("name", ""),
                    "reemplazante": (evento.get("assist") or {}).get("name", ""),
                    "stats_torneo": stats_j,
                    "es_argentina": es_arg,
                }
                tweet = gen.tweet_lesion(datos)

            else:
                marcar_evento_procesado(estado, eid)
                continue

            if tweet:
                publicar(tweet, preview, estado)
                marcar_evento_procesado(estado, eid)

        # Entretiempo
        if status == "HT":
            ht_id = generar_id_entretiempo(fixture_id)
            if not evento_ya_procesado(estado, ht_id):
                goles_pt = [
                    {"jugador": e.get("player", {}).get("name", ""),
                     "equipo": e.get("team", {}).get("name", ""),
                     "minuto": e.get("time", {}).get("elapsed", 0)}
                    for e in eventos
                    if e.get("type") == "Goal" and e.get("detail") != "Missed Penalty"
                ]
                datos = {
                    "evento": "ENTRETIEMPO",
                    "marcador": marcador,
                    "local": local,
                    "visitante": visitante,
                    "estadisticas": api.get_estadisticas(fixture_id),
                    "goles_primer_tiempo": goles_pt,
                    "es_argentina": es_arg,
                }
                tweet = gen.tweet_entretiempo(datos)
                if tweet:
                    publicar(tweet, preview, estado)
                    marcar_evento_procesado(estado, ht_id)

        # Final
        if status in ("FT", "AET", "PEN"):
            ft_id = generar_id_final(fixture_id)
            if not evento_ya_procesado(estado, ft_id):
                nombre_grupo, tabla = api.get_grupo_argentina()
                top_gol = api.get_top_goleadores(5)
                gol_str = "\n".join(
                    f"{g['player']['name']}: {g['statistics'][0]['goals']['total']} goles"
                    for g in top_gol
                )
                datos = {
                    "evento": "FINAL",
                    "marcador_final": api.formatear_marcador(fixture),
                    "local": local,
                    "visitante": visitante,
                    "estadisticas": api.get_estadisticas(fixture_id),
                    "tabla_grupo": api.formatear_tabla(tabla) if tabla else "",
                    "nombre_grupo": nombre_grupo,
                    "top_goleadores_torneo": gol_str,
                    "es_argentina": es_arg,
                }
                tweet = gen.tweet_final_partido(datos)
                if tweet:
                    publicar(tweet, preview, estado)
                    marcar_evento_procesado(estado, ft_id)

    guardar_estado(estado)
    commit_estado_en_github()


def modo_fixture_dia(preview: bool):
    estado = cargar_estado()
    hoy    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fid    = generar_id_fixture_dia(hoy)
    if evento_ya_procesado(estado, fid):
        log.info("Fixture del día ya tuiteado.")
        return
    partidos = api.get_partidos_hoy()
    if not partidos:
        log.info("Sin partidos hoy.")
        return
    arg_hoy = [
        p for p in partidos
        if p["teams"]["home"]["id"] == ARGENTINA_ID
        or p["teams"]["away"]["id"] == ARGENTINA_ID
    ]
    lista = []
    for p in partidos:
        dt = datetime.fromisoformat(p["fixture"]["date"].replace("Z", "+00:00"))
        hora_ar = (dt - timedelta(hours=3)).strftime("%H:%M")
        lista.append(
            f"{p['teams']['home']['name']} vs {p['teams']['away']['name']} "
            f"({hora_ar}hs AR) — {p['league'].get('round','')}"
        )
    datos = {
        "fecha": hoy,
        "cantidad": len(partidos),
        "partidos": lista,
        "argentina_juega": bool(arg_hoy),
        "partido_argentina": lista[0] if arg_hoy else None,
    }
    tweet = gen.tweet_fixture_dia(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, fid)
    guardar_estado(estado)
    commit_estado_en_github()


def modo_tabla_grupo(preview: bool):
    estado = cargar_estado()
    hoy    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tid    = generar_id_tabla(hoy)
    if evento_ya_procesado(estado, tid):
        log.info("Tabla ya tuiteada hoy.")
        return
    nombre_grupo, tabla = api.get_grupo_argentina()
    if not tabla:
        log.warning("Sin tabla disponible.")
        return
    proximo = api.get_proximo_argentina()
    datos = {
        "nombre_grupo": nombre_grupo,
        "tabla": api.formatear_tabla(tabla),
        "proximo_argentina": api.formatear_marcador(proximo) if proximo else "Sin próximo",
    }
    tweet = gen.tweet_tabla_grupo(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, tid)
    guardar_estado(estado)
    commit_estado_en_github()


def modo_dato_curioso(preview: bool):
    estado = cargar_estado()
    hoy    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    did    = generar_id_dato_curioso(hoy)
    if evento_ya_procesado(estado, did):
        log.info("Dato curioso ya tuiteado hoy.")
        return
    top_gol = api.get_top_goleadores(10)
    top_asi = api.get_top_asistidores(5)
    _, tabla = api.get_grupo_argentina()
    datos = {
        "top_goleadores": "\n".join(
            f"{g['player']['name']} ({g['statistics'][0]['team']['name']}): "
            f"{g['statistics'][0]['goals']['total']} goles"
            for g in top_gol
        ),
        "top_asistidores": "\n".join(
            f"{a['player']['name']}: {a['statistics'][0]['goals']['assists']} asistencias"
            for a in top_asi
        ),
        "tabla_grupo_arg": api.formatear_tabla(tabla) if tabla else "",
        "fecha": hoy,
    }
    tweet = gen.tweet_dato_curioso(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, did)
    guardar_estado(estado)
    commit_estado_en_github()


def modo_recordatorio(preview: bool):
    estado  = cargar_estado()
    proximo = api.get_proximo_argentina()
    if not proximo:
        log.info("Sin próximo partido.")
        return
    dt_partido = datetime.fromisoformat(
        proximo["fixture"]["date"].replace("Z", "+00:00")
    )
    hora_ar = (dt_partido - timedelta(hours=3)).strftime("%H:%M")
    rec_id  = f"recordatorio_{proximo['fixture']['id']}"
    if evento_ya_procesado(estado, rec_id):
        log.info("Recordatorio ya enviado.")
        return
    _, tabla = api.get_grupo_argentina()
    rival = (
        proximo["teams"]["away"]["name"]
        if proximo["teams"]["home"]["id"] == ARGENTINA_ID
        else proximo["teams"]["home"]["name"]
    )
    datos = {
        "local": proximo["teams"]["home"]["name"],
        "visitante": proximo["teams"]["away"]["name"],
        "rival": rival,
        "hora_argentina": hora_ar,
        "fecha": dt_partido.strftime("%d/%m"),
        "tabla_actual": api.formatear_tabla(tabla) if tabla else "",
        "ronda": proximo["league"].get("round", ""),
    }
    tweet = gen.tweet_recordatorio_partido(datos)
    if tweet:
        publicar(tweet, preview, estado)
        marcar_evento_procesado(estado, rec_id)
    guardar_estado(estado)
    commit_estado_en_github()


def modo_formaciones(preview: bool):
    """
    Publica las formaciones de los partidos del Mundial que están por empezar.
    Detecta cuando los XI titulares ya están confirmados (1hs antes del partido).
    """
    estado   = cargar_estado()
    partidos = api.get_partidos_hoy()

    if not partidos:
        log.info("Sin partidos del Mundial hoy.")
        guardar_estado(estado)
        return

    from datetime import datetime as _dt, timezone as _tz
    ahora = _dt.now(_tz.utc)

    for fixture in partidos:
        fixture_id = fixture["fixture"]["id"]
        status     = fixture["fixture"]["status"]["short"]
        local      = fixture["teams"]["home"]["name"]
        visitante  = fixture["teams"]["away"]["name"]
        es_arg     = (
            fixture["teams"]["home"]["id"] == ARGENTINA_ID or
            fixture["teams"]["away"]["id"] == ARGENTINA_ID
        )

        # Solo partidos que aún no empezaron (NS = Not Started)
        if status != "NS":
            continue

        form_id = f"formaciones_{fixture_id}"
        if evento_ya_procesado(estado, form_id):
            continue

        lineups = api.get_lineups(fixture_id)
        if not lineups or len(lineups) < 2:
            log.info(f"Formaciones aún no disponibles para {local} vs {visitante}")
            continue

        equipos = list(lineups.items())
        datos = {
            "evento":             "FORMACIONES",
            "local":              local,
            "visitante":          visitante,
            "formacion_local":    equipos[0][1].get("formation", ""),
            "formacion_visitante": equipos[1][1].get("formation", ""),
            "xi_local":           equipos[0][1].get("startXI", []),
            "xi_visitante":       equipos[1][1].get("startXI", []),
            "dt_local":           equipos[0][1].get("coach", ""),
            "dt_visitante":       equipos[1][1].get("coach", ""),
            "es_argentina":       es_arg,
        }
        tweet = gen.tweet_formaciones(datos)
        if tweet:
            publicar(tweet, preview, estado)
            marcar_evento_procesado(estado, form_id)

    guardar_estado(estado)
    commit_estado_en_github()


MODOS = {
    "en_vivo":      modo_en_vivo,
    "fixture_dia":  modo_fixture_dia,
    "tabla_grupo":  modo_tabla_grupo,
    "dato_curioso": modo_dato_curioso,
    "recordatorio": modo_recordatorio,
    "formaciones":  modo_formaciones,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot Mundial 2026")
    parser.add_argument("modo", choices=list(MODOS.keys()))
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    from state_manager import set_preview_mode
    set_preview_mode(args.preview)

    log.info(f"Modo={args.modo} preview={args.preview}")
    MODOS[args.modo](preview=args.preview)
    log.info("Fin.")
