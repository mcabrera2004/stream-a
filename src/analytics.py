"""
Analítica de la simulación: pre-computar métricas cuantitativas y pasárselas
al report_agent como evidencia dura, en vez de darle solo el feed crudo.

Todo es Python puro (sin libs pesadas): facciones, ranking de influencia,
trayectoria de sentimiento por persona y polarización.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from typing import List

from src.schema import Persona, Post


def _name_tokens(name: str) -> List[str]:
    """Tokens 'mencionables' de un nombre (descarta títulos y palabras cortas)."""
    drop = {"dr", "dra", "lic", "ing", "sr", "sra", "prof", "profesor", "profesora"}
    return [t for t in name.replace(".", " ").replace(",", " ").split()
            if len(t) > 3 and t.lower() not in drop]


def final_stance_by_persona(personas: List[Persona], feed: List[Post]) -> dict:
    """Último sentimiento posteado por cada persona (o su stance inicial si nunca posteó)."""
    last: dict = {}
    for post in feed:
        last[post.author] = post.sentiment
    return {p.name: last.get(p.name, p.stance) for p in personas}


def compute_factions(personas: List[Persona], feed: List[Post]) -> dict:
    """Agrupa las personas por su postura final: a favor / en contra / neutral."""
    finals = final_stance_by_persona(personas, feed)
    factions = {"a_favor": [], "en_contra": [], "neutral": []}
    for name, s in finals.items():
        bucket = "a_favor" if s > 0.15 else ("en_contra" if s < -0.15 else "neutral")
        factions[bucket].append((name, round(s, 2)))
    return factions


def influence_ranking(personas: List[Persona], feed: List[Post]) -> List[dict]:
    """
    Rankea a quién movió la conversación. Score =
        influence * (menciones_recibidas + 0.5 * posts_propios)
    Las menciones se detectan buscando tokens del nombre en posts ajenos.
    """
    posts_by = defaultdict(int)
    mentions = defaultdict(int)
    persona_by_name = {p.name: p for p in personas}
    tokens = {p.name: _name_tokens(p.name) for p in personas}

    for post in feed:
        posts_by[post.author] += 1
        low = post.text.lower()
        for name, toks in tokens.items():
            if name == post.author:
                continue
            if any(t.lower() in low for t in toks):
                mentions[name] += 1

    ranking = []
    for p in personas:
        score = p.influence * (mentions[p.name] + 0.5 * posts_by[p.name])
        ranking.append({
            "name": p.name,
            "archetype": p.archetype,
            "posts": posts_by[p.name],
            "mentions_received": mentions[p.name],
            "influence": round(p.influence, 2),
            "score": round(score, 2),
        })
    return sorted(ranking, key=lambda r: r["score"], reverse=True)


def trajectory_by_persona(personas: List[Persona], feed: List[Post]) -> dict:
    """Sentimiento de cada persona ronda a ronda (None si no posteó esa ronda)."""
    max_round = max((p.round for p in feed), default=0)
    traj = {p.name: [None] * max_round for p in personas}
    for post in feed:
        if post.author in traj and 1 <= post.round <= max_round:
            traj[post.author][post.round - 1] = round(post.sentiment, 2)
    return traj


def overall_stats(personas: List[Persona], feed: List[Post], sentiment_history: List[float]) -> dict:
    """Estadísticas globales: arranque, cierre, swing y polarización."""
    finals = list(final_stance_by_persona(personas, feed).values())
    initials = [p.stance for p in personas]
    polarization = round(statistics.pstdev(finals), 3) if len(finals) > 1 else 0.0
    return {
        "sentiment_history": [round(s, 3) for s in sentiment_history],
        "avg_inicial": round(statistics.mean(initials), 3) if initials else 0.0,
        "avg_final": round(statistics.mean(finals), 3) if finals else 0.0,
        "swing": round((statistics.mean(finals) - statistics.mean(initials)), 3)
                 if finals and initials else 0.0,
        "polarizacion": polarization,  # alta = opiniones muy dispersas
    }


def weighted_avg(personas: List[Persona], feed: List[Post]) -> float:
    """Sentimiento final promedio ponderado por influencia (la voz del experto pesa más)."""
    finals = final_stance_by_persona(personas, feed)
    w = {p.name: p.influence for p in personas}
    num = sum(s * w.get(n, 1.0) for n, s in finals.items())
    den = sum(w.get(p.name, 1.0) for p in personas) or 1.0
    return round(num / den, 3)


def _polarization(personas: List[Persona], feed: List[Post]) -> float:
    finals = list(final_stance_by_persona(personas, feed).values())
    return round(statistics.pstdev(finals), 3) if len(finals) > 1 else 0.0


def compare_runs(personas: List[Persona], baseline: dict, options: List[dict],
                 min_lift: float = 0.05) -> dict:
    """
    Compara el baseline contra cada intervención re-simulada (análisis contrafáctico).
    `baseline` y cada `option` tienen al menos {feed}. Devuelve deltas y la ganadora.
    """
    base_feed = baseline.get("feed", [])
    base_avg = weighted_avg(personas, base_feed)
    base_finals = final_stance_by_persona(personas, base_feed)

    results = []
    for opt in options:
        opt_feed = opt.get("feed", [])
        opt_avg = weighted_avg(personas, opt_feed)
        opt_finals = final_stance_by_persona(personas, opt_feed)
        # personas que mejoraron su postura > 0.2 frente al baseline
        won_over = [n for n in opt_finals
                    if opt_finals[n] - base_finals.get(n, 0.0) > 0.2]
        results.append({
            "name": opt.get("name", "intervención"),
            "text": opt.get("text", ""),
            "avg_final": opt_avg,
            "delta": round(opt_avg - base_avg, 3),
            "polarizacion": _polarization(personas, opt_feed),
            "won_over": won_over,
        })

    ranked = sorted(results, key=lambda r: r["delta"], reverse=True)
    best = ranked[0] if ranked else None
    winner = best["name"] if best and best["delta"] >= min_lift else "status quo (ninguna mejora suficiente)"

    return {
        "baseline": {"avg_final": base_avg, "polarizacion": _polarization(personas, base_feed)},
        "options": ranked,
        "winner": winner,
    }


def format_comparison(cmp: dict) -> str:
    """Renderiza la comparación contrafáctica como texto para el prompt / CLI."""
    b = cmp["baseline"]
    lines = [
        f"STATUS QUO (sin intervención): sentimiento final {b['avg_final']:+.2f}, "
        f"polarización {b['polarizacion']:.2f}",
        "",
        "INTERVENCIONES RE-SIMULADAS (ordenadas por efecto):",
    ]
    for o in cmp["options"]:
        won = f" — convenció a: {', '.join(o['won_over'])}" if o["won_over"] else ""
        lines.append(
            f"- «{o['name']}»: sentimiento {o['avg_final']:+.2f} "
            f"(Δ {o['delta']:+.2f} vs status quo), polariz. {o['polarizacion']:.2f}{won}\n"
            f"    └ propuesta: {o['text']}"
        )
    lines.append(f"\n🏆 GANADORA: {cmp['winner']}")
    return "\n".join(lines)


def build_analytics(personas: List[Persona], feed: List[Post], sentiment_history: List[float]) -> dict:
    """Bundle de todas las métricas."""
    return {
        "stats": overall_stats(personas, feed, sentiment_history),
        "factions": compute_factions(personas, feed),
        "influence": influence_ranking(personas, feed),
        "trajectory": trajectory_by_persona(personas, feed),
    }


def format_analytics(a: dict) -> str:
    """Renderiza las métricas como texto para inyectar en el prompt del reporte."""
    s = a["stats"]
    lines = [
        "ESTADÍSTICAS GLOBALES:",
        f"- Sentimiento promedio por ronda: {' → '.join(f'R{i+1}={v:+.2f}' for i, v in enumerate(s['sentiment_history'])) or 'n/a'}",
        f"- Opinión inicial promedio: {s['avg_inicial']:+.2f}  →  final: {s['avg_final']:+.2f}  (swing: {s['swing']:+.2f})",
        f"- Polarización final (desviación): {s['polarizacion']:.2f}  (alta = panel dividido)",
        "",
        "FACCIONES FINALES:",
        f"- A favor: {a['factions']['a_favor'] or '—'}",
        f"- En contra: {a['factions']['en_contra'] or '—'}",
        f"- Neutrales: {a['factions']['neutral'] or '—'}",
        "",
        "RANKING DE INFLUENCIA (quién movió la conversación):",
    ]
    for r in a["influence"]:
        lines.append(
            f"- {r['name']} ({r['archetype']}): score {r['score']} "
            f"[{r['posts']} posts, {r['mentions_received']} menciones, peso {r['influence']}]"
        )
    return "\n".join(lines)
