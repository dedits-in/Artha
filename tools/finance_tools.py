"""Small, deterministic calculations used by Artha's planning workflow."""

from __future__ import annotations

import math


def calculate_sip(monthly_amount: float, annual_return: float, years: int) -> dict:
    """Estimate SIP growth with monthly contributions made at each month-end.

    ``annual_return`` is a percentage (for example, 12 means 12% p.a.).
    """
    monthly_amount = float(monthly_amount)
    annual_return = float(annual_return)
    years = int(years)
    if not math.isfinite(monthly_amount) or monthly_amount < 0:
        raise ValueError("monthly_amount must be a finite non-negative number")
    if not math.isfinite(annual_return) or annual_return <= -100:
        raise ValueError("annual_return must be finite and greater than -100")
    if years <= 0:
        raise ValueError("years must be a positive integer")

    months = years * 12
    monthly_rate = (1 + annual_return / 100) ** (1 / 12) - 1
    maturity = monthly_amount * months if abs(monthly_rate) < 1e-12 else (
        monthly_amount * (((1 + monthly_rate) ** months - 1) / monthly_rate)
    )
    invested = monthly_amount * months
    return {
        "monthly_sip": monthly_amount,
        "annual_return_percent": annual_return,
        "years": years,
        "total_invested": round(invested, 2),
        "maturity_amount": round(maturity, 2),
        "estimated_returns": round(maturity - invested, 2),
    }


def calculate_cagr(initial_value: float, final_value: float, years: int) -> float:
    """Return compound annual growth rate as a percentage."""
    initial_value, final_value, years = float(initial_value), float(final_value), int(years)
    if not math.isfinite(initial_value) or initial_value <= 0:
        raise ValueError("initial_value must be a finite positive number")
    if not math.isfinite(final_value) or final_value < 0:
        raise ValueError("final_value must be a finite non-negative number")
    if years <= 0:
        raise ValueError("years must be a positive integer")
    return round(((final_value / initial_value) ** (1 / years) - 1) * 100, 2)


def monthly_sip_for_goal(target_value: float, annual_return: float, years: int) -> float:
    """Estimate month-end SIP needed to reach a future target (rupees)."""
    target_value, annual_return, years = float(target_value), float(annual_return), int(years)
    if not math.isfinite(target_value) or target_value <= 0:
        raise ValueError("target_value must be a finite positive number")
    if not math.isfinite(annual_return) or annual_return <= -100:
        raise ValueError("annual_return must be finite and greater than -100")
    if years <= 0:
        raise ValueError("years must be a positive integer")
    rate = (1 + annual_return / 100) ** (1 / 12) - 1
    months = years * 12
    factor = months if abs(rate) < 1e-12 else ((1 + rate) ** months - 1) / rate
    return round(target_value / factor, 2)


def risk_score(risk_appetite: str, horizon: int) -> dict:
    """Return a simple illustrative allocation based on appetite and horizon."""
    appetite = str(risk_appetite).strip().lower()
    years = int(horizon)
    if appetite not in {"low", "medium", "high"}:
        raise ValueError("risk_appetite must be Low, Medium, or High")
    if years <= 0:
        raise ValueError("horizon must be a positive integer")
    allocations = {
        "low": (20, 70, 10, "Conservative"),
        "medium": (50, 30, 20, "Moderate"),
        "high": (80, 10, 10, "Aggressive"),
    }
    equity, debt, hybrid, label = allocations[appetite]
    # Short horizons warrant a more defensive mix; longer horizons permit a
    # modest equity tilt while retaining the user's stated risk preference.
    if years < 3:
        shift = min(equity, 20)
        equity -= shift
        debt += shift
    elif years >= 10:
        shift = min(debt, 10)
        equity += shift
        debt -= shift
    note = ("Short horizon — prioritize capital stability" if years < 3 else
            "Long horizon — greater capacity to tolerate market volatility" if years >= 10 else
            "Medium horizon — maintain a balanced allocation")
    return {"equity": equity, "debt": debt, "hybrid": hybrid, "label": label, "note": note}
