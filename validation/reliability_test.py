"""
TEST-RETEST (RELIABILITY) — ¿el sistema es estable o cada corrida dice otra cosa?

Corre el MISMO tema N veces (personas frescas cada vez) con las MISMAS dos
intervenciones fijas, y mide:
  - varianza del sentimiento baseline (media ± desvío, rango)
  - estabilidad de la GANADORA (¿gana siempre la misma intervención?)

Producto confiable = baja varianza + ganadora estable. Si la ganadora cambia
cada corrida, la recomendación no es fiable.

Correr:  uv run python validation/reliability_test.py
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config

# Más liviano para poder repetir varias veces sin gastar de más.
config.NUM_PERSONAS = 5
config.MAX_ROUNDS = 2

from validation._harness import prepare, primed, run

TOPIC = "¿Deberían las redes sociales verificar la edad de los usuarios con documento?"
INTERVENTIONS = [
    ("A: Verificación privada (ZKP)",
     "Verificación con prueba de conocimiento cero: el documento no se almacena ni centraliza; auditoría independiente."),
    ("B: Gobernanza participativa",
     "Crearemos una mesa de gobernanza con sociedad civil y expertos para co-diseñar la implementación y un canal de apelación."),
]
N = 3


def main():
    print("=" * 70)
    print(f"TEST-RETEST · {N} corridas · tema fijo · 2 intervenciones fijas")
    print("=" * 70)
    base_avgs, winners = [], []
    for i in range(N):
        personas, ctx = prepare(TOPIC)
        base = run(TOPIC, personas, ctx)
        pr = primed(personas, base["finals"])
        opts = [(name, run(TOPIC, pr, ctx, text)["avg"]) for name, text in INTERVENTIONS]
        winner = max(opts, key=lambda o: o[1])[0]
        base_avgs.append(base["avg"])
        winners.append(winner)
        print(f"  corrida {i + 1}: baseline {base['avg']:+.2f} | "
              f"{' vs '.join(f'{n.split(chr(58))[0]}={a:+.2f}' for n, a in opts)} → gana {winner.split(':')[0]}")

    mean = statistics.mean(base_avgs)
    sd = statistics.pstdev(base_avgs)
    counts = {w: winners.count(w) for w in set(winners)}
    top, top_n = max(counts.items(), key=lambda kv: kv[1])

    print("\nResultados:")
    print(f"  Sentimiento baseline: media {mean:+.2f}  ±{sd:.2f}  (rango {min(base_avgs):+.2f}..{max(base_avgs):+.2f})")
    print(f"  Ganadora: {top.split(':')[0]} en {top_n}/{N} corridas  ({counts})")

    stable_winner = top_n == N
    low_var = sd < 0.15
    print("\nChequeos:")
    print(f"  [{'OK' if stable_winner else 'X'}] ganadora estable ({top_n}/{N})")
    print(f"  [{'OK' if low_var else 'X'}] baja varianza del baseline (±{sd:.2f} < 0.15)")
    print(f"\nVEREDICTO: {'✅ confiable' if stable_winner and low_var else '⚠️ variabilidad alta — interpretar con cuidado'}")


if __name__ == "__main__":
    main()
