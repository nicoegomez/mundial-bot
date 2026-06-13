"""
tweet_generator.py — Genera tweets con Claude para cada tipo de evento del Mundial
"""

import json
import logging
import anthropic

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 400

ESTILO_BASE = """
Sos un periodista deportivo argentino que cubre el Mundial 2026 en tiempo real para X (Twitter).
Tu estilo:
- Lenguaje rioplatense natural, apasionado pero con rigor periodístico
- Incluís siempre el dato estadístico más relevante del momento
- Nunca más de 280 caracteres
- Sin hashtags (excepto #Mundial2026 cuando sea muy relevante)
- Máximo 2 emojis por tweet, bien elegidos
- El marcador siempre visible cuando hay goles
- Contexto histórico cuando sea posible (récords, comparaciones, "por primera vez")
- Si es un partido que afecta a Argentina, lo aclarás aunque no juegue
"""


class TweetGenerator:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def _generar(self, system_extra: str, datos: dict) -> str:
        """Genera un tweet dado el contexto del evento."""
        system = ESTILO_BASE + "\n" + system_extra
        user   = json.dumps(datos, ensure_ascii=False, indent=2)

        try:
            resp = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            tweet = resp.content[0].text.strip().strip('"').strip("'")
            log.info(f"Tweet generado ({len(tweet)} chars): {tweet[:60]}...")
            return tweet
        except Exception as e:
            log.error(f"Error generando tweet: {e}")
            return ""

    # ── EVENTOS EN VIVO ───────────────────────────────────────────────────────

    def tweet_gol(self, datos: dict) -> str:
        """
        datos: marcador, minuto, goleador, asistidor, stats_goleador_torneo,
               estadisticas_partido, es_argentina, contexto_historico
        """
        return self._generar("""
Acaba de convertirse un GOL. Tu tweet debe incluir:
1. El marcador actualizado de forma clara (ej: "Argentina 2-0 Francia")
2. Quién hizo el gol y en qué minuto
3. Un dato estadístico potente: goles del jugador en el torneo, si es récord, 
   si es el primero del equipo en el Mundial, asistencias en el torneo, etc.
4. Si afecta la clasificación de Argentina aunque no juegue, mencionalo.
El tono es el de alguien que está viendo el partido en vivo y se emociona con el dato.
""", datos)

    def tweet_penal(self, datos: dict) -> str:
        """
        datos: marcador, minuto, ejecutor, resultado (gol/errado/atajado),
               arquero si atajó, stats_penal_torneo, es_argentina
        """
        return self._generar("""
Acaba de suceder un PENAL. Tu tweet debe incluir:
1. Si fue gol o errado/atajado y quién lo ejecutó
2. El marcador actual
3. Un dato: ¿cuántos penales convirtió/erró ese jugador en el torneo?
   ¿Es un momento clave del partido? ¿Cómo cambia el resultado?
4. Si el arquero atajó, mencionalo con algún dato suyo.
Tono: vivencial, como si lo estuvieras narrando.
""", datos)

    def tweet_tarjeta_roja(self, datos: dict) -> str:
        """
        datos: marcador, minuto, jugador_expulsado, equipo, razon,
               es_directa_o_segunda_amarilla, stats_partido_actuales
        """
        return self._generar("""
Acaba de haber una TARJETA ROJA. Tu tweet debe incluir:
1. Quién fue expulsado, de qué equipo y en qué minuto
2. Si fue directa o segunda amarilla
3. Cómo cambia tácticamente el partido (equipo en inferioridad)
4. El marcador actual
5. Si es un jugador clave, mencioná el impacto en el equipo
Tono: analítico pero con impacto emocional.
""", datos)

    def tweet_var(self, datos: dict) -> str:
        """
        datos: partido, minuto, que_se_reviso, decision_final, marcador_antes,
               marcador_despues, descripcion_jugada
        """
        return self._generar("""
Hubo una revisión del VAR. Tu tweet debe incluir:
1. Qué se revisó (gol, penal, roja, etc.)
2. La decisión final del árbitro tras el VAR
3. Si anuló un gol o cambió el marcador, remarcalo con el marcador nuevo
4. Si es polémico, podés usar un tono levemente crítico sin exagerar
5. El impacto en el partido
Tono: claro, informativo, con algo de picardía si la decisión es discutible.
""", datos)

    def tweet_lesion(self, datos: dict) -> str:
        """
        datos: partido, minuto, jugador_lesionado, equipo, descripcion,
               reemplazante, stats_jugador_torneo, es_figura
        """
        return self._generar("""
Hay una LESIÓN importante en el partido. Tu tweet debe incluir:
1. Quién se lesionó y en qué minuto
2. Qué tan clave es ese jugador para su selección
3. Stats del jugador en el torneo hasta ahora
4. Por quién fue reemplazado
5. El impacto potencial para el resto del partido/torneo
Solo cubrís lesiones de figuras o jugadores relevantes. Tono: con preocupación genuina.
""", datos)

    def tweet_entretiempo(self, datos: dict) -> str:
        """
        datos: marcador, estadisticas_completas, eventos_pt, goleadores,
               analisis_tactico, implica_argentina
        """
        return self._generar("""
Terminó el PRIMER TIEMPO. Tu tweet es un resumen ejecutivo que incluye:
1. El marcador y lo más destacado que pasó
2. Las 2-3 estadísticas más llamativas del PT (posesión, tiros al arco, etc.)
3. Si hubo goles, quién los hizo
4. Una frase de análisis táctico breve
5. Si el resultado afecta a Argentina (aunque no juegue), mencionalo
Tono: resumen periodístico, conciso y con datos precisos.
""", datos)

    def tweet_final_partido(self, datos: dict) -> str:
        """
        datos: marcador_final, estadisticas_completas, goleadores,
               tabla_grupo_actualizada, hito_historico, implica_argentina,
               top_goleadores_torneo
        """
        return self._generar("""
Terminó el PARTIDO. Tu tweet debe incluir:
1. El resultado final claro
2. Un dato estadístico que resuma el partido (ej: dominó posesión, más tiros, etc.)
3. Si hubo un hito histórico (primer gol de un país en el torneo, récord, etc.)
4. Cómo queda la tabla del grupo después de este resultado
5. Si afecta la clasificación de Argentina, es prioritario mencionarlo
Tono: contundente, con datos que justifiquen el resultado.
""", datos)

    # ── TWEETS FUERA DEL PARTIDO ──────────────────────────────────────────────

    def tweet_fixture_dia(self, datos: dict) -> str:
        """
        datos: partidos_hoy (lista con horarios AR, grupos, rivales),
               partidos_de_argentina
        """
        return self._generar("""
Es el resumen del FIXTURE DEL DÍA en el Mundial. Tu tweet debe incluir:
1. Cuántos partidos hay hoy y de qué grupos
2. Si Argentina juega, es la prioridad absoluta con horario AR (GMT-3)
3. Los partidos más atractivos del día
4. Qué está en juego (clasificación, primeros puestos, etc.)
Tono: anticipatorio, generando expectativa para el día mundialista.
""", datos)

    def tweet_tabla_grupo(self, datos: dict) -> str:
        """
        datos: nombre_grupo, tabla_formateada, que_necesita_argentina,
               partidos_restantes
        """
        return self._generar("""
Actualizá la TABLA DE POSICIONES del grupo de Argentina. Tu tweet debe incluir:
1. Las posiciones actuales del grupo (podés usar formato de lista corta)
2. Cómo está Argentina y qué necesita para clasificar
3. Quiénes son los rivales directos
4. Partidos restantes del grupo
Tono: informativo y claro, como un panel deportivo que actualiza la tabla.
""", datos)

    def tweet_dato_curioso(self, datos: dict) -> str:
        """
        datos: torneo_stats (goles totales, promedio, etc.), top_goleadores,
               records_del_dia, argentina_stats
        """
        return self._generar("""
Generá un DATO CURIOSO O ESTADÍSTICO del Mundial que sea genuinamente interesante.
Puede ser:
- Un récord que se acaba de romper
- Una comparación histórica ("la última vez que esto pasó fue en...")
- Un dato de Argentina en el torneo
- Una estadística llamativa del día
- Un hecho inédito del torneo
Tono: fascinación periodística. Que el lector quiera compartirlo.
""", datos)

    def tweet_recordatorio_partido(self, datos: dict) -> str:
        """
        datos: local, visitante, hora_argentina, grupo, lo_que_esta_en_juego,
               historial_reciente
        """
        return self._generar("""
Recordatorio de un PARTIDO QUE ESTÁ POR COMENZAR. Tu tweet debe incluir:
1. Los equipos que juegan y el horario en Argentina (GMT-3)
2. El grupo al que pertenece y qué está en juego
3. Un dato de expectativa: el jugador a seguir, el historial entre ambos, etc.
4. Si afecta a Argentina aunque no juegue, es prioritario
Tono: anticipatorio, generando ganas de ver el partido.
""", datos)

    def tweet_formaciones(self, datos: dict) -> str:
        """
        datos: local, visitante, formacion_local, formacion_visitante,
               xi_local, xi_visitante, dt_local, dt_visitante, es_argentina
        """
        return self._generar("""
Se confirmaron las FORMACIONES de un partido que está por empezar. Tu tweet debe incluir:
1. Los dos equipos y el horario si está disponible
2. El esquema táctico de cada uno (ej: 4-3-3 vs 4-4-2)
3. Si hay alguna sorpresa en el XI o ausencia importante, destacala
4. Mencioná 1-2 jugadores clave de cada lado
5. Si es Argentina, prioridad absoluta: el XI completo o los nombres más importantes
Por el límite de 280 caracteres, priorizá lo más relevante. Si es Argentina,
podés listar el XI de forma compacta. Para otros partidos, foco en el esquema y figuras.
Tono: el de alguien que acaba de ver salir las formaciones y las analiza.
""", datos)
