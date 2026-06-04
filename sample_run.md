# Sample run — ÁGORA · caso real (product marketing)

**Escenario de negocio:** un equipo de *product marketing* evalúa migrar una app de
**gratis → suscripción paga**. Antes de tocar nada, le pregunta a ÁGORA cómo va a
reaccionar la base de usuarios y **qué anuncio reduce la fricción**.

```bash
uv run python main.py "¿Debería una app gratuita pasar a cobrar una suscripción mensual?"
```

**El valor en una línea:** en ~3 minutos y centavos de LLM, ÁGORA detectó los *drivers de
churn*, identificó qué segmentos se van, y eligió el mensaje que recupera a los dudosos —
un pre-mortem que de otro modo lleva semanas de research.

> Corrida real (Gemini 2.5 Flash + Tavily). No-determinista; la lógica está validada en
> `tests/test_offline.py` y la utilidad en `validation/RESULTS.md`. **41 llamadas a Gemini**.

---

## Log breve de la corrida (intercambio entre agentes)

```
[persona_factory] 6 personas → Sofía(+0.7) · Roberto(-0.8) · Dra. Elena(+0.2/inf2.0)
                                  · Juan Pablo(+0.1) · María Fernanda(-0.4) · Gabriel(0.0)
[baseline] status quo
[base r1] postean 6/6
  ↳ Sofía (entusiasta) 🟢+0.80: ...la suscripción es una inversión en calidad y desarrollo.
  ↳ Roberto (escéptico) 🔴-0.75: Empiezan gratis para engancharte y después ¡zas!, la
                                 suscripción. El contenido básico no debería ser una trampa.
  ↳ María Fernanda (estudiante) 🔴-0.20: ¡Mi presupuesto es limitado! Perder mis apuntes
                                         por una suscripción sería terrible.
[base r1] sentimiento ponderado +0.11
[base r2] postean 6/6  →   +0.04 | Δ=0.065
[strategist] 2 palancas → «Modelo Freemium Transparente» | «Compromiso con Usuarios y Datos»
[counterfactual] re-simulando «Modelo Freemium Transparente» …  → +0.19
[counterfactual] re-simulando «Compromiso con Usuarios y Datos» …
  ↳ María Fernanda 🟢+0.40: que garanticen mis datos y haya plan Legacy flexible, ¡cambia
                            todo! Es un alivio no perder mis apuntes.
[compare] ganadora → «Compromiso con Usuarios Actuales y Datos»
[report_agent] reporte final generado.
[Observabilidad]: 41 llamadas a Gemini en toda la corrida.
```

## Lo que ÁGORA detectó (los drivers de churn)

| Segmento | Persona | Objeción |
|---|---|---|
| Escéptico del modelo | Roberto (−0.8) | *"Te enganchan gratis y después cobran"* → desconfianza/bait-and-switch |
| Usuario de bajo presupuesto | María Fernanda (−0.2) | *"Perder mis apuntes / no me alcanza"* → miedo a perder datos |
| Indeciso | Juan Pablo | *"Lo pago si me da valor real"* → recuperable |

Baseline: el entusiasmo inicial **se enfría** (+0.11 → +0.04) y el panel queda **dividido**
(polarización 0.45). Lanzar así = churn evitable.

## Análisis contrafáctico — qué palanca mueve la aguja

| Intervención | Sentimiento | Δ vs status quo | Recupera a |
|---|---|---|---|
| — status quo — | +0.04 | — | — |
| Modelo Freemium Transparente | +0.19 | +0.14 | Juan Pablo, María Fernanda |
| **Compromiso con Usuarios y Datos** | **+0.30** | **+0.26** | Juan Pablo, María Fernanda, Gabriel |

**Ganadora:** *"Garantizamos exportar tus datos en cualquier momento, incluso sin
suscripción, + plan 'Legacy' con precio preferencial y pago flexible."*
Gana porque ataca el **miedo raíz** (perder datos / sentirse penalizado), no solo comunica
"hay un plan gratis". Recupera a los dudosos; el escéptico ideológico (Roberto) no se mueve.

## Recomendación accionable (del report_agent)

1. **Proteger el acceso a datos de usuarios actuales** (descarga/exportación garantizada,
   con o sin suscripción) → desactiva el miedo a perder contenido.
2. **Plan "Legacy" justo y flexible** (precio preferencial, mensual/anual) para los usuarios
   existentes → transición suave que reconoce la lealtad.

> **Por qué esto vende:** el output no es "un análisis", es una **decisión de go-to-market**
> lista para ejecutar — qué objeciones esperar, qué segmentos peligran y el mensaje exacto
> que los recupera. Es el primer filtro barato antes de gastar en research o campaña real.
