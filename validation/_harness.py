"""
Helpers compartidos para los tests de validación de ÁGORA.

Reutilizan los nodos y el subgrafo del producto (no reimplementan nada): arman
el panel, corren simulaciones (con o sin intervención) y resumen métricas.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.analytics import _polarization, final_stance_by_persona, weighted_avg
from src.nodes import ingest_node, persona_factory_node
from src.simulation import run_simulation


def prepare(topic: str):
    """Corre ingest (Tavily) + persona_factory → (personas, contexto)."""
    ctx = ingest_node({"topic": topic}).get("source_context", [])
    personas = persona_factory_node({"topic": topic, "source_context": ctx}).get("personas", [])
    return personas, ctx


def run(topic: str, personas, ctx, intervention: str | None = None) -> dict:
    """Corre una simulación completa y devuelve métricas resumidas."""
    final = run_simulation(topic, personas, ctx, intervention)
    feed = final.get("feed", [])
    return {
        "avg": weighted_avg(personas, feed),          # sentimiento final ponderado por influencia
        "pol": _polarization(personas, feed),         # polarización (desviación de posturas finales)
        "finals": final_stance_by_persona(personas, feed),
    }


def primed(personas, baseline_finals):
    """Personas 'cargadas' con su postura final del baseline (para los contrafácticos)."""
    return [p.model_copy(update={"stance": round(baseline_finals.get(p.name, p.stance), 2)})
            for p in personas]
