"""Artha's sequential research and investment-planning workflow."""

from __future__ import annotations
import re
from crewai import Crew, Process, Task
from agents.calculator_agent import get_calculator_agent
from agents.reasoning_agent import get_reasoning_agent
from agents.reporter_agent import get_reporter_agent
from agents.retriever_agent import get_retriever_agent, retriever_task_description
from tools.finance_tools import calculate_sip, monthly_sip_for_goal, risk_score


def _goal_target_rupees(user_goal: str) -> float | None:
    text = user_goal.lower().replace(",", "").replace("₹", " rupees ")
    patterns = [
        (r"(\d+(?:\.\d+)?)\s*(?:crore|crores|cr)\b", 10_000_000),
        (r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs| lac| lacs)\b", 100_000),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group(1)) * multiplier
    return None


def run_artha_details(user_goal: str, monthly_budget: float, horizon: int, risk_appetite: str) -> dict:
    if not str(user_goal).strip():
        raise ValueError("Please enter a financial goal.")
    if float(monthly_budget) < 0:
        raise ValueError("Monthly budget cannot be negative.")
    horizon = int(horizon)
    sip_result = calculate_sip(monthly_budget, 12.0, horizon)
    risk_result = risk_score(risk_appetite, horizon)
    target_value = _goal_target_rupees(user_goal)
    required_monthly_sip = monthly_sip_for_goal(target_value, 12.0, horizon) if target_value else None

    retriever = get_retriever_agent()
    reasoner = get_reasoning_agent()
    calculator = get_calculator_agent()
    reporter = get_reporter_agent()

    task1 = Task(
        description=retriever_task_description(user_goal) + """
        Produce a compact evidence sheet from the retrieved passages. For every named scheme,
        preserve the exact scheme name and report its category, fund house, NAV date/value, and
        any risk, return, or fee facts only when those facts are explicitly present. Identify which
        passage supports each fact. Clearly label missing facts as "not present in retrieved data".
        """,
        expected_output="Evidence sheet of named schemes and only the attributes actually present in the retrieved text.",
        agent=retriever,
    )

    task2 = Task(
        description=(
            f"User goal: {user_goal}\nTime horizon: {horizon} years\n"
            f"Risk appetite: {risk_appetite}\nIllustrative allocation: "
            f"{risk_result['equity']}% equity, {risk_result['debt']}% debt, {risk_result['hybrid']}% hybrid.\n\n"
            "Recommend up to three SPECIFIC mutual fund schemes whose exact names appear in the preceding "
            "retriever output. For each, give exact scheme name, category, role in the portfolio, and one "
            "source fact that supports including it. Follow the allocation percentages supplied above; "
            "do not assign unsupported percentages to individual schemes. If no named scheme is present "
            "in the retriever output, say the retrieved evidence is insufficient and recommend categories only. "
            "Do not invent facts, returns, risk ratings, fees, or suitability claims. Treat NAV as a dated "
            "price observation, not performance evidence. State what must be independently verified."
        ),
        expected_output="Up to three source-grounded named fund candidates, each with category, rationale, and evidence limits.",
        agent=reasoner,
        context=[task1],
    )

    task3 = Task(
        description=(
            f"Monthly budget: ₹{monthly_budget:,.2f}; goal: {user_goal}; horizon: {horizon} years.\n"
            f"Deterministic SIP estimate at 12% annual return: {sip_result}\n"
            f"Parsed goal target in rupees: {target_value}\n"
            f"Estimated monthly SIP needed: {required_monthly_sip}\n"
            f"Illustrative risk allocation: {risk_result}\n"
            "Compare projected value with target, state the gap and required monthly SIP. "
            "Explain total contributions, estimated ending value and growth. "
            "State clearly that 12% is an assumption and returns are not guaranteed."
        ),
        expected_output="Clear SIP assumptions and projection with monthly contribution and allocation breakdown.",
        agent=calculator,
    )

    task4 = Task(
        description=(
            f"Prepare the final report for this goal: {user_goal}. "
            "Combine the preceding analyst and calculation outputs. "
            "Include these exact sections:\n"
            "1. Goal Summary — restate goal, timeline, monthly budget\n"
            "2. Recommended Fund Categories — 3 categories with expected returns and risk\n"
            "3. SIP Plan — monthly amount, total invested, projected value\n"
            "4. Portfolio Allocation — exact % split across equity/debt/hybrid\n"
            "5. Action Steps — 3 concrete next steps the user should take\n"
            "Use plain English, Indian rupee formatting. "
            "Use the retrieved evidence and analyst candidates. Copy every monetary figure from the calculator "
            "output exactly; do not recalculate or estimate new amounts. Do not introduce fund names absent "
            "from the analyst output. Label all projections as estimates, not guaranteed returns."
        ),
        expected_output="""A detailed investment report with 5 sections: Goal Summary, Recommended Fund Categories, SIP Plan, Portfolio Allocation, Action Steps.""",
        agent=reporter,
        context=[task1, task2, task3],
    )

    crew = Crew(
        agents=[retriever, reasoner, calculator, reporter],
        tasks=[task1, task2, task3, task4],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    task_outputs = getattr(result, "tasks_output", []) or []
    steps = [getattr(output, "raw", str(output)) for output in task_outputs]
    report = str(result)

    return {
        "report": report,
        "steps": steps,
        "sip": sip_result,
        "risk": risk_result,
        "target_value": target_value,
        "required_monthly_sip": required_monthly_sip,
    }


def run_artha(user_goal: str, monthly_budget: float, horizon: int, risk_appetite: str) -> str:
    return run_artha_details(user_goal, monthly_budget, horizon, risk_appetite)["report"]


if __name__ == "__main__":
    result = run_artha_details(
        user_goal="I want to save 50 lakhs in 10 years for retirement",
        monthly_budget=10000,
        horizon=10,
        risk_appetite="medium",
    )
    print("\n===== ARTHA REPORT =====\n")
    print(result["report"])
