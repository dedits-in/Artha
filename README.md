# Artha — AI Investment Research Agent

A multiagent AI system for personalized investment research and financial planning, built using CrewAI, Ollama (Llama3), and RAG.

## Tech Stack
- **LLM:** Ollama + Llama3 (local)
- **Multiagent Orchestration:** CrewAI
- **RAG Pipeline:** ChromaDB + HuggingFace Embeddings
- **Frontend:** Streamlit
- **Data:** AMFI India NAV data + curated fund knowledge base

## Architecture
User Goal → Retriever Agent (RAG) → Reasoning Agent (LLM) → Calculator Agent → Reporter Agent → Investment Plan

## Agents
| Agent | Role |
|-------|------|
| Retriever | Searches ChromaDB vector store for relevant fund data |
| Reasoning | Analyses goal and recommends fund categories |
| Calculator | Computes SIP projections and risk allocation |
| Reporter | Generates plain-English investment report |

## Setup

### Prerequisites
- Python 3.11+
- Ollama installed with llama3 model

### Installation
```bash
git clone https://github.com/YOUR_USERNAME/artha.git
cd artha
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
ollama pull llama3
```

### Add Data
- Download NAVAll.txt from amfiindia.com and save as CSV in data/raw/
- Run ingestion: `python rag/ingest.py`

### Run
```bash
streamlit run app.py
```

## Project Context
Built as an Experiential Learning project for the Agentic AI course — MBA in Data Science.
