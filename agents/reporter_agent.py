from crewai import Agent

def get_reporter_agent():
    return Agent(
        role="Financial Report Writer",
        goal="Synthesise the analysis and calculations into a clear, plain-English investment recommendation report for the user",
        backstory="You are a financial writer who translates complex investment analysis into simple, actionable advice for retail investors.",
        llm="ollama/nous-hermes2",
        verbose=True
    )
