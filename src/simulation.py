"""
Subgrafo de simulación del enjambre (reutilizable).

Es un grafo LangGraph independiente con su propio loop de convergencia:

    simulate → [¿convergió o max rondas?] → END
        ▲___________________│ no

El grafo PADRE (src/agent.py) invoca este subgrafo varias veces: una para el
baseline y otra por cada intervención contrafáctica (vía run_simulation()).
Cada invocación es un estado fresco e independiente.
"""
from __future__ import annotations

import os
import random

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from src import config
from src.schema import Persona, Post, SimState
from src.utils import (
    INTERVENTION_BLOCK,
    REACTION_PROMPT,
    clamp,
    log,
    parse_json_object,
    sentiment_bar,
)

# Import perezoso para evitar import circular con nodes.py
from langchain_google_genai import ChatGoogleGenerativeAI


def make_llm(temperature: float) -> ChatGoogleGenerativeAI:
    """Cliente Gemini con la temperatura indicada."""
    return ChatGoogleGenerativeAI(
        model=config.LLM_MODEL,
        temperature=temperature,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )


def format_context(source_context: list[dict], limit: int = 5) -> str:
    """Resume el contexto de Tavily a título + snippet para los prompts."""
    if not source_context:
        return "(sin contexto externo disponible)"
    lines = []
    for item in source_context[:limit]:
        if isinstance(item, dict):
            title = (item.get("title") or "").strip()
            content = (item.get("content") or "").strip()
            lines.append(f"- {title}: {content[:240]}")
    return "\n".join(lines) or "(sin contexto externo disponible)"


def _format_feed(feed: list[Post], limit: int = 12) -> str:
    """Renderiza el feed como diálogo para que las personas se lean entre sí."""
    if not feed:
        return "(el feed está vacío; sos de los primeros en opinar)"
    recent = feed[-limit:]
    return "\n".join(
        f"[R{p.round}] {p.author} ({p.archetype}): {p.text}" for p in recent
    )


def _select_active(personas: list[Persona], round_num: int) -> list[Persona]:
    """
    Participación no-uniforme: en la ronda 1 todos sientan postura; desde la ronda 2
    cada persona postea con probabilidad = su `activity` (con un piso de participantes).
    """
    if config.GUARANTEED_FIRST_ROUND and round_num == 1:
        return list(personas)
    active = [p for p in personas if random.random() < p.activity]
    if len(active) < config.MIN_POSTERS_PER_ROUND:
        extra = sorted((p for p in personas if p not in active),
                       key=lambda p: p.activity, reverse=True)
        active += extra[: config.MIN_POSTERS_PER_ROUND - len(active)]
        active = [p for p in personas if p in active]  # preservar orden
    return active


def simulation_round_node(state: SimState) -> dict:
    """Cada persona activa, en orden, lee el feed acumulado y postea su reacción."""
    personas = state.get("personas", [])
    new_round = state.get("round", 0) + 1
    history = state.get("sentiment_history", [])
    intervention = state.get("intervention")
    tag = "cf" if intervention else "base"

    if not personas:
        log("⚠️", f"{tag} r{new_round}", "no hay personas; corto la simulación.")
        return {"round": new_round, "sentiment_history": [0.0], "converged": True}

    topic = state.get("topic", "")
    context = format_context(state.get("source_context", []))
    intervention_block = INTERVENTION_BLOCK.format(intervention=intervention) if intervention else ""
    llm = make_llm(config.TEMP_REACTION)

    active = _select_active(personas, new_round)
    this_round: list[Post] = []
    running_view: list[Post] = list(state.get("feed", []))

    log("💬", f"{tag} r{new_round}", f"postean {len(active)}/{len(personas)} personas")
    for persona in active:
        prompt = REACTION_PROMPT.format(
            name=persona.name,
            profession=persona.profession,
            archetype=persona.archetype,
            backstory=persona.backstory,
            stance=persona.stance,
            volatility=persona.volatility,
            topic=topic,
            context=context,
            feed=_format_feed(running_view),
            intervention_block=intervention_block,
        )
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            data = parse_json_object(response.content)
            post = Post(
                author=persona.name,
                archetype=persona.archetype,
                round=new_round,
                text=str(data.get("text", "")).strip() or "(sin comentarios)",
                sentiment=clamp(data.get("sentiment", persona.stance)),
            )
        except Exception as exc:
            log("⚠️", f"{tag} r{new_round}", f"{persona.name} falló al postear: {exc}")
            post = Post(author=persona.name, archetype=persona.archetype,
                        round=new_round, text="(no pudo postear)", sentiment=persona.stance)
        this_round.append(post)
        running_view.append(post)
        log("  ↳", f"{tag} r{new_round}", f"{post.author} {sentiment_bar(post.sentiment)}: {post.text}")

    # Promedio del "humor" colectivo PONDERADO POR INFLUENCIA.
    weight = {p.name: p.influence for p in personas}
    num = sum(post.sentiment * weight.get(post.author, 1.0) for post in this_round)
    den = sum(weight.get(post.author, 1.0) for post in this_round) or 1.0
    avg = num / den

    prev = history[-1] if history else None
    converged = prev is not None and abs(avg - prev) < config.CONVERGENCE_THRESHOLD
    delta_txt = f"Δ={abs(avg - prev):.3f}" if prev is not None else "Δ=n/a (1ra ronda)"
    log("📊", f"{tag} r{new_round}", f"sentimiento ponderado {avg:+.2f} | {delta_txt}")

    return {
        "feed": this_round,
        "round": new_round,
        "sentiment_history": [round(avg, 4)],
        "converged": converged,
    }


def route_convergence(state: SimState) -> str:
    """Decide si seguir simulando o terminar la corrida (la DECISIÓN del subgrafo)."""
    if state.get("converged") or state.get("round", 0) >= config.MAX_ROUNDS:
        return "end"
    return "simulate"


def build_simulation_graph():
    g = StateGraph(SimState)
    g.add_node("simulate", simulation_round_node)
    g.set_entry_point("simulate")
    g.add_conditional_edges("simulate", route_convergence,
                            {"simulate": "simulate", "end": END})
    return g.compile()


# Subgrafo compilado una sola vez y reutilizado por el grafo padre.
sim_app = build_simulation_graph()


def run_simulation(topic: str, personas: list[Persona], source_context: list[dict],
                   intervention: str | None = None) -> dict:
    """Corre una simulación completa (todas las rondas hasta converger) y devuelve el estado final."""
    return sim_app.invoke({
        "topic": topic,
        "source_context": source_context,
        "personas": personas,
        "intervention": intervention,
        "feed": [],
        "round": 0,
        "sentiment_history": [],
        "converged": False,
    })
