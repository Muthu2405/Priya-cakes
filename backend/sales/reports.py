from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

PERIODS = ("day", "week", "month")
ZERO = Decimal("0.00")


def bucket_start(d: date, period: str) -> date:
    if period == "week":
        return d - timedelta(days=d.weekday())  # Monday
    if period == "month":
        return d.replace(day=1)
    return d


def next_bucket(d: date, period: str) -> date:
    if period == "day":
        return d + timedelta(days=1)
    if period == "week":
        return d + timedelta(days=7)
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def bucket_end(d: date, period: str) -> date:
    """Last day of the bucket containing d."""
    return next_bucket(bucket_start(d, period), period) - timedelta(days=1)


def _label(start: date, period: str) -> str:
    if period == "month":
        return start.strftime("%b %Y")
    if period == "week":
        end = start + timedelta(days=6)
        return f"{start:%d %b} – {end:%d %b %Y}"
    return f"{start:%d %b %Y}"


def _row():
    return {"orders": 0, "units": 0, "revenue": ZERO, "cost": ZERO}


def _finish(row):
    row["profit"] = row["revenue"] - row["cost"]
    return row


def build_report(sales, period: str, start: date, end: date) -> dict:
    """Group sales into day/week/month buckets, with empty periods included."""
    buckets, products = defaultdict(_row), defaultdict(_row)
    names = {}
    for s in sales:
        for row in (buckets[bucket_start(s.sold_on, period)], products[s.product_id]):
            row["orders"] += 1
            row["units"] += s.quantity
            row["revenue"] += s.revenue
            row["cost"] += s.cost
        names[s.product_id] = s.product.name

    series, cursor = [], bucket_start(start, period)
    while cursor <= end:
        row = _finish(buckets.get(cursor, _row()))
        series.append({"period_start": cursor.isoformat(), "label": _label(cursor, period), **row})
        cursor = next_bucket(cursor, period)

    total = _row()
    for row in buckets.values():
        for k in total:
            total[k] += row[k]

    by_product = sorted(
        ({"product": pid, "product_name": names[pid], **_finish(row)} for pid, row in products.items()),
        key=lambda r: r["revenue"], reverse=True,
    )
    return {
        "period": period, "start": start.isoformat(), "end": end.isoformat(),
        "totals": _finish(total), "series": series, "by_product": by_product,
    }
