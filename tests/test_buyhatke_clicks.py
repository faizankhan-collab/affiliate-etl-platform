import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import requests

from backend.buyhatke_clicks import BuyhatkeClicksService


class TestBuyhatkeClicksService(unittest.TestCase):
    def setUp(self):
        self.service = BuyhatkeClicksService(api_key="test_key_123")

    def test_init_defaults(self):
        self.assertEqual(self.service.api_key, "test_key_123")
        self.assertIn("X-API-Key", self.service.headers)
        self.assertEqual(self.service.headers["X-API-Key"], "test_key_123")

    @patch.object(requests.Session, "get")
    def test_fetch_raw_stats_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "data": {
                "pagination": {"page": 1, "page_size": 1000, "total_rows": 2, "total_pages": 1},
                "totals": {"internal_clicks": 50000},
                "rows": [
                    {
                        "position": 2,
                        "website_name": "Flipkart",
                        "affiliate_network_id": 0,
                        "affiliate_network_name": "Bypassed",
                        "internal_clicks": 35000,
                    },
                    {
                        "position": 63,
                        "website_name": "Amazon",
                        "affiliate_network_id": 19,
                        "affiliate_network_name": "zonet",
                        "internal_clicks": 15000,
                    },
                ],
            },
        }
        mock_get.return_value = mock_resp

        res = self.service.fetch_raw_stats(from_date="2026-11-11", upto_date="2026-11-17")
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["totals"]["internal_clicks"], 50000)
        self.assertEqual(len(res["data"]["rows"]), 2)

    @patch.object(requests.Session, "get")
    def test_get_clicks_dataframe(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "data": {
                "pagination": {"page": 1, "page_size": 1000, "total_rows": 2, "total_pages": 1},
                "totals": {"internal_clicks": 50000},
                "rows": [
                    {
                        "position": 2,
                        "website_name": "Flipkart",
                        "affiliate_network_id": 0,
                        "affiliate_network_name": "Bypassed",
                        "internal_clicks": 35000,
                    },
                    {
                        "position": 63,
                        "website_name": "Amazon",
                        "affiliate_network_id": 19,
                        "affiliate_network_name": "zonet",
                        "internal_clicks": 15000,
                    },
                ],
            },
        }
        mock_get.return_value = mock_resp

        df = self.service.get_clicks_dataframe(from_date="2026-11-11", upto_date="2026-11-17")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertListEqual(
            list(df.columns),
            [
                "WEBSITE / BRAND",
                "AFFILIATE NETWORK",
                "SUM of INTERNAL CLICKS",
                "POSITION",
                "NETWORK_ID",
            ],
        )
        self.assertEqual(df.iloc[0]["WEBSITE / BRAND"], "Flipkart")
        self.assertEqual(df.iloc[0]["SUM of INTERNAL CLICKS"], 35000)
        self.assertEqual(df.iloc[1]["WEBSITE / BRAND"], "Amazon")
        self.assertEqual(df.iloc[1]["SUM of INTERNAL CLICKS"], 15000)

    @patch.object(requests.Session, "get")
    def test_get_daily_timeseries(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "data": {
                "rows": [
                    {"date": "2026-11-11", "week_day": "Wednesday", "internal_clicks": 12000},
                    {"date": "2026-11-12", "week_day": "Thursday", "internal_clicks": 14000},
                ]
            },
        }
        mock_get.return_value = mock_resp

        ts = self.service.get_daily_timeseries("2026-11-11", "2026-11-12")
        self.assertEqual(len(ts), 2)
        self.assertEqual(ts[0]["date"], "2026-11-11")
        self.assertEqual(ts[0]["internal_clicks"], 12000)

    @patch.object(requests.Session, "get")
    def test_api_error_handling(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_get.return_value = mock_resp

        res = self.service.fetch_raw_stats("2026-11-11", "2026-11-17")
        self.assertFalse(res["success"])
        self.assertIn("500", res["error"])

    def test_fastapi_endpoints(self):
        import asyncio
        from backend.app import (
            api_get_internal_clicks_stats,
            api_get_internal_clicks_timeseries,
            api_get_internal_clicks_top_brands,
        )

        with patch("backend.app.buyhatke_clicks.fetch_raw_stats", return_value={"success": True, "total": 100}):
            stats = asyncio.run(api_get_internal_clicks_stats(start_date="2026-11-11", end_date="2026-11-17"))
            self.assertTrue(stats["success"])
            self.assertEqual(stats["total"], 100)

        with patch("backend.app.buyhatke_clicks.get_daily_timeseries", return_value=[{"date": "2026-11-11", "internal_clicks": 100}]):
            ts = asyncio.run(api_get_internal_clicks_timeseries(start_date="2026-11-11", end_date="2026-11-17"))
            self.assertTrue(ts["success"])
            self.assertEqual(len(ts["timeseries"]), 1)

        with patch("backend.app.buyhatke_clicks.get_top_brands_summary", return_value=[{"website_name": "Flipkart", "internal_clicks": 1000}]):
            tb = asyncio.run(api_get_internal_clicks_top_brands(start_date="2026-11-11", end_date="2026-11-17"))
            self.assertTrue(tb["success"])
            self.assertEqual(tb["count"], 1)

    def test_rolling_30d_rpc_timeseries(self):
        res = self.service.get_rolling_30d_rpc_timeseries(lag_days=6)
        self.assertTrue(res["success"])
        self.assertEqual(res["days_count"], 30)
        self.assertEqual(len(res["timeline"]), 30)
        self.assertIn("summary", res)
        self.assertIn("avg_rpc", res["summary"])
        self.assertIn("peak_day", res["summary"])
        self.assertIn("lowest_day", res["summary"])
        self.assertGreater(res["summary"]["peak_day"]["rpc"], 0)
        self.assertGreater(res["summary"]["lowest_day"]["rpc"], 0)
        self.assertIn("alerts", res)
        self.assertIn("top_merchants_today", res)
        
        # Test 7-Day Rolling Diagnostic Engine & Live Alerts
        self.assertIn("rolling_7d", res["summary"])
        rolling_7d = res["summary"]["rolling_7d"]
        self.assertIn("current_7d_rpc", rolling_7d)
        self.assertIn("prior_7d_rpc", rolling_7d)
        self.assertIn("change_pct", rolling_7d)
        self.assertIn("status", rolling_7d)
        self.assertIn("total_potential_gain", rolling_7d)
        self.assertGreater(rolling_7d["total_potential_gain"], 0)

        alerts = res["alerts"]
        self.assertGreaterEqual(len(alerts), 4)
        for a in alerts:
            self.assertIn("id", a)
            self.assertIn("badge", a)
            self.assertIn("title", a)
            self.assertIn("observation", a)
            self.assertIn("root_cause", a)
            self.assertIn("how_to_increase", a)
            self.assertIn("projected_gain", a)
            self.assertIn("action_label", a)

    def test_api_live_rpc_timeseries_endpoint(self):
        import asyncio
        from backend.app import api_get_live_rpc_timeseries
        res = asyncio.run(api_get_live_rpc_timeseries(lag_days=6))
        self.assertTrue(res["success"])
        self.assertEqual(res["days_count"], 30)
        self.assertIn("window_label", res)

    def test_harvest_live_day(self):
        day_res = self.service.harvest_live_day("2026-11-18")
        self.assertIn("clicks", day_res)
        self.assertIn("revenue", day_res)
        self.assertIn("rpc", day_res)
        self.assertGreater(day_res["clicks"], 0)
        self.assertGreater(day_res["rpc"], 0.0)

    def test_live_dashboard_decoupled_from_saved_reports(self):
        import shutil
        from pathlib import Path
        
        # Snapshot current live timeseries
        baseline = self.service.get_rolling_30d_rpc_timeseries(lag_days=6)
        
        # Create a dummy report in saved_reports with extreme values
        dummy_dir = Path(__file__).parent.parent / "backend" / "saved_reports"
        dummy_file = dummy_dir / "report_20261117_20261117_dummy.json"
        try:
            dummy_dir.mkdir(parents=True, exist_ok=True)
            with open(dummy_file, "w", encoding="utf-8") as f:
                f.write('{"summary": {"total_revenue": 999999999, "total_internal_clicks": 1}}')
            
            # Re-fetch live timeseries
            after_dummy = self.service.get_rolling_30d_rpc_timeseries(lag_days=6)
            
            # The Live Dashboard MUST BE completely immune to any files in saved_reports
            self.assertEqual(baseline["summary"]["total_revenue"], after_dummy["summary"]["total_revenue"])
            self.assertEqual(baseline["summary"]["avg_rpc"], after_dummy["summary"]["avg_rpc"])
            self.assertEqual(baseline["timeline"][-1]["revenue"], after_dummy["timeline"][-1]["revenue"])
        finally:
            if dummy_file.exists():
                dummy_file.unlink()


if __name__ == "__main__":
    unittest.main()
