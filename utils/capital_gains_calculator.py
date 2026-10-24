"""
utils/capital_gains_calculator.py
Deterministic capital gains tax calculator for mutual funds and equity holdings.
Complies with Finance (No. 2) Act, 2024 (effective from 23 July 2024).
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from data.tax_rules import CapitalGainsRules, get_tax_rules


@dataclass
class CapitalGainsTxnResult:
    """Result of capital gain calculation on a single transaction or holding."""
    asset_name: str
    asset_category: str           # "EQUITY", "DEBT", or "OTHER"
    purchase_date: Optional[date]
    sale_date: Optional[date]
    holding_period_days: int
    holding_period_months: float
    gain_type: str                # "LTCG", "STCG", or "LOSS"
    cost_basis: float
    sale_proceeds: float
    net_capital_gain: float
    exemption_applied: float
    taxable_gain: float
    tax_rate_pct: float
    base_tax: float
    cess: float
    total_tax: float
    note: str


def classify_fund_asset_type(scheme_name: str) -> str:
    """
    Classify mutual fund scheme into EQUITY, DEBT, or OTHER based on scheme name.
    """
    if not scheme_name:
        return "OTHER"

    name_lower = scheme_name.lower()

    # Debt keywords
    debt_keywords = [
        "liquid", "overnight", "money market", "ultra short", "low duration",
        "short term", "medium duration", "credit risk", "corporate bond",
        "banking & psu", "gilt", "floater", "treasury", "debt"
    ]
    for kw in debt_keywords:
        if kw in name_lower:
            return "DEBT"

    # Equity keywords
    equity_keywords = [
        "equity", "nifty", "sensex", "index", "large cap", "mid cap",
        "small cap", "flexi cap", "multi cap", "focused", "elss",
        "tax saver", "value fund", "contra fund", "growth fund"
    ]
    for kw in equity_keywords:
        if kw in name_lower:
            return "EQUITY"

    # Default to Equity if standard mutual fund growth, else Other
    if "growth" in name_lower or "regular" in name_lower or "direct" in name_lower:
        return "EQUITY"

    return "OTHER"


def calculate_transaction_capital_gain(
    asset_name: str,
    asset_category: str,         # "EQUITY", "DEBT", or "OTHER"
    purchase_date: date,
    sale_date: date,
    cost_basis: float,
    sale_proceeds: float,
    financial_year: str = "2024-25",
    available_ltcg_exemption: float = 125000.0,
    slab_rate: float = 0.30,     # Applicable for debt funds taxed at slab rate
) -> CapitalGainsTxnResult:
    """
    Compute capital gains, holding period, and tax for a transaction under Finance Act 2024.
    """
    rules: CapitalGainsRules = get_tax_rules(financial_year)["capital_gains"]

    if sale_date < purchase_date:
        raise ValueError("Sale date cannot be earlier than purchase date.")

    days = (sale_date - purchase_date).days
    months = days / 30.4375

    raw_gain = sale_proceeds - cost_basis

    if raw_gain <= 0:
        return CapitalGainsTxnResult(
            asset_name=asset_name,
            asset_category=asset_category,
            purchase_date=purchase_date,
            sale_date=sale_date,
            holding_period_days=days,
            holding_period_months=round(months, 1),
            gain_type="LOSS",
            cost_basis=cost_basis,
            sale_proceeds=sale_proceeds,
            net_capital_gain=raw_gain,
            exemption_applied=0.0,
            taxable_gain=0.0,
            tax_rate_pct=0.0,
            base_tax=0.0,
            cess=0.0,
            total_tax=0.0,
            note="Capital loss. Can be carried forward or set off against eligible capital gains as per Section 70/71.",
        )

    cat_upper = asset_category.upper()
    exemption_applied = 0.0

    if cat_upper == "EQUITY":
        # Holding period threshold: 12 months (365 days)
        is_long_term = days > 365
        if is_long_term:
            gain_type = "LTCG"
            tax_rate = rules.equity_ltcg_rate  # 12.5%
            # Apply annual exemption (₹1,25,000)
            exemption_applied = min(raw_gain, max(0.0, available_ltcg_exemption))
            taxable_gain = max(0.0, raw_gain - exemption_applied)
            note = (
                f"Long-term equity gain (> 12 months). Taxed @ 12.5% under Section 112A. "
                f"Exemption of ₹{exemption_applied:,.0f} applied."
            )
        else:
            gain_type = "STCG"
            tax_rate = rules.equity_stcg_rate  # 20.0%
            taxable_gain = raw_gain
            note = "Short-term equity gain (<= 12 months). Taxed @ 20% under Section 111A. No exemption applies."

    elif cat_upper == "DEBT":
        # Specified Debt Mutual Funds (Sec 50AA): Always STCG at slab rates
        gain_type = "STCG"
        tax_rate = slab_rate
        taxable_gain = raw_gain
        note = (
            "Specified debt mutual fund acquired on/after 1 Apr 2023. Treated as short-term capital gain "
            f"under Section 50AA and taxed at marginal slab rate ({tax_rate * 100:.1f}%)."
        )

    else:
        # Other funds / unlisted / gold / international: 24 months threshold
        is_long_term = days > 730
        if is_long_term:
            gain_type = "LTCG"
            tax_rate = rules.other_funds_ltcg_rate  # 12.5% without indexation
            taxable_gain = raw_gain
            note = "Long-term non-equity gain (> 24 months). Taxed @ 12.5% under Section 112 without indexation."
        else:
            gain_type = "STCG"
            tax_rate = slab_rate
            taxable_gain = raw_gain
            note = f"Short-term non-equity gain (<= 24 months). Taxed at marginal slab rate ({tax_rate * 100:.1f}%)."

    base_tax = taxable_gain * tax_rate
    cess = base_tax * rules.cess_rate
    total_tax = round(base_tax + cess, 2)

    return CapitalGainsTxnResult(
        asset_name=asset_name,
        asset_category=cat_upper,
        purchase_date=purchase_date,
        sale_date=sale_date,
        holding_period_days=days,
        holding_period_months=round(months, 1),
        gain_type=gain_type,
        cost_basis=cost_basis,
        sale_proceeds=sale_proceeds,
        net_capital_gain=raw_gain,
        exemption_applied=exemption_applied,
        taxable_gain=taxable_gain,
        tax_rate_pct=tax_rate * 100.0,
        base_tax=base_tax,
        cess=cess,
        total_tax=total_tax,
        note=note,
    )


def analyze_cas_holdings_capital_gains(
    funds_df: Any,
    financial_year: str = "2024-25",
    current_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Analyze mutual fund portfolio holdings from parsed CAMS CAS DataFrame for capital gains.
    Evaluates unrealized gains, holding period profile, potential tax liability, and LTCG exemption utilization.
    """
    if current_date is None:
        current_date = date.today()

    if funds_df is None or getattr(funds_df, "empty", True):
        return {
            "has_data": False,
            "message": "No CAMS CAS mutual fund portfolio holdings available. Upload a CAS PDF to view automated capital gains analysis.",
            "total_portfolio_value": 0.0,
            "total_invested_amount": 0.0,
            "total_unrealized_gain": 0.0,
            "holdings": [],
            "ltcg_potential_gain": 0.0,
            "stcg_potential_gain": 0.0,
            "estimated_tax_if_redeemed_today": 0.0,
            "disclaimers": [
                "CAMS CAS PDF provides current valuation and purchase cash flows.",
                "Actual realized capital gains depend on exact sale dates and redemption orders.",
                "Form 26AS/AIS and broker Tax P&L statements should be referenced for filing official ITR.",
            ]
        }

    holdings_list: List[Dict[str, Any]] = []
    total_val = 0.0
    total_inv = 0.0
    total_ltcg_equity_gains = 0.0
    total_stcg_equity_gains = 0.0
    total_debt_gains = 0.0

    rules = get_tax_rules(financial_year)["capital_gains"]

    for _, row in funds_df.iterrows():
        scheme = str(row.get("scheme", "Unknown Scheme"))
        val = float(row.get("current_value", 0.0) or 0.0)
        units = float(row.get("units", 0.0) or 0.0)
        nav = float(row.get("nav", 0.0) or 0.0)
        txns = row.get("transactions", [])

        # Calculate invested amount from transactions
        inv_amt = 0.0
        oldest_date: Optional[date] = None
        newest_date: Optional[date] = None

        if isinstance(txns, list) and txns:
            for t in txns:
                amt = float(t.get("amount", 0.0) or 0.0)
                inv_amt += amt
                t_date = t.get("date")
                if isinstance(t_date, (datetime, date)):
                    d = t_date.date() if isinstance(t_date, datetime) else t_date
                    if oldest_date is None or d < oldest_date:
                        oldest_date = d
                    if newest_date is None or d > newest_date:
                        newest_date = d
        else:
            # Fallback if no transactions recorded
            inv_amt = val

        gain = val - inv_amt
        cat = classify_fund_asset_type(scheme)

        # Holding duration based on oldest purchase
        days_held = (current_date - oldest_date).days if oldest_date else 366
        is_long_term = days_held > 365

        if cat == "EQUITY":
            if is_long_term:
                total_ltcg_equity_gains += max(0.0, gain)
                period_label = "Long Term (> 12m)"
            else:
                total_stcg_equity_gains += max(0.0, gain)
                period_label = "Short Term (<= 12m)"
        elif cat == "DEBT":
            total_debt_gains += max(0.0, gain)
            period_label = "Taxed at Slab Rates"
        else:
            period_label = "Other Non-Equity"

        total_val += val
        total_inv += inv_amt

        holdings_list.append({
            "scheme": scheme,
            "category": cat,
            "current_value": val,
            "invested_amount": inv_amt,
            "unrealized_gain": gain,
            "units": units,
            "nav": nav,
            "oldest_purchase_date": oldest_date.strftime("%d-%b-%Y") if oldest_date else "N/A",
            "holding_period_label": period_label,
            "is_long_term": is_long_term,
        })

    # Calculate estimated potential tax if redeemed today
    # LTCG on equity gets ₹1,25,000 exemption
    exemption_used = min(total_ltcg_equity_gains, rules.equity_ltcg_exemption)
    taxable_ltcg = max(0.0, total_ltcg_equity_gains - exemption_used)
    tax_ltcg = taxable_ltcg * rules.equity_ltcg_rate * (1 + rules.cess_rate)

    tax_stcg = total_stcg_equity_gains * rules.equity_stcg_rate * (1 + rules.cess_rate)
    tax_debt = total_debt_gains * 0.30 * (1 + rules.cess_rate)  # Indicative 30% slab rate

    total_est_tax = round(tax_ltcg + tax_stcg + tax_debt, 2)

    return {
        "has_data": True,
        "total_portfolio_value": total_val,
        "total_invested_amount": total_inv,
        "total_unrealized_gain": total_val - total_inv,
        "total_ltcg_equity_gains": total_ltcg_equity_gains,
        "total_stcg_equity_gains": total_stcg_equity_gains,
        "total_debt_gains": total_debt_gains,
        "equity_ltcg_exemption_limit": rules.equity_ltcg_exemption,
        "exemption_used": exemption_used,
        "exemption_remaining": max(0.0, rules.equity_ltcg_exemption - exemption_used),
        "taxable_ltcg_equity": taxable_ltcg,
        "estimated_tax_if_redeemed_today": total_est_tax,
        "holdings": holdings_list,
        "disclaimers": [
            "CAMS CAS statement provides portfolio holdings and transaction amounts.",
            "Finance Act 2024: Equity STCG taxed @ 20%, LTCG @ 12.5% above ₹1,25,000 annual exemption.",
            "Debt funds purchased after 1 April 2023 taxed at individual slab rates.",
            "Redemptions, grandfathering, and tax-loss harvesting should be verified with broker Capital Gains statements for official ITR filing.",
        ]
    }
