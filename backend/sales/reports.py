from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

PERIODS = ("day", "week", "month")
ZERO = Decimal("0.00")


def month_start(d: date) -> date:
    return d.replace(day=1)


def month_end(d: date) -> date:
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def resolve_range(period: str, start: date, end: date):
    """Days and weeks use the dates as given. Months are always whole calendar months."""
    if period == "month":
        return month_start(start), month_end(end)
    return start, end


def bucket_start(d: date, period: str, anchor: date) -> date:
    """Weeks are plain 7-day blocks counted from the report's start date, whatever the weekday."""
    if period == "week":
        return anchor + timedelta(days=7 * ((d - anchor).days // 7))
    if period == "month":
        return month_start(d)
    return d


def bucket_end(start: date, period: str, last: date) -> date:
    if period == "week":
        end = start + timedelta(days=6)
    elif period == "month":
        end = month_end(start)
    else:
        end = start
    return min(end, last)


def _label(start: date, end: date, period: str) -> str:
    if period == "month":
        return start.strftime("%b %Y")
    if period == "week":
        return f"{start.day} {start:%b %Y} \u2013 {end.day} {end:%b %Y}"
    return f"{start.day} {start:%b %Y}"


def _row():
    return {"orders": 0, "units": 0, "revenue": ZERO, "cost": ZERO, "profit": ZERO, "no_cost_orders": 0}


def add_sale(row, s):
    row["orders"] += 1
    row["units"] += s.quantity
    row["revenue"] += s.revenue
    if s.unit_cost is None:
        row["no_cost_orders"] += 1  # revenue counts, but there is no cost or profit to add
    else:
        row["cost"] += s.cost
        row["profit"] += s.profit


def build_report(sales, period: str, start: date, end: date) -> dict:
    """Group sales into day/week/month buckets, with empty periods included.

    `start`/`end` must already be resolved with resolve_range().
    """
    buckets, products = defaultdict(_row), defaultdict(_row)
    labels = {}
    for s in sales:
        add_sale(buckets[bucket_start(s.sold_on, period, start)], s)
        key = f"p{s.product_id}" if s.product_id else f"n{s.product_name.casefold()}"
        add_sale(products[key], s)
        labels[key] = (s.product_id, s.product_name)

    series, cursor = [], start
    while cursor <= end:
        last = bucket_end(cursor, period, end)
        series.append({
            "period_start": cursor.isoformat(), "period_end": last.isoformat(),
            "label": _label(cursor, last, period), "days": (last - cursor).days + 1,
            **buckets.get(cursor, _row()),
        })
        cursor = last + timedelta(days=1)

    total = _row()
    for row in buckets.values():
        for k in total:
            total[k] += row[k]

    by_product = sorted(
        ({"product": labels[k][0], "product_name": labels[k][1], "in_catalog": labels[k][0] is not None, **row}
         for k, row in products.items()),
        key=lambda r: r["revenue"], reverse=True,
    )
    return {
        "period": period, "start": start.isoformat(), "end": end.isoformat(),
        "totals": total, "series": series, "by_product": by_product,
    }
