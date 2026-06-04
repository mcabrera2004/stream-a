# Validación de utilidad — ÁGORA

No alcanza con que el flujo *corra*: hay que saber si **sirve** y si **le pega a la
realidad**. Estos tests atacan tres preguntas distintas.

> ÁGORA es una herramienta de **pre-mortem / priorización de mensajes** (cf. Argyle et al.
> 2023, *Out of One, Many*): su valor está en las objeciones que surgen y en el
> **ordenamiento relativo** de intervenciones, validado contra comportamiento real. Un
> primer filtro rápido que complementa la investigación tradicional.

## Los tres tests

### 1. `placebo_test.py` — ¿la recomendación es significativa o es ruido?
Compara, sobre el mismo baseline, una intervención **real** (ataca la objeción) vs un
**placebo** (anuncio irrelevante). **PASS** si la real mueve la aguja y el placebo casi
no. Si el placebo moviera lo mismo, "cualquier anuncio sube el sentimiento" → ruido.

```bash
uv run python validation/placebo_test.py
```

### 2. `reliability_test.py` — ¿es estable (test-retest)?
Corre el mismo tema N veces (personas frescas) con intervenciones fijas y mide la
varianza del sentimiento baseline y la **estabilidad de la ganadora**. Producto
confiable = baja varianza + gana siempre la misma palanca.

```bash
uv run python validation/reliability_test.py
```

### 3. `ab_validation.py` — ¿la gente reacciona así en la VIDA REAL? (validez externa)
La prueba angular. Usa el **Upworthy Research Archive** (32.487 experimentos A/B reales de
titulares con *clicks* medidos). Una audiencia sintética elige —a ciegas— el titular que
clickearía; comparamos contra el ganador real (mayor CTR). Resultado: **60% de acierto
(67% en casos claros) vs 50% del azar**. Valida la afirmación central del producto contra
comportamiento humano real (no opiniones). *Validación inicial; escalable a n≥100.*

```bash
# requiere el CSV (14MB, no se versiona):
curl -sL https://osf.io/download/3vqmp/ -o validation/data/upworthy_exploratory.csv
uv run python validation/ab_validation.py
```

## Cómo se relaciona con la literatura

- **Argyle et al. 2023** (*silicon sampling*): validar personas LLM contra datos reales.
  La prueba de validez externa (`ab_validation`) es una aplicación de esa idea.
- **Hegselmann–Krause 2002**: la convergencia/polarización que medimos es el objeto de
  estudio de los modelos de opinion dynamics.

## Costo

Cada test hace varias corridas completas (decenas de llamadas a Gemini). Son más caros
que una corrida normal; corrunlos puntualmente, no en cada cambio.
