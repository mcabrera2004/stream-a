# Volta AI Story Angle Generator

This project is a LangGraph-powered PR assistant that fetches recent EV charging industry news using Tavily Search and generates 3-5 strategic PR story angles using Google Gemini.

## Requirements
- Python 3.10+
- `uv` package manager

## Installation

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install streamlit langgraph langchain-google-genai langchain-core langchain-community tavily-python python-dotenv pydantic tenacity
```

Alternatively, you can install from `pyproject.toml`:
```bash
uv pip install -r pyproject.toml
```

## Running the App

```bash
streamlit run app.py
```
