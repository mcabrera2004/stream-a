"""
Grafo PADRE del ÁGORA (LangGraph).

Orquesta la simulación baseline y el loop contrafáctico de intervención:

    ingest → persona_factory → baseline → strategist → counterfactual → compare → report → END
                                  │            │             │             │
                            (subgrafo sim)  (propone   (re-corre subgrafo  (efecto causal,
                                            palancas)   por intervención)   ganadora)

DECISIONES del sistema:
  - Convergencia de la opinión: conditional edge DENTRO del subgrafo de simulación
    (src/simulation.py) → cuándo dejar de simular.
  - Palanca ganadora: el nodo `compare` elige qué intervención mueve mejor la aguja.

El subgrafo de simulación se invoca varias veces (baseline + 1 por intervención).
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.nodes import (
    baseline_node,
    compare_node,
    counterfactual_node,
    ingest_node,
    persona_factory_node,
    report_agent_node,
    strategist_node,
)
from src.schema import AgentState


def create_agent():
    g = StateGraph(AgentState)

    g.add_node("ingest", ingest_node)
    g.add_node("persona_factory", persona_factory_node)
    g.add_node("baseline", baseline_node)
    g.add_node("strategist", strategist_node)
    g.add_node("counterfactual", counterfactual_node)
    g.add_node("compare", compare_node)
    g.add_node("report", report_agent_node)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "persona_factory")
    g.add_edge("persona_factory", "baseline")
    g.add_edge("baseline", "strategist")
    g.add_edge("strategist", "counterfactual")
    g.add_edge("counterfactual", "compare")
    g.add_edge("compare", "report")
    g.add_edge("report", END)

    return g.compile()


agent_app = create_agent()


def initial_state(topic: str) -> dict:
    """Estado inicial limpio para arrancar una simulación."""
    return {
        "topic": topic,
        "source_context": [],
        "personas": [],
        "baseline": {},
        "interventions": [],
        "counterfactuals": [],
        "comparison": {},
        "report": "",
    }
