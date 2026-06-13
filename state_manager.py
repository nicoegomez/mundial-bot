"""
state_manager.py — Persiste el estado del bot para no repetir tweets.

En GitHub Actions cada run es efímero (sin filesystem persistente),
por eso usamos el repositorio mismo como almacenamiento vía Git.
El archivo state.json se commitea automáticamente al final de cada run.

Estructura de state.json:
{
  "eventos_procesados": ["fixture_123_evento_45_gol", ...],
  "ultimo_run": "2026-06-14T20:00:00Z",
  "partidos_monitoreados": [123456, 789012],
  "tweets_hoy": 12
}
"""

import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

STATE_FILE = Path("state.json")

# Cuando está en True, no se persiste nada (modo preview).
PREVIEW_MODE = False


def set_preview_mode(activo: bool):
    """Activa el modo preview: no se guarda ni commitea el estado."""
    global PREVIEW_MODE
    PREVIEW_MODE = activo


def cargar_estado() -> dict:
    """Carga el estado desde el archivo JSON."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                estado = json.load(f)
            log.info(f"Estado cargado: {len(estado.get('eventos_procesados', []))} eventos previos")
            return estado
        except Exception as e:
            log.warning(f"Error cargando estado, iniciando vacío: {e}")
    return {
        "eventos_procesados": [],
        "ultimo_run": None,
        "partidos_monitoreados": [],
        "tweets_hoy": 0,
    }


def guardar_estado(estado: dict):
    """Guarda el estado en el archivo JSON."""
    if PREVIEW_MODE:
        log.info("Modo preview: no se guarda el estado.")
        return
    estado["ultimo_run"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
        log.info("Estado guardado correctamente.")
    except Exception as e:
        log.error(f"Error guardando estado: {e}")


def evento_ya_procesado(estado: dict, evento_id: str) -> bool:
    """Verifica si un evento ya fue tuiteado."""
    return evento_id in estado.get("eventos_procesados", [])


def marcar_evento_procesado(estado: dict, evento_id: str):
    """Marca un evento como procesado."""
    if "eventos_procesados" not in estado:
        estado["eventos_procesados"] = []
    if evento_id not in estado["eventos_procesados"]:
        estado["eventos_procesados"].append(evento_id)
        # Limpiar eventos viejos (más de 500) para no inflar el archivo
        if len(estado["eventos_procesados"]) > 500:
            estado["eventos_procesados"] = estado["eventos_procesados"][-300:]


def generar_evento_id(fixture_id: int, evento: dict) -> str:
    """
    Genera un ID único para un evento de partido.
    Combina fixture_id + minuto + tipo + jugador para ser determinístico.
    """
    minuto  = evento.get("time", {}).get("elapsed", 0)
    extra   = evento.get("time", {}).get("extra", 0) or 0
    tipo    = evento.get("type", "").replace(" ", "_").lower()
    detalle = evento.get("detail", "").replace(" ", "_").lower()
    jugador = evento.get("player", {}).get("name", "").replace(" ", "_").lower()
    return f"{fixture_id}_{minuto}+{extra}_{tipo}_{detalle}_{jugador}"


def generar_id_entretiempo(fixture_id: int) -> str:
    return f"{fixture_id}_HT_resumen"


def generar_id_final(fixture_id: int) -> str:
    return f"{fixture_id}_FT_final"


def generar_id_fixture_dia(fecha: str) -> str:
    return f"fixture_dia_{fecha}"


def generar_id_tabla(fecha: str) -> str:
    return f"tabla_grupo_{fecha}"


def generar_id_dato_curioso(fecha: str) -> str:
    return f"dato_curioso_{fecha}"


def commit_estado_en_github():
    """
    En GitHub Actions: hace git commit del state.json actualizado
    para que persista entre runs.
    Solo funciona dentro de GitHub Actions.
    """
    if PREVIEW_MODE:
        log.info("Modo preview: no se commitea el estado.")
        return
    if not os.environ.get("GITHUB_ACTIONS"):
        log.info("No estamos en GitHub Actions, skip commit de estado.")
        return

    try:
        os.system('git config --global user.email "bot@mundial2026.com"')
        os.system('git config --global user.name "Mundial Bot"')
        os.system("git add state.json")
        os.system('git commit -m "bot: actualizar estado [skip ci]" --allow-empty')
        os.system("git push")
        log.info("Estado commiteado a GitHub.")
    except Exception as e:
        log.error(f"Error en commit de estado: {e}")
