from crewai import Agent

def get_reasoning_agent():
    return Agent(
        role="Investment Analyst",
        goal="Analyse retrieved fund information and the user's goal to suggest appropriate fund categories and explain their tradeoffs",
        backstory="You are a cautious Indian mutual fund research analyst. You do not claim registration, guarantee returns, or fabricate scheme facts.",
        llm="ollama/nous-hermes2",
        verbose=True
    )
