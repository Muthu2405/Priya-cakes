import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings


class SpaFallbackTests(TestCase):
    def test_page_routes_serve_index_when_built(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "index.html").write_text("<div id=root>app</div>")
            with override_settings(FRONTEND_DIST=Path(d)):
                res = self.client.get("/sales/report")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"app", res.content)

    def test_missing_build_is_a_404_and_api_is_untouched(self):
        with override_settings(FRONTEND_DIST=Path("/nonexistent")):
            self.assertEqual(self.client.get("/sales/report").status_code, 404)
        self.assertEqual(self.client.get("/api/sales/").status_code, 401)


class DatabaseUrlTests(SimpleTestCase):
    def test_postgres_url_is_parsed(self):
        import dj_database_url
        cfg = dj_database_url.parse("postgresql://u:p%40ss@db.example.neon.tech/app?sslmode=require")
        self.assertEqual(cfg["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual((cfg["USER"], cfg["PASSWORD"], cfg["HOST"], cfg["NAME"]), ("u", "p@ss", "db.example.neon.tech", "app"))
        self.assertEqual(cfg["OPTIONS"]["sslmode"], "require")
