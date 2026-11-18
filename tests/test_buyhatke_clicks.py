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


if __name__ == "__main__":
    unittest.main()
