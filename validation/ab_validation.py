"""
VALIDEZ EXTERNA — ¿la audiencia sintética predice el comportamiento REAL?

Usa el Upworthy Research Archive (32.487 experimentos A/B reales de titulares con clicks
medidos). Para cada par de titulares, una audiencia sintética de lectores elige —a ciegas—
en cuál haría click, y comparamos el ganador predicho contra el ganador REAL (mayor CTR).

Esto valida la afirmación central del producto: "de estos mensajes, este funciona mejor",
contra comportamiento humano real (no opiniones autodeclaradas).

Baseline a batir: 50% (elegir al azar entre 2). Si la audiencia sintética acierta bien por
encima de 50%, hay evidencia de validez externa.

Dataset (no se versiona): validation/data/upworthy_exploratory.csv
  Descargar: curl -sL https://osf.io/download/3vqmp/ -o validation/data/upworthy_exploratory.csv

Correr:  uv run python validation/ab_validation.py
"""
import collections
import csv
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage

from src.simulation import make_llm
from src.utils import parse_json_array

DATA = Path(__file__).resolve().parent / "data" / "upworthy_exploratory.csv"
N_PAIRS = 20          # pares A/B a evaluar
PANEL_SIZE = 5        # lectores sintéticos
MIN_IMPRESSIONS = 1000
MIN_GAP = 1.20        # el ganador real debe tener CTR ≥ 1.20× el perdedor (ganador claro)
SEED = 7


def load_pairs():
    """Pares A/B limpios: 2 titulares distintos, impresiones suficientes, ganador claro."""
    pkg = collections.defaultdict(dict)
    for r in csv.DictReader(open(DATA, encoding="utf-8")):
        try:
            imp, clk = int(r["impressions"]), int(r["clicks"])
        except (ValueError, KeyError):
            continue
        h = r["headline"].strip()
        if not h:
            continue
        d = pkg[r["clickability_test_id"]].setdefault(h, [0, 0])
        d[0] += imp; d[1] += clk

    pairs = []
    for tid in sorted(pkg):  # orden determinista
        hs = pkg[tid]
        if len(hs) < 2:
            continue
        (h1, (i1, c1)), (h2, (i2, c2)) = sorted(hs.items(), key=lambda kv: kv[1][0], reverse=True)[:2]
        if min(i1, i2) < MIN_IMPRESSIONS:
            continue
        ctr1, ctr2 = c1 / i1, c2 / i2
        hi, lo = max(ctr1, ctr2), min(ctr1, ctr2)
        if lo <= 0 or hi / lo < MIN_GAP:
            continue
        pairs.append({
            "winner": h1 if ctr1 > ctr2 else h2,
            "loser": h2 if ctr1 > ctr2 else h1,
            "gap": hi / lo,
            "ctr_win": round(hi, 4), "ctr_lose": round(lo, 4),
        })
    return pairs


def build_panel():
    """Genera una audiencia sintética de lectores diversos (una sola vez)."""
    prompt = (
        f"Generá {PANEL_SIZE} lectores diversos de noticias/contenido viral en redes "
        f"(distinta edad, intereses, nivel de cinismo ante el clickbait). "
        f'Devolvé SOLO un array JSON: [{{"name":"...","perfil":"1 frase de intereses y estilo"}}]'
    )
    resp = make_llm(0.9).invoke([HumanMessage(content=prompt)])
    panel = [p for p in parse_json_array(resp.content) if p.get("name")]
    return panel[:PANEL_SIZE]


def vote(persona, headline_A, headline_B):
    """Un lector elige A o B (forced choice, sin explicación)."""
    sys_p = f"Sos {persona.get('name')}: {persona.get('perfil','')}. Reaccionás como esta persona real."
    user_p = (
        "Estos dos titulares aparecen en tu feed. ¿En CUÁL harías click? "
        "Respondé SOLO con la letra A o B, nada más.\n\n"
        f"A) {headline_A}\nB) {headline_B}"
    )
    try:
        resp = make_llm(0.3).invoke([SystemMessage(content=sys_p), HumanMessage(content=user_p)])
        m = re.search(r"\b([AB])\b", resp.content.strip().upper())
        return m.group(1) if m else None
    except Exception:
        return None


def main():
    if not DATA.exists():
        print(f"Falta el dataset: {DATA}\nDescargalo con:\n  curl -sL https://osf.io/download/3vqmp/ -o {DATA}")
        return

    random.seed(SEED)
    pairs = load_pairs()
    print(f"Pares A/B limpios disponibles: {len(pairs)}  ·  evaluando {N_PAIRS} (seed {SEED})")
    sample = random.sample(pairs, min(N_PAIRS, len(pairs)))

    panel = build_panel()
    print(f"Audiencia sintética: {', '.join(p['name'] for p in panel)}\n")

    correct = ties = 0
    clear, clear_correct = 0, 0
    for k, pair in enumerate(sample, 1):
        # randomizar qué titular real es 'A' para evitar sesgo de posición
        flip = random.random() < 0.5
        A, B = (pair["winner"], pair["loser"]) if not flip else (pair["loser"], pair["winner"])
        votes = collections.Counter()
        for persona in panel:
            v = vote(persona, A, B)
            if v:
                votes[v] += 1
        if votes["A"] == votes["B"]:
            ties += 1
            verdict = "empate"
        else:
            pick = "A" if votes["A"] > votes["B"] else "B"
            picked_headline = A if pick == "A" else B
            hit = picked_headline == pair["winner"]
            correct += int(hit)
            verdict = "✅ acierta" if hit else "❌ falla"
            if pair["gap"] >= 1.5:
                clear += 1; clear_correct += int(hit)
        print(f"[{k:>2}/{len(sample)}] gap {pair['gap']:.2f}x · votos A={votes['A']} B={votes['B']} → {verdict}")

    decided = len(sample) - ties
    acc = correct / decided if decided else 0
    print("\n" + "=" * 60)
    print(f"Aciertos: {correct}/{decided} decididos = {acc*100:.0f}%  (empates: {ties})  ·  baseline azar: 50%")
    if clear:
        print(f"En pares con ganador MUY claro (gap≥1.5x): {clear_correct}/{clear} = {clear_correct/clear*100:.0f}%")
    lift = (acc - 0.5) * 100
    print(f"\nVEREDICTO: {'✅ predice el comportamiento real por encima del azar (+%.0f pts)' % lift if acc>0.5 else '⚠️ no supera el azar'}")
    print("(Validez externa sobre clicks REALES del Upworthy Research Archive.)")


if __name__ == "__main__":
    main()
