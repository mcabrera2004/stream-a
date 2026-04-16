# Volta AI Story Angle Generator

This project is a LangGraph-powered PR assistant that fetches recent EV charging industry news using Tavily Search and generates 3-5 strategic PR story angles using Google Gemini.

## Requirements
- Python 3.13+
- `uv` package manager

## Installation

The project uses `uv` for dependency management. To set up the environment and install dependencies, simply run:

```bash
uv sync
```

This will create a virtual environment and install all required packages from `uv.lock`.

## Configuration

Create a `.env` file with your API keys:
```env
GOOGLE_API_KEY=your_google_key
TAVILY_API_KEY=your_tavily_key
```

## Running the App

You don't need to manually activate the virtual environment. Use `uv run` to run the application:

```bash
uv run streamlit run app.py
```
