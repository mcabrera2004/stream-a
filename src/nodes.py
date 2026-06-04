"""
Nodos del GRAFO PADRE = los agentes de alto nivel del ÁGORA.

  ingest           -> contexto real del tema (Tavily)
  persona_factory  -> genera N personas estratificadas por arquetipo
  baseline         -> corre la simulación baseline (subgrafo) → status quo
  strategist       -> propone intervenciones que atacan la objeción principal
  counterfactual   -> RE-SIMULA el enjambre bajo cada intervención
  compare          -> mide el efecto causal de cada palanca → ganadora
  report           -> reporte predictivo + recomendación contrafáctica

La simulación en sí vive en el subgrafo `src/simulation.py`, que este grafo
invoca para el baseline y para cada contrafáctico.
"""
from __future__ import annotations

import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_tavily import TavilySearch

from src import config
from src.analytics import (
    build_analytics,
    compare_runs,
    final_stance_by_persona,
    format_analytics,
    format_comparison,
)
from src.schema import AgentState, Persona
from src.simulation import format_context, make_llm, run_simulation
from src.utils import (
    PERSONA_FACTORY_PROMPT,
    REPORT_AGENT_PROMPT,
    STRATEGIST_PROMPT,
    clamp,
    log,
    parse_json_array,
)


def _feed_txt(feed: list) -> str:
    return "\n".join(
        f"[R{p.round}] {p.author} ({p.archetype}) [{p.sentiment:+.2f}]: {p.text}" for p in feed
    )


# ---------------------------------------------------------------------------
# 1. ingest — herramienta externa (Tavily)
# ---------------------------------------------------------------------------

def ingest_node(state: AgentState) -> dict:
    """Trae contexto real del tema usando Tavily."""
    topic = state.get("topic", "")
    if not os.getenv("TAVILY_API_KEY"):
        log("⚠️", "ingest", "TAVILY_API_KEY ausente; el enjambre reaccionará solo al tema.")
        return {"source_context": []}

    search = TavilySearch(max_results=config.TAVILY_MAX_RESULTS, search_depth="advanced")
    try:
        resp = search.invoke({"query": topic})
        # langchain-tavily devuelve {"results": [{title, url, content, ...}]}
        results = resp.get("results", []) if isinstance(resp, dict) else (resp if isinstance(resp, list) else [])
    except Exception as exc:
        log("⚠️", "ingest", f"Tavily falló ({exc}); sigo sin contexto externo.")
        results = []

    log("🌐", "ingest", f"{len(results)} fuentes recuperadas sobre el tema.")
    return {"source_context": results}


# ---------------------------------------------------------------------------
# 2. persona_factory — genera el enjambre (estratificado por arquetipo)
# ---------------------------------------------------------------------------

def _assigned_archetypes() -> list[dict]:
    base = config.ARCHETYPES
    return [base[i % len(base)] for i in range(config.NUM_PERSONAS)]


def persona_factory_node(state: AgentState) -> dict:
    """Genera N personas, una por arquetipo pre-asignado (estratificación controlada)."""
    if not os.getenv("GOOGLE_API_KEY"):
        log("⚠️", "persona_factory", "GOOGLE_API_KEY ausente; no se pueden generar personas.")
        return {"personas": []}

    import random

    assigned = _assigned_archetypes()
    archetypes_txt = "\n".join(
        f"{i + 1}. {a['label']}  (stance objetivo entre {a['stance'][0]:+.1f} y {a['stance'][1]:+.1f})"
        for i, a in enumerate(assigned)
    )
    prompt = PERSONA_FACTORY_PROMPT.format(
        n=config.NUM_PERSONAS,
        topic=state.get("topic", ""),
        context=format_context(state.get("source_context", [])),
        archetypes=archetypes_txt,
    )
    response = make_llm(config.TEMP_FACTORY).invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="Generá ahora el panel de personas como array JSON."),
    ])

    raw_personas = parse_json_array(response.content)
    personas: list[Persona] = []
    for i, arch in enumerate(assigned):
        raw = raw_personas[i] if i < len(raw_personas) else {}
        lo, hi = arch["stance"]
        stance = clamp(raw.get("stance", (lo + hi) / 2), lo, hi)
        personas.append(Persona(
            name=str(raw.get("name") or f"Persona {i + 1}"),
            archetype=arch["label"],
            profession=str(raw.get("profession", "")),
            backstory=str(raw.get("backstory", "")),
            stance=round(stance, 2),
            volatility=round(random.uniform(*arch["volatility"]), 2),
            influence=arch["influence"],
            activity=arch["activity"],
        ))

    roster = " · ".join(f"{p.name}({p.stance:+.1f}/inf{p.influence})" for p in personas)
    log("🌱", "persona_factory", f"{len(personas)} personas generadas → {roster}")
    return {"personas": personas}


# ---------------------------------------------------------------------------
# 3. baseline — simulación del status quo (invoca el subgrafo)
# ---------------------------------------------------------------------------

def baseline_node(state: AgentState) -> dict:
    """Corre la simulación baseline: cómo reacciona el enjambre sin intervención."""
    personas = state.get("personas", [])
    log("🎬", "baseline", "simulación del status quo (sin intervención)")
    final = run_simulation(state.get("topic", ""), personas, state.get("source_context", []))
    analytics = build_analytics(personas, final.get("feed", []), final.get("sentiment_history", []))
    return {"baseline": {
        "feed": final.get("feed", []),
        "sentiment_history": final.get("sentiment_history", []),
        "converged": final.get("converged", False),
        "analytics": analytics,
    }}


# ---------------------------------------------------------------------------
# 4. strategist — propone intervenciones (palancas)
# ---------------------------------------------------------------------------

def strategist_node(state: AgentState) -> dict:
    """Lee el baseline y propone intervenciones que atacan la objeción principal."""
    if not config.ENABLE_COUNTERFACTUAL or not os.getenv("GOOGLE_API_KEY"):
        return {"interventions": []}

    baseline = state.get("baseline", {})
    prompt = STRATEGIST_PROMPT.format(
        k=config.NUM_INTERVENTIONS,
        topic=state.get("topic", ""),
        analytics=format_analytics(baseline.get("analytics", {})) if baseline.get("analytics") else "(sin métricas)",
        feed=_feed_txt(baseline.get("feed", [])),
    )
    response = make_llm(config.TEMP_FACTORY).invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="Proponé ahora las intervenciones como array JSON."),
    ])

    interventions = []
    for raw in parse_json_array(response.content)[: config.NUM_INTERVENTIONS]:
        if isinstance(raw, dict) and raw.get("text"):
            interventions.append({"name": str(raw.get("name", "intervención")), "text": str(raw["text"])})

    names = " | ".join(i["name"] for i in interventions) or "—"
    log("🧠", "strategist", f"{len(interventions)} intervenciones propuestas → {names}")
    return {"interventions": interventions}


# ---------------------------------------------------------------------------
# 5. counterfactual — re-simula bajo cada intervención
# ---------------------------------------------------------------------------

def counterfactual_node(state: AgentState) -> dict:
    """Para cada intervención, RE-SIMULA el enjambre partiendo de la opinión final del baseline."""
    interventions = state.get("interventions", [])
    if not interventions:
        return {"counterfactuals": []}

    personas = state.get("personas", [])
    baseline_feed = state.get("baseline", {}).get("feed", [])
    # Las personas arrancan el contrafáctico desde su postura FINAL del baseline.
    finals = final_stance_by_persona(personas, baseline_feed)
    primed = [p.model_copy(update={"stance": round(finals.get(p.name, p.stance), 2)}) for p in personas]

    results = []
    for interv in interventions:
        log("🔮", "counterfactual", f"re-simulando con: «{interv['name']}»")
        final = run_simulation(state.get("topic", ""), primed,
                               state.get("source_context", []), intervention=interv["text"])
        results.append({
            "name": interv["name"],
            "text": interv["text"],
            "feed": final.get("feed", []),
            "sentiment_history": final.get("sentiment_history", []),
        })
    return {"counterfactuals": results}


# ---------------------------------------------------------------------------
# 6. compare — efecto causal de cada palanca
# ---------------------------------------------------------------------------

def compare_node(state: AgentState) -> dict:
    """Compara baseline vs cada intervención re-simulada y elige la ganadora."""
    personas = state.get("personas", [])
    counterfactuals = state.get("counterfactuals", [])
    if not counterfactuals:
        return {"comparison": {}}

    cmp = compare_runs(personas, state.get("baseline", {}), counterfactuals,
                       min_lift=config.INTERVENTION_MIN_LIFT)
    log("⚖️", "compare", f"ganadora → {cmp['winner']}")
    return {"comparison": cmp}


# ---------------------------------------------------------------------------
# 7. report_agent — síntesis predictiva + recomendación contrafáctica
# ---------------------------------------------------------------------------

def report_agent_node(state: AgentState) -> dict:
    """Gemini sintetiza el reporte final (baseline + análisis contrafáctico)."""
    if not os.getenv("GOOGLE_API_KEY"):
        return {"report": "_(GOOGLE_API_KEY ausente: no se pudo generar el reporte.)_"}

    personas = state.get("personas", [])
    baseline = state.get("baseline", {})
    comparison = state.get("comparison", {})

    personas_txt = "\n".join(
        f"- {p.name} ({p.archetype}, {p.profession}) | stance inicial {p.stance:+.1f}, peso {p.influence}"
        for p in personas
    )
    analytics_txt = format_analytics(baseline["analytics"]) if baseline.get("analytics") else "(sin métricas)"
    comparison_txt = format_comparison(comparison) if comparison else "(no se corrieron contrafácticos)"

    prompt = REPORT_AGENT_PROMPT.format(
        topic=state.get("topic", ""),
        personas=personas_txt,
        analytics=analytics_txt,
        feed=_feed_txt(baseline.get("feed", [])),
        comparison=comparison_txt,
    )
    response = make_llm(config.TEMP_REPORT).invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="Generá ahora el reporte en Markdown con las secciones indicadas."),
    ])
    log("📝", "report_agent", "reporte final generado.")
    return {"report": response.content}
