"""
fifa_reports.py — Lee los Post-Match Summary Reports (PMSR) oficiales de la FIFA
desde el Match Report Hub del FIFA Training Centre.

Extrae estadísticas avanzadas: xG, posesión, remates, pases, físico, duelos, etc.
Los PDFs son públicos (sin login). Patrón de URL:
  .../fifa-world-cup/2026/PMSR-M##-XXX-V-YYY.pdf

NOTA DE COPYRIGHT: los reportes son de la FIFA. Este módulo extrae DATOS
(números, hechos) para que Claude genere análisis ORIGINAL. No reproduce el
documento ni su texto.
"""

import io
import re
import logging
import requests
import pypdf

log = logging.getLogger(__name__)

HUB_URL = "https://www.fifatrainingcentre.com/en/fifa-world-cup-2026/match-report-hub.php"
PDF_BASE = "https://www.fifatrainingcentre.com/media/native/tournaments/fifa-world-cup/2026/"

# Mapeo de nombres openfootball -> código FIFA de 3 letras (para armar URLs y matchear)
COD_FIFA = {
    "Mexico": "MEX", "South Africa": "RSA", "South Korea": "KOR", "Korea Republic": "KOR",
    "Czech Republic": "CZE", "Czechia": "CZE", "Canada": "CAN", "Bosnia & Herzegovina": "BIH",
    "Qatar": "QAT", "Switzerland": "SUI", "Brazil": "BRA", "Morocco": "MAR",
    "Haiti": "HAI", "Scotland": "SCO", "USA": "USA", "Paraguay": "PAR",
    "Australia": "AUS", "Turkey": "TUR", "Türkiye": "TUR", "Germany": "GER",
    "Curaçao": "CUW", "Netherlands": "NED", "Japan": "JAP", "Sweden": "SWE",
    "Tunisia": "TUN", "Ivory Coast": "CIV", "Ecuador": "ECU", "Iran": "IRN",
    "New Zealand": "NZL", "Belgium": "BEL", "Egypt": "EGY", "Saudi Arabia": "KSA",
    "Uruguay": "URU", "Spain": "ESP", "Cape Verde": "CPV", "France": "FRA",
    "Senegal": "SEN", "Iraq": "IRQ", "Norway": "NOR", "Argentina": "ARG",
    "Algeria": "ALG", "Austria": "AUT", "Jordan": "JOR", "Portugal": "POR",
    "DR Congo": "COD", "Uzbekistan": "UZB", "Colombia": "COL", "Ghana": "GHA",
    "Panama": "PAN", "England": "ENG", "Croatia": "CRO",
}


def _descargar_hub() -> str:
    """Baja el HTML del Match Report Hub para encontrar los PDFs disponibles."""
    try:
        r = requests.get(HUB_URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text
    except Exception as e:
        log.error(f"No se pudo leer el Match Report Hub: {e}")
        return ""


def buscar_pdf_partido(team1: str, team2: str) -> str | None:
    """
    Busca el link del PDF para un partido dado (en cualquier orden de equipos).
    Devuelve la URL completa o None si no está disponible todavía.
    """
    html = _descargar_hub()
    if not html:
        return None

    c1 = COD_FIFA.get(team1)
    c2 = COD_FIFA.get(team2)
    if not c1 or not c2:
        log.warning(f"Sin código FIFA para {team1} o {team2}")
        return None

    # Los links son tipo PMSR-M07-BRA-V-MAR.pdf o PMSR-M07 BRA V MAR.pdf
    # Buscamos cualquier PDF que contenga ambos códigos.
    pdfs = re.findall(r'(PMSR[^"\']*?\.pdf)', html)
    for pdf in pdfs:
        pdf_up = pdf.upper().replace("%20", " ")
        if c1 in pdf_up and c2 in pdf_up:
            url = PDF_BASE + pdf.replace(" ", "%20")
            log.info(f"PDF encontrado para {team1} vs {team2}: {pdf}")
            return url
    log.info(f"Reporte FIFA aún no disponible para {team1} vs {team2}")
    return None


def _texto_pdf(url: str) -> str:
    """Descarga el PDF y extrae todo el texto."""
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        reader = pypdf.PdfReader(io.BytesIO(r.content))
        texto = "\n".join(page.extract_text() or "" for page in reader.pages)
        return texto
    except Exception as e:
        log.error(f"Error leyendo PDF {url}: {e}")
        return ""


def _num(texto: str, patron: str) -> str | None:
    """Extrae el primer match de un patrón, o None."""
    m = re.search(patron, texto)
    return m.group(1) if m else None


def extraer_stats(team1: str, team2: str) -> dict | None:
    """
    Extrae las estadísticas clave del reporte de un partido.
    Devuelve un dict con los datos, o None si no hay reporte disponible.

    El equipo 1 del reporte es el local (team1 del PDF), que puede no coincidir
    con el orden que pedimos. Por eso devolvemos los datos etiquetados con los
    nombres tal como aparecen en el PDF.
    """
    url = buscar_pdf_partido(team1, team2)
    if not url:
        return None

    texto = _texto_pdf(url)
    if not texto:
        return None

    stats = {"_fuente": "FIFA Technical Study Group", "_url": url}

    # La sección "Key Statistics" tiene el formato:
    #   46.7% 8.1% 45.2% Total      <- posesión (local / disputa / visitante)
    #   1 Goals 1
    #   0.99 xG (Expected Goals) 1.33
    #   12 (5) Attempts at Goal (On Target) 14 (3)
    #   514 (457) Total Passes (Complete) 503 (431)
    #   89 % Pass Completion % 86 %
    # etc.

    # xG — el más valioso
    m = re.search(r'([\d.]+)\s+xG \(Expected Goals\)\s+([\d.]+)', texto)
    if m:
        stats["xg_local"] = m.group(1)
        stats["xg_visitante"] = m.group(2)

    # Posesión: "46.7% 8.1% 45.2% Total"
    m = re.search(r'([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%\s+Total', texto)
    if m:
        stats["posesion_local"] = m.group(1)
        stats["posesion_disputa"] = m.group(2)
        stats["posesion_visitante"] = m.group(3)

    # Remates: "12 (5) Attempts at Goal (On Target) 14 (3)"
    m = re.search(r'(\d+) \((\d+)\) Attempts at Goal \(On Target\) (\d+) \((\d+)\)', texto)
    if m:
        stats["remates_local"] = m.group(1)
        stats["remates_local_arco"] = m.group(2)
        stats["remates_visitante"] = m.group(3)
        stats["remates_visitante_arco"] = m.group(4)

    # Pases: "514 (457) Total Passes (Complete) 503 (431)"
    m = re.search(r'(\d+) \((\d+)\) Total Passes \(Complete\) (\d+) \((\d+)\)', texto)
    if m:
        stats["pases_local"] = m.group(1)
        stats["pases_local_ok"] = m.group(2)
        stats["pases_visitante"] = m.group(3)
        stats["pases_visitante_ok"] = m.group(4)

    # % acierto de pase: "89 % Pass Completion % 86 %"
    m = re.search(r'(\d+) % Pass Completion % (\d+) %', texto)
    if m:
        stats["pase_pct_local"] = m.group(1)
        stats["pase_pct_visitante"] = m.group(2)

    # Distancia total: "113.7 km Total Distance Covered 114.9 km"
    m = re.search(r'([\d.]+) km Total Distance Covered ([\d.]+) km', texto)
    if m:
        stats["distancia_local"] = m.group(1)
        stats["distancia_visitante"] = m.group(2)

    # Forced turnovers: "41 Forced Turnovers 50"
    m = re.search(r'(\d+) Forced Turnovers (\d+)', texto)
    if m:
        stats["turnovers_local"] = m.group(1)
        stats["turnovers_visitante"] = m.group(2)

    # Formaciones: "FORMATION 4-4-2" ... "FORMATION 4-2-3-1"
    formaciones = re.findall(r'(\d-\d(?:-\d)?(?:-\d)?)\s*\n?\s*F\s*O\s*R\s*M', texto)
    # fallback: buscar "FORMATION" con número cerca
    forms = re.findall(r'FORMATION\s*(\d[-\d]+)', texto.replace("\n", " "))
    if forms:
        if len(forms) >= 2:
            stats["formacion_local"] = forms[0]
            stats["formacion_visitante"] = forms[1]

    # Velocidad máxima del partido (Top Speed más alto)
    velocidades = re.findall(r'(\d{2}\.\d)\s*$', texto, re.MULTILINE)
    velocidades += re.findall(r'\b(3[0-9]\.\d|2[0-9]\.\d)\b', texto)
    if velocidades:
        try:
            top = max(float(v) for v in velocidades if 25 <= float(v) <= 40)
            stats["velocidad_max"] = f"{top:.1f}"
        except (ValueError, TypeError):
            pass

    # Guardamos los nombres tal cual para que Claude sepa quién es local/visitante
    # En el PDF, el orden es el del encabezado "Team1 X - Y Team2"
    m = re.search(r'^(.+?)\s+(\d+)\s*-\s*(\d+)\s+(.+?)$', texto.strip().split("\n")[0])
    if m:
        stats["equipo_local"] = m.group(1).strip()
        stats["goles_local"] = m.group(2)
        stats["goles_visitante"] = m.group(3)
        stats["equipo_visitante"] = m.group(4).strip()

    # Solo devolvemos si conseguimos al menos el xG (el dato estrella)
    if "xg_local" not in stats:
        log.warning("No se pudo extraer xG del reporte; quizá cambió el formato.")
        return None

    log.info(f"Stats FIFA extraídas: {len(stats)} campos")
    return stats
