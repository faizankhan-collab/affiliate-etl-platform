import asyncio
import unittest
from unittest.mock import patch, MagicMock
from backend.campaign_finder import CampaignFinderService
from backend.app import (
    api_search_campaigns,
    api_get_campaign_networks,
    api_get_campaign_categories,
    read_campaigns_view,
)


class TestCuelinksCampaignFinder(unittest.TestCase):
    def setUp(self):
        self.service = CampaignFinderService()

    def test_networks_summary(self):
        summary = self.service.get_networks_summary()
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["id"], "cuelinks")
        self.assertEqual(summary[0]["status"], "connected")
        self.assertIn("Official REST API", summary[0]["badge"])

    def test_categories(self):
        cats = self.service.get_categories()
        self.assertGreaterEqual(len(cats), 5)
        cat_ids = [c["id"] for c in cats]
        self.assertIn("all", cat_ids)
        self.assertIn("Fashion", cat_ids)
        self.assertIn("Electronics", cat_ids)

    @patch("backend.campaign_finder.requests.get")
    def test_search_campaigns_with_mocked_live_response(self, mock_get):
        # Mock actual Cuelinks v3 response format
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "Flipkart",
                    "domain": "flipkart.com",
                    "payout": "6.8",
                    "payout_type": "Per Sale(%)",
                    "payout_currency": "%",
                    "campaign_type": "CPS",
                    "access_status": "open",
                    "categories": [{"id": 1, "name": "Fashion"}],
                    "countries": [{"id": 252, "name": "India"}],
                    "cookie_duration": "30 minutes",
                    "epc_7d": "0.34",
                    "tracking_url": "https://linksredirect.com/?cid=33273&url=https%3A%2F%2Fwww.flipkart.com",
                }
            ],
            "meta": {"total": 1, "page": 1, "per_page": 30}
        }
        mock_get.return_value = mock_resp

        res = self.service.search_campaigns(query="Flipkart")
        self.assertTrue(res["success"])
        self.assertEqual(res["total"], 1)
        self.assertEqual(len(res["results"]), 1)
        
        item = res["results"][0]
        self.assertEqual(item["brand_name"], "Flipkart")
        self.assertEqual(item["network_id"], "cuelinks")
        self.assertEqual(item["status"], "active")
        self.assertIn("6.8%", item["payout_display"])
        self.assertEqual(item["panel_url"], "https://www.cuelinks.com/campaigns/flipkart-affiliate-program")
        self.assertIn("linksredirect.com", item["tracking_url"])

    def test_campaigns_html_page_route(self):
        resp = asyncio.run(read_campaigns_view())
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Cuelinks Live Campaign Explorer", resp.body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
