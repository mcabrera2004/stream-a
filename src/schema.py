"""
Estados del grafo y modelos de datos del ÁGORA.

Hay dos estados:
  - SimState:   estado del SUBGRAFO de simulación (una corrida del enjambre).
  - AgentState: estado del GRAFO PADRE que orquesta baseline + contrafácticos.

El "diálogo" entre agentes vive en `feed`: cada Persona lee el feed acumulado y
agrega su reacción, de modo que las personas se responden entre sí.
"""
from __future__ import annotations

import operator
from typing import Annotated, List, Optional, TypedDict

from pydantic import BaseModel, Field


class Persona(BaseModel):
    """Un agente individual de la simulación, con voz y opinión propia."""

    name: str = Field(description="Nombre de la persona.")
    archetype: str = Field(description="Arquetipo, p.ej. 'escéptico tecnológico', 'early adopter'.")
    profession: str = Field(description="Profesión/ocupación; da textura demográfica.")
    backstory: str = Field(description="1-2 frases que dan contexto y voz a la persona.")
    stance: float = Field(description="Opinión actual sobre el tema, de -1 (en contra) a +1 (a favor).")
    volatility: float = Field(description="0-1: qué tan fácil cambia de opinión ante el feed.")
    influence: float = Field(default=1.0, description="Peso de influencia (0.5-2+): cuánto pesa su voz en la opinión colectiva.")
    activity: float = Field(default=0.8, description="0-1: probabilidad de postear en una ronda dada.")


class Post(BaseModel):
    """Una reacción posteada en el feed compartido. Es la unidad del diálogo."""

    author: str = Field(description="Nombre de la persona que postea.")
    archetype: str = Field(default="", description="Arquetipo del autor (para la UI).")
    round: int = Field(description="Número de ronda en que se posteó.")
    text: str = Field(description="El texto de la reacción.")
    sentiment: float = Field(description="Sentimiento del post hacia el tema, de -1 a +1.")


# ---------------------------------------------------------------------------
# Estado del SUBGRAFO de simulación (una corrida del enjambre)
# ---------------------------------------------------------------------------
class SimState(TypedDict):
    topic: str
    source_context: List[dict]
    personas: List[Persona]
    intervention: Optional[str]                 # anuncio/mensaje inyectado (None = baseline)
    feed: Annotated[List[Post], operator.add]   # el diálogo, se acumula por ronda
    round: int
    sentiment_history: Annotated[List[float], operator.add]
    converged: bool


# ---------------------------------------------------------------------------
# Estado del GRAFO PADRE (orquesta baseline + contrafácticos)
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    topic: str
    source_context: List[dict]
    personas: List[Persona]
    baseline: dict          # {feed, sentiment_history, converged, analytics}
    interventions: List[dict]   # propuestas del Estratega: [{name, text}]
    counterfactuals: List[dict] # resultados por intervención: [{name, text, feed, ..., analytics}]
    comparison: dict        # baseline vs intervenciones + ganadora
    report: str             # reporte final
