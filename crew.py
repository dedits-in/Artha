"""Artha's sequential research and investment-planning workflow."""

from __future__ import annotations

import os
import re
import time

# Avoid a pre-existing non-directory named "ARTHA" in CrewAI's default
# per-project app-data location on this machine. Users may override this.
os.environ.setdefault("CREWAI_STORAGE_DIR", "Artha_Groq_Runtime")
os.environ["LITELLM_DROP_PARAMS"] = "true"

from crewai import Crew, Process, Task
from agents.calculator_agent import get_calculator_agent
from agents.reasoning_agent import get_reasoning_agent
from agents.reporter_agent import get_reporter_agent
from agents.retriever_agent import get_retriever_agent, retriever_task_description
from rag.fund_candidates import get_local_fund_examples
from tools.finance_tools import calculate_sip, monthly_sip_for_goal, risk_score

# Seconds to wait between agent tasks so Groq's per-minute output-token limit
# (1000 OTPM) can reset. Lower it if you upgrade your Groq tier.
TASK_DELAY_SECONDS = int(os.getenv("ARTHA_TASK_DELAY", "40"))


def _pause_between_tasks(_output) -> None:
    """Task callback: wait so the next LLM call doesn't exceed the rate limit."""
    if TASK_DELAY_SECONDS > 0:
        time.sleep(TASK_DELAY_SECONDS)


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


def _build_verified_report(
    user_goal: str,
    monthly_budget: float,
    horizon: int,
    risk_profile: dict,
    sip: dict,
    target_value: float | None,
    required_monthly_sip: float | None,
    fund_examples: dict[str, list[str]],
) -> str:
    """Build the user-facing plan from calculated facts; use the analyst only for research leads."""
    sections = [
        "## Goal summary",
        f"Goal: {user_goal}",
        f"Time horizon: {horizon} years · Monthly budget: ₹{monthly_budget:,.0f}",
        "",
        "## SIP projection",
        f"At an illustrative 12% annual return, investing ₹{sip['monthly_sip']:,.0f}/month for {horizon} years "
        f"would contribute ₹{sip['total_invested']:,.0f} and project to ₹{sip['maturity_amount']:,.0f}. "
        f"Estimated growth: ₹{sip['estimated_returns']:,.0f}. This is an assumption, not a forecast or guarantee.",
    ]
    if target_value is not None and required_monthly_sip is not None:
        shortfall = max(0, target_value - sip["maturity_amount"])
        monthly_gap = max(0, required_monthly_sip - monthly_budget)
        sections += [
            "",
            "## Goal feasibility",
            f"Target: ₹{target_value:,.0f} · Projected at current budget: ₹{sip['maturity_amount']:,.0f} · "
            f"Estimated SIP needed: ₹{required_monthly_sip:,.0f}/month.",
            (f"At the current budget, the projection is ₹{shortfall:,.0f} below target; "
             f"the estimated monthly budget gap is ₹{monthly_gap:,.0f}.") if shortfall else
            "The projection reaches the target under the stated return assumption.",
        ]
    sections += [
        "",
        "## Illustrative portfolio allocation",
        f"Equity {risk_profile['equity']}% · Debt {risk_profile['debt']}% · Hybrid {risk_profile['hybrid']}% "
        f"({risk_profile['label']} profile; {risk_profile['note']}).",
        "",
        "## Fund research leads",
        "Examples named in the local guidance file (research leads only; verify current scheme status, "
        "category, plan, risk, fees, holdings, and suitability from official documents):",
        "\n".join(
            f"- {bucket}: {', '.join(names[:3]) if names else 'No names listed in local guidance'}"
            for bucket, names in fund_examples.items()
        ),
    ]
    return "\n\n".join(sections)


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
        Keep the answer under 250 words.
        """,
        expected_output=(
            "Short evidence sheet (under 250 words) of named schemes and only the "
            "attributes actually present in the retrieved text."
        ),
        agent=retriever,
        callback=_pause_between_tasks,
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
            "Do not invent facts, returns, risk ratings, fees, or suitability claims. "
            "Do NOT state any monthly SIP amount, corpus figure, or return assumption; those come from "
            "the calculator. Only use a fund if its category in the retrieved text fits its role. "
            "State what must be independently verified. Keep the answer under 250 words."
        ),
        expected_output=(
            "Up to three source-grounded named fund candidates (under 250 words), each with "
            "category, rationale, and evidence limits, and no SIP amounts."
        ),
        agent=reasoner,
        context=[task1],
        callback=_pause_between_tasks,
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
            "State clearly that 12% is an assumption and returns are not guaranteed. "
            "Keep the answer under 200 words."
        ),
        expected_output=(
            "Short SIP assumptions and projection (under 200 words) with monthly contribution "
            "and allocation breakdown."
        ),
        agent=calculator,
        callback=_pause_between_tasks,
    )

    task4 = Task(
        description=(
            f"Write the guidance section of an investment plan for this goal: {user_goal}. "
            "The user's screen already shows all rupee amounts, the SIP tables and the allocation, "
            "so do NOT restate amounts or projections. Use these exact headings:\n"
            "1. Why this plan fits you — 3 short bullets tying the horizon, risk appetite and allocation together\n"
            "2. How to choose funds — 3 short bullets (category fit, expense ratio, consistency over 5+ years); "
            "name only funds that appear in the analyst output\n"
            "3. Risks to watch — 3 short bullets (market falls, return assumption too high, stopping SIPs early)\n"
            "4. First 30 days — 4 numbered steps (complete KYC, pick direct plans, set up SIP mandates, set a yearly review date)\n"
            "5. Yearly review checklist — 3 short bullets\n"
            "Use plain English. Do not introduce fund names absent from the analyst output. "
            "Label anything about returns as an estimate, not guaranteed. Keep the whole answer under 350 words."
        ),
        expected_output=(
            "Guidance with 5 headed sections, under 350 words, without restating rupee projections."
        ),
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
    ai_report_draft = str(result)
    fund_examples = get_local_fund_examples()
    report = _build_verified_report(
        user_goal=user_goal,
        monthly_budget=float(monthly_budget),
        horizon=horizon,
        risk_profile=risk_result,
        sip=sip_result,
        target_value=target_value,
        required_monthly_sip=required_monthly_sip,
        fund_examples=fund_examples,
    )

    return {
        "report": report,
        "ai_report_draft": ai_report_draft,
        "steps": steps,
        "sip": sip_result,
        "risk": risk_result,
        "target_value": target_value,
        "required_monthly_sip": required_monthly_sip,
        "fund_examples": fund_examples,
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