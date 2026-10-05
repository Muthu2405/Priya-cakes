"""Costing logic. All money maths uses Decimal, never float."""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
DEFAULT_PROFIT_RATE = Decimal("0.30")

# unit -> (family, factor to the family's base unit)
UNITS = {
    "kg": ("weight", Decimal(1000)),
    "g": ("weight", Decimal(1)),
    "L": ("volume", Decimal(1000)),
    "ml": ("volume", Decimal(1)),
    "pcs": ("count", Decimal(1)),
}


class IncompatibleUnitsError(ValueError):
    pass


def money(value) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def normalize(quantity, unit):
    """Return (family, quantity in base unit), e.g. (1, 'kg') -> ('weight', 1000)."""
    try:
        family, factor = UNITS[unit]
    except KeyError:
        raise IncompatibleUnitsError(f"Unsupported unit: {unit!r}")
    return family, Decimal(quantity) * factor


def ingredient_cost(ingredient, used_quantity, used_unit) -> Decimal:
    """Cost of `used_quantity used_unit` of an ingredient, rounded to paise."""
    stock_family, stock_base = normalize(ingredient.quantity, ingredient.unit)
    used_family, used_base = normalize(used_quantity, used_unit)
    if stock_family != used_family:
        raise IncompatibleUnitsError(
            f"{ingredient.name} is priced in {ingredient.unit} ({stock_family}); "
            f"cannot use it in {used_unit} ({used_family})."
        )
    # price * used / stock, multiplied before dividing to limit rounding error.
    return money(Decimal(ingredient.price) * used_base / stock_base)


def default_profit(total_cost) -> Decimal:
    """30% of the cost, to the paisa."""
    return money(Decimal(total_cost) * DEFAULT_PROFIT_RATE)


def calculate_product(lines, packaging_cost=0, eb_cost=0, labour_cost=0, profit=None) -> dict:
    """`lines`: iterable of dicts with ingredient, used_quantity, used_unit."""
    results = []
    for line in lines:
        cost = ingredient_cost(line["ingredient"], line["used_quantity"], line["used_unit"])
        results.append({**line, "calculated_cost": cost})

    ingredient_total = sum((r["calculated_cost"] for r in results), Decimal("0.00"))
    packaging, eb, labour = money(packaging_cost), money(eb_cost), money(labour_cost)
    total = ingredient_total + packaging + eb + labour
    suggested = default_profit(total)
    profit = suggested if profit is None else money(profit)

    return {
        "lines": results,
        "total_ingredient_cost": ingredient_total,
        "packaging_cost": packaging,
        "eb_cost": eb,
        "labour_cost": labour,
        "total_additional_cost": packaging + eb + labour,
        "total_cost": total,
        "default_profit": suggested,
        "profit": profit,
        "selling_price": total + profit,
    }
