"""
Observabilidad liviana.

`LLMCounter` es un callback de LangChain que cuenta cada llamada al modelo. Se pasa
una sola vez al invocar el grafo (config={"callbacks": [counter]}) y, como LangGraph
propaga los callbacks a TODO el grafo (incluido el subgrafo de simulación), captura
todas las invocaciones — baseline + contrafácticos — sin instrumentar cada nodo.

Para trazado completo (timeline, prompts, latencias) ver la sección LangSmith del README:
basta con setear LANGSMITH_TRACING=true y LANGSMITH_API_KEY en el .env (langsmith ya
es dependencia); LangGraph traza automáticamente.
"""
from __future__ import annotations

from langchain_core.callbacks import BaseCallbackHandler


class LLMCounter(BaseCallbackHandler):
    """Cuenta invocaciones al LLM (chat o completions) en toda la corrida del grafo."""

    def __init__(self) -> None:
        self.calls = 0

    def on_chat_model_start(self, *args, **kwargs) -> None:
        self.calls += 1

    def on_llm_start(self, *args, **kwargs) -> None:
        self.calls += 1
