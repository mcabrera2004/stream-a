"""
Prompts, parsers de JSON y logging del ÁGORA.

El logging es deliberadamente legible: imprime el intercambio entre agentes
como un diálogo, que es justo lo que pide el challenge (trazabilidad del
intercambio de mensajes).
"""
from __future__ import annotations

import json
import re
from typing import List


# ---------------------------------------------------------------------------
# Logging / trazabilidad
# ---------------------------------------------------------------------------

def log(emoji: str, stage: str, message: str) -> None:
    """Traza una transición del grafo de forma legible en consola."""
    print(f"{emoji} [{stage}] {message}", flush=True)


def sentiment_bar(value: float) -> str:
    """Representa un sentimiento (-1..1) como una etiqueta + signo legible."""
    sign = "🟢" if value > 0.15 else ("🔴" if value < -0.15 else "🟡")
    return f"{sign}{value:+.2f}"


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

PERSONA_FACTORY_PROMPT = """Sos un diseñador de simulaciones sociales (estilo "swarm intelligence").
A partir de un TEMA y CONTEXTO real, encarnás un panel realista de personas que representan
distintos segmentos de la opinión pública.

Te doy una lista de ARQUETIPOS pre-asignados (uno por persona). Para CADA arquetipo, en el
mismo orden, creás una persona concreta y creíble que encaje con ese rol y con el rango de
opinión indicado. Esto garantiza un panel diverso y con tensión real.

REGLAS:
1. RESPETÁ el arquetipo y su rango de stance (la opinión inicial, de -1 a +1).
2. REALISMO: nombre, profesión y trasfondo creíbles y variados (género, edad, contexto).
3. ANCLÁ la persona al TEMA y al CONTEXTO cuando tenga sentido.

==============================================================================
TEMA:
{topic}

CONTEXTO (fuentes reales):
{context}

ARQUETIPOS A ENCARNAR (en este orden):
{archetypes}
==============================================================================

FORMATO DE SALIDA (SOLO un array JSON de {n} objetos, en el MISMO orden que los arquetipos):
[
  {{
    "name": "Nombre Apellido",
    "profession": "profesión",
    "backstory": "1-2 frases que dan voz y contexto",
    "stance": -0.6
  }}
]
"""


REACTION_PROMPT = """Sos {name}, {profession}. Arquetipo: {archetype}.
Trasfondo: {backstory}
Tu opinión actual sobre el tema (de -1 a +1): {stance}.
Tu volatilidad (qué tan fácil cambiás de opinión): {volatility}.

Estás en una red social discutiendo este TEMA:
"{topic}"

CONTEXTO de la noticia:
{context}

FEED de la conversación hasta ahora (posts de otras personas; puede estar vacío en la ronda 1):
{feed}
{intervention_block}
TU TAREA:
Escribí UN post corto (máx 40 palabras), en primera persona, con tu voz característica.
- Si hay posts en el feed, RESPONDÉ a alguno mencionando a esa persona por nombre cuando tenga sentido.
- Dejá que tu volatilidad influya: si es alta, podés moverte hacia los argumentos que leíste; si es baja, mantené tu postura.
- Reportá tu sentimiento ACTUALIZADO hacia el tema tras leer el feed, de -1 a +1.

FORMATO DE SALIDA (SOLO un objeto JSON, sin texto extra):
{{"text": "tu post", "sentiment": 0.2}}
"""


INTERVENTION_BLOCK = """
⚡ INTERVENCIÓN / ANUNCIO NUEVO que acabás de ver (reaccioná teniéndolo en cuenta;
puede cambiar o reforzar tu postura según tu volatilidad):
"{intervention}"
"""

STRATEGIST_PROMPT = """Sos un estratega de comunicación. Acabás de observar una simulación de cómo
reacciona el público ante un TEMA. El debate convergió con cierto sentimiento y dejó al descubierto
las OBJECIONES principales. Tu trabajo es proponer {k} intervenciones DISTINTAS (mensajes, anuncios
o ajustes de política) que podrían MEJORAR la recepción, atacando esas objeciones de raíz.

REGLAS:
1. Cada intervención debe ser concreta y accionable (algo que de verdad se podría anunciar/hacer).
2. Cada una debe atacar un ángulo distinto de las objeciones detectadas (no variaciones de lo mismo).
3. Realista: no prometas magia; abordá la preocupación real que mostró el feed.

TEMA:
{topic}

MÉTRICAS Y OBJECIONES DE LA SIMULACIÓN BASELINE:
{analytics}

TRANSCRIPCIÓN (resumen del feed):
{feed}

FORMATO DE SALIDA (SOLO un array JSON de {k} objetos):
[
  {{"name": "etiqueta corta de la intervención", "text": "el anuncio/mensaje concreto, 1-2 frases"}}
]
"""


REPORT_AGENT_PROMPT = """Sos un analista de simulaciones sociales. Estás observando, con "vista de
Dios", una SIMULACIÓN del futuro: cómo reaccionaría la gente real ante este tema. El discurso y
las reacciones de los agentes son un PROXY de comportamiento humano futuro, no opiniones del presente.

REGLAS DE RIGOR:
- Basá TODAS tus afirmaciones ÚNICAMENTE en los datos de la simulación (feed + métricas).
  NO uses tu conocimiento general del tema ni inventes hechos que no estén en los datos.
- Tratá las métricas pre-computadas como evidencia dura; citá nombres de agentes como prueba.
- Sé predictivo (qué va a pasar), no descriptivo (qué pasó).

TEMA:
{topic}

PERSONAS QUE PARTICIPARON:
{personas}

MÉTRICAS PRE-COMPUTADAS DE LA SIMULACIÓN:
{analytics}

TRANSCRIPCIÓN COMPLETA DEL FEED BASELINE (todas las rondas):
{feed}

ANÁLISIS CONTRAFÁCTICO (qué pasó al RE-SIMULAR con cada intervención propuesta):
{comparison}

Generá un reporte en MARKDOWN con EXACTAMENTE estas secciones:

## 🔮 Outcome esperado (status quo)
(2-3 frases: si no se hace nada, ¿hacia dónde se inclina la opinión? ¿se polariza, converge, se enfría?)

## 📈 Trayectoria del sentimiento
(interpretá la evolución ronda a ronda del baseline: ¿se movió la aguja? ¿por qué?)

## ⚔️ Bandos emergentes
(qué facciones se formaron, quién las lidera, qué argumentos las unen)

## 🎯 Influencers clave
(qué personas movieron la conversación o hicieron cambiar de opinión a otras)

## 🧪 Análisis contrafáctico (qué palanca funciona)
(comparÁ las intervenciones re-simuladas contra el status quo: cuánto movió cada una el
sentimiento, a quién convenció, cuál es la GANADORA y por qué. Citá los números del análisis.)

## ⚠️ Riesgos de narrativa / PR
(qué argumentos o reacciones representan un riesgo si esto fuera real)

## ✅ Recomendación
(1-2 acciones concretas, fundadas en la intervención ganadora del análisis contrafáctico)
"""


# ---------------------------------------------------------------------------
# Parsers de JSON (tolerantes a la verborragia del LLM)
# ---------------------------------------------------------------------------

def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def parse_json_array(response_text: str) -> List[dict]:
    """Extrae un array JSON de la respuesta del LLM (para las personas)."""
    cleaned = _strip_code_fences(response_text)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        # Fallback: agarrar el primer bloque [...] que encontremos
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return []


def parse_json_object(response_text: str) -> dict:
    """Extrae un objeto JSON de la respuesta del LLM (para una reacción)."""
    cleaned = _strip_code_fences(response_text)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {}


def clamp(value, low: float = -1.0, high: float = 1.0) -> float:
    """Acota un valor numérico al rango [low, high]; devuelve 0.0 si no es numérico."""
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return 0.0
