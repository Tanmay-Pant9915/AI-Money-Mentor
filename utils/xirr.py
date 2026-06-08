from datetime import datetime
from scipy.optimize import newton


def xnpv(rate: float, cashflows: list[tuple[datetime, float]]) -> float:
    if rate <= -0.9999:
        return float("inf")

    first_date = cashflows[0][0]

    return sum(
        amount / ((1 + rate) ** ((date - first_date).days / 365.0))
        for date, amount in cashflows
    )


def calculate_xirr(cashflows: list[tuple[datetime, float]]) -> float:
    """
    Calculate annualized return (XIRR).

    cashflows example:
    [
        (datetime(2026, 4, 1), -5000),
        (datetime(2026, 5, 1), -2000),
        (datetime(2026, 6, 1), 8500),
    ]

    Raises:
        ValueError: If cashflows are insufficient or the solver cannot converge.
    """
    if not cashflows:
        raise ValueError("No cashflows provided.")

    if len(cashflows) < 2:
        raise ValueError("At least two cashflows are required to calculate XIRR.")

    # Guard: all amounts in the same direction means no solution exists.
    amounts = [cf[1] for cf in cashflows]
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        raise ValueError(
            "Cashflows must have both positive and negative values for XIRR to be solvable."
        )

    # Try several starting points before giving up — improves convergence rate.
    for x0 in (0.1, 0.0, -0.1, 0.5):
        try:
            result = newton(
                lambda r: xnpv(r, cashflows),
                x0=x0,
                maxiter=100,
            )
            if -1 < result < 100:     # Sanity check: rates outside this range are bogus.
                return result
        except (RuntimeError, FloatingPointError, ZeroDivisionError):
            continue

    raise ValueError(
        "XIRR calculation did not converge. "
        "The fund may have insufficient or inconsistent transaction data."
    )
