"""Streamlit interface for Artha's investment-planning workflow."""

from __future__ import annotations

import streamlit as st

from crew import run_artha_details
from tools.finance_tools import calculate_sip, risk_score


def rupees(value: float) -> str:
    return f"₹{value:,.0f}"


st.set_page_config(page_title="Artha", page_icon="₹", layout="wide")
st.title("Artha — Your AI Investment Research Agent")
st.write("Explore an illustrative investment plan informed by your goal, time horizon, and risk preference.")

with st.sidebar:
    st.header("Your inputs")
    monthly_budget = st.number_input("Monthly investment budget (₹)", min_value=0, value=10000, step=500)
    horizon = st.slider("Investment horizon (years)", min_value=1, max_value=30, value=10)
    risk_appetite = st.radio("Risk appetite", ["Low", "Medium", "High"], index=1)
    st.divider()
    st.subheader("Illustrative SIP estimate")
    sip = calculate_sip(monthly_budget, 12.0, horizon)
    st.caption("Assumes a 12% annual return. Actual returns vary and are not guaranteed.")
    st.metric("Total invested", rupees(sip["total_invested"]))
    st.metric("Estimated value", rupees(sip["maturity_amount"]))
    st.metric("Estimated growth", rupees(sip["estimated_returns"]))
    allocation = risk_score(risk_appetite, horizon)
    st.subheader(f"{allocation['label']} profile")
    st.write(f"Equity {allocation['equity']}% · Debt {allocation['debt']}% · Hybrid {allocation['hybrid']}%")
    st.caption(allocation["note"])

user_goal = st.text_input(
    "What are you planning for?",
    placeholder="For example, save ₹50 lakh in 10 years for retirement",
)
if st.button("Generate My Investment Plan", type="primary", use_container_width=True):
    if not user_goal.strip():
        st.warning("Enter a financial goal to generate a plan.")
    else:
        with st.spinner("Researching your goal and preparing a plan…"):
            try:
                result = run_artha_details(user_goal, monthly_budget, horizon, risk_appetite)
                st.session_state["artha_result"] = result
                st.session_state["artha_inputs"] = {
                    "goal": user_goal.strip(), "budget": monthly_budget,
                    "horizon": horizon, "risk": risk_appetite,
                }
            except Exception as exc:
                st.error(f"Artha could not complete the plan: {exc}")

inputs = st.session_state.get("artha_inputs", {})
current = {
    "goal": user_goal.strip(), "budget": monthly_budget,
    "horizon": horizon, "risk": risk_appetite,
}
result = st.session_state.get("artha_result") if inputs == current else None
if inputs and not result:
    st.info("Your inputs changed. Generate the plan again to refresh the results.")

if result:
    st.subheader("Your investment plan")
    st.markdown(f"**Goal:** {user_goal.strip()}")
    st.caption("Planning figures below are deterministic calculations. Agent-written observations are available separately for review.")

    if result["target_value"]:
        target = result["target_value"]
        projected = result["sip"]["maturity_amount"]
        shortfall = max(0, target - projected)
        c1, c2, c3 = st.columns(3)
        c1.metric("Goal target", rupees(target))
        c2.metric("Projected at current budget", rupees(projected))
        c3.metric("Estimated SIP needed", f"{rupees(result['required_monthly_sip'])}/month")
        if shortfall:
            st.warning(
                f"At {rupees(monthly_budget)}/month, the estimate is {rupees(shortfall)} below your goal. "
                f"The estimated monthly shortfall is {rupees(max(0, result['required_monthly_sip'] - monthly_budget))}. "
                "This uses an assumed 12% annual return and is not guaranteed."
            )
        else:
            st.success("The projection reaches the goal under the illustrative return assumption; actual returns may differ.")
    else:
        st.info("No target amount was detected. Include an amount such as ‘50 lakh’ or ‘2 crore’ to see goal feasibility figures.")

    st.markdown("### SIP projection")
    st.write(
        f"Investing {rupees(result['sip']['monthly_sip'])} each month for {horizon} years would contribute "
        f"{rupees(result['sip']['total_invested'])}. At the illustrative 12% annual return assumption, "
        f"the estimated value is {rupees(result['sip']['maturity_amount'])}, including estimated growth of "
        f"{rupees(result['sip']['estimated_returns'])}."
    )

    profile = result["risk"]
    st.markdown("### Risk profile and allocation")
    st.write(
        f"**{profile['label']}:** Equity {profile['equity']}%, debt {profile['debt']}%, "
        f"hybrid {profile['hybrid']}%. {profile['note']}. These are illustrative asset buckets, "
        "not specific fund selections."
    )

    st.markdown("### AI-generated investment report")
    st.caption("The report uses retrieved local data. The deterministic SIP and allocation figures above are authoritative if any AI-written number differs.")
    st.markdown(result["report"] or "The reporter did not return a report.")

    st.markdown("### Fund research and candidates")
    st.caption("AI analysis based on retrieved local data. Treat named schemes as candidates for further research, not personalized recommendations.")
    if len(result["steps"]) > 1 and result["steps"][1].strip():
        st.markdown(result["steps"][1])
    else:
        st.info("The analyst did not return a fund analysis. Check the agent output and RAG retrieval below.")

    st.markdown("### Agent reasoning steps")
    labels = ["Retrieved source context", "Full analyst output", "Calculator agent output", "Report writer draft"]
    for index, step in enumerate(result["steps"]):
        label = labels[index] if index < len(labels) else f"Agent output {index + 1}"
        with st.expander(label):
            st.markdown(step)
    st.caption("The SIP projection and portfolio allocation above come from local calculations. Verify scheme details and current documents before investing.")

    with st.expander("About the fund data used"):
        st.write(
            "The local NAVAll.csv is a dated AMFI NAV snapshot. It contains scheme identifiers, scheme names, "
            "plan/option labels, NAV values, and dates. The separate fund_knowledge.txt is locally supplied guidance; "
            "its return ranges and fund examples have not been independently verified. Neither source alone is enough "
            "to assess current risk, fees, holdings, benchmark performance, or suitability."
        )

st.caption("Educational planning estimates only; this is not personalized financial advice. Mutual fund investments are subject to market risk.")
