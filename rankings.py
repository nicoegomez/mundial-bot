"""
rankings.py — Acumula datos de los partidos procesados y arma rankings del torneo.

Guarda un histórico en rankings.json (commiteado al repo, como state.json) y permite
generar tweets de rankings: máximo xG, partido más físico, jugador más veloz, etc.

Esto da contenido en días sin partidos o de poca actividad.
"""

import os
import json
import logging

log = logging.getLogger(__name__)

RANKINGS_FILE = os.path.join(os.path.dirname(__file__), "rankings.json")


def _cargar() -> dict:
    if os.path.exists(RANKINGS_FILE):
        try:
            with open(RANKINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Error leyendo rankings.json: {e}")
    return {"partidos": []}


def _guardar(data: dict):
    try:
        with open(RANKINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error guardando rankings.json: {e}")


def registrar_partido(stats: dict):
    """
    Guarda los datos relevantes de un partido en el histórico para rankings.
    Idempotente: no duplica si ya está registrado.
    """
    data = _cargar()
    local = stats.get("equipo_local", "?")
    visit = stats.get("equipo_visitante", "?")
    clave = f"{local}_{visit}"

    # Evitar duplicados
    if any(p.get("clave") == clave for p in data["partidos"]):
        return

    registro = {
        "clave": clave,
        "local": local,
        "visitante": visit,
        "xg_local": _f(stats.get("xg_local")),
        "xg_visitante": _f(stats.get("xg_visitante")),
        "distancia_local": _f(stats.get("distancia_local")),
        "distancia_visitante": _f(stats.get("distancia_visitante")),
        "remates_local": _i(stats.get("remates_local")),
        "remates_visitante": _i(stats.get("remates_visitante")),
        "posesion_local": _f(stats.get("posesion_local")),
        "posesion_visitante": _f(stats.get("posesion_visitante")),
    }

    # Destacados físicos individuales
    df = stats.get("destacados_fisicos") or {}
    if df.get("mas_rapido"):
        registro["mas_rapido"] = df["mas_rapido"]
    if df.get("mas_corredor"):
        registro["mas_corredor"] = df["mas_corredor"]

    data["partidos"].append(registro)
    _guardar(data)
    log.info(f"Partido registrado en rankings: {clave}")


def _f(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _i(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def calcular_rankings() -> dict:
    """
    Devuelve un dict con los líderes del torneo en distintas categorías.
    Solo incluye categorías con datos suficientes.
    """
    data = _cargar()
    partidos = data["partidos"]
    if not partidos:
        return {}

    rankings = {"total_partidos": len(partidos)}

    # Mayor xG de un equipo en un partido
    mejor_xg = None
    for p in partidos:
        for lado, eq in [("xg_local", "local"), ("xg_visitante", "visitante")]:
            xg = p.get(lado)
            if xg is not None and (mejor_xg is None or xg > mejor_xg["xg"]):
                mejor_xg = {"xg": xg, "equipo": p[eq],
                            "rival": p["visitante"] if eq == "local" else p["local"]}
    if mejor_xg:
        rankings["mayor_xg"] = mejor_xg

    # Jugador más rápido del torneo
    mas_rapido = None
    for p in partidos:
        mr = p.get("mas_rapido")
        if mr and (mas_rapido is None or mr["velocidad_max"] > mas_rapido["velocidad_max"]):
            mas_rapido = mr
    if mas_rapido:
        rankings["mas_rapido"] = mas_rapido

    # Jugador que más corrió en un partido
    mas_corredor = None
    for p in partidos:
        mc = p.get("mas_corredor")
        if mc and (mas_corredor is None or mc["distancia_km"] > mas_corredor["distancia_km"]):
            mas_corredor = mc
    if mas_corredor:
        rankings["mas_corredor"] = mas_corredor

    # Equipo que más corrió en un partido
    mejor_dist = None
    for p in partidos:
        for lado, eq in [("distancia_local", "local"), ("distancia_visitante", "visitante")]:
            d = p.get(lado)
            if d is not None and (mejor_dist is None or d > mejor_dist["km"]):
                mejor_dist = {"km": d, "equipo": p[eq]}
    if mejor_dist:
        rankings["equipo_mas_corredor"] = mejor_dist

    return rankings
