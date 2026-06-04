"""
UI Streamlit del ÁGORA.

Muestra el flujo completo:
  1. el enjambre de personas,
  2. el feed baseline como hilo social + evolución del sentimiento,
  3. los analytics (facciones, influencia),
  4. el ANÁLISIS CONTRAFÁCTICO: qué intervención mueve mejor la aguja,
  5. el reporte predictivo final.
"""
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src import config
from src.agent import agent_app, initial_state
from src.metrics import LLMCounter

load_dotenv()  # local: lee el .env

# Streamlit Cloud: expone los secrets como variables de entorno, así el resto del
# código (os.getenv en los nodos) funciona igual en local y en la nube, sin cambios.
try:
    for _k, _v in st.secrets.items():
        os.environ.setdefault(_k, str(_v))
except Exception:
    pass

st.set_page_config(page_title="ÁGORA", layout="wide", page_icon="🏛️")

st.title("🏛️ ÁGORA")
st.caption("El ágora sintética — simulá la reacción pública y encontrá la palanca que la mueve.")
st.markdown(
    "Simulación multi-agente de **opinión pública** con **loop contrafáctico**. "
    "Un enjambre de ciudadanos sintéticos debate un tema (baseline); luego un agente "
    "Estratega propone intervenciones y se **re-simula** cada una para descubrir qué "
    "palanca mejora la recepción."
)

google_key = os.getenv("GOOGLE_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")

with st.sidebar:
    st.header("⚙️ Simulación")
    topic_input = st.text_area(
        "Tema a simular",
        "¿Deberían las ciudades prohibir los autos a combustión para 2030?",
        height=100,
    )
    st.caption(
        f"Personas: **{config.NUM_PERSONAS}** · Máx rondas: **{config.MAX_ROUNDS}** · "
        f"Umbral converg.: **{config.CONVERGENCE_THRESHOLD}** · "
        f"Intervenciones: **{config.NUM_INTERVENTIONS}**"
    )
    run = st.button("🚀 Correr simulación", use_container_width=True, type="primary")


def _chip(value: float) -> str:
    color = "#1b873f" if value > 0.15 else ("#cf222e" if value < -0.15 else "#9a6700")
    bg = "#e9f7ee" if value > 0.15 else ("#ffebe9" if value < -0.15 else "#fff8c5")
    return (f"<span style='background:{bg};color:{color};padding:2px 8px;"
            f"border-radius:10px;font-size:0.8em;font-weight:600;'>{value:+.2f}</span>")


if run:
    if not google_key:
        st.error("Falta `GOOGLE_API_KEY` en el archivo `.env` (obligatoria).")
        st.stop()
    if not tavily_key:
        st.warning("Falta `TAVILY_API_KEY`: la simulación corre sin contexto externo de Tavily.")

    final_state = initial_state(topic_input)
    counter = LLMCounter()
    status = st.status("Arrancando el enjambre…", expanded=True)
    try:
        for chunk in agent_app.stream(initial_state(topic_input), config={"callbacks": [counter]}):
            for node_name, updates in chunk.items():
                final_state.update(updates)
                msg = {
                    "ingest": "🌐 Contexto recuperado.",
                    "persona_factory": f"🌱 {len(updates.get('personas', []))} personas generadas.",
                    "baseline": "🎬 Simulación baseline completa.",
                    "strategist": f"🧠 {len(updates.get('interventions', []))} intervenciones propuestas.",
                    "counterfactual": f"🔮 {len(updates.get('counterfactuals', []))} contrafácticos re-simulados.",
                    "compare": f"⚖️ Ganadora: {updates.get('comparison', {}).get('winner', '—')}",
                    "report": "📝 Reporte generado.",
                }.get(node_name)
                if msg:
                    status.write(msg)
        status.update(label="Simulación completa ✅", state="complete", expanded=False)
    except Exception as exc:
        status.update(label="Error", state="error")
        st.error(f"Error ejecutando la simulación: {exc}")
        st.stop()

    personas = final_state.get("personas", [])
    baseline = final_state.get("baseline", {})

    # --- Enjambre ---
    st.subheader("👥 El enjambre")
    cols = st.columns(min(3, max(1, len(personas))))
    for i, p in enumerate(personas):
        with cols[i % len(cols)]:
            st.markdown(
                f"**{p.name}** {_chip(p.stance)}<br>"
                f"<small>_{p.archetype} · {p.profession}_<br>"
                f"⭐ influencia {p.influence} · 🔥 volatilidad {p.volatility}<br>{p.backstory}</small>",
                unsafe_allow_html=True,
            )

    # --- Feed baseline ---
    st.subheader("💬 Feed baseline (status quo)")
    current = 0
    for post in baseline.get("feed", []):
        if post.round != current:
            current = post.round
            st.markdown(f"**— Ronda {current} —**")
        st.markdown(f"{_chip(post.sentiment)} **{post.author}** "
                    f"<small>_({post.archetype})_</small><br>{post.text}", unsafe_allow_html=True)
        st.markdown("")

    # --- Evolución del sentimiento ---
    history = baseline.get("sentiment_history", [])
    if history:
        st.subheader("📈 Evolución del sentimiento (baseline)")
        df = pd.DataFrame({"Sentimiento": history},
                          index=[f"Ronda {i + 1}" for i in range(len(history))])
        st.line_chart(df, y="Sentimiento")
        st.caption("✅ Convergió." if baseline.get("converged") else "⏱️ Corte por tope de rondas.")

    # --- Analytics ---
    a = baseline.get("analytics") or {}
    if a:
        st.subheader("📊 Analytics del baseline")
        s = a["stats"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Opinión inicial → final", f"{s['avg_final']:+.2f}", f"{s['swing']:+.2f} swing")
        c2.metric("Polarización", f"{s['polarizacion']:.2f}", help="Alta = panel dividido.")
        c3.metric("Convergió", "Sí ✅" if baseline.get("converged") else "No ⏱️")
        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown("**⚔️ Facciones finales**")
            f = a["factions"]
            st.markdown(
                f"- 🟢 A favor: {', '.join(n for n, _ in f['a_favor']) or '—'}\n"
                f"- 🔴 En contra: {', '.join(n for n, _ in f['en_contra']) or '—'}\n"
                f"- 🟡 Neutrales: {', '.join(n for n, _ in f['neutral']) or '—'}")
        with fc2:
            st.markdown("**🎯 Ranking de influencia**")
            st.dataframe(pd.DataFrame(a["influence"])[
                ["name", "posts", "mentions_received", "influence", "score"]],
                hide_index=True, use_container_width=True)

    # --- Análisis contrafáctico ---
    cmp = final_state.get("comparison") or {}
    if cmp:
        st.subheader("🧪 Análisis contrafáctico — ¿qué palanca funciona?")
        st.success(f"🏆 **Ganadora:** {cmp['winner']}")
        base_avg = cmp["baseline"]["avg_final"]
        rows = [{"Intervención": "— status quo —", "Sentimiento": base_avg, "Δ vs status quo": 0.0,
                 "Convenció a": ""}]
        for o in cmp["options"]:
            rows.append({
                "Intervención": o["name"],
                "Sentimiento": o["avg_final"],
                "Δ vs status quo": o["delta"],
                "Convenció a": ", ".join(o["won_over"]),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        for o in cmp["options"]:
            st.markdown(f"- **{o['name']}** (Δ{o['delta']:+.2f}): _{o['text']}_")

    # --- Reporte ---
    st.subheader("🔮 Reporte predictivo")
    st.markdown(final_state.get("report", "_(sin reporte)_"))

    st.caption(
        f"📊 Observabilidad: **{counter.calls}** llamadas a Gemini en toda la corrida "
        f"(baseline + {len(final_state.get('counterfactuals', []))} contrafácticos)."
    )

    # --- Fuentes ---
    sources = final_state.get("source_context", [])
    if sources:
        with st.expander(f"🌐 Fuentes externas usadas ({len(sources)})"):
            for src in sources:
                if isinstance(src, dict):
                    st.markdown(f"- [{src.get('title', src.get('url', 'fuente'))}]({src.get('url', '#')})")
