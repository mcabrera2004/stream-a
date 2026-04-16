from langgraph.graph import StateGraph, END
from .schema import AgentState
from .nodes import fetch_news_node, analyze_competitors_node, angle_generator_node, reviewer_node

def route_evaluation(state: AgentState):
    # If passed or hit max retries, exit
    if state.get("feedback") == "PASS" or state.get("iteration", 0) >= 3:
        return "end"
    # Otherwise, loop back to generator to fix issues
    return "generate"

def create_agent():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("fetch", fetch_news_node)
    workflow.add_node("analyze", analyze_competitors_node)
    workflow.add_node("generate", angle_generator_node)
    workflow.add_node("reviewer", reviewer_node)
    
    # Add edges
    workflow.set_entry_point("fetch")
    workflow.add_edge("fetch", "analyze")
    workflow.add_edge("analyze", "generate")
    workflow.add_edge("generate", "reviewer")
    
    # Conditional logic
    workflow.add_conditional_edges(
        "reviewer",
        route_evaluation,
        {
            "end": END,
            "generate": "generate"
        }
    )
    
    # Compile graph
    app = workflow.compile()
    
    return app

agent_app = create_agent()
