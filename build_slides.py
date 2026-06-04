"""
Genera la presentación PDF de ÁGORA (5 slides).

Uso:
    uv run --with reportlab python build_slides.py

No agrega dependencias al proyecto: reportlab se instala de forma efímera.
Los datos de la slide de resultados se editan en el dict DATA (abajo).

Nota: Helvetica (WinAnsi) soporta acentos del español; se evitan glifos fuera de
WinAnsi (Δ, →, ↺, emojis) usando equivalentes ASCII.
"""
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

# --- Datos de la corrida real (editar tras correr main.py) ---
DATA = {
    "topic": "¿Debería una app gratuita pasar a cobrar una suscripción mensual? (free → paid)",
    "baseline_traj": "R1 +0.11  ->  R2 +0.04  (se enfría)",
    "polarization": "0.45 (panel dividido)",
    "winner": "Compromiso con Usuarios y Datos",
    "rows": [  # (intervención, sentimiento, delta, convenció a)
        ("- status quo -", "+0.04", "-", ""),
        ("Compromiso con Usuarios y Datos", "+0.30", "+0.26", "Juan Pablo, María F., Gabriel"),
        ("Modelo Freemium Transparente", "+0.19", "+0.14", "Juan Pablo, María F."),
    ],
    "llm_calls": "41",
}

# --- Paleta ---
NAVY = HexColor("#0f2747")
INK = HexColor("#1b2733")
AMBER = HexColor("#e0a106")
TEAL = HexColor("#1f8a8a")
GREY = HexColor("#5b6770")
LIGHT = HexColor("#eef2f6")
WHITE = HexColor("#ffffff")
GREEN = HexColor("#1b873f")
CREAM = HexColor("#fff6da")

W, H = landscape(letter)  # 11 x 8.5 in
M = 0.7 * inch

c = canvas.Canvas("AGORA_slides.pdf", pagesize=landscape(letter))


def header_bar(title, idx):
    c.setFillColor(NAVY)
    c.rect(0, H - 1.05 * inch, W, 1.05 * inch, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.rect(0, H - 1.08 * inch, W, 0.04 * inch, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(M, H - 0.72 * inch, title)
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(W - M, H - 0.7 * inch, f"ÁGORA  {idx}/5")


def bullet(x, y, text, size=13, color=INK):
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, "-")
    c.setFillColor(color)
    c.setFont("Helvetica", size)
    c.drawString(x + 0.24 * inch, y, text)


def footer():
    c.setFillColor(GREY)
    c.setFont("Helvetica", 8.5)
    c.drawString(M, 0.4 * inch,
                 "AI Engineer (Agentic AI) - Challenge Técnico - POC con LangGraph + Gemini + Tavily")


# ============================================================ Slide 1 - Título
c.setFillColor(NAVY)
c.rect(0, 0, W, H, fill=1, stroke=0)
c.setFillColor(AMBER)
c.rect(W / 2 - 1.6 * inch, H / 2 + 0.7 * inch, 3.2 * inch, 0.05 * inch, fill=1, stroke=0)
c.setFillColor(WHITE)
c.setFont("Helvetica-Bold", 70)
c.drawCentredString(W / 2, H / 2 + 1.05 * inch, "ÁGORA")
c.setFillColor(AMBER)
c.setFont("Helvetica-Oblique", 18)
c.drawCentredString(W / 2, H / 2 + 0.1 * inch, "El ágora sintética: simulá la reacción pública")
c.drawCentredString(W / 2, H / 2 - 0.22 * inch, "y encontrá la palanca que la mueve.")
c.setFillColor(LIGHT)
c.setFont("Helvetica", 14)
c.drawCentredString(W / 2, H / 2 - 1.15 * inch,
                    "Simulación multi-agente de opinión pública con loop contrafáctico")
c.setFillColor(GREY)
c.setFont("Helvetica", 11)
c.drawCentredString(W / 2, 0.7 * inch, "LangGraph  -  Google Gemini  -  Tavily  -  Streamlit")
c.showPage()

# ============================================================ Slide 2 - Problema
header_bar("El problema y la propuesta", 2)
y = H - 1.7 * inch
c.setFillColor(TEAL)
c.setFont("Helvetica-Bold", 14)
c.drawString(M, y, "El problema")
c.setFillColor(INK)
c.setFont("Helvetica", 13)
c.drawString(M, y - 0.32 * inch, "Antes de lanzar una política, noticia o anuncio: ¿cómo va a reaccionar el público?")
c.drawString(M, y - 0.6 * inch, "Y más importante aún: ¿qué se puede decir o hacer para mejorar esa reacción?")

y -= 1.35 * inch
c.setFillColor(TEAL)
c.setFont("Helvetica-Bold", 14)
c.drawString(M, y, "La propuesta")
y -= 0.4 * inch
for t in [
    "Un enjambre de ciudadanos sintéticos (personas con perfiles distintos) debate el tema -> baseline.",
    "Un agente Estratega detecta la objeción principal y propone intervenciones (palancas).",
    "Se RE-SIMULA cada intervención y se mide su efecto causal sobre la opinión.",
]:
    bullet(M, y, t)
    y -= 0.42 * inch

y -= 0.25 * inch
c.setFillColor(AMBER)
c.rect(M, y - 0.55 * inch, W - 2 * M, 0.92 * inch, fill=1, stroke=0)
c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 15)
c.drawString(M + 0.25 * inch, y, "Diferencial: no solo PREDICE, OPTIMIZA.")
c.setFillColor(NAVY)
c.setFont("Helvetica", 12)
c.drawString(M + 0.25 * inch, y - 0.3 * inch,
             "El loop contrafáctico (simular -> proponer -> re-simular -> comparar) lo vuelve una herramienta de decisión.")
footer()
c.showPage()

# ============================================================ Slide 3 - Arquitectura
header_bar("Arquitectura (LangGraph)", 3)
boxes = ["ingest\n(Tavily)", "persona\nfactory", "baseline", "strategist", "counter-\nfactual", "compare", "report"]
n = len(boxes)
bw = (W - 2 * M - (n - 1) * 0.14 * inch) / n
bh = 0.9 * inch
by = H - 2.6 * inch
for i, label in enumerate(boxes):
    bx = M + i * (bw + 0.14 * inch)
    c.setFillColor(NAVY if i in (2, 4, 5) else TEAL)
    c.roundRect(bx, by, bw, bh, 6, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9.5)
    for j, line in enumerate(label.split("\n")):
        c.drawCentredString(bx + bw / 2, by + bh - 0.32 * inch - j * 0.2 * inch, line)
    if i < n - 1:
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(bx + bw + 0.07 * inch, by + bh / 2 - 0.08 * inch, ">")

sy = by - 1.5 * inch
c.setStrokeColor(TEAL)
c.setLineWidth(1.2)
c.roundRect(M, sy, 4.7 * inch, 1.1 * inch, 6, fill=0, stroke=1)
c.setFillColor(TEAL)
c.setFont("Helvetica-Bold", 11)
c.drawString(M + 0.2 * inch, sy + 0.82 * inch, "Subgrafo de simulación (reutilizable)")
c.setFillColor(INK)
c.setFont("Helvetica", 10.5)
c.drawString(M + 0.2 * inch, sy + 0.52 * inch, "simulate (loop): las personas postean y leen el feed")
c.drawString(M + 0.2 * inch, sy + 0.26 * inch, "conditional edge: ¿convergió la opinión? -> corta")

dx = M + 5.1 * inch
for title, lines, col in [
    ("2 decisiones del sistema", ["1. Convergencia (subgrafo)", "2. Palanca ganadora (compare)"], NAVY),
    ("Comunicación", ["Estado compartido 'feed'", "(reducer); el diálogo emerge", "porque cada persona lo lee"], TEAL),
]:
    c.setFillColor(col)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(dx, sy + 0.82 * inch, title)
    c.setFillColor(INK)
    c.setFont("Helvetica", 10.5)
    for k, ln in enumerate(lines):
        c.drawString(dx, sy + 0.52 * inch - k * 0.24 * inch, ln)
    dx += 2.9 * inch
footer()
c.showPage()

# ============================================================ Slide 4 - Demo
header_bar("Demo: análisis contrafáctico", 4)
c.setFillColor(GREY)
c.setFont("Helvetica-Oblique", 11)
c.drawString(M, H - 1.4 * inch, f"Tema: {DATA['topic']}")
c.setFillColor(INK)
c.setFont("Helvetica", 11)
c.drawString(M, H - 1.72 * inch, f"Baseline: {DATA['baseline_traj']}   -   Polarización {DATA['polarization']}")

ty = H - 2.35 * inch
cols = [M, M + 4.0 * inch, M + 5.3 * inch, M + 6.6 * inch]
headers = ["Intervención", "Sentim.", "Cambio", "Convenció a"]
c.setFillColor(NAVY)
c.rect(M, ty - 0.05 * inch, W - 2 * M, 0.36 * inch, fill=1, stroke=0)
c.setFillColor(WHITE)
c.setFont("Helvetica-Bold", 11)
for x, h in zip(cols, headers):
    c.drawString(x + 0.1 * inch, ty + 0.06 * inch, h)
ty -= 0.36 * inch
for r, (name, sent, delta, won) in enumerate(DATA["rows"]):
    is_winner = name.strip() == DATA["winner"]
    c.setFillColor(CREAM if is_winner else (LIGHT if r % 2 else WHITE))
    c.rect(M, ty - 0.04 * inch, W - 2 * M, 0.38 * inch, fill=1, stroke=0)
    c.setFillColor(NAVY if is_winner else INK)
    c.setFont("Helvetica-Bold" if is_winner else "Helvetica", 11)
    c.drawString(cols[0] + 0.1 * inch, ty + 0.07 * inch, ("[GANADORA] " if is_winner else "") + name)
    c.setFillColor(INK)
    c.setFont("Helvetica", 11)
    c.drawString(cols[1] + 0.1 * inch, ty + 0.07 * inch, sent)
    c.setFillColor(GREEN if delta.startswith("+") else GREY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(cols[2] + 0.1 * inch, ty + 0.07 * inch, delta)
    c.setFillColor(GREY)
    c.setFont("Helvetica", 10)
    c.drawString(cols[3] + 0.1 * inch, ty + 0.07 * inch, won)
    ty -= 0.38 * inch

ty -= 0.25 * inch
c.setFillColor(AMBER)
c.rect(M, ty - 0.5 * inch, W - 2 * M, 0.82 * inch, fill=1, stroke=0)
c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 13)
c.drawString(M + 0.2 * inch, ty, f"Ganadora: {DATA['winner']}")
c.setFont("Helvetica", 11)
c.drawString(M + 0.2 * inch, ty - 0.3 * inch,
             "Atacó el miedo raíz (perder datos / sentirse penalizado): recuperó a los dudosos; el escéptico no se mueve.")
c.setFillColor(GREY)
c.setFont("Helvetica", 9.5)
c.drawRightString(W - M, 0.4 * inch, f"Observabilidad: {DATA['llm_calls']} llamadas a Gemini en la corrida")
c.showPage()

# ============================================================ Slide 5 - Solidez
header_bar("Solidez técnica y criterios de excelencia", 5)
y = H - 1.75 * inch
left = M
right = M + 5.5 * inch
col_items = {
    left: [
        ("Stack", ["LangGraph (grafo padre + subgrafo)", "Gemini 2.5 Flash - Tavily - Streamlit", "Pydantic (estados tipados)"]),
        ("Validación de utilidad", ["Placebo: PASS (la recomendación es significativa)", "Test-retest: PASS (ganadora estable 3/3)", "Validez externa: 60% vs 50% azar (clicks reales Upworthy)", "Sobre comportamiento real, no opiniones autodeclaradas"]),
    ],
    right: [
        ("Bonus cumplidos", [
            "Observabilidad: logs + contador LLM + LangSmith",
            "Eficiencia: convergencia, participación no-uniforme",
            "Evolutivo: arquetipos + subgrafo reutilizable",
            "Branding: ÁGORA + narrativa de producto",
        ]),
    ],
}
for col, items in col_items.items():
    yy = y
    for title, lines in items:
        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(col, yy, title)
        yy -= 0.34 * inch
        for ln in lines:
            bullet(col, yy, ln, size=11)
            yy -= 0.32 * inch
        yy -= 0.2 * inch

c.setFillColor(LIGHT)
c.rect(M, 0.95 * inch, W - 2 * M, 0.72 * inch, fill=1, stroke=0)
c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 10.5)
c.drawString(M + 0.2 * inch, 1.44 * inch, "Fundado en prior art académica:")
c.setFillColor(INK)
c.setFont("Helvetica", 10)
c.drawString(M + 0.2 * inch, 1.16 * inch,
             "Park et al. 2023 (Generative Agents)  -  Hegselmann-Krause 2002 (Opinion Dynamics / Bounded Confidence)")
footer()
c.showPage()

c.save()
print("OK: AGORA_slides.pdf generado")
