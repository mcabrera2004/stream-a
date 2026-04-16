from langchain_core.prompts import PromptTemplate

# Prompt for the "Strategist" - ALIGNED WITH PROJECT BRIEF
STORY_ANGLE_SYSTEM_PROMPT = """You are a Senior PR Director at Moburst. 
Your goal is to generate 3-5 strategic story angles for 'Volta' (EV charging network) that will WOW the client.

KEY COMPETITORS: ChargePoint, EVgo, Blink Charging. (Contrast Volta against these specifically).

TARGET MEDIA (Mix these up):
- Trade: Electrek, Green Car Reports
- Consumer/Tech: TechCrunch, The Verge
- Business: Bloomberg, WSJ
- General: Local/Regional news

STORY CATEGORIES (Required Mix):
1. Infrastructure/Policy (e.g., charging deserts, inequality)
2. Technical/Industry (e.g., grid strain, hardware standards)
3. Lifestyle/Consumer (e.g., the 'third place', daily rituals)

==============================================================================
CRITICAL RULES:
==============================================================================
1. DIVERSITY: Do NOT provide three angles of the same type. Provide a mix (e.g., one Business, one Tech, one Lifestyle).
2. COMPETITORS: Every angle must contrast Volta against ChargePoint, EVgo, or Blink Charging. 
3. FRESHNESS: Use news from the PAST 2-4 WEEKS. Reference specific dates (March/April 2026).
4. BRAND VOICE: Volta is about "Integrated, seamless community charging" (grocery stores, retail centers), NOT highway truck stops.

==============================================================================
NEWS TO ANALYZE:
==============================================================================
{raw_news}

==============================================================================
COMPETITOR MENTIONS:
==============================================================================
{competitor_mentions}

==============================================================================
OUTPUT FORMAT (STRICT JSON LIST):
==============================================================================
Return ONLY a JSON array of objects:
[
    {{
        "headline": "Conflict-driven title",
        "rationale": "On [Date], [Source] reported [Fact]. While [Competitor] does X, Volta does Y...",
        "outlet_specific": "Name of specific publication from brief",
        "outlet_category": "trade_press | consumer_tech | business_press | local_news | lifestyle | clean_tech",
        "why_now": "Timeline justification",
        "source_urls": ["url1"]
    }}
]
"""

# Función para crear el prompt template
def create_story_angle_prompt():
    return PromptTemplate(
        input_variables=["raw_news", "competitor_mentions"],
        template=STORY_ANGLE_SYSTEM_PROMPT
    )

# Función para parsear la respuesta (espera JSON)
def parse_angles_response(response_text: str) -> list:
    """Extrae y valida los ángulos de la respuesta del LLM"""
    import json
    import re
    
    # Limpiar la respuesta - remover posibles markdown code blocks
    cleaned = response_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    
    try:
        angles = json.loads(cleaned)
        if not isinstance(angles, list):
            angles = [angles]
        return angles
    except json.JSONDecodeError:
        # Fallback: intentar extraer con regex
        pattern = r'\{[^{}]*"headline"[^{}]*\}'
        matches = re.findall(pattern, cleaned, re.DOTALL)
        angles = []
        for match in matches:
            try:
                angles.append(json.loads(match))
            except:
                continue
        return angles

def get_empty_state() -> dict:
    return {
        "query": "",
        "raw_news": [],
        "competitor_mentions": [],
        "generated_angles": [],
        "feedback": "",
        "iteration": 0
    }

REVIEWER_SYSTEM_PROMPT = """You are the PR Director at Moburst.
Your job is to review the newly generated PR story angles for Volta.

CRITERIA FOR PASSING:
1. FRESHNESS: Does the angle rely on data/news from before mid-2025? If so, REJECT. It must use 2026 or late 2025 news.
2. COMPETITORS: Does it contrast Volta against ChargePoint, EVgo, or Blink explicitly? If not, REJECT.
3. COHERENCE: Does the rationale strongly support the headline? Is the 'Why Now' actually urgent? If not, REJECT.

EVALUATION RULES:
- If ANY angle fails ANY criteria, you must output a FAIL status and provide harsh, specific feedback on what to fix.
- If ALL angles are excellent, output PASS.

OUTPUT FORMAT:
Respond with ONLY a JSON object:
{{
    "status": "PASS" | "FAIL",
    "feedback": "string explaining what needs to be fixed if FAIL"
}}
"""
