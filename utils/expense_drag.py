def calculate_expense_drag(
    current_value: float,
    expense_ratio: float,
) -> float:
    """
    Calculate annual expense ratio cost in rupees.

    Returns 0.0 for any invalid / missing inputs instead of crashing
    so the rest of the portfolio row remains usable.
    """
    try:
        if current_value is None or expense_ratio is None:
            return 0.0
        if current_value < 0 or expense_ratio < 0:
            return 0.0
        return current_value * (expense_ratio / 100)
    except (TypeError, ZeroDivisionError):
        return 0.0