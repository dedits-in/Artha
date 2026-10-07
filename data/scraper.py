"""
Artha Data Scraper
Scrapes mutual fund data from free public sources for RAG ingestion.
Sources: mfapi.in, AMFI India
"""

import requests
import json
import os
import time
import csv

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(OUTPUT_PATH, exist_ok=True)

# ── 1. Fund list from mfapi.in ─────────────────────────────────────────────

FUND_CODES = {
    # Large Cap
    "mirae_large_cap":          "120503",
    "hdfc_top_100":             "119598",
    "icici_bluechip":           "120586",
    "sbi_bluechip":             "119224",
    "axis_bluechip":            "125354",

    # Mid Cap
    "hdfc_midcap_opp":          "118701",
    "kotak_emerging_equity":    "131768",
    "axis_midcap":              "125497",
    "nippon_midcap":            "118778",

    # Small Cap
    "sbi_small_cap":            "125494",
    "nippon_small_cap":         "118778",
    "quant_small_cap":          "120828",

    # Flexi Cap
    "parag_parikh_flexi":       "122639",
    "hdfc_flexi_cap":           "118701",
    "quant_flexi_cap":          "120828",

    # ELSS
    "axis_elss":                "125354",
    "mirae_elss":               "120503",
    "quant_elss":               "120828",

    # Hybrid
    "icici_balanced_advantage": "120586",
    "hdfc_balanced_advantage":  "119598",

    # Debt
    "hdfc_short_term_debt":     "119598",
    "icici_corporate_bond":     "120586",
}


def fetch_fund_data(name, code):
    url = f"https://api.mfapi.in/mf/{code}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data
    except Exception as e:
        print(f"  Failed {name}: {e}")
        return None


def compute_returns(nav_data):
    """Compute approximate 1Y and 3Y returns from NAV history."""
    try:
        latest = float(nav_data[0]["nav"])
        returns = {}
        for label, days in [("1Y", 365), ("3Y", 1095)]:
            if len(nav_data) > days:
                past = float(nav_data[days]["nav"])
                pct = ((latest - past) / past) * 100
                returns[label] = round(pct, 2)
            else:
                returns[label] = "N/A"
        return returns
    except Exception:
        return {"1Y": "N/A", "3Y": "N/A"}


def save_as_text(name, meta, nav_data, returns):
    """Save fund data as readable text for RAG ingestion."""
    recent_navs = nav_data[:10]
    content = f"""
MUTUAL FUND PROFILE
===================
Fund Name      : {meta.get('scheme_name', name)}
Fund House     : {meta.get('fund_house', 'N/A')}
Scheme Type    : {meta.get('scheme_type', 'N/A')}
Scheme Category: {meta.get('scheme_category', 'N/A')}
Scheme Code    : {meta.get('scheme_code', 'N/A')}

PERFORMANCE
-----------
1 Year Return  : {returns.get('1Y', 'N/A')}%
3 Year Return  : {returns.get('3Y', 'N/A')}%
Latest NAV     : ₹{nav_data[0]['nav'] if nav_data else 'N/A'} (as of {nav_data[0]['date'] if nav_data else 'N/A'})

RECENT NAV HISTORY
------------------
"""
    for entry in recent_navs:
        content += f"  {entry['date']}  →  ₹{entry['nav']}\n"

    filepath = os.path.join(OUTPUT_PATH, f"{name}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Saved {name}.txt")


def scrape_all_funds():
    print("\n=== Scraping mutual fund data from mfapi.in ===\n")
    success = 0
    for name, code in FUND_CODES.items():
        print(f"Fetching {name} (code: {code})...")
        data = fetch_fund_data(name, code)
        if data:
            meta = data.get("meta", {})
            nav_data = data.get("data", [])
            returns = compute_returns(nav_data)
            save_as_text(name, meta, nav_data, returns)
            success += 1
        time.sleep(0.5)  # be polite to the API
    print(f"\nDone. {success}/{len(FUND_CODES)} funds scraped.")


# ── 2. AMFI category-level data ────────────────────────────────────────────

CATEGORY_KNOWLEDGE = """
MUTUAL FUND CATEGORY GUIDE - INDIA
====================================

LARGE CAP FUNDS
---------------
Definition: Invest minimum 80% in top 100 companies by market capitalisation.
Risk Level: Moderate
Ideal Horizon: 3-5 years
Expected Returns: 10-12% CAGR (long term)
Best For: Conservative equity investors, first-time investors
Top Funds: Mirae Asset Large Cap, HDFC Top 100, ICICI Prudential Bluechip, Axis Bluechip
SEBI Category: Large Cap Fund

MID CAP FUNDS
-------------
Definition: Invest minimum 65% in companies ranked 101-250 by market cap.
Risk Level: High
Ideal Horizon: 5-7 years
Expected Returns: 12-15% CAGR (long term)
Best For: Investors with moderate-high risk appetite
Top Funds: HDFC Mid-Cap Opportunities, Kotak Emerging Equity, Axis Midcap
SEBI Category: Mid Cap Fund

SMALL CAP FUNDS
---------------
Definition: Invest minimum 65% in companies ranked below 250 by market cap.
Risk Level: Very High
Ideal Horizon: 7+ years
Expected Returns: 15-18% CAGR (long term, high volatility)
Best For: Aggressive investors with long horizon
Top Funds: SBI Small Cap, Nippon India Small Cap, Quant Small Cap
SEBI Category: Small Cap Fund

FLEXI CAP FUNDS
---------------
Definition: Can invest across large, mid and small cap without restriction.
Risk Level: Moderate to High
Ideal Horizon: 5+ years
Expected Returns: 12-15% CAGR
Best For: Investors wanting diversification across market caps
Top Funds: Parag Parikh Flexi Cap, HDFC Flexi Cap, Quant Flexi Cap
SEBI Category: Flexi Cap Fund

ELSS - TAX SAVING FUNDS
------------------------
Definition: Equity Linked Savings Scheme with 3-year lock-in period.
Risk Level: High
Lock-in Period: 3 years (mandatory)
Tax Benefit: Up to ₹1.5 lakh deduction under Section 80C
Expected Returns: 12-14% CAGR
Best For: Investors seeking tax saving under Section 80C + wealth creation
Top Funds: Axis ELSS, Mirae Asset ELSS, Quant ELSS
SEBI Category: ELSS

HYBRID - BALANCED ADVANTAGE FUNDS
----------------------------------
Definition: Dynamically manages equity-debt allocation based on market valuations.
Risk Level: Moderate
Ideal Horizon: 3-5 years
Expected Returns: 9-11% CAGR
Best For: First-time investors, moderate risk appetite, medium-term goals
Top Funds: ICICI Prudential Balanced Advantage, HDFC Balanced Advantage
SEBI Category: Dynamic Asset Allocation

DEBT FUNDS - SHORT DURATION
-----------------------------
Definition: Invest in bonds and fixed income securities with 1-3 year maturity.
Risk Level: Low
Ideal Horizon: 1-3 years
Expected Returns: 6-8% CAGR
Best For: Capital preservation, short-term goals, emergency corpus
Top Funds: HDFC Short Term Debt, ICICI Prudential Corporate Bond
SEBI Category: Short Duration Fund

GOAL-BASED RECOMMENDATIONS
===========================
Car Purchase (3-5 years)    → Hybrid Balanced Advantage + Large Cap (60:40)
Retirement (10+ years)      → Mid Cap + Large Cap + ELSS (40:40:20)
Child Education (10-15 yrs) → Mid Cap + Small Cap + Large Cap (40:30:30)
Tax Saving (any horizon)    → ELSS funds (3-year lock-in)
Emergency Fund              → Liquid funds or short-duration debt funds
House Down Payment (5-7 yr) → Flexi Cap + Hybrid (70:30)
Wedding Fund (3-5 years)    → Large Cap + Hybrid (60:40)

SIP BEST PRACTICES
==================
- Start early — every year of delay costs significant compounding
- Step-up SIP — increase SIP by 10% every year
- Stay invested through market corrections
- Diversify across 3-4 fund categories maximum
- Review portfolio every 6 months, rebalance annually
- Avoid stopping SIP during market downturns — buy more units at lower NAV
"""

def save_category_knowledge():
    filepath = os.path.join(OUTPUT_PATH, "fund_category_guide.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(CATEGORY_KNOWLEDGE)
    print("Saved fund_category_guide.txt")


# ── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    save_category_knowledge()
    scrape_all_funds()
    print("\nAll done. Now run: python rag/ingest.py")