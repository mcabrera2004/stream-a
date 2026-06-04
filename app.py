"""
UI Streamlit de ÁGORA — sandbox de decisiones de product marketing.

Flujo: el usuario plantea una decisión (cambio de precio, free→paid, nueva feature…);
ÁGORA simula la reacción de una audiencia sintética, propone mensajes (palancas) y
re-simula cada uno para recomendar el que mejor mueve la aguja.
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

st.set_page_config(page_title="ÁGORA", layout="wide", page_icon="🏛️",
                   initial_sidebar_state="expanded")

# --- Estilo (paleta navy + ámbar de la marca) ---
st.markdown("""
<style>
:root { --navy:#0f2747; --amber:#e0a106; }
.block-container { padding-top: 2.2rem; max-width: 1200px; }
h1, h2, h3 { color: #0f2747; }
.agora-hero { background: linear-gradient(135deg,#0f2747,#1f3a63); color:#fff;
  padding: 1.4rem 1.6rem; border-radius: 14px; margin-bottom: 1rem; }
.agora-hero h1 { color:#fff; margin:0; font-size:2.1rem; }
.agora-hero .tag { color:#e0a106; font-weight:600; margin-top:.2rem; }
.agora-hero .sub { color:#cdd6e2; font-size:.95rem; margin-top:.5rem; }
.persona-card { border:1px solid #e6e9ef; border-left:4px solid #1f3a63;
  border-radius:10px; padding:.7rem .9rem; height:100%; background:#fff; }
.winner-box { background:#fff8e6; border:1px solid #e0a106; border-radius:12px;
  padding:1rem 1.2rem; }
div[data-testid="stMetricValue"] { color:#0f2747; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="agora-hero">
  <h1>🏛️ ÁGORA</h1>
  <div class="tag">Simulá la reacción del público y encontrá el mensaje que la mueve.</div>
  <div class="sub">Sandbox de decisiones de <b>product marketing</b>: testeá un cambio de precio,
  un free→paid o una nueva feature contra una audiencia sintética — y descubrí qué palanca
  reduce la fricción, antes de gastar en la campaña real.</div>
</div>
""", unsafe_allow_html=True)

google_key = os.getenv("GOOGLE_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")

EXAMPLES = [
    "¿Deberíamos pasar nuestra app de gratis a una suscripción mensual?",
    "¿Conviene subir el precio del plan Pro un 30%?",
    "¿Eliminamos el plan gratuito y dejamos solo una prueba de 14 días?",
    "¿Lanzamos anuncios (ads) en la versión gratuita?",
    "¿Migramos a todos los usuarios a una interfaz rediseñada?",
]

# --- Sidebar: escenario + controles ---
with st.sidebar:
    st.header("🎯 Decisión a testear")

    if "topic" not in st.session_state:
        st.session_state.topic = EXAMPLES[0]

    def _set_example():
        st.session_state.topic = st.session_state.example_pick

    st.selectbox("Ejemplos (product marketing)", EXAMPLES,
                 key="example_pick", on_change=_set_example)
    topic_input = st.text_area("Tema / decisión", key="topic", height=90)

    with st.expander("⚙️ Parámetros de simulación"):
        num_personas = st.slider("Tamaño de la audiencia", 4, 8, config.NUM_PERSONAS)
        max_rounds = st.slider("Máx. rondas de debate", 2, 4, config.MAX_ROUNDS)
        num_interv = st.slider("Mensajes a testear (A/B)", 1, 3, config.NUM_INTERVENTIONS)
        st.caption("Más audiencia/rondas/mensajes = más realista, pero más lento y caro.")

    run = st.button("🚀 Simular", use_container_width=True, type="primary")

    st.divider()
    st.caption(
        ("🟢 Gemini OK" if google_key else "🔴 Falta GOOGLE_API_KEY") + "  ·  " +
        ("🟢 Tavily OK" if tavily_key else "🟡 Sin Tavily (corre igual)")
    )


def _chip(value: float) -> str:
    color = "#1b873f" if value > 0.15 else ("#cf222e" if value < -0.15 else "#9a6700")
    bg = "#e9f7ee" if value > 0.15 else ("#ffebe9" if value < -0.15 else "#fff8c5")
    return (f"<span style='background:{bg};color:{color};padding:2px 8px;"
            f"border-radius:10px;font-size:0.8em;font-weight:600;'>{value:+.2f}</span>")


def _avatar(value: float) -> str:
    return "🟢" if value > 0.15 else ("🔴" if value < -0.15 else "🟡")


if not run:
    st.info("👈 Elegí un escenario (o escribí el tuyo) y tocá **Simular**. "
            "Tip: funciona mejor con decisiones que generan opiniones encontradas.")
    st.stop()

if not google_key:
    st.error("Falta `GOOGLE_API_KEY` (en `.env` local o en *Secrets* de Streamlit Cloud).")
    st.stop()
if not tavily_key:
    st.warning("Sin `TAVILY_API_KEY`: la simulación corre sin contexto externo de Tavily.")

# Aplicar parámetros elegidos.
config.NUM_PERSONAS = num_personas
config.MAX_ROUNDS = max_rounds
config.NUM_INTERVENTIONS = num_interv

final_state = initial_state(topic_input)
counter = LLMCounter()
status = st.status("Arrancando la audiencia sintética…", expanded=True)
try:
    for chunk in agent_app.stream(initial_state(topic_input), config={"callbacks": [counter]}):
        for node_name, updates in chunk.items():
            final_state.update(updates)
            msg = {
                "ingest": "🌐 Contexto recuperado de la web (Tavily).",
                "persona_factory": f"🌱 {len(updates.get('personas', []))} personas generadas.",
                "baseline": "🎬 Debate baseline (status quo) completo.",
                "strategist": f"🧠 {len(updates.get('interventions', []))} mensajes propuestos.",
                "counterfactual": f"🔮 {len(updates.get('counterfactuals', []))} re-simulaciones.",
                "compare": f"⚖️ Mejor palanca: {updates.get('comparison', {}).get('winner', '—')}",
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
analytics = baseline.get("analytics") or {}
cmp = final_state.get("comparison") or {}

tab_res, tab_aud, tab_feed, tab_metrics, tab_report = st.tabs(
    ["🎯 Resultado", "👥 Audiencia", "💬 Debate", "📊 Métricas", "🔮 Reporte"]
)

# ============================== RESULTADO (la respuesta de negocio) ==============
with tab_res:
    if cmp:
        st.markdown(
            f"<div class='winner-box'><h3 style='margin-top:0'>🏆 Mensaje recomendado: "
            f"{cmp['winner']}</h3>", unsafe_allow_html=True)
        base_avg = cmp["baseline"]["avg_final"]
        best = cmp["options"][0] if cmp.get("options") else None
        c1, c2, c3 = st.columns(3)
        c1.metric("Status quo (no hacer nada)", f"{base_avg:+.2f}")
        if best:
            c2.metric("Con el mejor mensaje", f"{best['avg_final']:+.2f}", f"{best['delta']:+.2f}")
            c3.metric("Usuarios recuperados", len(best.get("won_over", [])))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("#### Comparación de mensajes (A/B simulado)")
        rows = [{"Mensaje": "— status quo —", "Sentimiento": round(base_avg, 2),
                 "Δ vs status quo": 0.0, "Recupera a": ""}]
        for o in cmp["options"]:
            rows.append({"Mensaje": o["name"], "Sentimiento": round(o["avg_final"], 2),
                         "Δ vs status quo": round(o["delta"], 2),
                         "Recupera a": ", ".join(o["won_over"])})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        st.markdown("#### Qué decía cada mensaje")
        for o in cmp["options"]:
            st.markdown(f"**{o['name']}** (Δ{o['delta']:+.2f}) — _{o['text']}_")
    else:
        st.info("No se generaron contrafácticos (revisá la config o las API keys).")

    st.caption(f"📊 Observabilidad: **{counter.calls}** llamadas a Gemini en toda la corrida.")

# ============================== AUDIENCIA ========================================
with tab_aud:
    st.caption("Audiencia sintética estratificada por arquetipo (perfiles diversos a propósito).")
    cols = st.columns(min(3, max(1, len(personas))))
    for i, p in enumerate(personas):
        with cols[i % len(cols)]:
            st.markdown(
                f"<div class='persona-card'><b>{p.name}</b> {_chip(p.stance)}<br>"
                f"<small><i>{p.archetype} · {p.profession}</i><br>"
                f"⭐ influencia {p.influence} · 🔥 volatilidad {p.volatility}<br>"
                f"{p.backstory}</small></div>",
                unsafe_allow_html=True,
            )
            st.markdown("")

# ============================== DEBATE (feed como chat) ==========================
with tab_feed:
    st.caption("El diálogo emergente: cada persona lee el feed y responde (status quo, sin intervención).")
    current = 0
    for post in baseline.get("feed", []):
        if post.round != current:
            current = post.round
            st.markdown(f"**— Ronda {current} —**")
        with st.chat_message(post.author, avatar=_avatar(post.sentiment)):
            st.markdown(f"**{post.author}** · _{post.archetype}_ &nbsp; {_chip(post.sentiment)}",
                        unsafe_allow_html=True)
            st.markdown(post.text)

# ============================== MÉTRICAS ========================================
with tab_metrics:
    history = baseline.get("sentiment_history", [])
    if history:
        st.markdown("#### 📈 Evolución del sentimiento (baseline)")
        df = pd.DataFrame({"Sentimiento": history},
                          index=[f"Ronda {i + 1}" for i in range(len(history))])
        st.line_chart(df, y="Sentimiento")
        st.caption("✅ La opinión convergió." if baseline.get("converged")
                   else "⏱️ Corte por tope de rondas.")
    if analytics:
        s = analytics["stats"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Opinión inicial → final", f"{s['avg_final']:+.2f}", f"{s['swing']:+.2f} swing")
        c2.metric("Polarización", f"{s['polarizacion']:.2f}", help="Alta = panel dividido.")
        c3.metric("Convergió", "Sí ✅" if baseline.get("converged") else "No ⏱️")
        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown("**⚔️ Facciones finales**")
            f = analytics["factions"]
            st.markdown(
                f"- 🟢 A favor: {', '.join(n for n, _ in f['a_favor']) or '—'}\n"
                f"- 🔴 En contra: {', '.join(n for n, _ in f['en_contra']) or '—'}\n"
                f"- 🟡 Neutrales: {', '.join(n for n, _ in f['neutral']) or '—'}")
        with fc2:
            st.markdown("**🎯 Ranking de influencia**")
            st.dataframe(pd.DataFrame(analytics["influence"])[
                ["name", "posts", "mentions_received", "influence", "score"]],
                hide_index=True, use_container_width=True)

# ============================== REPORTE ========================================
with tab_report:
    st.markdown(final_state.get("report", "_(sin reporte)_"))
    sources = final_state.get("source_context", [])
    if sources:
        with st.expander(f"🌐 Fuentes externas usadas ({len(sources)})"):
            for src in sources:
                if isinstance(src, dict):
                    st.markdown(f"- [{src.get('title', src.get('url', 'fuente'))}]({src.get('url', '#')})")
