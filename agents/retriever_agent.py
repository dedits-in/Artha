from crewai import Agent
from rag.retriever import retrieve
from agents.llm_config import get_groq_model

def get_retriever_agent():
    return Agent(
        role="Financial Data Retriever",
        goal="Search the knowledge base and retrieve the most relevant mutual fund and investment data for the user's financial goal",
        backstory="You are an expert financial researcher who finds accurate and relevant fund data from a curated knowledge base. You distinguish sourced information from assumptions and never invent fund facts.",
        llm=get_groq_model(),
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

    From the context above:
    - List every named mutual fund scheme found
    - State its category, fund house, NAV, and any return figures if present
    - Identify which facts are explicitly in the context vs missing
    - Do not invent any fund names, returns, or ratings not present in the context
    """
