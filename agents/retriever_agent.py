from crewai import Agent
from rag.retriever import retrieve

def get_retriever_agent():
    return Agent(
        role="Financial Data Retriever",
        goal="Summarize only relevant mutual fund and investment information supplied from the local knowledge base",
        backstory="You are a careful research assistant. You distinguish sourced information from assumptions and never invent fund facts.",
        llm="ollama/nous-hermes2",
        verbose=True
    )

def retriever_task_description(user_goal: str) -> str:
    try:
        context = retrieve(user_goal)
    except Exception as exc:
        context = f"The local knowledge base could not be queried ({type(exc).__name__}: {exc}). Do not invent sourced facts."
    return f"""
    User Goal: {user_goal}

    Retrieved Knowledge Base Context:
    {context}

    Summarise only relevant facts in the context above. Identify if this data is insufficient
    to support specific fund or performance claims. Do not provide a buy/sell instruction.
    """
