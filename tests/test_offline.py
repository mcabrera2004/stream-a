"""
Test offline del grafo completo (sin API real).

Mockea Gemini y Tavily para validar la ORQUESTACIÓN de forma determinista:
estratificación por arquetipo, simulación baseline con convergencia, propuesta de
intervenciones, RE-SIMULACIÓN contrafáctica, comparación y elección de la ganadora.

Correr con:  uv run python tests/test_offline.py
"""
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["GOOGLE_API_KEY"] = "dummy"
os.environ["TAVILY_API_KEY"] = "dummy"

from src import config, nodes, simulation
from src.agent import agent_app, initial_state


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    """Respuestas canónicas según el tipo de prompt."""

    def invoke(self, messages):
        text = messages[0].content
        if "diseñador de simulaciones" in text:  # persona_factory
            people = ",".join(
                f'{{"name":"P{i}","profession":"prof{i}","backstory":"bio{i}","stance":0.0}}'
                for i in range(config.NUM_PERSONAS)
            )
            return _FakeResponse(f"[{people}]")
        if "estratega de comunicación" in text:  # strategist
            return _FakeResponse(
                '[{"name":"Palanca A","text":"Anuncio A"},'
                '{"name":"Palanca B","text":"Anuncio B"}]'
            )
        if "Escribí UN post" in text:  # reacción de persona
            # Con intervención (ANUNCIO NUEVO) el sentimiento mejora → efecto causal medible.
            sentiment = 0.6 if "ANUNCIO NUEVO" in text else 0.2
            return _FakeResponse(f'{{"text":"Mi postura.","sentiment":{sentiment}}}')
        if "analista de simulaciones" in text:  # report_agent
            return _FakeResponse("## 🔮 Outcome esperado (status quo)\nDividido pero mejorable.")
        return _FakeResponse("{}")


class _FakeTavily:
    def __init__(self, *a, **k):
        pass

    def invoke(self, *a, **k):
        # langchain-tavily devuelve {"results": [...]}
        return {"results": [{"title": "Fuente", "content": "contexto mock", "url": "http://x"}]}


def run():
    random.seed(42)
    # make_llm está importado en AMBOS módulos: hay que parchar los dos.
    simulation.make_llm = lambda temperature: _FakeLLM()
    nodes.make_llm = lambda temperature: _FakeLLM()
    nodes.TavilySearch = _FakeTavily

    final = agent_app.invoke(initial_state("Tema de prueba"))

    # --- Personas estratificadas ---
    assert len(final["personas"]) == config.NUM_PERSONAS, "una persona por arquetipo"
    assert {p.influence for p in final["personas"]} != {1.0}, "influencias deben variar"

    # --- Baseline: convergió en R2 (sentimiento fijo 0.2) ---
    base = final["baseline"]
    assert base["sentiment_history"] == [0.2, 0.2], base["sentiment_history"]
    assert base["converged"] is True
    assert {"factions", "influence"} <= set(base["analytics"])

    # --- Estratega propuso intervenciones ---
    assert len(final["interventions"]) == config.NUM_INTERVENTIONS

    # --- Contrafácticos re-simulados, uno por intervención ---
    assert len(final["counterfactuals"]) == config.NUM_INTERVENTIONS

    # --- Comparación: la intervención mejora (0.2 → 0.6) y elige ganadora ---
    cmp = final["comparison"]
    assert cmp["baseline"]["avg_final"] == 0.2, cmp["baseline"]
    best = cmp["options"][0]
    assert best["avg_final"] == 0.6 and best["delta"] == 0.4, best
    assert cmp["winner"] in ("Palanca A", "Palanca B"), cmp["winner"]
    assert best["won_over"], "la intervención debería convencer a alguien"

    assert "Outcome esperado" in final["report"]

    print("Orquestación validada (baseline + contrafáctico):")
    print(f"   personas={len(final['personas'])}  baseline={base['sentiment_history']}  "
          f"convergió={base['converged']}")
    print(f"   intervenciones={[i['name'] for i in final['interventions']]}")
    print(f"   status quo={cmp['baseline']['avg_final']:+.2f} → "
          f"ganadora '{cmp['winner']}' con Δ{best['delta']:+.2f}")
    print(f"   convenció a: {best['won_over']}")
    print("\nTODOS LOS ASSERTS PASARON")


if __name__ == "__main__":
    run()
