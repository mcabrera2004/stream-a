from langgraph.graph import StateGraph, END
from .schema import AgentState
from .nodes import fetch_news_node, analyze_competitors_node, angle_generator_node

def create_agent():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("fetch", fetch_news_node)
    workflow.add_node("analyze", analyze_competitors_node)
    workflow.add_node("generate", angle_generator_node)
    
    # Add edges
    workflow.set_entry_point("fetch")
    workflow.add_edge("fetch", "analyze")
    workflow.add_edge("analyze", "generate")
    workflow.add_edge("generate", END)
    
    # Compile graph
    app = workflow.compile()
    
    return app

agent_app = create_agent()
