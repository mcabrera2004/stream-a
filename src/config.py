"""Parámetros de la simulación. Centralizados para tunear fácil."""

# Modelo LLM (Gemini). Flash = rápido y barato, ideal para N personas x M rondas.
LLM_MODEL = "gemini-2.5-flash"

# Tamaño del enjambre y duración de la simulación.
NUM_PERSONAS = 6          # cuántos agentes generamos
MAX_ROUNDS = 3            # tope de rondas (corte duro del loop)

# Criterio de convergencia (la "decisión" del grafo).
# Si el cambio del sentimiento promedio entre rondas es menor a este umbral,
# consideramos que la opinión se estabilizó y disparamos el reporte.
CONVERGENCE_THRESHOLD = 0.1

# Temperaturas por rol.
TEMP_FACTORY = 0.9        # diversidad alta al generar personas
TEMP_REACTION = 0.8       # voces variadas y reactivas
TEMP_REPORT = 0.3         # síntesis estable y consistente

# Tavily
TAVILY_MAX_RESULTS = 5

# ---------------------------------------------------------------------------
# Estratificación por arquetipo.
#
# En vez de dejar que el LLM invente las opiniones libremente (riesgo: 6 voces
# tibias y parecidas), pre-asignamos un arquetipo por persona con DISTRIBUCIONES
# controladas de stance / volatility / influence / activity. Esto garantiza un
# panel diverso y con tensión real. La factory rellena nombre/profesión/voz
# dentro de cada arquetipo.
#
# stance/volatility son rangos (se muestrea dentro); influence/activity son base.
# ---------------------------------------------------------------------------
ARCHETYPES = [
    {"key": "entusiasta",  "label": "entusiasta / early adopter",
     "stance": (0.4, 0.9),   "volatility": (0.10, 0.30), "influence": 1.0, "activity": 0.9},
    {"key": "esceptico",   "label": "escéptico / crítico",
     "stance": (-0.9, -0.4), "volatility": (0.10, 0.30), "influence": 1.0, "activity": 0.9},
    {"key": "experto",     "label": "experto / académico (voz de autoridad)",
     "stance": (-0.3, 0.3),  "volatility": (0.10, 0.25), "influence": 2.0, "activity": 0.6},
    {"key": "pragmatico",  "label": "pragmático / indeciso (swing voter)",
     "stance": (-0.2, 0.2),  "volatility": (0.60, 0.90), "influence": 0.8, "activity": 0.6},
    {"key": "afectado",    "label": "afectado directo / ciudadano de a pie",
     "stance": (-0.5, 0.5),  "volatility": (0.50, 0.80), "influence": 0.7, "activity": 0.7},
    {"key": "observador",  "label": "periodista / observador",
     "stance": (-0.2, 0.2),  "volatility": (0.10, 0.30), "influence": 1.3, "activity": 0.8},
]

# Todos postean en la ronda 1 (sientan postura); desde la ronda 2 la
# participación es no-uniforme según `activity` de cada persona.
GUARANTEED_FIRST_ROUND = True
MIN_POSTERS_PER_ROUND = 2  # piso para que ninguna ronda quede (casi) vacía

# ---------------------------------------------------------------------------
# Loop contrafáctico (diferencial propio).
#
# Tras la simulación baseline, un agente Estratega propone N intervenciones
# (mensajes/políticas) que atacan la objeción principal. Se RE-SIMULA cada una
# partiendo de la opinión final del baseline, y se compara el efecto causal.
# ---------------------------------------------------------------------------
ENABLE_COUNTERFACTUAL = True
NUM_INTERVENTIONS = 2          # cuántas palancas propone el Estratega (A/B)
# Umbral de mejora (en sentimiento promedio) para declarar que una intervención
# "funciona" frente al status quo.
INTERVENTION_MIN_LIFT = 0.05
