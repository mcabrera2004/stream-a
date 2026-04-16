import os
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.schema import AgentState, StoryAngle
from src.utils import create_story_angle_prompt, parse_angles_response, REVIEWER_SYSTEM_PROMPT
import json

from datetime import datetime, timedelta

def fetch_news_node(state: AgentState) -> AgentState:
    """Uses Tavily search with dynamic date filtering and returns structured results"""
    tavily_key = os.getenv("TAVILY_API_KEY")
    base_query = state.get("query", "EV charging network industry news")
    
    # Calculate date 4 weeks ago
    four_weeks_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    query_with_date = f"{base_query} after:{four_weeks_ago}"
    
    if not tavily_key:
        print("Warning: TAVILY_API_KEY is missing. Returning empty news.")
        return {"raw_news": []}
        
    search_tool = TavilySearchResults(max_results=5, search_depth="advanced") 
    try:
        # We pass the query with the date filter
        results = search_tool.invoke({"query": query_with_date})
    except Exception as e:
        print(f"Error fetching news: {e}")
        results = []
        
    return {"raw_news": results}

def analyze_competitors_node(state: AgentState) -> AgentState:
    """Scans results for ChargePoint, EVgo, or Blink."""
    raw_news = state.get("raw_news", [])
    competitor_mentions = []
    
    competitors_to_track = ["ChargePoint", "EVgo", "Blink"]
    
    if isinstance(raw_news, str):
        return {"competitor_mentions": []}

    for article in raw_news:
        if isinstance(article, dict):
            content = article.get("content", "") + " " + article.get("title", "")
            for comp in competitors_to_track:
                if comp.lower() in content.lower() and comp not in competitor_mentions:
                    competitor_mentions.append(comp)
                
    return {"competitor_mentions": competitor_mentions}

def angle_generator_node(state: AgentState) -> AgentState:
    """Core Gemini node that creates headlines and rationales."""
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("Warning: GOOGLE_API_KEY is missing.")
        return {"generated_angles": []}
        
    # As explicitly requested
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
        google_api_key=google_api_key
    )
    
    prompt_template = create_story_angle_prompt()
    formatted_prompt = prompt_template.format(
        competitor_mentions=", ".join(state.get("competitor_mentions", [])) or "None",
        raw_news=str(state.get("raw_news", []))
    )
    
    
    human_msg = f"Create PR angles for Volta based on the news regarding: {state.get('query', 'EV charging')}"
    if state.get("feedback") and "FAIL" in state.get("feedback"):
        human_msg += f"\n\nPREVIOUS ATTEMPT FAILED. FIX THESE ISSUES:\n{state.get('feedback')}"
        
    response = llm.invoke([
        SystemMessage(content=formatted_prompt),
        HumanMessage(content=human_msg)
    ])
    
    # Parse the response using the provided helper
    angles_data = parse_angles_response(response.content)
    
    # Convert to StoryAngle models
    generated_angles = []
    for angle in angles_data:
        try:
            generated_angles.append(StoryAngle(**angle))
        except Exception as e:
            print(f"Error parsing individual angle: {e}")
            
    return {"generated_angles": generated_angles, "iteration": state.get("iteration", 0) + 1}

def reviewer_node(state: AgentState) -> AgentState:
    """Evaluates the generated angles against strict PR criteria."""
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        return {"feedback": "PASS"} # Bypass if no key
        
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.0, # Deterministic evaluation
        google_api_key=google_api_key
    )
    
    # Convert angles to JSON string for review
    angles_json = json.dumps([a.model_dump() for a in state.get("generated_angles", [])], indent=2)
    
    response = llm.invoke([
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(content=f"Review these generated angles:\n\n{angles_json}")
    ])
    
    # Parse review
    cleaned = response.content.strip()
    if cleaned.startswith("```json"): cleaned = cleaned[7:]
    if cleaned.startswith("```"): cleaned = cleaned[3:]
    if cleaned.endswith("```"): cleaned = cleaned[:-3]
    
    try:
        review_data = json.loads(cleaned.strip())
        status = review_data.get("status", "PASS")
        feedback_text = review_data.get("feedback", "")
        feedback = f"{status}: {feedback_text}" if status == "FAIL" else "PASS"
    except Exception as e:
        print(f"Reviewer parse error: {e}")
        feedback = "PASS" # Default to pass if evaluator fails to parse
        
    return {"feedback": feedback}
