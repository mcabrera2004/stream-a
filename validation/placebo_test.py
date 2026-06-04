"""
TEST DE PLACEBO — ¿la recomendación es significativa o cualquier anuncio "sube" el sentimiento?

Comparamos, sobre el mismo baseline:
  - una intervención REAL (ataca la objeción detectada)
  - un PLACEBO (anuncio irrelevante al tema)

Criterio de éxito (PASS):
  - la REAL mueve la aguja claramente (Δ alto y positivo)
  - el PLACEBO casi no mueve nada (|Δ| pequeño) y pierde contra la real

Si el placebo "ganara" o moviera tanto como la real, la recomendación sería ruido.

Correr:  uv run python validation/placebo_test.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config

config.MAX_ROUNDS = 2  # corridas más cortas/baratas; la convergencia suele caer en R2

from validation._harness import prepare, primed, run

TOPIC = "¿Deberían las redes sociales verificar la edad de los usuarios con documento?"
REAL = ("Verificación privada (ZKP)",
        "Implementaremos la verificación de edad con prueba de conocimiento cero: tu documento "
        "nunca se almacena ni se centraliza, y un comité independiente audita el sistema.")
PLACEBO = ("Placebo: rediseño de marca",
           "Renovaremos el logo de la app a un tono azul y actualizaremos la tipografía para "
           "una experiencia más moderna.")

THRESH_PLACEBO = 0.10   # |Δ| del placebo debe ser menor a esto
MARGIN = 0.10           # la real debe superar al placebo por al menos esto


def main():
    print("=" * 70)
    print("TEST DE PLACEBO")
    print("=" * 70)
    personas, ctx = prepare(TOPIC)
    base = run(TOPIC, personas, ctx)
    pr = primed(personas, base["finals"])

    real = run(TOPIC, pr, ctx, REAL[1])
    plac = run(TOPIC, pr, ctx, PLACEBO[1])

    d_real = round(real["avg"] - base["avg"], 3)
    d_plac = round(plac["avg"] - base["avg"], 3)

    print(f"\nStatus quo (baseline):        sentimiento {base['avg']:+.2f}")
    print(f"REAL    ({REAL[0]}):  {real['avg']:+.2f}   Δ {d_real:+.2f}")
    print(f"PLACEBO ({PLACEBO[0]}): {plac['avg']:+.2f}   Δ {d_plac:+.2f}")

    real_moves = d_real > MARGIN
    placebo_flat = abs(d_plac) < THRESH_PLACEBO
    real_wins = d_real - d_plac > MARGIN
    passed = real_moves and placebo_flat and real_wins

    print("\nChequeos:")
    print(f"  [{'OK' if real_moves else 'X'}] la intervención REAL mueve la aguja (Δ {d_real:+.2f} > {MARGIN})")
    print(f"  [{'OK' if placebo_flat else 'X'}] el PLACEBO casi no mueve (|Δ| {abs(d_plac):.2f} < {THRESH_PLACEBO})")
    print(f"  [{'OK' if real_wins else 'X'}] la REAL le gana al PLACEBO por > {MARGIN}")
    print(f"\nVEREDICTO: {'✅ PASS — la recomendación es significativa, no ruido.' if passed else '⚠️ REVISAR'}")


if __name__ == "__main__":
    main()
