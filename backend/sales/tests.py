from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from products.models import Product

from . import reports
from .models import Sale, today

User = get_user_model()


class RangeTests(SimpleTestCase):
    def test_weeks_are_seven_day_blocks_from_the_start_date_not_calendar_weeks(self):
        start = date(2026, 9, 29)  # a Tuesday
        self.assertEqual(reports.bucket_start(date(2026, 10, 5), "week", start), date(2026, 9, 29))
        self.assertEqual(reports.bucket_start(date(2026, 10, 6), "week", start), date(2026, 10, 6))

    def test_months_snap_to_whole_months(self):
        self.assertEqual(reports.resolve_range("month", date(2026, 9, 16), date(2026, 10, 2)),
                         (date(2026, 9, 1), date(2026, 10, 31)))
        self.assertEqual(reports.resolve_range("week", date(2026, 9, 16), date(2026, 10, 2)),
                         (date(2026, 9, 16), date(2026, 10, 2)))


class SalesApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("a", password="x")
        self.other = User.objects.create_user("b", password="x")
        self.cake = Product.objects.create(owner=self.user, name="Cake", total_cost=Decimal("100"), profit=Decimal("30"))
        self.theirs = Product.objects.create(owner=self.other, name="Pie", total_cost=Decimal("50"))
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.user).key}")

    def sell(self, qty, price, on, product=None, **extra):
        body = {"quantity": qty, "unit_price": price, "sold_on": on.isoformat(), **extra}
        if product is not False:
            body["product"] = (product or self.cake).pk
        return self.api.post("/api/sales/", body, format="json")

    def report(self, **params):
        return self.api.get("/api/sales/report/", params).data

    # ----- recording
    def test_login_required(self):
        self.assertEqual(APIClient().get("/api/sales/").status_code, 401)
        self.assertEqual(APIClient().get("/api/sales/report/").status_code, 401)

    def test_catalogue_sale_fills_name_cost_and_profit(self):
        res = self.sell(3, "130", today())
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data["product_name"], "Cake")
        self.assertTrue(res.data["in_catalog"])
        self.assertEqual(res.data["unit_cost"], "100.00")
        self.assertEqual(res.data["revenue"], "390.00")
        self.assertEqual(res.data["profit"], "90.00")  # 3 x (130 - 100)
        self.cake.total_cost = Decimal("999"); self.cake.save()
        self.assertEqual(Sale.objects.get().unit_cost, Decimal("100.00"))  # snapshot

    def test_client_cannot_override_catalogue_cost(self):
        res = self.sell(1, "130", today(), unit_cost="1")
        self.assertEqual(res.data["unit_cost"], "100.00")

    def test_sale_of_product_not_in_list(self):
        res = self.sell(2, "40", today(), product=False, product_name="  Brownie ")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual((res.data["product_name"], res.data["in_catalog"]), ("Brownie", False))
        self.assertIsNone(res.data["profit"])      # no cost known, so no profit is invented
        self.assertEqual(res.data["revenue"], "80.00")

    def test_unlisted_sale_with_cost_gets_profit(self):
        res = self.sell(2, "40", today(), product=False, product_name="Brownie", unit_cost="25")
        self.assertEqual(res.data["profit"], "30.00")

    def test_unlisted_sale_needs_a_name(self):
        self.assertEqual(self.sell(1, "10", today(), product=False).status_code, 400)
        self.assertEqual(self.sell(1, "10", today(), product=False, product_name="  ").status_code, 400)

    def test_cannot_sell_someone_elses_product(self):
        self.assertEqual(self.sell(1, "10", today(), self.theirs).status_code, 400)

    def test_rejects_future_date_and_zero_quantity(self):
        self.assertEqual(self.sell(1, "10", today() + timedelta(days=1)).status_code, 400)
        self.assertEqual(self.sell(0, "10", today()).status_code, 400)

    def test_kg_product_accepts_decimal_quantity(self):
        murukku = Product.objects.create(owner=self.user, name="Murukku", sold_by="kg", total_cost=Decimal("200"))
        res = self.sell("0.5", "300", today(), murukku)
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual((res.data["sold_by"], res.data["revenue"], res.data["profit"]), ("kg", "150.00", "50.00"))
        self.assertEqual(self.report(period="day")["totals"]["units"], 0.5)

    def test_pcs_product_rejects_fractional_quantity(self):
        self.assertEqual(self.sell("1.5", "130", today()).status_code, 400)
        self.assertEqual(self.sell("2.0", "130", today()).status_code, 201)

    def test_only_own_sales_listed(self):
        Sale.objects.create(owner=self.other, product=self.theirs, product_name="Pie", quantity=1, unit_price=1, unit_cost=1)
        self.sell(1, "10", today())
        self.assertEqual(len(self.api.get("/api/sales/").data), 1)

    def test_edit_can_switch_between_listed_and_unlisted(self):
        sid = self.sell(1, "130", today()).data["id"]
        res = self.api.put(f"/api/sales/{sid}/", {"product": None, "product_name": "Brownie", "quantity": 1,
                                                 "unit_price": "50", "sold_on": today().isoformat()}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((res.data["product_name"], res.data["in_catalog"], res.data["profit"]), ("Brownie", False, None))
        res = self.api.put(f"/api/sales/{sid}/", {"product": self.cake.pk, "quantity": 1,
                                                 "unit_price": "150", "sold_on": today().isoformat()}, format="json")
        self.assertEqual((res.data["product_name"], res.data["profit"]), ("Cake", "50.00"))

    def test_deleting_a_product_keeps_its_sales(self):
        self.sell(1, "130", today())
        self.api.delete(f"/api/products/{self.cake.pk}/")
        sale = Sale.objects.get()
        self.assertIsNone(sale.product_id)
        self.assertEqual((sale.product_name, sale.unit_cost), ("Cake", Decimal("100.00")))

    # ----- reports
    def test_daily_report_includes_empty_days(self):
        d = date(2026, 9, 14)
        self.sell(2, "150", d); self.sell(1, "150", d); self.sell(1, "200", d + timedelta(days=2))
        r = self.report(period="day", **{"from": "2026-09-14", "to": "2026-09-16"})
        self.assertEqual([x["revenue"] for x in r["series"]], ["450.00", "0.00", "200.00"])
        self.assertEqual(r["series"][0]["orders"], 2)
        self.assertEqual(r["totals"]["revenue"], "650.00")
        self.assertEqual(r["totals"]["profit"], "250.00")  # 650 - 4*100

    def test_weekly_report_is_seven_day_blocks_from_the_from_date(self):
        # 29 Sep (Tue) to 5 Oct (Mon) is one 7-day week, even though it isn't Monday-Sunday.
        self.sell(1, "100", date(2026, 9, 28)); self.sell(1, "100", date(2026, 9, 29))
        self.sell(1, "100", date(2026, 10, 5))
        r = self.report(period="week", **{"from": "2026-09-22", "to": "2026-10-05"})
        self.assertEqual([(x["period_start"], x["period_end"], x["days"]) for x in r["series"]],
                         [("2026-09-22", "2026-09-28", 7), ("2026-09-29", "2026-10-05", 7)])
        self.assertEqual([x["units"] for x in r["series"]], [1, 2])
        self.assertEqual(r["series"][1]["label"], "29 Sep 2026 – 5 Oct 2026")
        self.assertEqual((r["start"], r["end"]), ("2026-09-22", "2026-10-05"))  # dates are not widened

    def test_last_week_is_clipped_to_the_to_date(self):
        r = self.report(period="week", **{"from": "2026-09-22", "to": "2026-10-01"})
        self.assertEqual([x["days"] for x in r["series"]], [7, 3])
        self.assertEqual(r["series"][1]["period_end"], "2026-10-01")

    def test_default_weekly_range_is_four_whole_weeks_ending_today(self):
        r = self.report(period="week")
        self.assertEqual([x["days"] for x in r["series"]], [7, 7, 7, 7])
        self.assertEqual(r["end"], today().isoformat())

    def test_monthly_report_and_product_breakdown(self):
        self.sell(1, "100", date(2026, 9, 30)); self.sell(2, "100", date(2026, 10, 1))
        self.sell(1, "10", date(2026, 10, 1), product=False, product_name="Brownie")
        r = self.report(period="month", **{"from": "2026-09-16", "to": "2026-10-02"})
        self.assertEqual((r["start"], r["end"]), ("2026-09-01", "2026-10-31"))
        self.assertEqual([x["units"] for x in r["series"]], [1, 3])
        names = {p["product_name"]: p for p in r["by_product"]}
        self.assertEqual(names["Cake"]["units"], 3)
        self.assertFalse(names["Brownie"]["in_catalog"])

    def test_sales_without_a_cost_add_revenue_but_not_profit(self):
        self.sell(1, "130", date(2026, 9, 14))                                   # profit 30
        self.sell(2, "40", date(2026, 9, 14), product=False, product_name="Brownie")  # revenue 80, cost unknown
        t = self.report(period="day", **{"from": "2026-09-14", "to": "2026-09-14"})["totals"]
        self.assertEqual((t["revenue"], t["cost"], t["profit"], t["no_cost_orders"]), ("210.00", "100.00", "30.00", 1))

    def test_report_excludes_other_users(self):
        Sale.objects.create(owner=self.other, product=self.theirs, product_name="Pie", sold_on=today(), quantity=5, unit_price=10, unit_cost=1)
        self.assertEqual(self.report(period="day")["totals"]["units"], 0)

    def test_bad_params(self):
        for params in ({"period": "year"}, {"from": "nope"}, {"from": "2026-10-09", "to": "2026-10-01"}):
            self.assertEqual(self.api.get("/api/sales/report/", params).status_code, 400)

    def test_csv_export(self):
        self.sell(1, "100", date(2026, 9, 21))
        res = self.api.get("/api/sales/report/csv/", {"period": "day", "from": "2026-09-21", "to": "2026-09-21"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res["Content-Type"])
        self.assertIn("Total,1,1,100.00,100.00,0.00", res.content.decode())
