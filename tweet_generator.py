"""
tweet_generator.py — Genera tweets con Claude para el Mundial 2026
Tono: periodístico argentino, apasionado pero con rigor. Sin informalidad extrema.
"""

import re
import json
import logging
import anthropic

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 400

ESTILO_BASE = """
Sos un periodista deportivo argentino que cubre el Mundial 2026 para X (Twitter).
Tu voz: apasionada pero con rigor periodístico, con la cadencia del Río de la Plata,
sin caer en informalidad excesiva ni en exceso de modismos. Profesional y cercano.

Reglas de estilo:
- Lenguaje rioplatense natural (vos, podés, tenés), pero serio y creíble
- Siempre incluís el dato más relevante: marcador, goleador, estadística, contexto
- Nunca más de 280 caracteres. Apuntá a 240-250 para tener margen seguro.
- Contexto histórico cuando sume (récords, comparaciones, antecedentes mundialistas)
- Foco en Argentina cuando corresponda, aunque no sea protagonista del partido
- Máximo 2 emojis bien elegidos

REGLAS DE FORMATO ESTRICTAS:
- Respondé SOLO con el texto del tweet, nada más.
- NO uses prefijos tipo "TWEET:", ni encabezados.
- NO uses markdown: nada de asteriscos, negritas, ni guiones separadores (---).
- NO comentes la cantidad de caracteres.
- NO uses comillas envolviendo el tweet.
- Texto plano, como aparecería publicado directamente en X.
"""


class TweetGenerator:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def _generar(self, system_extra: str, datos: dict) -> str:
        system = ESTILO_BASE + "\n" + system_extra
        user = json.dumps(datos, ensure_ascii=False, indent=2)
        try:
            resp = self.client.messages.create(
                model=MODEL, max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            tweet = self._limpiar(resp.content[0].text.strip())
            log.info(f"Tweet generado ({len(tweet)} chars): {tweet[:60]}...")
            return tweet
        except Exception as e:
            log.error(f"Error generando tweet: {e}")
            return ""

    @staticmethod
    def _limpiar(texto: str) -> str:
        t = texto.strip()
        t = re.sub(r'^\**\s*tweet\s*:?\s*\**\s*', '', t, flags=re.IGNORECASE)
        t = t.strip().strip('"').strip("'").strip()
        t = re.sub(r'\*\*([^*]+)\*\*', r'\1', t)
        t = re.sub(r'\*([^*]+)\*', r'\1', t)
        t = re.sub(r'\n-{2,}\n', '\n', t)
        t = re.sub(r'^\s*-{2,}\s*$', '', t, flags=re.MULTILINE)
        t = re.sub(r'\n*\*?\(?\d+\s*caracteres?[^)]*\)?\*?\s*$', '', t, flags=re.IGNORECASE)
        return t.strip()

    # ── RESUMEN DE PARTIDO ────────────────────────────────────────────────────

    def tweet_resumen_partido(self, datos: dict) -> str:
        return self._generar("""
Acaba de terminar un partido del Mundial. Generá un tweet de cierre que incluya:
1. El resultado final claro (marcador)
2. Los goleadores con el minuto (si los datos los traen)
3. Un dato o lectura del partido: qué significa, cómo cambia el grupo
4. Si es Argentina, prioridad total. Si no, una lectura con criterio.
5. Si el resultado afecta indirectamente a Argentina, mencionalo.
Tono: el de un periodista que cierra la transmisión con un resumen filoso.
""", datos)

    # ── ANÁLISIS DE CLASIFICACIÓN ─────────────────────────────────────────────

    def tweet_analisis_clasificacion(self, datos: dict) -> str:
        return self._generar("""
Generá un tweet de ANÁLISIS DE CLASIFICACIÓN del grupo de Argentina.
Recibís datos ya calculados (tabla, puntos, escenarios). Narralos con criterio:
1. Según la fecha del grupo:
   - Fecha 1: panorama + un dato histórico (equipos que arrancaron así y avanzaron)
   - Fecha 2: qué necesita cada equipo para clasificar en la última fecha
   - Fecha 3: situación final, quiénes pasan
2. Datos concretos: puntos, qué resultado necesita un equipo, chances reales
3. Foco en Argentina, pero podés señalar la situación dramática de cualquier equipo
4. Una comparación histórica que enriquezca el análisis
Usá los números que te paso, no inventes resultados. Preciso y atractivo a la vez.
Tono: analista que sabe de números y de historia mundialista.
""", datos)

    # ── FIXTURE DEL DÍA ───────────────────────────────────────────────────────

    def tweet_fixture_dia(self, datos: dict) -> str:
        return self._generar("""
Es el resumen del FIXTURE DEL DÍA en el Mundial. Tu tweet debe incluir:
1. Cuántos partidos hay hoy
2. Si Argentina juega, es prioridad absoluta con horario AR
3. Los partidos más atractivos del día
4. Qué está en juego
Tono: anticipatorio, generando expectativa para la jornada.
""", datos)

    # ── PREVIA DE ARGENTINA ───────────────────────────────────────────────────

    def tweet_previa_argentina(self, datos: dict) -> str:
        return self._generar("""
Generá la PREVIA del próximo partido de Argentina en el Mundial. Incluí:
1. Rival, día y horario en Argentina (GMT-3)
2. Qué está en juego según la tabla del grupo
3. Un dato del rival o del historial entre ambos
4. El estadio si está disponible
Tono: previa periodística que genera expectativa, sin exagerar.
""", datos)

    # ── DATO CURIOSO ──────────────────────────────────────────────────────────

    def tweet_dato_curioso(self, datos: dict) -> str:
        return self._generar("""
Generá un DATO CURIOSO O ESTADÍSTICO del Mundial 2026 que sea genuinamente interesante.
Puede ser sobre el formato de 48 equipos, un récord, una comparación histórica,
el promedio de goles del torneo hasta ahora, o un dato de Argentina.
Recibís algunos números del torneo (partidos jugados, goles). Usalos si suman.

IMPORTANTE: Si los datos vienen vacíos o incompletos, NO lo menciones.
NUNCA escribas "los datos llegaron vacíos" ni nada similar. Generá un dato real
y verificable con tu conocimiento del Mundial y su historia.
Tono: fascinación periodística, que invite a compartir.
""", datos)
