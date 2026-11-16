import asyncio
import unittest
from backend.campaign_finder import CampaignFinderService
from backend.app import (
    api_search_campaigns,
    api_get_campaign_networks,
    api_get_campaign_categories,
    read_campaigns_view,
)


class TestCampaignFinder(unittest.TestCase):
    def setUp(self):
        self.service = CampaignFinderService()

    def test_search_brand_amazon(self):
        res = self.service.search_campaigns(query="amazon")
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["total"], 3)
        
        # Verify networks represented
        networks = [r["network_id"] for r in res["results"]]
        self.assertIn("admitad", networks)
        self.assertIn("cuelinks", networks)
        self.assertIn("inrdeals", networks)

        # Verify best payout detection
        best_offers = [r for r in res["results"] if r.get("is_best_payout")]
        self.assertEqual(len(best_offers), 1)
        self.assertEqual(best_offers[0]["network_id"], "admitad")
        self.assertIn("Top Payout", best_offers[0]["payout_diff_label"])

    def test_filter_by_specific_network(self):
        # User requirement: view all campaigns on a particular network
        res = self.service.search_campaigns(network="cuelinks")
        self.assertTrue(res["success"])
        self.assertGreater(res["total"], 10)
        for r in res["results"]:
            self.assertEqual(r["network_id"], "cuelinks")

    def test_filter_by_category(self):
        res = self.service.search_campaigns(category="Fashion")
        self.assertTrue(res["success"])
        for r in res["results"]:
            self.assertEqual(r["category"], "Fashion")

    def test_networks_summary(self):
        summary = self.service.get_networks_summary()
        self.assertGreaterEqual(len(summary), 9)  # All + 8 networks
        net_ids = [n["id"] for n in summary]
        for expected in ["all", "cuelinks", "admitad", "inrdeals", "cj", "cashkaro", "icubeswire", "pantech", "zonet"]:
            self.assertIn(expected, net_ids)

    def test_api_search_endpoint(self):
        data = asyncio.run(api_search_campaigns(query="nike"))
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["total"], 2)

    def test_api_networks_endpoint(self):
        data = asyncio.run(api_get_campaign_networks())
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 9)

    def test_api_categories_endpoint(self):
        data = asyncio.run(api_get_campaign_categories())
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 3)

    def test_campaigns_html_page_route(self):
        resp = asyncio.run(read_campaigns_view())
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Universal Affiliate Campaign Finder", resp.body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
