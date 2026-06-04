"""
Punto de entrada por línea de comandos del ÁGORA.

Uso:
    uv run python main.py "¿Debería prohibirse el uso de celulares en las escuelas?"

Corre el grafo completo (ingest → personas → baseline → estratega → contrafácticos →
comparación → reporte) e imprime el feed, las métricas, el análisis contrafáctico y el
reporte. Toda la traza del intercambio entre agentes se ve en consola.
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from src.agent import agent_app, initial_state
from src.analytics import format_analytics, format_comparison
from src.metrics import LLMCounter
from src.utils import sentiment_bar

DEFAULT_TOPIC = "¿Deberían las ciudades prohibir los autos a combustión para 2030?"


def main() -> None:
    load_dotenv()

    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: falta GOOGLE_API_KEY en el .env (es obligatoria).")
        sys.exit(1)
    if not os.getenv("TAVILY_API_KEY"):
        print("Aviso: falta TAVILY_API_KEY; la simulación corre sin contexto externo.\n")

    topic = " ".join(sys.argv[1:]).strip() or DEFAULT_TOPIC

    print("=" * 78)
    print(f"🏛️  ÁGORA  ·  tema: {topic}")
    print("=" * 78, "\n")

    counter = LLMCounter()
    final = agent_app.invoke(initial_state(topic), config={"callbacks": [counter]})
    baseline = final.get("baseline", {})

    print("\n" + "=" * 78)
    print("FEED BASELINE (el diálogo entre agentes, sin intervención)")
    print("=" * 78)
    current_round = 0
    for post in baseline.get("feed", []):
        if post.round != current_round:
            current_round = post.round
            print(f"\n--- Ronda {current_round} ---")
        print(f"  {sentiment_bar(post.sentiment)} {post.author} ({post.archetype}): {post.text}")

    print("\n" + "=" * 78)
    print("ANALYTICS DEL BASELINE")
    print("=" * 78)
    if baseline.get("analytics"):
        print(format_analytics(baseline["analytics"]))

    print("\n" + "=" * 78)
    print("ANÁLISIS CONTRAFÁCTICO (qué palanca mueve la aguja)")
    print("=" * 78)
    if final.get("comparison"):
        print(format_comparison(final["comparison"]))
    else:
        print("(no se corrieron contrafácticos)")

    print("\n" + "=" * 78)
    print("REPORTE PREDICTIVO")
    print("=" * 78)
    print(final.get("report", "(sin reporte)"))

    print("\n" + "-" * 78)
    print(f"📊 Observabilidad: {counter.calls} llamadas a Gemini en toda la corrida "
          f"(baseline + {len(final.get('counterfactuals', []))} contrafácticos).")


if __name__ == "__main__":
    main()
