from crewai import Agent

def get_calculator_agent():
    return Agent(
        role="Financial Calculator",
        goal="Calculate SIP amounts, CAGR projections and risk scores based on the user's inputs and analyst recommendations",
        backstory="You are a quantitative analyst who specialises in computing precise financial projections for retail investors.",
        llm="ollama/nous-hermes2",
        verbose=True
    )