"""
analisis.py — Cálculo de probabilidades y escenarios de clasificación.

Toda la matemática es determinística (reglas oficiales FIFA Mundial 2026):
- 12 grupos de 4, juegan 3 partidos cada uno
- Clasifican 1° y 2° de cada grupo + 8 mejores terceros
- 3 pts victoria, 1 empate, 0 derrota
- Desempate: dif gol general, goles a favor (head-to-head es más complejo,
  lo aproximamos con dif gol que es el caso más común)

El resultado de estos cálculos se le pasa a Claude para que arme el tweet
con contexto histórico y narración.
"""

import logging

log = logging.getLogger(__name__)

PARTIDOS_POR_EQUIPO = 3
PUNTOS_VICTORIA     = 3


def analizar_equipo(equipo: dict, partidos_restantes: int) -> dict:
    """
    Para un equipo, calcula su situación de clasificación.

    equipo: dict de la tabla (pts, pj, dg, gf, posicion, nombre)
    partidos_restantes: cuántos partidos le quedan por jugar

    Devuelve un dict con el análisis listo para narrar.
    """
    pts        = equipo["pts"]
    pj         = equipo["pj"]
    pos        = equipo.get("posicion", 0)
    restantes  = partidos_restantes

    pts_maximos    = pts + restantes * PUNTOS_VICTORIA
    pts_minimos    = pts  # si pierde todo

    # Situaciones típicas de fase de grupos (4 equipos, 3 fechas)
    analisis = {
        "nombre":         equipo["nombre"],
        "puntos":         pts,
        "posicion":       pos,
        "partidos_jugados": pj,
        "partidos_restantes": restantes,
        "puntos_maximos": pts_maximos,
        "diferencia_gol": equipo["dg"],
        "goles_favor":    equipo["gf"],
    }

    # Heurísticas de clasificación (aproximadas pero realistas)
    # En grupos de 4: 6-7 pts casi siempre clasifica, 4 pts suele alcanzar
    # para mejor tercero, 0 pts a falta de 1 fecha es casi eliminación.

    if restantes == 0:
        # Grupo terminado
        if pos <= 2:
            analisis["estado"] = "clasificado_directo"
        elif pos == 3:
            analisis["estado"] = "tercero_depende_otros_grupos"
        else:
            analisis["estado"] = "eliminado"
    else:
        # Todavía hay partidos
        if pts_maximos < 3 and restantes <= 1:
            analisis["estado"] = "casi_eliminado"
        elif pts >= 6:
            analisis["estado"] = "muy_bien_encaminado"
        elif pts_maximos >= 6:
            analisis["estado"] = "depende_de_si_mismo"
        else:
            analisis["estado"] = "complicado"

    # Qué necesita en el próximo partido (si quedan partidos)
    if restantes > 0:
        analisis["escenarios_proximo"] = {
            "si_gana":   pts + 3,
            "si_empata": pts + 1,
            "si_pierde": pts,
        }

    return analisis


def analizar_grupo(tabla: list, fecha_actual: int) -> dict:
    """
    Analiza el grupo completo.

    tabla: lista ordenada de equipos (de construir_tabla_grupo)
    fecha_actual: número de fecha jugada (1, 2 o 3)

    Devuelve un resumen con el análisis de cada equipo.
    """
    partidos_restantes = PARTIDOS_POR_EQUIPO - fecha_actual

    resumen = {
        "fecha_actual":        fecha_actual,
        "partidos_restantes":  partidos_restantes,
        "tabla":               [],
        "equipos":             [],
    }

    for equipo in tabla:
        # Restantes reales por equipo (puede variar si jugaron distinto)
        rest = PARTIDOS_POR_EQUIPO - equipo["pj"]
        analisis = analizar_equipo(equipo, rest)
        resumen["equipos"].append(analisis)
        resumen["tabla"].append(
            f"{equipo.get('posicion','?')}. {equipo['nombre']}: "
            f"{equipo['pts']}pts | {equipo['pj']}PJ | "
            f"DG:{equipo['dg']:+d} | GF:{equipo['gf']}"
        )

    return resumen


def detectar_fecha(tabla: list) -> int:
    """Detecta en qué fecha del grupo estamos según partidos jugados."""
    if not tabla:
        return 0
    max_pj = max(t["pj"] for t in tabla)
    return max_pj


def formatear_para_claude(resumen: dict) -> dict:
    """Prepara el análisis en formato legible para el prompt de Claude."""
    return {
        "fecha_del_grupo":     resumen["fecha_actual"],
        "partidos_restantes":  resumen["partidos_restantes"],
        "tabla":               "\n".join(resumen["tabla"]),
        "analisis_equipos": [
            {
                "equipo":   e["nombre"],
                "posicion": e["posicion"],
                "puntos":   e["puntos"],
                "estado":   e["estado"],
                "puntos_maximos_posibles": e["puntos_maximos"],
                "escenarios_proximo_partido": e.get("escenarios_proximo", {}),
            }
            for e in resumen["equipos"]
        ],
    }
