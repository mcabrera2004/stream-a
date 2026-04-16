import os
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from .schema import AgentState, StoryAngle
from .utils import create_story_angle_prompt, parse_angles_response

from datetime import datetime, timedelta

def fetch_news_node(state: AgentState) -> AgentState:
    """Uses Tavily search with dynamic date filtering and returns structured results"""
    tavily_key = os.getenv("TAVILY_API_KEY")
    base_query = state.get("query", "EV charging network industry news")
    
    # Calculate date 2 weeks ago
    two_weeks_ago = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    query_with_date = f"{base_query} after:{two_weeks_ago}"
    
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
    
    response = llm.invoke([
        SystemMessage(content=formatted_prompt),
        HumanMessage(content=f"Create PR angles for Volta based on the news regarding: {state.get('query', 'EV charging')}")
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
            
    return {"generated_angles": generated_angles}
