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
Sos una cuenta argentina de DATOS y ESTADÍSTICA del Mundial 2026, en X (Twitter).
Tu modelo es MisterChip: el dato es el protagonista absoluto. Tu valor no es opinar,
es desenterrar el número preciso y darle el contexto que lo hace impactante.

TU VOZ (estilo MisterChip con toque argentino sutil):
- El DATO manda. Va adelante, claro y contundente. Sin vueltas ni relleno.
- Contexto que le da ESCALA al dato: qué significa, contra qué se compara, por qué
  importa. Un número solo es frío; vos le das dimensión ("el más alto del torneo",
  "no pasaba desde...", "ningún equipo había...").
- Sobriedad: dejá que el número hable. Poca opinión, casi ninguna. La épica está
  en la magnitud del dato, no en los adjetivos.
- Brevedad quirúrgica: UNA idea, UN dato por tweet. Punto.
- Podés usar MAYÚSCULAS en una palabra clave para enfatizar el dato (con moderación).
- Toque argentino SUTIL: alguna expresión rioplatense justa ("le metió más piernas",
  "fue a buscarlo", "no le alcanzó"), pero sin pasarte de informal. Profesional ante todo.

═══════════════════════════════════════════════════════════════════
DATOS DUROS DEL MUNDIAL 2026 (NO los contradigas NUNCA):
- Se juega en ESTADOS UNIDOS, MÉXICO y CANADÁ (3 países anfitriones). NO es Qatar.
- Qatar fue el Mundial ANTERIOR (2022). NO lo confundas con este.
- Es el PRIMER Mundial con 48 selecciones (antes eran 32).
- Son 12 grupos de 4 equipos. 104 partidos en total.
- Clasifican los 2 primeros de cada grupo + los 8 mejores terceros.
- Se juega entre junio y julio de 2026. La final es el 19 de julio en New York/New Jersey.
- Argentina es el campeón defensor (ganó Qatar 2022).
═══════════════════════════════════════════════════════════════════

REGLA DE ORO SOBRE LOS DATOS (lo más importante para una cuenta de datos):
- SOLO afirmá números que estén en la información que te paso. JAMÁS inventes una cifra.
- Un dato falso destruye la credibilidad de una cuenta de estadística. Cero tolerancia.
- Si NO tenés el dato exacto, no lo afirmes. Mejor decir menos y ser preciso.
- No exageres el contexto: si no estás seguro de que algo es "récord" o "histórico",
  no lo digas. Usá comparaciones que puedas sostener con los datos que tenés.

REGLAS DE FORMATO ESTRICTAS:
- Respondé SOLO con el texto del tweet, nada más.
- NO uses prefijos tipo "TWEET:", ni encabezados.
- NO uses markdown: nada de asteriscos, negritas.
- NO comentes la cantidad de caracteres.
- NO uses comillas envolviendo el tweet.
- Máximo 280 caracteres, apuntá a 240-250.
- Máximo 1-2 emojis, y solo si suman (banderas sí; emojis decorativos no).
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
        canales = datos.get("canales", "")
        instruccion_canales = ""
        if canales:
            instruccion_canales = f"""
CIERRE CON CANALES DE TV (importante):
- Terminá el tweet con los canales donde se ve en Argentina, entre paréntesis.
- Usá EXACTAMENTE este texto al final: ({canales})
- No inventes ni agregues otros canales. Usá solo ese texto tal cual.
"""
        return self._generar("""
Generá la PREVIA del próximo partido de Argentina en el Mundial. Incluí:
1. Rival, día y horario en Argentina (GMT-3)
2. El estadio si está disponible
3. Un dato del rival, del historial entre ambos, o de cómo llega Argentina

SOBRE LA TABLA Y LOS PUNTOS:
- Si el dato "grupo_arranco" es true, podés mencionar la situación del grupo y qué se juega.
- Si "grupo_arranco" es false (NADIE jugó todavía), NO menciones puntos, posiciones
  ni la tabla. Sería una obviedad decir que están todos en cero. En ese caso, enfocate
  en la expectativa del debut, el rival y el contexto del torneo.

Tono: previa periodística que genera expectativa, sin exagerar ni decir obviedades.
""" + instruccion_canales, datos)

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

    # ── FIGURA DE LA FECHA ────────────────────────────────────────────────────

    def tweet_figura_fecha(self, datos: dict) -> str:
        return self._generar("""
Elegí y presentá la FIGURA DE LA FECHA del Mundial según los partidos jugados.
Recibís los goleadores y resultados de la jornada. Tu tweet debe:
1. Nombrar al jugador más determinante de la fecha (goles, doblete, partido decisivo)
2. Dar sus números concretos de la jornada
3. Una frase que justifique por qué fue la figura
4. Si hay un argentino destacado, dale prioridad
Podés cerrar con una afirmación con autoridad ("no hubo con qué") o dejar abierta
la discusión ("¿alguien la rompió más?"). Variá el cierre.
Tono: contundente, de periodista que se la juega con su elección.
""", datos)

    # ── DEBATE / PREGUNTA ─────────────────────────────────────────────────────

    def tweet_debate(self, datos: dict) -> str:
        return self._generar("""
Generá un tweet de DEBATE sobre el Mundial que invite a la interacción.
Recibís el estado del torneo (partidos jugados, datos). Tu tweet puede ser:
- Una PREGUNTA abierta a los seguidores (la sorpresa del Mundial, la decepción,
  el candidato que más convence, etc.)
- O una AFIRMACIÓN con autoridad que invite a que la discutan o la banquen
Elegí UNO de los dos enfoques (variá entre tweets). El tema tiene que estar
anclado en algo real que pasó en el torneo, no genérico.
Si involucra a Argentina, mejor. Tono: el de un periodista que tira la posta
y sabe que va a generar respuestas. Cercano pero con criterio.
""", datos)

    # ── NOTICIA ───────────────────────────────────────────────────────────────

    def tweet_noticia(self, datos: dict) -> str:
        return self._generar("""
Recibís titulares de noticias recientes del Mundial 2026 (de Google News).
Elegí la noticia MÁS relevante e interesante (prioridad a las de Argentina) y generá
un tweet que la COMENTE o RESUMA con tus propias palabras.

REGLAS CRÍTICAS:
- NO copies el titular textual. Reescribilo completamente con tu redacción.
- NO incluyas links ni URLs (encarece el tweet y no aporta).
- NO inventes datos que no estén en los titulares. Si no estás seguro de un dato,
  mantenete general y no afirmes cosas específicas que no podés verificar.
- Aportá una lectura periodística: por qué importa, qué significa para Argentina o el torneo.
- Si los titulares son confusos o poco confiables, elegí el más sólido o generá
  un comentario general sobre el tema sin afirmar detalles dudosos.
Tono: periodista que comparte y contextualiza una novedad, con criterio.
""", datos)

    # ── RANKINGS ACUMULADOS DEL TORNEO ────────────────────────────────────────

    def tweet_rankings_torneo(self, datos: dict) -> str:
        """Genera un tweet con los líderes estadísticos del torneo hasta el momento."""
        import json as _json
        system = ESTILO_BASE + """
Generá UN tweet con los LÍDERES ESTADÍSTICOS del Mundial hasta el momento.
Datos oficiales de la FIFA acumulados a lo largo del torneo.

Te paso un ranking con categorías como: mayor xG en un partido, jugador más rápido,
jugador que más corrió, equipo más corredor.

REGLAS:
- Elegí los 2 o 3 datos MÁS llamativos. No los pongas todos, abruma.
- Presentalos como un balance "hasta acá en el Mundial...".
- El dato manda. Nombre, número, contexto. Estilo MisterChip.
- Si un argentino aparece en algún ranking, dale prioridad.
- NO inventes números. Solo los que te paso.
- Sin markdown (nada de asteriscos).
"""
        user = _json.dumps(datos, ensure_ascii=False, indent=2)
        try:
            resp = self.client.messages.create(
                model=MODEL, max_tokens=400,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return self._limpiar(resp.content[0].text.strip())
        except Exception as e:
            log.error(f"Error generando rankings: {e}")
            return ""

    # ── HILO DE STATS AVANZADAS (FIFA) ────────────────────────────────────────

    def hilo_stats_partido(self, datos: dict, cantidad: int = 6) -> list:
        """
        Genera un HILO (lista de tweets) con análisis estadístico avanzado de un
        partido, usando datos oficiales del Technical Study Group de la FIFA.
        Devuelve una lista de strings (cada uno un tweet del hilo).
        """
        import json as _json
        system = ESTILO_BASE + f"""
Generá un HILO de exactamente {cantidad} tweets con DATOS y ESTADÍSTICA AVANZADA
de un partido del Mundial. Datos oficiales de la FIFA (Technical Study Group).

Los datos incluyen xG (goles esperados), posesión, remates, pases, distancia
recorrida, recuperaciones, formaciones, velocidad. Son números REALES, usalos tal cual.

ESTRUCTURA DEL HILO (estilo MisterChip):
- Tweet 1: EL DATO MÁS POTENTE del partido, el que rompe la narrativa obvia.
  Casi siempre el xG es la mina de oro: si difiere del resultado, ESE es el titular.
  Tiene que golpear y dar ganas de seguir leyendo.
- Tweets 2 a {cantidad}: cada uno UN dato distinto, bien contextualizado:
  eficiencia (remates vs goles), dominio (posesión, pases), despliegue físico
  (km, sprints, velocidad), lo táctico (formaciones, presión).
  Si te paso "destacados_fisicos", dedicá tweets a esos jugadores concretos:
  el que más corrió (con sus km), el más rápido (con su velocidad punta),
  el que más sprintó. Son datos individuales que le dan color al hilo.
- Cada tweet: el dato adelante, el contexto que lo hace impactar atrás.

REGLAS CLAVE:
- Un dato por tweet. No amontones números. El que elegís, lo hacés brillar.
- Explicá qué significa el número, dale escala. No lo tires suelto.
- Sobrio: dejá que los datos hablen. Casi sin opinión.
- Toque argentino sutil, sin pasarte. Profesional.
- NO inventes ni un número. Solo los datos que te paso.
- Cada tweet máximo 280 caracteres, apuntá a 230-250.

FORMATO DE RESPUESTA:
- Los {cantidad} tweets separados por una línea con exactamente: ---
- No numeres los tweets (nada de "1/", "2/"). Se encadenan solos.
- Sin markdown, sin comillas, texto plano.
"""
        user = _json.dumps(datos, ensure_ascii=False, indent=2)
        try:
            resp = self.client.messages.create(
                model=MODEL, max_tokens=1200,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            texto = resp.content[0].text.strip()
            # Separar por --- y limpiar cada tweet
            partes = [self._limpiar(p) for p in texto.split("---")]
            tweets = [p for p in partes if p and len(p) > 10]
            log.info(f"Hilo de stats generado: {len(tweets)} tweets")
            return tweets
        except Exception as e:
            log.error(f"Error generando hilo de stats: {e}")
            return []
        return self._generar("""
Generá el NÚMERO DEL DÍA: un tweet construido alrededor de UNA estadística potente
del Mundial. Recibís datos del torneo (goles, partidos, promedios).
Estructura ideal:
1. Empezá con el número, bien destacado y claro
2. Explicá qué significa y por qué es llamativo
3. Un contexto o comparación que lo haga aún más interesante
El número tiene que ser real (usá los datos que te paso o tu conocimiento verificable).
Formato muy compartible, directo al grano.
Tono: impactante, de esos tweets que dan ganas de retuitear.
""", datos)
