"""
data_source.py — Fuente de datos del Mundial 2026 basada en openfootball.

Usa los JSON públicos de dominio libre de openfootball (sin API key, sin límites,
imposible de suspender). Fuente primaria: mirror "live" que actualiza rápido.
Fallback: repo oficial.

Estructura de cada partido (match):
{
  "round": "Matchday 1",
  "date": "2026-06-11",
  "time": "13:00 UTC-6",
  "team1": "Mexico",
  "team2": "South Africa",
  "score": {"ft": [2, 0], "ht": [1, 0]},   # puede no estar si no se jugó
  "goals1": [{"name": "...", "minute": 9, "penalty": true}],
  "goals2": [],
  "group": "Group A",
  "ground": "Mexico City"
}
"""

import logging
import requests

log = logging.getLogger(__name__)

# Fuentes en orden de prioridad (primero el mirror rápido)
FUENTES = [
    "https://raw.githubusercontent.com/upbound-web/worldcup-live.json/master/2026/worldcup.json",
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json",
]

ARGENTINA = "Argentina"

# Mapeo de países (nombres como vienen en openfootball) a emoji de bandera
BANDERAS = {
    "Argentina": "🇦🇷", "Brazil": "🇧🇷", "France": "🇫🇷", "Spain": "🇪🇸",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Germany": "🇩🇪", "Portugal": "🇵🇹", "Netherlands": "🇳🇱",
    "Belgium": "🇧🇪", "Italy": "🇮🇹", "Croatia": "🇭🇷", "Uruguay": "🇺🇾",
    "Mexico": "🇲🇽", "USA": "🇺🇸", "Canada": "🇨🇦", "Japan": "🇯🇵",
    "South Korea": "🇰🇷", "Australia": "🇦🇺", "Morocco": "🇲🇦", "Senegal": "🇸🇳",
    "Switzerland": "🇨🇭", "Denmark": "🇩🇰", "Poland": "🇵🇱", "Serbia": "🇷🇸",
    "Czech Republic": "🇨🇿", "Ecuador": "🇪🇨", "Paraguay": "🇵🇾", "Colombia": "🇨🇴",
    "Peru": "🇵🇪", "Chile": "🇨🇱", "Qatar": "🇶🇦", "Saudi Arabia": "🇸🇦",
    "Iran": "🇮🇷", "Ghana": "🇬🇭", "Nigeria": "🇳🇬", "Cameroon": "🇨🇲",
    "Tunisia": "🇹🇳", "Algeria": "🇩🇿", "Egypt": "🇪🇬", "South Africa": "🇿🇦",
    "Austria": "🇦🇹", "Jordan": "🇯🇴", "Turkey": "🇹🇷", "Bosnia & Herzegovina": "🇧🇦",
    "Norway": "🇳🇴", "Sweden": "🇸🇪", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "Ukraine": "🇺🇦", "Costa Rica": "🇨🇷", "Panama": "🇵🇦", "Jamaica": "🇯🇲",
    "New Zealand": "🇳🇿", "Cape Verde": "🇨🇻", "Ivory Coast": "🇨🇮", "Mali": "🇲🇱",
    "Uzbekistan": "🇺🇿", "Iraq": "🇮🇶", "UAE": "🇦🇪", "Bolivia": "🇧🇴",
    "Venezuela": "🇻🇪", "Honduras": "🇭🇳", "Curaçao": "🇨🇼", "Haiti": "🇭🇹",
}


def bandera(pais: str) -> str:
    """Devuelve el emoji de bandera del país, o cadena vacía si no está."""
    return BANDERAS.get(pais, "")


class WorldCupData:
    def __init__(self):
        self._cache = None

    def _cargar(self) -> dict:
        """Descarga el JSON del Mundial probando las fuentes en orden."""
        if self._cache is not None:
            return self._cache
        for url in FUENTES:
            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                log.info(f"Datos cargados desde: {url.split('/')[3]} "
                         f"({len(data.get('matches', []))} partidos)")
                self._cache = data
                return data
            except Exception as e:
                log.warning(f"Falló fuente {url}: {e}")
        log.error("Todas las fuentes fallaron.")
        return {"matches": []}

    def todos_los_partidos(self) -> list:
        return self._cargar().get("matches", [])

    def _jugado(self, match: dict) -> bool:
        """Un partido está jugado si tiene score con ft (full time)."""
        return "score" in match and "ft" in match.get("score", {})

    def partidos_jugados(self) -> list:
        return [m for m in self.todos_los_partidos() if self._jugado(m)]

    def partidos_de_fecha(self, fecha_iso: str) -> list:
        """Partidos de una fecha específica (formato YYYY-MM-DD)."""
        return [m for m in self.todos_los_partidos() if m.get("date") == fecha_iso]

    def partidos_jugados_de_fecha(self, fecha_iso: str) -> list:
        return [m for m in self.partidos_de_fecha(fecha_iso) if self._jugado(m)]

    # ── ARGENTINA ─────────────────────────────────────────────────────────────

    def partidos_argentina(self) -> list:
        return [
            m for m in self.todos_los_partidos()
            if m.get("team1") == ARGENTINA or m.get("team2") == ARGENTINA
        ]

    def ultimo_partido_argentina(self) -> dict | None:
        jugados = [m for m in self.partidos_argentina() if self._jugado(m)]
        if not jugados:
            return None
        jugados.sort(key=lambda m: m.get("date", ""))
        return jugados[-1]

    def proximo_partido_argentina(self) -> dict | None:
        pendientes = [m for m in self.partidos_argentina() if not self._jugado(m)]
        if not pendientes:
            return None
        pendientes.sort(key=lambda m: m.get("date", ""))
        return pendientes[0]

    def grupo_de_argentina(self) -> str | None:
        for m in self.partidos_argentina():
            if m.get("group"):
                return m["group"]
        return None

    # ── GRUPOS ────────────────────────────────────────────────────────────────

    def partidos_de_grupo(self, grupo: str) -> list:
        return [m for m in self.todos_los_partidos() if m.get("group") == grupo]

    def equipos_de_grupo(self, grupo: str) -> list:
        equipos = set()
        for m in self.partidos_de_grupo(grupo):
            equipos.add(m["team1"])
            equipos.add(m["team2"])
        return sorted(equipos)

    def construir_tabla_grupo(self, grupo: str) -> list:
        """
        Construye la tabla del grupo sumando los resultados de los partidos jugados.
        Devuelve lista ordenada de dicts con estadísticas por equipo.
        """
        equipos = self.equipos_de_grupo(grupo)
        tabla = {e: {
            "nombre": e, "pj": 0, "pg": 0, "pe": 0, "pp": 0,
            "gf": 0, "gc": 0, "dg": 0, "pts": 0,
        } for e in equipos}

        for m in self.partidos_de_grupo(grupo):
            if not self._jugado(m):
                continue
            t1, t2 = m["team1"], m["team2"]
            g1, g2 = m["score"]["ft"]

            for t in (t1, t2):
                if t in tabla:
                    tabla[t]["pj"] += 1

            if t1 in tabla:
                tabla[t1]["gf"] += g1; tabla[t1]["gc"] += g2
            if t2 in tabla:
                tabla[t2]["gf"] += g2; tabla[t2]["gc"] += g1

            if g1 > g2:
                if t1 in tabla: tabla[t1]["pg"] += 1; tabla[t1]["pts"] += 3
                if t2 in tabla: tabla[t2]["pp"] += 1
            elif g2 > g1:
                if t2 in tabla: tabla[t2]["pg"] += 1; tabla[t2]["pts"] += 3
                if t1 in tabla: tabla[t1]["pp"] += 1
            else:
                if t1 in tabla: tabla[t1]["pe"] += 1; tabla[t1]["pts"] += 1
                if t2 in tabla: tabla[t2]["pe"] += 1; tabla[t2]["pts"] += 1

        for t in tabla.values():
            t["dg"] = t["gf"] - t["gc"]

        orden = sorted(tabla.values(), key=lambda t: (t["pts"], t["dg"], t["gf"]), reverse=True)
        for i, t in enumerate(orden, 1):
            t["posicion"] = i
        return orden

    # ── HELPERS DE FORMATO ────────────────────────────────────────────────────

    @staticmethod
    def marcador(match: dict) -> str:
        t1, t2 = match["team1"], match["team2"]
        b1, b2 = bandera(t1), bandera(t2)
        n1 = f"{b1} {t1}".strip()
        n2 = f"{t2} {b2}".strip()
        if "score" in match and "ft" in match["score"]:
            g1, g2 = match["score"]["ft"]
            return f"{n1} {g1}-{g2} {n2}"
        return f"{n1} vs {n2}"

    @staticmethod
    def goles_texto(match: dict) -> str:
        """Lista de goleadores con minuto. Marca penales y goles en contra."""
        lineas = []
        for i, lado in enumerate(("goals1", "goals2"), 1):
            equipo = match[f"team{i}"]
            for g in match.get(lado, []):
                minuto = g.get("minute", "")
                offset = g.get("offset")
                min_txt = f"{minuto}+{offset}'" if offset else f"{minuto}'"
                if g.get("owngoal"):
                    # El gol cuenta para 'equipo' pero lo hizo un jugador rival
                    lineas.append(
                        f"{g['name']} {min_txt} (gol en contra, suma para {equipo})"
                    )
                else:
                    pen = " (penal)" if g.get("penalty") else ""
                    lineas.append(f"{g['name']} {min_txt}{pen} ({equipo})")
        return "\n".join(lineas)

    @staticmethod
    def formatear_tabla(tabla: list) -> str:
        lineas = []
        for t in tabla:
            b = bandera(t["nombre"])
            nombre = f"{b} {t['nombre']}".strip()
            lineas.append(
                f"{t['posicion']}. {nombre}: {t['pts']}pts | "
                f"{t['pj']}PJ | DG:{t['dg']:+d} | GF:{t['gf']}"
            )
        return "\n".join(lineas)

    @staticmethod
    def hora_argentina(match: dict) -> str:
        """Convierte el horario del partido a hora Argentina (aprox)."""
        # El formato es "13:00 UTC-6" — convertimos a UTC-3 (Argentina)
        time_str = match.get("time", "")
        try:
            hora_parte = time_str.split(" ")[0]
            h, mn = map(int, hora_parte.split(":"))
            # Detectar offset
            if "UTC-6" in time_str:
                h = (h + 3) % 24  # UTC-6 a UTC-3 = +3
            elif "UTC-4" in time_str:
                h = (h + 1) % 24  # UTC-4 a UTC-3 = +1
            elif "UTC-7" in time_str:
                h = (h + 4) % 24
            return f"{h:02d}:{mn:02d}"
        except Exception:
            return time_str


# ── TRANSMISIONES DE TV EN ARGENTINA (Mundial 2026) ───────────────────────────
# Fuente: acuerdos de derechos confirmados para Argentina.
#   DSports/DGO: los 104 partidos (único con todo). También vía Flow, Paramount+, Prime Video.
#   Telefe (aire, gratis): 32 partidos — todos los de Argentina, inaugural, semis, final.
#   TyC Sports (cable): 52 partidos — todos los de Argentina + cruces.
#   TV Pública (aire, gratis): ~10 partidos, incluidos todos los de Argentina.
#   Disney+ Premium (ESPN): plan premium.

def canales_partido(team1: str, team2: str, fase: str = "grupos") -> str:
    """
    Devuelve el texto de los canales que pasan un partido en Argentina,
    listo para poner entre paréntesis al final de una previa.

    - Si juega Argentina: todas las señales (priorizando las gratis de aire).
    - Otros partidos de fase de grupos: DSports (tiene todo). Telefe/TyC para los grandes.
    - El detalle fino (qué partido puntual pasa cada canal parcial) no siempre se
      conoce de antemano, así que para no afirmar de más, en partidos comunes
      mostramos la opción segura (DSports/DGO) que SÍ tiene todos.
    """
    es_arg = ARGENTINA in (team1, team2)

    if es_arg:
        # Los partidos de Argentina van por todas las señales, gratis incluidas.
        return "📺 TV Pública, Telefe, TyC Sports, DSports y DGO"

    # Partidos sin Argentina: DSports tiene el 100%. Es el dato seguro.
    return "📺 DSports / DGO"


# Selecciones "grandes" cuyos partidos suelen ir también por TV abierta/cable parcial.
SELECCIONES_TV_ABIERTA = {
    "Brazil", "France", "Spain", "England", "Germany", "Portugal",
    "Netherlands", "Italy", "Uruguay", "Mexico",
}
