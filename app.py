"""Streamlit interface for Artha's investment-planning workflow."""

from __future__ import annotations

import csv
import io
import re

import streamlit as st

from crew import run_artha_details
from rag.fund_candidates import get_local_fund_examples
from rag.fund_cards import load_fund_cards
from tools.finance_tools import calculate_sip, calculate_sip_projection, monthly_sip_for_goal


def rupees(value: float) -> str:
    number = str(int(round(abs(float(value)))))
    if len(number) > 3:
        tail, head = number[-3:], number[:-3]
        pairs = []
        while head:
            pairs.insert(0, head[-2:])
            head = head[:-2]
        number = ",".join(pairs + [tail])
    return f"{'-' if value < 0 else ''}₹{number}"


def years_text(months: int) -> str:
    years, rem = divmod(months, 12)
    return f"{years} years" + (f" {rem} months" if rem else "")


def years_in_goal(text: str) -> int | None:
    match = re.search(r"(\d+)\s*(?:years?|yrs?)\b", text.lower())
    return int(match.group(1)) if match else None


def gap_options(target: float, budget: float, horizon: int, step_up: int) -> list[dict]:
    """Different ways to reach the target, all from deterministic calculations."""
    rows = [{
        "Option": f"Flat SIP for {horizon} years",
        "What it takes": f"{rupees(monthly_sip_for_goal(target, 12.0, horizon))}/month",
    }]
    if step_up > 0:
        per_rupee = calculate_sip_projection(1000, horizon, 12, step_up)["maturity_amount"] / 1000
        rows.append({
            "Option": f"Raise SIP {step_up}% every year for {horizon} years",
            "What it takes": f"Start at {rupees(target / per_rupee)}/month",
        })
    for extra in (5, 10):
        longer = horizon + extra
        if longer <= 40:
            rows.append({
                "Option": f"Flat SIP for {longer} years",
                "What it takes": f"{rupees(monthly_sip_for_goal(target, 12.0, longer))}/month",
            })
    if budget > 0:
        months = calculate_sip_projection(budget, 40, 12, 0, target)["months_to_target"]
        rows.append({
            "Option": f"Keep {rupees(budget)}/month flat",
            "What it takes": f"About {years_text(months)}" if months else "More than 40 years",
        })
    return rows


def return_sensitivity(target: float, budget: float, horizon: int) -> list[dict]:
    """How the answer changes if returns are lower or higher than 12%."""
    return [
        {
            "Assumed annual return": f"{rate}%",
            "Projected at your budget": rupees(calculate_sip(budget, rate, horizon)["maturity_amount"]),
            "SIP needed for the goal": f"{rupees(monthly_sip_for_goal(target, rate, horizon))}/month",
        }
        for rate in (8, 10, 12)
    ]


def monthly_split(profile: dict, budget: float, needed: float | None) -> list[dict]:
    rows = []
    for bucket, key in (("Equity", "equity"), ("Debt", "debt"), ("Hybrid", "hybrid")):
        pct = profile[key]
        row = {"Bucket": bucket, "Share": f"{pct}%", "At your budget": rupees(budget * pct / 100)}
        if needed:
            row["At the SIP needed"] = rupees(needed * pct / 100)
        rows.append(row)
    return rows


st.set_page_config(page_title="Artha", page_icon="₹", layout="wide")
st.title("Artha — Your AI Investment Research Agent")
st.write("Explore an illustrative investment plan informed by your goal, time horizon, and risk preference.")

with st.sidebar:
    st.header("Your inputs")
    monthly_budget = st.number_input("Monthly investment budget (₹)", min_value=0, value=10000, step=500)
    horizon = st.slider("Investment horizon (years)", min_value=1, max_value=30, value=10)
    risk_appetite = st.radio("Risk appetite", ["Low", "Medium", "High"], index=1)
    annual_step_up = st.number_input("Increase SIP each year (%)", min_value=0, max_value=50, value=10, step=1)
    st.caption("Headline projections assume a 12% annual return. Actual returns vary and are not guaranteed.")

user_goal = st.text_input(
    "What are you planning for?",
    placeholder="For example, save ₹50 lakh in 10 years for retirement",
)
if st.button("Generate My Investment Plan", type="primary", use_container_width=True):
    if not user_goal.strip():
        st.warning("Enter a financial goal to generate a plan.")
    else:
        with st.spinner("Researching your goal and preparing a plan… (this can take 2-3 minutes)"):
            try:
                result = run_artha_details(user_goal, monthly_budget, horizon, risk_appetite)
                st.session_state["artha_result"] = result
                st.session_state["artha_inputs"] = {
                    "goal": user_goal.strip(), "budget": monthly_budget,
                    "horizon": horizon, "risk": risk_appetite, "step_up": annual_step_up,
                }
            except Exception as exc:
                st.error(f"Artha could not complete the plan: {exc}")

inputs = st.session_state.get("artha_inputs", {})
current = {
    "goal": user_goal.strip(), "budget": monthly_budget,
    "horizon": horizon, "risk": risk_appetite, "step_up": annual_step_up,
}
result = st.session_state.get("artha_result") if inputs == current else None
if inputs and not result:
    st.info("Your inputs changed. Generate the plan again to refresh the results.")

if result:
    target = result["target_value"]
    sip = result["sip"]
    profile = result["risk"]
    needed = result["required_monthly_sip"]

    # ---------- 1. Goal and numbers ----------
    st.subheader("Your investment plan")
    st.markdown(f"**Goal:** {user_goal.strip()}")
    mentioned = years_in_goal(user_goal)
    if mentioned and mentioned != horizon:
        st.warning(
            f"Your goal mentions {mentioned} years, but the horizon slider is set to {horizon}. "
            f"This plan uses {horizon} years. Change the slider and generate again if that's not what you meant."
        )
    st.caption(
        f"Investing {rupees(monthly_budget)}/month for {horizon} years contributes {rupees(sip['total_invested'])}. "
        f"At an assumed 12% return it grows to about {rupees(sip['maturity_amount'])}. Not guaranteed."
    )

    if target:
        shortfall = max(0, target - sip["maturity_amount"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Goal target", rupees(target))
        c2.metric("Projected at your budget", rupees(sip["maturity_amount"]))
        c3.metric("SIP needed (flat)", f"{rupees(needed)}/month")
        if shortfall:
            st.warning(f"At {rupees(monthly_budget)}/month you would fall about {rupees(shortfall)} short of the goal.")
            st.markdown("### Ways to close the gap")
            st.dataframe(gap_options(target, monthly_budget, horizon, annual_step_up),
                         hide_index=True, use_container_width=True)
        else:
            st.success("Your budget reaches the goal under the 12% assumption; actual returns may differ.")

        st.markdown("### How the answer changes with returns")
        st.caption("A mix that includes debt usually earns less than an all-equity return, so 10% is a more "
                   "cautious base case than 12%.")
        st.dataframe(return_sensitivity(target, monthly_budget, horizon),
                     hide_index=True, use_container_width=True)
    else:
        st.info("No target amount detected. Include an amount such as '50 lakh' or '2 crore' to see goal feasibility.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total invested", rupees(sip["total_invested"]))
        c2.metric("Estimated value", rupees(sip["maturity_amount"]))
        c3.metric("Estimated growth", rupees(sip["estimated_returns"]))

    # ---------- 2. Growth chart ----------
    fixed_8 = calculate_sip_projection(monthly_budget, horizon, 8, 0, target)
    fixed_12 = calculate_sip_projection(monthly_budget, horizon, 12, 0, target)
    stepped_12 = calculate_sip_projection(monthly_budget, horizon, 12, annual_step_up, target)
    series = [
        ("8% return · fixed SIP", fixed_8),
        ("12% return · fixed SIP", fixed_12),
        (f"12% return · {annual_step_up}% yearly increase", stepped_12),
    ]
    chart_rows = []
    for year_index in range(horizon + 1):
        point = {"Year": year_index}
        for label, projection in series:
            point[label] = projection["schedule"][year_index]["projected_corpus"]
        if target:
            point["Goal target"] = target
        chart_rows.append(point)

    st.markdown("### Corpus growth scenarios")
    st.caption("Illustrations only: smooth return assumptions; actual returns will vary and may be negative.")
    chart_columns = [label for label, _ in series] + (["Goal target"] if target else [])
    st.line_chart(chart_rows, x="Year", y=chart_columns, y_label="Estimated corpus (₹)")

    timing = None
    months = stepped_12["months_to_target"]
    if target:
        if months:
            timing = years_text(months)
            st.success(f"With a {annual_step_up}% yearly SIP increase, the projection reaches the target in about {timing}.")
        else:
            st.info(f"With a {annual_step_up}% yearly SIP increase, the target is not reached within {horizon} years.")

    with st.expander("Year-by-year SIP and corpus estimate"):
        st.caption(f"The monthly SIP rises {annual_step_up}% after every 12 contributions.")
        table = [
            {
                "Year": row["year"],
                "Monthly SIP in that year": rupees(row["monthly_sip"]),
                "Total contributed to date": rupees(row["total_invested"]),
                "Projected corpus (12%)": rupees(row["projected_corpus"]),
            }
            for row in stepped_12["schedule"][1:]
        ]
        st.dataframe(table, hide_index=True, use_container_width=True)

    # ---------- 3. Where to invest ----------
    st.markdown("### Where to invest")
    st.write(
        f"**{profile['label']} profile:** Equity {profile['equity']}% · Debt {profile['debt']}% · "
        f"Hybrid {profile['hybrid']}%. {profile['note']}."
    )
    st.markdown("**Monthly split**")
    st.dataframe(monthly_split(profile, monthly_budget, needed), hide_index=True, use_container_width=True)

    st.markdown("**Funds from your data**")
    st.caption("Details are read from the fund files in your data folder. Research leads only, not personal advice. "
               "Verify scheme details, fees and risk from official documents. Return figures may be cumulative, "
               "not annual.")
    cards = load_fund_cards()
    fund_examples = get_local_fund_examples()
    for tab, bucket in zip(st.tabs(["Equity", "Debt", "Hybrid"]), ("Equity", "Debt", "Hybrid")):
        with tab:
            if cards.get(bucket):
                st.dataframe(cards[bucket], hide_index=True, use_container_width=True)
            else:
                names = fund_examples[bucket][:3]
                st.markdown("\n".join(f"- {name}" for name in names) if names else "No funds found for this bucket.")

    # ---------- 4. AI-written guidance ----------
    st.markdown("### AI-written guidance")
    st.caption("Written by the AI agents from your fund data. Amounts and allocation above come from local "
               "calculations; check any figure here against them.")
    st.markdown(result.get("ai_report_draft") or "The reporter did not return a report.")

    # ---------- 5. Agent steps ----------
    with st.expander("Agent reasoning steps"):
        labels = ["Retrieved source context", "Analyst output", "Calculator agent output", "Report writer draft"]
        for index, step in enumerate(result["steps"]):
            label = labels[index] if index < len(labels) else f"Agent output {index + 1}"
            st.markdown(f"**{label}**")
            st.markdown(step)
            st.divider()

    # ---------- 6. Downloads ----------
    fund_markdown = "\n".join(
        f"- **{bucket}:** " + (", ".join(r["Fund"] for r in cards.get(bucket, [])[:3]) or "None found in data")
        for bucket in ("Equity", "Debt", "Hybrid")
    )
    report_text = f"""# Artha investment plan

## Goal and inputs
- Goal: {user_goal.strip()}
- Monthly budget: {rupees(monthly_budget)}
- Horizon: {horizon} years
- Risk appetite: {risk_appetite}
- Return assumption: 12% per year (illustrative, not guaranteed)
- Annual SIP step-up: {annual_step_up}%

## Current-budget projection
- Total contributed: {rupees(sip['total_invested'])}
- Projected corpus: {rupees(sip['maturity_amount'])}
- Estimated growth: {rupees(sip['estimated_returns'])}
- Goal target: {rupees(target) if target else 'Not detected'}
- Flat SIP needed: {rupees(needed) if needed else 'Not calculated'}

## Annual step-up scenario
- Projected corpus after {horizon} years: {rupees(stepped_12['maturity_amount'])}
- Total contributions: {rupees(stepped_12['total_invested'])}
- Time to target: {timing or 'Not reached within horizon or no target detected'}

## Illustrative allocation
- Equity: {profile['equity']}%
- Debt: {profile['debt']}%
- Hybrid: {profile['hybrid']}%

## Funds to research
{fund_markdown}

## AI-written guidance
{result.get('ai_report_draft') or ''}

These are research leads, not verified recommendations. Mutual fund returns are not guaranteed. Verify current official scheme documents before investing.
"""
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=["year", "monthly_sip", "total_invested", "projected_corpus"])
    writer.writeheader()
    writer.writerows(row for row in stepped_12["schedule"] if row["year"] > 0)
    d1, d2 = st.columns(2)
    d1.download_button("Download report (Markdown)", report_text, file_name="artha_investment_plan.md",
                       mime="text/markdown", use_container_width=True)
    d2.download_button("Download projection (CSV)", csv_buffer.getvalue(), file_name="artha_sip_projection.csv",
                       mime="text/csv", use_container_width=True)

st.caption("Educational planning estimates only; this is not personalized financial advice. "
           "Mutual fund investments are subject to market risk.")