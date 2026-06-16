"""
fixture_tv.py — Fixture oficial del Mundial 2026 con canales de TV en Argentina
y horarios en hora argentina (GMT-3).

Fuente: grilla de transmisiones confirmada para Argentina (provista por el usuario).
Cubre la fase de grupos (11 al 27 de junio). Para fases posteriores, si no hay
dato, se usa el fallback (DSports/DGO, que tiene los 104 partidos).

Cada partido se identifica por los dos equipos (en nombres openfootball, en inglés).
Notas sobre canales:
  - DGO es la app de streaming de DSports (mismo contenido): no se lista aparte.
  - "Disney+" siempre significa ESPN vía Disney+ Premium: se muestra como "Disney+ (ESPN)".
"""

import logging

log = logging.getLogger(__name__)

# Mapa: nombre español del fixture -> nombre openfootball (inglés)
ES_A_EN = {
    "México": "Mexico", "Sudáfrica": "South Africa", "Corea del Sur": "South Korea",
    "Chequia": "Czech Republic", "Canadá": "Canada", "Bosnia y Herz.": "Bosnia & Herzegovina",
    "Estados Unidos": "USA", "Paraguay": "Paraguay", "Catar": "Qatar", "Suiza": "Switzerland",
    "Brasil": "Brazil", "Marruecos": "Morocco", "Haití": "Haiti", "Escocia": "Scotland",
    "Australia": "Australia", "Turquía": "Turkey", "Alemania": "Germany", "Curazao": "Curaçao",
    "Países Bajos": "Netherlands", "Japón": "Japan", "Costa de Marfil": "Ivory Coast",
    "Ecuador": "Ecuador", "Suecia": "Sweden", "Túnez": "Tunisia", "España": "Spain",
    "Cabo Verde": "Cape Verde", "Bélgica": "Belgium", "Egipto": "Egypt",
    "Arabia Saudí": "Saudi Arabia", "Uruguay": "Uruguay", "RI de Irán": "Iran",
    "Nueva Zelanda": "New Zealand", "Francia": "France", "Senegal": "Senegal",
    "Irak": "Iraq", "Noruega": "Norway", "Argentina": "Argentina", "Argelia": "Algeria",
    "Austria": "Austria", "Jordania": "Jordan", "Portugal": "Portugal", "RD Congo": "DR Congo",
    "Inglaterra": "England", "Croacia": "Croatia", "Ghana": "Ghana", "Panamá": "Panama",
    "Uzbekistán": "Uzbekistan", "Colombia": "Colombia",
}

# Fixture crudo: (fecha, hora_AR, equipo1_es, equipo2_es, canales)
# Los canales son tal cual la grilla; DGO se agrega automáticamente abajo.
_FIXTURE_RAW = [
    ("2026-06-11", "16:00", "México", "Sudáfrica", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-11", "23:00", "Corea del Sur", "Chequia", ["DSports", "TyC Sports"]),
    ("2026-06-12", "16:00", "Canadá", "Bosnia y Herz.", ["DSports"]),
    ("2026-06-12", "22:00", "Estados Unidos", "Paraguay", ["DSports", "Telefe", "TyC Sports"]),
    ("2026-06-13", "16:00", "Catar", "Suiza", ["DSports"]),
    ("2026-06-13", "19:00", "Brasil", "Marruecos", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-13", "22:00", "Haití", "Escocia", ["DSports", "TyC Sports"]),
    ("2026-06-14", "01:00", "Australia", "Turquía", ["DSports", "TyC Sports"]),
    ("2026-06-14", "14:00", "Alemania", "Curazao", ["DSports"]),
    ("2026-06-14", "17:00", "Países Bajos", "Japón", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-14", "20:00", "Costa de Marfil", "Ecuador", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-14", "23:00", "Suecia", "Túnez", ["DSports", "TyC Sports"]),
    ("2026-06-15", "13:00", "España", "Cabo Verde", ["DSports"]),
    ("2026-06-15", "16:00", "Bélgica", "Egipto", ["DSports", "TyC Sports"]),
    ("2026-06-15", "19:00", "Arabia Saudí", "Uruguay", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-15", "22:00", "RI de Irán", "Nueva Zelanda", ["DSports", "TyC Sports"]),
    ("2026-06-16", "16:00", "Francia", "Senegal", ["DSports"]),
    ("2026-06-16", "19:00", "Irak", "Noruega", ["DSports", "TyC Sports"]),
    ("2026-06-16", "22:00", "Argentina", "Argelia", ["DSports", "Telefe", "TyC Sports", "Disney+"]),
    ("2026-06-17", "01:00", "Austria", "Jordania", ["DSports", "TyC Sports"]),
    ("2026-06-17", "14:00", "Portugal", "RD Congo", ["DSports"]),
    ("2026-06-17", "17:00", "Inglaterra", "Croacia", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-17", "20:00", "Ghana", "Panamá", ["DSports", "TyC Sports"]),
    ("2026-06-17", "23:00", "Uzbekistán", "Colombia", ["DSports", "TyC Sports"]),
    ("2026-06-18", "13:00", "Chequia", "Sudáfrica", ["DSports", "TyC Sports"]),
    ("2026-06-18", "16:00", "Suiza", "Bosnia y Herz.", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-18", "19:00", "Canadá", "Catar", ["DSports"]),
    ("2026-06-18", "22:00", "México", "Corea del Sur", ["DSports", "TyC Sports"]),
    ("2026-06-19", "16:00", "Estados Unidos", "Australia", ["DSports", "TyC Sports"]),
    ("2026-06-19", "19:00", "Escocia", "Marruecos", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-19", "21:30", "Brasil", "Haití", ["DSports", "TyC Sports"]),
    ("2026-06-20", "00:00", "Turquía", "Paraguay", ["DSports"]),
    ("2026-06-20", "14:00", "Países Bajos", "Suecia", ["DSports", "TyC Sports"]),
    ("2026-06-20", "17:00", "Alemania", "Costa de Marfil", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-20", "21:00", "Ecuador", "Curazao", ["DSports"]),
    ("2026-06-21", "01:00", "Túnez", "Japón", ["DSports"]),
    ("2026-06-21", "13:00", "España", "Arabia Saudí", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-21", "16:00", "Bélgica", "RI de Irán", ["DSports"]),
    ("2026-06-21", "19:00", "Uruguay", "Cabo Verde", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-21", "22:00", "Nueva Zelanda", "Egipto", ["DSports"]),
    ("2026-06-22", "14:00", "Argentina", "Austria", ["DSports", "Telefe", "TyC Sports", "Disney+"]),
    ("2026-06-22", "18:00", "Francia", "Irak", ["DSports"]),
    ("2026-06-22", "21:00", "Noruega", "Senegal", ["DSports", "TyC Sports"]),
    ("2026-06-23", "00:00", "Jordania", "Argelia", ["DSports", "TyC Sports"]),
    ("2026-06-23", "14:00", "Portugal", "Uzbekistán", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-23", "17:00", "Inglaterra", "Ghana", ["DSports"]),
    ("2026-06-23", "20:00", "Panamá", "Croacia", ["DSports", "TyC Sports"]),
    ("2026-06-23", "23:00", "Colombia", "RD Congo", ["DSports", "TyC Sports"]),
    ("2026-06-24", "16:00", "Suiza", "Canadá", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-24", "16:00", "Bosnia y Herz.", "Catar", ["DSports"]),
    ("2026-06-24", "19:00", "Escocia", "Brasil", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-24", "19:00", "Marruecos", "Haití", ["DSports", "TyC Sports"]),
    ("2026-06-24", "22:00", "Chequia", "México", ["DSports"]),
    ("2026-06-24", "22:00", "Sudáfrica", "Corea del Sur", ["DSports", "TyC Sports"]),
    ("2026-06-25", "17:00", "Ecuador", "Alemania", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-25", "17:00", "Curazao", "Costa de Marfil", ["DSports"]),
    ("2026-06-25", "20:00", "Túnez", "Países Bajos", ["DSports"]),
    ("2026-06-25", "20:00", "Japón", "Suecia", ["DSports", "TyC Sports"]),
    ("2026-06-25", "23:00", "Turquía", "Estados Unidos", ["DSports", "TyC Sports"]),
    ("2026-06-25", "23:00", "Paraguay", "Australia", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-26", "16:00", "Noruega", "Francia", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-26", "16:00", "Senegal", "Irak", ["DSports"]),
    ("2026-06-26", "21:00", "Uruguay", "España", ["DSports", "Telefe", "Disney+"]),
    ("2026-06-26", "21:00", "Cabo Verde", "Arabia Saudí", ["DSports"]),
    ("2026-06-27", "00:00", "Nueva Zelanda", "Bélgica", ["DSports"]),
    ("2026-06-27", "00:00", "Egipto", "RI de Irán", ["DSports", "TyC Sports"]),
    ("2026-06-27", "18:00", "Panamá", "Inglaterra", ["DSports"]),
    ("2026-06-27", "18:00", "Croacia", "Ghana", ["DSports"]),
    ("2026-06-27", "20:30", "Colombia", "Portugal", ["DSports"]),
    ("2026-06-27", "20:30", "RD Congo", "Uzbekistán", ["DSports"]),
    ("2026-06-27", "23:00", "Jordania", "Argentina", ["DSports", "Telefe", "TyC Sports", "Disney+"]),
    ("2026-06-27", "23:00", "Argelia", "Austria", ["DSports", "TyC Sports"]),
]


def _construir_indice():
    """Arma un índice {frozenset(equipos_en): {canales, hora, fecha}} para búsqueda rápida."""
    indice = {}
    for fecha, hora, e1_es, e2_es, canales in _FIXTURE_RAW:
        e1 = ES_A_EN.get(e1_es, e1_es)
        e2 = ES_A_EN.get(e2_es, e2_es)
        # Normalizamos nombres de canales:
        #   - DGO es la app de DSports (mismo contenido): no se lista aparte.
        #   - "Disney+" en el fixture siempre es ESPN vía Disney+: lo aclaramos.
        cc = []
        for canal in canales:
            if canal == "DGO":
                continue  # redundante con DSports
            if canal == "Disney+":
                cc.append("Disney+ (ESPN)")
            else:
                cc.append(canal)
        clave = frozenset([e1, e2])
        indice[clave] = {"canales": cc, "hora_ar": hora, "fecha": fecha}
    return indice


_INDICE = _construir_indice()


def canales_de(team1: str, team2: str) -> str | None:
    """
    Devuelve el texto de canales para un partido (en cualquier orden de equipos),
    listo para poner entre paréntesis. None si el partido no está en el fixture.
    """
    info = _INDICE.get(frozenset([team1, team2]))
    if not info:
        return None
    return "📺 " + ", ".join(info["canales"])


def hora_ar_de(team1: str, team2: str) -> str | None:
    """Devuelve la hora argentina (GMT-3) del partido, o None si no está."""
    info = _INDICE.get(frozenset([team1, team2]))
    return info["hora_ar"] if info else None


def info_de(team1: str, team2: str) -> dict | None:
    """Devuelve toda la info de TV/horario del partido, o None."""
    return _INDICE.get(frozenset([team1, team2]))
