"""
football_api.py — Wrapper para API-Football v3
Adaptado para plan Free: no usa filtros league+season en los endpoints
que lo requieren. Filtra por Mundial localmente.
"""

import logging
import requests
from datetime import datetime, timezone

log = logging.getLogger(__name__)

FOOTBALL_API_BASE = "https://v3.football.api-sports.io"
MUNDIAL_ID        = 1
MUNDIAL_SEASON    = 2026
ARGENTINA_ID      = 26


class FootballAPI:
    def __init__(self, api_key: str):
        self.headers = {"x-apisports-key": api_key}
        self.base    = FOOTBALL_API_BASE

    def _get(self, endpoint: str, params: dict = {}) -> dict:
        try:
            resp = requests.get(
                f"{self.base}/{endpoint}",
                headers=self.headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            remaining = resp.headers.get("x-ratelimit-requests-remaining", "?")
            log.info(f"API [{endpoint}] OK — requests restantes: {remaining}")
            if data.get("errors"):
                log.warning(f"API errors: {data['errors']}")
            return data
        except Exception as e:
            log.error(f"Error API [{endpoint}]: {e}")
            return {"response": []}

    def _es_mundial(self, fixture: dict) -> bool:
        """Verifica si un fixture pertenece al Mundial 2026."""
        league = fixture.get("league", {})
        return (
            league.get("id") == MUNDIAL_ID and
            league.get("season") == MUNDIAL_SEASON
        )

    # ── FIXTURES EN VIVO ──────────────────────────────────────────────────────

    def get_partidos_en_vivo(self) -> list:
        """Todos los partidos del Mundial en curso ahora mismo."""
        data = self._get("fixtures", {"live": "all"})
        todos = data.get("response", [])
        mundiales = [f for f in todos if self._es_mundial(f)]
        log.info(f"Partidos en vivo totales: {len(todos)} — Mundial: {len(mundiales)}")
        return mundiales

    def get_partidos_hoy(self) -> list:
        """Todos los partidos del Mundial de hoy."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data  = self._get("fixtures", {"date": today})
        todos = data.get("response", [])
        return [f for f in todos if self._es_mundial(f)]

    def get_proximo_argentina(self) -> dict | None:
        """
        Próximo partido de Argentina en el Mundial.
        Usa el listado completo (sin 'next', bloqueado en Free) y filtra
        el primer partido aún no jugado, ordenado por fecha.
        """
        from datetime import datetime as _dt, timezone as _tz
        fixtures = self.get_todos_fixtures_argentina()
        ahora = _dt.now(_tz.utc)
        futuros = []
        for f in fixtures:
            estado = f["fixture"]["status"]["short"]
            dt = _dt.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00"))
            if estado == "NS" or dt > ahora:
                futuros.append((dt, f))
        futuros.sort(key=lambda x: x[0])
        return futuros[0][1] if futuros else None

    def get_ultimo_argentina(self) -> dict | None:
        """
        Último partido jugado por Argentina en el Mundial.
        Usa el listado completo (sin 'last', bloqueado en Free) y filtra
        el último partido finalizado, ordenado por fecha.
        """
        from datetime import datetime as _dt
        fixtures = self.get_todos_fixtures_argentina()
        jugados = []
        for f in fixtures:
            estado = f["fixture"]["status"]["short"]
            if estado in ("FT", "AET", "PEN"):
                dt = _dt.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00"))
                jugados.append((dt, f))
        jugados.sort(key=lambda x: x[0])
        return jugados[-1][1] if jugados else None

    def get_todos_fixtures_argentina(self) -> list:
        """Todos los partidos de Argentina en el Mundial (jugados y por jugar)."""
        data  = self._get("fixtures", {"team": ARGENTINA_ID})
        todos = data.get("response", [])
        return [f for f in todos if self._es_mundial(f)]

    def get_fixtures_por_equipo(self, team_id: int) -> list:
        """Todos los partidos de un equipo en el Mundial."""
        data  = self._get("fixtures", {"team": team_id})
        todos = data.get("response", [])
        return [f for f in todos if self._es_mundial(f)]

    def identificar_grupo_argentina(self) -> tuple:
        """
        Identifica el grupo de Argentina y sus rivales desde los fixtures.
        Devuelve (nombre_ronda_grupo, set de team_ids del grupo).
        No usa standings (bloqueado en Free) — lo deduce de los partidos.
        """
        fixtures = self.get_todos_fixtures_argentina()
        if not fixtures:
            return "Grupo ?", set()

        # El campo 'round' identifica la fase; para fase de grupos los rivales
        # de Argentina en esos partidos son los del grupo.
        equipos = set()
        for f in fixtures:
            rnd = f["league"].get("round", "")
            if "Group" in rnd or "Grupo" in rnd:
                equipos.add(f["teams"]["home"]["id"])
                equipos.add(f["teams"]["away"]["id"])

        # Nombre del grupo a partir del primer fixture de grupo
        nombre = "Grupo de Argentina"
        return nombre, equipos

    def construir_tabla_grupo(self, team_ids: set) -> list:
        """
        Construye la tabla del grupo sumando los resultados de los partidos
        FINALIZADOS de cada equipo. No depende del endpoint standings.

        Devuelve lista de dicts ordenada por: puntos, dif gol, goles a favor.
        Cada dict: {team_id, nombre, pj, pg, pe, pp, gf, gc, dg, pts, amarillas, rojas}
        """
        # Recolectar todos los fixtures únicos del grupo
        fixtures_vistos = {}
        for tid in team_ids:
            for f in self.get_fixtures_por_equipo(tid):
                fid = f["fixture"]["id"]
                rnd = f["league"].get("round", "")
                if ("Group" in rnd or "Grupo" in rnd):
                    fixtures_vistos[fid] = f

        # Inicializar tabla
        tabla = {tid: {
            "team_id": tid, "nombre": "", "pj": 0, "pg": 0, "pe": 0, "pp": 0,
            "gf": 0, "gc": 0, "dg": 0, "pts": 0, "amarillas": 0, "rojas": 0,
        } for tid in team_ids}

        for f in fixtures_vistos.values():
            estado = f["fixture"]["status"]["short"]
            if estado not in ("FT", "AET", "PEN"):
                continue  # Solo partidos terminados

            h_id = f["teams"]["home"]["id"]
            a_id = f["teams"]["away"]["id"]
            h_name = f["teams"]["home"]["name"]
            a_name = f["teams"]["away"]["name"]
            gh = f["goals"]["home"] or 0
            ga = f["goals"]["away"] or 0

            for tid, name in ((h_id, h_name), (a_id, a_name)):
                if tid in tabla:
                    tabla[tid]["nombre"] = name

            if h_id in tabla:
                tabla[h_id]["pj"] += 1
                tabla[h_id]["gf"] += gh
                tabla[h_id]["gc"] += ga
            if a_id in tabla:
                tabla[a_id]["pj"] += 1
                tabla[a_id]["gf"] += ga
                tabla[a_id]["gc"] += gh

            if gh > ga:
                if h_id in tabla: tabla[h_id]["pg"] += 1; tabla[h_id]["pts"] += 3
                if a_id in tabla: tabla[a_id]["pp"] += 1
            elif ga > gh:
                if a_id in tabla: tabla[a_id]["pg"] += 1; tabla[a_id]["pts"] += 3
                if h_id in tabla: tabla[h_id]["pp"] += 1
            else:
                if h_id in tabla: tabla[h_id]["pe"] += 1; tabla[h_id]["pts"] += 1
                if a_id in tabla: tabla[a_id]["pe"] += 1; tabla[a_id]["pts"] += 1

        # Calcular diferencia de gol
        for t in tabla.values():
            t["dg"] = t["gf"] - t["gc"]

        # Ordenar: puntos, dif gol, goles a favor
        orden = sorted(
            tabla.values(),
            key=lambda t: (t["pts"], t["dg"], t["gf"]),
            reverse=True
        )
        for i, t in enumerate(orden, 1):
            t["posicion"] = i
        return orden

    # ── EVENTOS Y ESTADÍSTICAS ────────────────────────────────────────────────

    def get_eventos(self, fixture_id: int) -> list:
        data = self._get("fixtures/events", {"fixture": fixture_id})
        return data.get("response", [])

    def get_estadisticas(self, fixture_id: int) -> dict:
        data  = self._get("fixtures/statistics", {"fixture": fixture_id})
        stats = {}
        for team_data in data.get("response", []):
            nombre       = team_data["team"]["name"]
            stats[nombre] = {s["type"]: s["value"] for s in team_data["statistics"]}
        return stats

    def get_lineups(self, fixture_id: int) -> dict:
        data    = self._get("fixtures/lineups", {"fixture": fixture_id})
        lineups = {}
        for team_data in data.get("response", []):
            nombre = team_data["team"]["name"]
            lineups[nombre] = {
                "formation": team_data.get("formation", ""),
                "startXI":   [p["player"]["name"] for p in team_data.get("startXI", [])],
                "coach":     team_data.get("coach", {}).get("name", ""),
            }
        return lineups

    def get_stats_jugador_torneo(self, player_id: int) -> dict:
        """Stats del jugador en el torneo — puede fallar en plan Free."""
        data = self._get("players", {
            "id":     player_id,
            "league": MUNDIAL_ID,
            "season": MUNDIAL_SEASON,
        })
        r = data.get("response", [])
        if not r:
            return {}
        p     = r[0]
        stats = p.get("statistics", [{}])[0]
        return {
            "nombre":        p["player"]["name"],
            "goles":         stats.get("goals", {}).get("total", 0) or 0,
            "asistencias":   stats.get("goals", {}).get("assists", 0) or 0,
            "partidos":      stats.get("games", {}).get("appearences", 0) or 0,
            "amarillas":     stats.get("cards", {}).get("yellow", 0) or 0,
            "rojas":         stats.get("cards", {}).get("red", 0) or 0,
        }

    def get_top_goleadores(self, limit: int = 10) -> list:
        data = self._get("players/topscorers", {
            "league": MUNDIAL_ID, "season": MUNDIAL_SEASON,
        })
        return data.get("response", [])[:limit]

    def get_top_asistidores(self, limit: int = 5) -> list:
        data = self._get("players/topassists", {
            "league": MUNDIAL_ID, "season": MUNDIAL_SEASON,
        })
        return data.get("response", [])[:limit]

    # ── TABLA DE POSICIONES ───────────────────────────────────────────────────

    def get_tabla_completa(self) -> list:
        data = self._get("standings", {
            "league": MUNDIAL_ID, "season": MUNDIAL_SEASON,
        })
        try:
            return data["response"][0]["league"]["standings"]
        except (KeyError, IndexError):
            return []

    def get_grupo_argentina(self) -> tuple:
        todos = self.get_tabla_completa()
        for grupo in todos:
            for equipo in grupo:
                if equipo["team"]["id"] == ARGENTINA_ID:
                    return equipo.get("group", "Grupo ?"), grupo
        return "Grupo ?", []

    # ── HELPERS ───────────────────────────────────────────────────────────────

    @staticmethod
    def formatear_marcador(fixture: dict) -> str:
        local     = fixture["teams"]["home"]["name"]
        visitante = fixture["teams"]["away"]["name"]
        goles_l   = fixture["goals"]["home"] if fixture["goals"]["home"] is not None else 0
        goles_v   = fixture["goals"]["away"] if fixture["goals"]["away"] is not None else 0
        estado    = fixture["fixture"]["status"]["short"]
        minuto    = fixture["fixture"]["status"].get("elapsed", "")

        if estado in ("1H", "2H", "ET"):
            tiempo = f"{minuto}'"
        elif estado == "HT":
            tiempo = "ET"
        elif estado == "FT":
            tiempo = "FT"
        elif estado == "NS":
            from datetime import timedelta
            dt    = datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00"))
            hora  = (dt - timedelta(hours=3)).strftime("%H:%M")
            tiempo = f"{hora}hs AR"
        else:
            tiempo = estado

        return f"{local} {goles_l}-{goles_v} {visitante} [{tiempo}]"

    @staticmethod
    def formatear_tabla(tabla: list) -> str:
        lineas = []
        for pos in tabla:
            eq  = pos["team"]["name"]
            pts = pos["points"]
            pj  = pos["all"]["played"]
            gf  = pos["all"]["goals"]["for"]
            gc  = pos["all"]["goals"]["against"]
            gd  = pos["goalsDiff"]
            lineas.append(f"{pos['rank']}. {eq}: {pts}pts | {pj}PJ | {gf}:{gc} (DG:{gd:+d})")
        return "\n".join(lineas)

    @staticmethod
    def es_figura(player_name: str, fixture: dict) -> bool:
        figuras = [
            "Messi", "Mbappé", "Ronaldo", "Neymar", "Vinicius",
            "Bellingham", "Pedri", "Yamal", "Haaland", "Salah",
            "Pulisic", "Alvarez", "De Paul", "Mac Allister",
        ]
        return any(f.lower() in player_name.lower() for f in figuras)
