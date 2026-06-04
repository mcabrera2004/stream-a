# ÁGORA — Notas de la entrega

## Resumen

Diseñé y construí una POC de **flujo agentic multi-agente** sobre **LangGraph**: un
enjambre de agentes con personalidades distintas debate un tema (baseline), y luego un
agente Estratega propone intervenciones que se **re-simulan** para descubrir cuál mejora
la recepción. Es una aplicación de *agent-based social simulation* con agentes LLM,
fundada en la literatura del área, con un aporte propio: el **loop contrafáctico de
intervención**.

**Caso de uso (product marketing):** pre-mortem de mensajes/lanzamientos — simular la
reacción del público y encontrar el framing que reduce la fricción, antes de gastar en
investigación o campaña real.

## Marco teórico (prior art)

- **Generative Agents** — Park et al., 2023 (Stanford). El paradigma de agentes LLM que
  simulan comportamiento humano en un entorno; base conceptual de este trabajo.
- **Opinion Dynamics / Bounded Confidence** — Hegselmann & Krause, 2002. Modela cómo las
  opiniones convergen o se polarizan según la influencia mutua. El loop de
  convergencia + la métrica de polarización son una versión simplificada y aplicada.

## Decisiones de diseño y trade-offs

### 1. Orquestación: grafo padre + subgrafo de simulación
Elegí LangGraph (sobre CrewAI) porque el challenge pondera que los agentes **"toman
decisiones"**, y LangGraph materializa eso con conditional edges y ciclos. La simulación
del enjambre es un subgrafo reutilizable con su propio loop de convergencia; el grafo padre lo invoca para el baseline y para cada intervención contrafáctica. Hay dos decisiones explícitas en el sistema:
1. **Convergencia** (conditional edge del subgrafo): cuándo dejar de simular.
2. **Palanca ganadora** (`compare`): qué intervención mueve mejor la aguja.

### 2. El diferencial: loop contrafáctico de intervención
Agregué un paso que optimiza ("¿qué mensaje/política mejora la reacción?"):
`baseline → strategist propone intervenciones → re-simulación de cada una partiendo de la
opinión final del baseline → compare mide el efecto causal → recomendación`. Es el loop
agentic puro (percibir → decidir → actuar → re-evaluar) y convierte el simulador en una
herramienta de decisión aparte de predicción

### 3. Comunicación entre agentes: estado compartido
Los agentes colaboran a través de un estado compartido (`feed`), el modelo idiomático y
auditable de LangGraph. El `feed` usa un *reducer* (`operator.add`) para acumular posts;
el "diálogo" emerge porque cada persona lee el feed acumulado antes de postear.

### 4. Fan-out secuencial (decisión deliberada)
Dentro de cada ronda las personas reaccionan una por una, viendo lo que ya postearon
las anteriores. Esto habilita respuestas dirigidas ("@Ana, no coincido…") y dinámica de
grupo real. Se podría paralelizar con la Send API para escalar a cientos de agentes, pero
se elige secuencial a propósito para preservar el diálogo intra-ronda.

### 5. Diversidad garantizada por estratificación
Las personas se pre-asignan a arquetipos con distribuciones controladas de stance,
volatility, influence y activity (`config.ARCHETYPES`), en vez de dejar que el LLM invente
opiniones libremente. Garantiza un panel polarizado y con tensión, no seis voces tibias.

### 6. Memoria simple en estado (no vector DB)
Cada persona "recuerda" leyendo el feed desde el estado. Robusto y sin dependencias. La
evolución natural sería memoria vectorial / GraphRAG de largo plazo por agente (futuro).

### 7. LLM: Gemini 2.5 Flash
Hay muchas llamadas (N personas × M rondas × (1 baseline + K intervenciones)), así que
prioricé un modelo flash (rápido y barato). El modelo es configurable en una línea (`config.LLM_MODEL`).

### 8. Herramienta externa: Tavily
`ingest` ancla el debate en contexto real. Es degradable: si falta la key o falla la red,
la simulación corre igual reaccionando al enunciado (nunca se cae por la dependencia).

## Roles de los agentes

- `ingest`: Investigador contexto externo (Tavily)
- `persona_factory`: Diseñador del enjambre N personas diversas estratificadas
- `simulate` (subgrafo): Las personas debatiendo posts en el feed + sentimiento/ronda
- *(router del subgrafo)*: **Decisión 1** seguir ronda vs. cerrar (convergencia)
- `strategist`: Estratega intervenciones candidatas
- `counterfactual`: Re-simulador feed por intervención
- `compare`: **Decisión 2** efecto causal → palanca ganadora
- `report_agent`: Analista reporte predictivo + recomendación

## Validación

`tests/test_offline.py` mockea Gemini y Tavily y corre el grafo completo de forma
determinista: estratificación, convergencia del baseline, propuesta de intervenciones,
re-simulación contrafáctica, comparación y elección de la ganadora. Valida la orquestación
sin gastar API. Además, `validation/` mide la utilidad del producto: placebo (la
recomendación es significativa), test-retest (estable), y **validez externa contra clicks
REALES** del Upworthy Research Archive — la audiencia sintética acierta el ganador A/B el
**60% (67% en casos claros) vs 50% del azar**. Ver `validation/RESULTS.md`.

## Cómo correr

**1) Setup (una sola vez):**
```bash
uv sync                       # instala dependencias
cp .env.example .env          # y completar GOOGLE_API_KEY (Tavily y LangSmith son opcionales)
```

**2) Correr (elegí UNA opción):**
```bash
uv run streamlit run app.py              # UI (recomendado)
uv run python main.py "tu tema acá"      # CLI / headless
uv run python tests/test_offline.py      # test de orquestación (sin API keys)
```

## Limitaciones y trabajo futuro

- **Memoria:** hoy es el feed en estado. Siguiente paso: memoria vectorial / GraphRAG por agente.
- **Escala:** secuencial por diseño; para cientos de agentes, migrar a la Send API.
- **Costo:** el loop contrafáctico multiplica las llamadas (1 baseline + K intervenciones).
  Configurable vía `config.NUM_INTERVENTIONS`.

## Referencias

- Park et al. (2023). *Generative Agents: Interactive Simulacra of Human Behavior.* arXiv:2304.03442.
- Hegselmann & Krause (2002). *Opinion Dynamics and Bounded Confidence.* JASSS 5(3).
