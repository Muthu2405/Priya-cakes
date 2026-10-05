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


class BucketTests(SimpleTestCase):
    def test_week_starts_monday(self):
        self.assertEqual(reports.bucket_start(date(2026, 10, 7), "week"), date(2026, 10, 5))
        self.assertEqual(reports.bucket_start(date(2026, 10, 11), "week"), date(2026, 10, 5))

    def test_month_rollover(self):
        self.assertEqual(reports.next_bucket(date(2026, 12, 1), "month"), date(2027, 1, 1))
        self.assertEqual(reports.next_bucket(date(2026, 1, 1), "month"), date(2026, 2, 1))


class SalesApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("a", password="x")
        self.other = User.objects.create_user("b", password="x")
        self.cake = Product.objects.create(owner=self.user, name="Cake", total_cost=Decimal("100"))
        self.theirs = Product.objects.create(owner=self.other, name="Pie", total_cost=Decimal("50"))
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.user).key}")

    def sell(self, qty, price, on, product=None):
        return self.api.post("/api/sales/", {
            "product": (product or self.cake).pk, "quantity": qty,
            "unit_price": price, "sold_on": on.isoformat()}, format="json")

    def test_login_required(self):
        self.assertEqual(APIClient().get("/api/sales/").status_code, 401)
        self.assertEqual(APIClient().get("/api/sales/report/").status_code, 401)

    def test_record_sale_snapshots_cost(self):
        res = self.sell(3, "150", today())
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["unit_cost"], "100.00")
        self.assertEqual(res.data["revenue"], "450.00")
        self.cake.total_cost = Decimal("999"); self.cake.save()
        self.assertEqual(Sale.objects.get().unit_cost, Decimal("100.00"))

    def test_cannot_sell_someone_elses_product(self):
        self.assertEqual(self.sell(1, "10", today(), self.theirs).status_code, 400)

    def test_rejects_future_date_and_zero_quantity(self):
        self.assertEqual(self.sell(1, "10", today() + timedelta(days=1)).status_code, 400)
        self.assertEqual(self.sell(0, "10", today()).status_code, 400)

    def test_only_own_sales_listed(self):
        Sale.objects.create(owner=self.other, product=self.theirs, quantity=1, unit_price=1, unit_cost=1)
        self.sell(1, "10", today())
        self.assertEqual(len(self.api.get("/api/sales/").data), 1)

    def test_daily_report_includes_empty_days(self):
        d = date(2026, 9, 14)
        self.sell(2, "150", d); self.sell(1, "150", d); self.sell(1, "200", d + timedelta(days=2))
        r = self.api.get("/api/sales/report/", {"period": "day", "from": "2026-09-14", "to": "2026-09-16"}).data
        self.assertEqual([x["revenue"] for x in r["series"]], ["450.00", "0.00", "200.00"])
        self.assertEqual(r["series"][0]["orders"], 2)
        self.assertEqual(r["totals"]["revenue"], "650.00")
        self.assertEqual(r["totals"]["profit"], "250.00")  # 650 - 4*100

    def test_weekly_report_groups_monday_to_sunday(self):
        self.sell(1, "100", date(2026, 9, 20))   # Sunday, previous week
        self.sell(1, "100", date(2026, 9, 21))   # Monday
        self.sell(1, "100", date(2026, 9, 27))  # Sunday, same week
        r = self.api.get("/api/sales/report/", {"period": "week", "from": "2026-09-14", "to": "2026-09-27"}).data
        self.assertEqual([x["units"] for x in r["series"]], [1, 2])
        self.assertEqual(r["series"][1]["period_start"], "2026-09-21")

    def test_monthly_report_and_product_breakdown(self):
        self.sell(1, "100", date(2026, 9, 30)); self.sell(2, "100", date(2026, 10, 1))
        r = self.api.get("/api/sales/report/", {"period": "month", "from": "2026-09-01", "to": "2026-10-31"}).data
        self.assertEqual([x["units"] for x in r["series"]], [1, 2])
        self.assertEqual(r["by_product"][0]["product_name"], "Cake")
        self.assertEqual(r["by_product"][0]["units"], 3)

    def test_report_excludes_other_users(self):
        Sale.objects.create(owner=self.other, product=self.theirs, sold_on=today(), quantity=5, unit_price=10, unit_cost=1)
        r = self.api.get("/api/sales/report/", {"period": "day"}).data
        self.assertEqual(r["totals"]["units"], 0)

    def test_range_snaps_to_whole_weeks_and_months(self):
        self.sell(1, "100", date(2026, 9, 14))  # Monday
        r = self.api.get("/api/sales/report/", {"period": "week", "from": "2026-09-16", "to": "2026-09-23"}).data
        self.assertEqual((r["start"], r["end"]), ("2026-09-14", "2026-09-27"))
        self.assertEqual(r["totals"]["units"], 1)  # Monday sale is inside the first, whole week
        r = self.api.get("/api/sales/report/", {"period": "month", "from": "2026-09-16", "to": "2026-10-02"}).data
        self.assertEqual((r["start"], r["end"]), ("2026-09-01", "2026-10-31"))

    def test_bad_params(self):
        self.assertEqual(self.api.get("/api/sales/report/", {"period": "year"}).status_code, 400)
        self.assertEqual(self.api.get("/api/sales/report/", {"from": "nope"}).status_code, 400)
        self.assertEqual(self.api.get("/api/sales/report/", {"from": "2026-10-09", "to": "2026-10-01"}).status_code, 400)

    def test_csv_export(self):
        self.sell(1, "100", date(2026, 9, 21))
        res = self.api.get("/api/sales/report/csv/", {"period": "day", "from": "2026-09-21", "to": "2026-09-21"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res["Content-Type"])
        self.assertIn("Total,1,1,100.00,100.00,0.00", res.content.decode())

    def test_product_with_sales_cannot_be_deleted(self):
        self.sell(1, "100", today())
        res = self.api.delete(f"/api/products/{self.cake.pk}/")
        self.assertEqual(res.status_code, 409)
        self.assertTrue(Product.objects.filter(pk=self.cake.pk).exists())
