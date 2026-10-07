# Artha — AI Investment Research Agent

> A multiagent RAG system for personalised investment research and financial planning, built using CrewAI, Groq's API, and ChromaDB.

---

## Overview

Artha is an Agentic AI system that acts as a personal investment research analyst. A user describes their financial goal — buying a car, saving for retirement, funding education — and Artha autonomously retrieves relevant mutual fund data, analyses it, computes SIP projections, and generates a plain-English investment plan.

The RAG store and frontend run locally. CrewAI agents use the Groq API, configured with a key in `.env`.

---

## Problem Statement

Retail investors in India face three key challenges:

1. **Information overload** — Over 2,500 mutual fund schemes exist across 44 AMCs, making it difficult to identify relevant options for a specific goal.
2. **Lack of personalisation** — Generic financial advice does not account for individual goals, risk appetite, or investment horizon.
3. **Accessibility gap** — Professional financial advisory is expensive and inaccessible to most first-time investors.

Existing tools either provide raw data without interpretation, or require users to already understand financial concepts. Artha bridges this gap by combining a curated knowledge base with autonomous AI agents that reason, calculate, and communicate in plain English.

---

## Project Objectives

- Build a **multiagent AI system** where specialised agents collaborate to solve a complex financial research task
- Implement a **RAG pipeline** that grounds agent responses in real mutual fund data rather than hallucinated facts
- Demonstrate **sequential agent orchestration** using CrewAI with Groq-hosted Llama 3.3
- Deliver a **working web application** where users can input their financial goals and receive structured investment plans
- Keep user data and the vector store local while using an API-hosted LLM

---

## Proposed Solution

Artha uses a four-agent pipeline orchestrated by CrewAI. Each agent has a distinct role:

| Agent | Role |
|-------|------|
| Retriever | Queries ChromaDB vector store using RAG to find relevant fund data |
| Reasoner | Analyses the goal and retrieved context to recommend fund categories |
| Calculator | Computes SIP projections, CAGR estimates, and risk allocation |
| Reporter | Synthesises all outputs into a structured plain-English report |

The agents run sequentially — each agent's output becomes the next agent's input — mimicking how a human financial analyst would research, analyse, calculate, and then communicate.

The RAG pipeline ingests AMFI NAV data and a curated mutual fund knowledge base, chunks and embeds them using HuggingFace's `all-MiniLM-L6-v2` model, and stores them in ChromaDB. When a user submits a goal, the Retriever agent queries this vector store and pulls the most relevant context before any LLM reasoning begins — ensuring responses are grounded in real data.

---


````markdown
## AI Agent Pipeline

```
User Goal
    ↓
Streamlit App (frontend)
    ↓
CrewAI Orchestrator (sequential process)
    ↓
[1] Retriever Agent  →  queries ChromaDB (RAG) → returns top-5 relevant chunks
    ↓
[2] Reasoning Agent  →  analyses goal + context → recommends 3 fund categories
    ↓
[3] Calculator Agent →  computes SIP amount, CAGR, risk allocation breakdown
    ↓
[4] Reporter Agent   →  writes final structured investment report
    ↓
Streamlit App (displays report + agent reasoning trail)
```

All agents use Groq through CrewAI/LiteLLM. The model defaults to `groq/qwen/qwen3.8-27b`; configure it with `ARTHA_LLM_MODEL` in `.env` if you want to select another model available to your Groq account.
````

````markdown
## Project Structure

```
artha/
├── agents/
│   ├── __init__.py
│   ├── retriever_agent.py      # RAG-based retrieval agent
│   ├── reasoning_agent.py      # Investment analysis agent
│   ├── calculator_agent.py     # SIP and CAGR calculation agent
│   └── reporter_agent.py       # Report generation agent
├── rag/
│   ├── __init__.py
│   ├── ingest.py               # Loads, chunks and embeds documents into ChromaDB
│   └── retriever.py            # Queries vector store for relevant context
├── data/
│   ├── raw/                    # Source data: AMFI NAV CSV, fund knowledge base TXT
│   └── vectorstore/            # ChromaDB persistent vector index
├── tools/
│   ├── __init__.py
│   └── finance_tools.py        # SIP, CAGR, risk score calculation functions
├── crew.py                     # CrewAI orchestration — agents, tasks, crew
├── app.py                      # Streamlit frontend
└── requirements.txt
```
````


---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Groq API + Qwen 3.8 27B |
| Multiagent Orchestration | CrewAI |
| RAG — Vector Store | ChromaDB |
| RAG — Embeddings | HuggingFace `all-MiniLM-L6-v2` |
| Document Loading | LangChain Community |
| Frontend | Streamlit |
| Language | Python 3.11 |

---

## Setup and Installation

### Prerequisites
- Python 3.11+
- A Groq API key

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/dedits-in/Artha.git
cd Artha

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure the API key (copy .env.example to .env and add your key)
copy .env.example .env

# 5. Add data files to data/raw/
#    Download NAVAll.txt from amfiindia.com and save as NAVAll.csv

# 6. Build the vector store if it does not already exist
python rag/ingest.py

# 7. Run the app
streamlit run app.py
```

---

## Academic Context

**Course:** Agentic AI — Experiential Learning Project  
**Program:** MBA in Data Science and Data Analytics  
**Concepts demonstrated:** Multiagent systems, Retrieval-Augmented Generation (RAG), sequential agent orchestration, API-hosted LLMs, goal-based financial reasoning

## Verify the Groq API connection

Activate the project virtual environment and confirm the selected model configuration:

```powershell
python -c "from agents.llm_config import get_groq_model; print(get_groq_model())"
```

Send a small prompt through LiteLLM, the provider interface used by CrewAI:

```powershell
python -c "from pathlib import Path; from dotenv import load_dotenv; load_dotenv(Path('.env')); from litellm import completion; r=completion(model='groq/qwen/qwen3.8-27b', messages=[{'role':'user','content':'Reply with exactly: Artha API test passed'}], max_tokens=40); print(r.choices[0].message.content)"
```

Then run the full sequential crew and launch the UI:

```powershell
python crew.py
streamlit run app.py
```

Keep `.env` private; `.env.example` is only a template.

---

*This project is for educational purposes only and does not constitute financial advice. Mutual fund investments are subject to market risk.*
