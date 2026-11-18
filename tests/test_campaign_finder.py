import asyncio
import unittest
from unittest.mock import patch, MagicMock
import requests
from backend.campaign_finder import CampaignFinderService
from backend.app import (
    api_search_campaigns,
    api_get_campaign_networks,
    api_get_campaign_categories,
    api_open_cuelinks_campaign,
    read_campaigns_view,
)


class TestUniversalCampaignFinder(unittest.TestCase):
    def setUp(self):
        self.service = CampaignFinderService()

    def test_networks_summary(self):
        summary = self.service.get_networks_summary()
        self.assertGreaterEqual(len(summary), 4)
        net_ids = [n["id"] for n in summary]
        self.assertIn("all", net_ids)
        self.assertIn("cuelinks", net_ids)
        self.assertIn("cashkaro", net_ids)
        self.assertIn("cj", net_ids)
        
        cuelinks_net = next(n for n in summary if n["id"] == "cuelinks")
        self.assertEqual(cuelinks_net["status"], "connected")
        self.assertIn("Official REST API", cuelinks_net["badge"])

        cashkaro_net = next(n for n in summary if n["id"] == "cashkaro")
        self.assertEqual(cashkaro_net["status"], "connected")
        self.assertIn("Trackier", cashkaro_net["badge"])

        cj_net = next(n for n in summary if n["id"] == "cj")
        self.assertEqual(cj_net["status"], "connected")
        self.assertIn("Lookup API", cj_net["badge"])
        self.assertEqual(cj_net["count"], 2816)

    def test_categories(self):
        cats = self.service.get_categories()
        self.assertGreaterEqual(len(cats), 5)
        cat_ids = [c["id"] for c in cats]
        self.assertIn("all", cat_ids)
        self.assertIn("Fashion", cat_ids)
        self.assertIn("Electronics", cat_ids)

    @patch.object(requests.Session, "get")
    def test_search_campaigns_with_mocked_live_response(self, mock_get):
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

        res = self.service.search_campaigns(query="Flipkart", network="cuelinks")
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
        self.assertIn("Universal", resp.body.decode("utf-8"))

    @patch.object(requests.Session, "get")
    def test_smart_search_spacing_tolerance(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": 5622,
                    "name": "Airindia",
                    "domain": "airindia.com",
                    "payout": "400.0",
                    "payout_type": "Per Sale",
                    "payout_currency": "INR",
                    "campaign_type": "CPS",
                    "access_status": "open",
                    "categories": [{"id": 5, "name": "Travel"}],
                    "countries": [{"id": 252, "name": "India"}],
                    "cookie_duration": "30 days",
                    "epc_7d": "0.75",
                    "tracking_url": "https://linksredirect.com/?cid=33273&url=airindia",
                }
            ],
            "meta": {"total": 1, "page": 1, "per_page": 30}
        }
        mock_get.return_value = mock_resp

        res = self.service.search_campaigns(query="air india", network="cuelinks")
        self.assertTrue(res["success"])
        self.assertGreaterEqual(len(res["results"]), 1)
        self.assertEqual(res["results"][0]["brand_name"], "Airindia")

    @patch.object(requests.Session, "get")
    def test_cross_network_arbitrage_search(self, mock_get):
        # Mock Cuelinks returning Myntra at 4.0%
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": 100,
                    "name": "Myntra",
                    "domain": "myntra.com",
                    "payout": "4.0",
                    "payout_type": "Per Sale(%)",
                    "payout_currency": "%",
                    "campaign_type": "CPS",
                    "access_status": "open",
                    "categories": [{"id": 1, "name": "Fashion"}],
                    "countries": [{"id": 252, "name": "India"}],
                    "cookie_duration": "30 days",
                    "epc_7d": "0.20",
                    "tracking_url": "https://linksredirect.com/myntra",
                }
            ],
            "meta": {"total": 1, "page": 1, "per_page": 30}
        }
        mock_get.return_value = mock_resp

        # Mock CashKaro returning Myntra at 7.0%
        mock_cashkaro_campaigns = [
            {
                "id": "52",
                "network_id": "cashkaro",
                "network_name": "CashKaro",
                "brand_name": "Myntra",
                "campaign_title": "Myntra",
                "domain": "myntra.com",
                "image_url": "https://static.vnative.co/images/myntra.png",
                "payout_display": "7.0% (CPS)",
                "payout_numeric": 7.0,
                "payout_type": "CPS",
                "status": "active",
                "raw_status": "Active",
                "status_label": "Active",
                "status_color": "emerald",
                "category": "Fashion",
                "categories_list": ["Fashion"],
                "cookie_days": "30 Days",
                "epc_7d": "0.0",
                "tracking_url": "",
                "panel_url": "https://cashkaro.trackier.io/publisher/campaign/52.html",
                "publisher_url": "https://cashkaro.trackier.io/publisher/campaign/52.html",
                "deeplink_allowed": True,
                "geo": "IN",
                "countries_list": ["India"],
                "is_featured": False,
            }
        ]

        with patch.object(self.service.cashkaro, "search_campaigns", return_value=mock_cashkaro_campaigns):
            res = self.service.search_campaigns(query="Myntra", network="all")
            self.assertTrue(res["success"])
            self.assertEqual(len(res["results"]), 2)
            
            # CashKaro should win arbitrage because 7.0% > 4.0%
            cashkaro_card = next(r for r in res["results"] if r["network_id"] == "cashkaro")
            cuelinks_card = next(r for r in res["results"] if r["network_id"] == "cuelinks")
            
            self.assertTrue(cashkaro_card.get("is_best_payout"))
            self.assertIn("higher than Cuelinks", cashkaro_card.get("payout_diff_label", ""))
            self.assertFalse(cuelinks_card.get("is_best_payout", False))

    def test_open_campaign_redirect(self):
        # Test Cuelinks redirect
        resp_cue = asyncio.run(api_open_cuelinks_campaign(network="cuelinks", brand="Flipkart"))
        self.assertEqual(resp_cue.status_code, 302)
        self.assertIn("flipkart-affiliate-program", resp_cue.headers["location"])

        # Test CashKaro redirect
        resp_ck = asyncio.run(api_open_cuelinks_campaign(network="cashkaro", id="1166"))
        self.assertEqual(resp_ck.status_code, 302)
        self.assertEqual(resp_ck.headers["location"], "https://cashkaro.trackier.io/publisher/campaign/1166.html")

        # Test CJ redirect
        resp_cj = asyncio.run(api_open_cuelinks_campaign(network="cj", id="3812192"))
        self.assertEqual(resp_cj.status_code, 302)
        self.assertIn("advertiserDetail.do?advertiserId=3812192", resp_cj.headers["location"])

    def test_cj_search_and_arbitrage(self):
        # Mock CJ returning Dell at 5.0%
        mock_cj_items = [
            {
                "id": "3812192",
                "network_id": "cj",
                "network_name": "CJ Affiliate",
                "brand_name": "Dell",
                "campaign_title": "Dell Technologies",
                "domain": "dell.com",
                "image_url": "https://www.google.com/s2/favicons?domain=dell.com&sz=128",
                "payout_display": "5.0% (Sale)",
                "payout_numeric": 5.0,
                "payout_type": "Sale",
                "status": "active",
                "raw_status": "joined",
                "status_label": "Active / Joined",
                "status_color": "emerald",
                "category": "Hardware",
                "categories_list": ["Hardware"],
                "cookie_days": "30 Days",
                "epc_7d": "45.20",
                "tracking_url": "",
                "panel_url": "https://members.cj.com/member/publisher/7935480/advertiserDetail.do?advertiserId=3812192",
                "publisher_url": "https://members.cj.com/member/publisher/7935480/advertiserDetail.do?advertiserId=3812192",
                "deeplink_allowed": True,
                "geo": "Global",
                "countries_list": ["Global"],
                "is_featured": False,
            }
        ]

        # 1. Search CJ exclusively
        with patch.object(self.service.cj, "search_advertisers", return_value=mock_cj_items):
            res_cj = self.service.search_campaigns(query="Dell", network="cj")
            self.assertTrue(res_cj["success"])
            self.assertEqual(len(res_cj["results"]), 1)
            item = res_cj["results"][0]
            self.assertEqual(item["network_id"], "cj")
            self.assertEqual(item["brand_name"], "Dell")
            self.assertEqual(item["payout_numeric"], 5.0)
            self.assertIn("members.cj.com", item["panel_url"])

        # 2. Search all networks and verify 3-way arbitrage
        # Mock Cuelinks returning Dell at 2.5%
        mock_cue_resp = MagicMock()
        mock_cue_resp.status_code = 200
        mock_cue_resp.json.return_value = {
            "data": [
                {
                    "id": 8801,
                    "name": "Dell India",
                    "domain": "dell.com",
                    "payout": "2.5",
                    "payout_type": "Per Sale(%)",
                    "payout_currency": "%",
                    "campaign_type": "CPS",
                    "access_status": "open",
                    "categories": [{"id": 3, "name": "Electronics"}],
                    "countries": [{"id": 252, "name": "India"}],
                    "cookie_duration": "30 days",
                    "epc_7d": "1.20",
                    "tracking_url": "https://linksredirect.com/dell",
                }
            ],
            "meta": {"total": 1, "page": 1, "per_page": 30}
        }

        with patch.object(requests.Session, "get", return_value=mock_cue_resp), \
             patch.object(self.service.cashkaro, "search_campaigns", return_value=[]), \
             patch.object(self.service.cj, "search_advertisers", return_value=mock_cj_items):
            res_all = self.service.search_campaigns(query="Dell", network="all")
            self.assertTrue(res_all["success"])
            self.assertEqual(len(res_all["results"]), 2)

            cj_card = next(r for r in res_all["results"] if r["network_id"] == "cj")
            cue_card = next(r for r in res_all["results"] if r["network_id"] == "cuelinks")

            # CJ pays 5.0% vs Cuelinks 2.5%, so CJ is arbitrage winner!
            self.assertTrue(cj_card.get("is_best_payout"))
            self.assertIn("higher than Cuelinks", cj_card.get("payout_diff_label", ""))
            self.assertFalse(cue_card.get("is_best_payout", False))


if __name__ == "__main__":
    unittest.main()
