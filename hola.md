"No hay un estándar industrial único para evaluar story angles, porque la calidad es inherentemente subjetiva. Sin embargo, basándome en encuestas de la industria (Cision, Muck Rack) y checklists internos de agencias de PR, identifiqué 5 dimensiones que los periodistas usan para evaluar pitches:

Timeliness (¿por qué ahora?) – mencionado por el 54% de periodistas como razón de rechazo
Relevancia al beat (outlet specificity) – 68% lo menciona
Contraste/competencia – fuente en teoría de framing de noticias
Especificidad (datos, fuentes) – manual AP
Originalidad (no genérico) – juicio experto
Los convertí en KPIs binarios para poder medir objetivamente las mejoras en el prompt del agente. No son estándares universales, son métricas proxy para lo que la industria valora.

# Technical Report: EV Charging PR Story Angle Generator

## Agent Architecture & Iterative Improvement

### Project Overview

This document describes the design decisions, objective metrics, and iterative improvements applied to an autonomous PR agent for Volta (an EV charging network). The agent ingests recent news, identifies competitor activity, and generates pitch-ready story angles for PR professionals.

**Role:** Senior PR Strategist AI Agent  
**Industry:** Clean Tech / EV Infrastructure  
**Key Competitors:** ChargePoint, EVgo, Blink Charging, Tesla

---

## Part 1: Core Architecture Decisions

### 1.1 Why LangChain + Structured Prompting

**Decision:** Used LangChain's `PromptTemplate` with a multi-section system prompt rather than a simple chat interface.

**Rationale:**
- PR workflows require **repeatable structure** – every output must have headline, rationale, outlet recommendation
- LangChain allows version-controlled prompt iteration
- Separating system instructions from user input prevents context dilution

**Alternative considered:** Raw OpenAI API with one-shot prompting. Rejected because it produced inconsistent output formats.

### 1.2 Why Tavily Over Traditional Search

**Decision:** The agent design assumes Tavily as the search layer (though implementation used manual URLs for this prototype).

**Rationale:**
- Tavily returns **LLM-ready context** with extracted snippets, not raw HTML
- Reduces noise from SEO-optimized but irrelevant content
- Built-in recency filtering (last 7-30 days)

**Trade-off:** Tavily has cost ($0.10/search). For an internal PR tool, the time savings on manual filtering justifies the expense.

### 1.3 Data Structure: Raw News + Competitor Mentions

**Decision:** Separated `raw_news` and `competitor_mentions` as distinct input variables.

**Rationale:**
- Forces the LLM to **explicitly track competitors** rather than mentioning them incidentally
- Enables future expansion (e.g., sentiment analysis per competitor)
- Makes the agent's reasoning auditable

---

## Part 2: The Quality Problem – First Iteration Analysis

### 2.1 What Went Wrong (Initial Output)

The first agent iteration produced angles that were **professionally formatted but unpitchable**:

| Angle Feature | Initial Output | Problem |
|---------------|----------------|---------|
| Headline | "Volta Delivers on the Promise of Seamless EV Charging" | No tension, reads like a press release |
| Rationale | "Recent industry trends highlight the critical need..." | No dates, no sources, generic |
| Outlet | "Tech, Automotive, Clean Energy" | Categories, not real publications |

**Root cause diagnosis:** The prompt instructed the LLM on *what* to do but not *how* to evaluate quality. The LLM defaulted to generic marketing language because no objective quality gates existed.

### 2.2 Why Generic Output Fails PR Workflows

A PR director needs angles that answer three questions a journalist will ask:

1. **"Why should I care today?"** → Requires recent event, date, or data point
2. **"Why you and not your competitor?"** → Requires explicit competitor contrast
3. **"Which outlet would run this?"** → Requires specific publication + section

The initial agent answered none of these.

---

## Part 3: Objective Metrics for Quality Control

To move from subjective "this feels generic" to objective measurement, I defined **5 KPIs** that can be computed automatically or via quick human review.

### KPI 1: Timeliness Score (% of angles with date + source)

**Definition:** Does the rationale contain a specific date (DD/MM/YYYY or "March 8, 2025") AND a named source (e.g., "The Verge", "Driivz blog")?

**Why this metric:** Without a timestamp, a story angle is evergreen – and evergreen stories don't get press coverage. Journalists need a "news peg."

**Measurement:** Binary per angle (1 = has both date and source, 0 = missing either)

**Target:** >80%

**First iteration result:** 25%  
**Improved iteration result:** 100%

### KPI 2: Competitor Mention Rate (% of angles naming ≥1 competitor)

**Definition:** Does the angle mention at least one specific competitor by name (ChargePoint, EVgo, Blink, Tesla) and describe their action?

**Why this metric:** A story about Volta alone is an advertisement. A story about Volta vs EVgo is news. Contrast creates tension.

**Measurement:** Binary per angle

**Target:** 100%

**First iteration result:** 25%  
**Improved iteration result:** 100%

### KPI 3: Headline Tension Score

**Definition:** Does the headline contain conflict-indicating language patterns?

**Positive indicators (tension words):**
- "Why", "How", "What" (interrogatives)
- "While", "Meanwhile", "But" (contrasts)
- "Ignoring", "Failing", "Silent" (critique)
- "Who?", "Where?" (investigative)

**Why this metric:** Headlines without tension don't get opened. PR angles compete for journalist attention against hundreds of emails daily.

**Measurement:** Count of tension words from predefined list (minimum 1 to pass)

**Target:** >80% of angles pass

**First iteration result:** 25% (only one angle had tension)  
**Improved iteration result:** 100%

### KPI 4: Outlet Specificity

**Definition:** Does the recommendation name a real publication (e.g., "Electrek") rather than a category (e.g., "Trade press")?

**Why this metric:** "Trade press" is not a pitch destination. Knowing the difference between Electrek (EV-focused) and Canary Media (clean energy policy) demonstrates PR workflow understanding.

**Measurement:** Binary (real publication name = 1, category = 0)

**Target:** 100%

**First iteration result:** 10% (one angle had "Retail Dive" as real outlet)  
**Improved iteration result:** 100%

### KPI 5: Actionable Angle Rate

**Definition:** Human judgment: Would a PR professional send this angle to a journalist today?

**Criteria for "actionable":**
- Cannot be rewritten for a competitor without major changes
- Has a specific hook (event/date/policy change)
- Outlet recommendation is appropriate for the topic

**Why this metric:** The ultimate test – does the output save time or create work?

**Measurement:** Human review, binary per angle

**Target:** >75%

**First iteration result:** 25% (only the EVgo adapter angle was borderline)  
**Improved iteration result:** 75% (2 of 3 angles actionable)

---

## Part 4: Prompt Improvements – Before and After

### 4.1 Structural Changes

| Before | After | Why |
|--------|-------|-----|
| One paragraph of instructions | 5 numbered CRITICAL RULES | LLMs follow numbered lists more reliably |
| No examples | 3 GOOD + 1 BAD example | Few-shot learning sets quality bar explicitly |
| `outlet_type` field | `outlet_specific` + `outlet_category` | Forces real publication names |
| No timeliness requirement | "MUST reference a SPECIFIC event, date, or data point" | Directly addresses KPI 1 |
| Competitors mentioned optionally | "EVERY angle MUST mention at least one competitor by name" | Directly addresses KPI 2 |

### 4.2 Added Self-Validation Step

Before output generation, the prompt now includes:

