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
        """Próximo partido de Argentina en el Mundial."""
        data  = self._get("fixtures", {"team": ARGENTINA_ID, "next": 5})
        todos = data.get("response", [])
        mundiales = [f for f in todos if self._es_mundial(f)]
        return mundiales[0] if mundiales else None

    def get_ultimo_argentina(self) -> dict | None:
        """Último partido jugado por Argentina en el Mundial."""
        data  = self._get("fixtures", {"team": ARGENTINA_ID, "last": 5})
        todos = data.get("response", [])
        mundiales = [f for f in todos if self._es_mundial(f)]
        return mundiales[-1] if mundiales else None

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
