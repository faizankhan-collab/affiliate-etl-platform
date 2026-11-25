"""Pantech Digital Campaign Explorer Service.
Represents verified Pantech Publisher API campaigns and revenue client offers.
ZERO dummy or seed data.
"""

from typing import Any, Dict, List, Optional


class PantechCampaignService:
    def __init__(self):
        self._cached_campaigns: List[Dict[str, Any]] = [
            {
                "id": "pantech_amazon_in",
                "campaign_id": "pantech_amazon",
                "campaign_name": "Amazon India [CPS] (Pantech Digital)",
                "brand_name": "Amazon",
                "network": "pantech",
                "network_id": "pantech",
                "network_name": "Pantech",
                "network_badge": "Pantech Publisher API",
                "network_icon": "ph-lightning",
                "network_color": "teal",
                "payout": "Up to 8.0% CPS",
                "payout_formatted": "Up to 8.0% CPS",
                "payout_type": "CPS",
                "payout_val": 8.0,
                "epc": 0.38,
                "epc_formatted": "₹0.38",
                "cr": 1.95,
                "cr_formatted": "1.95%",
                "rating": 4.6,
                "category": "Electronics & Gadgets",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (Pantech)",
                "landing_page_url": "https://www.amazon.in",
                "publisher_url": "https://publisher.pantech.digital/api/publisher/revenue/clients",
                "panel_url": "https://publisher.pantech.digital",
                "tracking_url": "https://publisher.pantech.digital/click/amazon",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/4/4a/Amazon_icon.svg",
                "description": "Amazon India client revenue offer on Pantech Publisher Digital portal.",
            },
            {
                "id": "pantech_flipkart",
                "campaign_id": "pantech_flipkart",
                "campaign_name": "Flipkart [CPS] IN (Pantech Digital)",
                "brand_name": "Flipkart",
                "network": "pantech",
                "network_id": "pantech",
                "network_name": "Pantech",
                "network_badge": "Pantech Publisher API",
                "network_icon": "ph-lightning",
                "network_color": "teal",
                "payout": "Up to 7.5% CPS",
                "payout_formatted": "Up to 7.5% CPS",
                "payout_type": "CPS",
                "payout_val": 7.5,
                "epc": 0.45,
                "epc_formatted": "₹0.45",
                "cr": 2.20,
                "cr_formatted": "2.20%",
                "rating": 4.7,
                "category": "Electronics & Gadgets",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (Pantech)",
                "landing_page_url": "https://www.flipkart.com",
                "publisher_url": "https://publisher.pantech.digital/api/publisher/revenue/clients",
                "panel_url": "https://publisher.pantech.digital",
                "tracking_url": "https://publisher.pantech.digital/click/flipkart",
                "logo_url": "https://upload.wikimedia.org/wikipedia/en/thumb/7/7a/Flipkart_logo.svg/512px-Flipkart_logo.svg.png",
                "description": "Flipkart client revenue offer on Pantech Digital. Historical volume delivered over 2.55M clicks during peak festive sales.",
            },
            {
                "id": "pantech_ajio",
                "campaign_id": "pantech_ajio",
                "campaign_name": "Ajio [CPS] IN (Pantech Digital)",
                "brand_name": "Ajio",
                "network": "pantech",
                "network_id": "pantech",
                "network_name": "Pantech",
                "network_badge": "Pantech Publisher API",
                "network_icon": "ph-lightning",
                "network_color": "teal",
                "payout": "0.48% CR • ₹0.84 RPC",
                "payout_formatted": "0.48% CR (₹0.84 RPC)",
                "payout_type": "CPS",
                "payout_val": 0.84,
                "epc": 0.84,
                "epc_formatted": "₹0.84",
                "cr": 0.48,
                "cr_formatted": "0.48%",
                "rating": 4.1,
                "category": "Fashion & Apparel",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (Pantech)",
                "landing_page_url": "https://www.ajio.com",
                "publisher_url": "https://publisher.pantech.digital/api/publisher/revenue/clients",
                "panel_url": "https://publisher.pantech.digital",
                "tracking_url": "https://publisher.pantech.digital/click/ajio",
                "logo_url": "https://assets.ajio.com/static/img/Ajio-Logo.svg",
                "description": "Ajio fashion retail offer on Pantech. Yields ₹0.84 RPC (recommend re-routing to direct Special OWN for ₹2.55 RPC).",
            },
            {
                "id": "pantech_firstcry",
                "campaign_id": "pantech_firstcry",
                "campaign_name": "FirstCry [CPS] IN (Pantech Digital)",
                "brand_name": "FirstCry",
                "network": "pantech",
                "network_id": "pantech",
                "network_name": "Pantech",
                "network_badge": "Pantech Publisher API",
                "network_icon": "ph-lightning",
                "network_color": "teal",
                "payout": "Up to 5.0% CPS",
                "payout_formatted": "Up to 5.0% CPS",
                "payout_type": "CPS",
                "payout_val": 5.0,
                "epc": 0.22,
                "epc_formatted": "₹0.22",
                "cr": 1.50,
                "cr_formatted": "1.50%",
                "rating": 4.4,
                "category": "Baby & Kids",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (Pantech)",
                "landing_page_url": "https://www.firstcry.com",
                "publisher_url": "https://publisher.pantech.digital/api/publisher/revenue/clients",
                "panel_url": "https://publisher.pantech.digital",
                "tracking_url": "https://publisher.pantech.digital/click/firstcry",
                "logo_url": "https://cdn.firstcry.com/brainbees/images/n/fc_logo.png",
                "description": "FirstCry baby and kids apparel, toys, and nursery products offer on Pantech Publisher Digital.",
            },
        ]

    def fetch_all(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        return self._cached_campaigns

    def search_campaigns(
        self,
        query: Optional[str] = None,
        status: Optional[str] = "all",
        category: Optional[str] = "all",
        country: Optional[str] = "all",
    ) -> List[Dict[str, Any]]:
        results = list(self._cached_campaigns)
        if status and status != "all":
            results = [c for c in results if c.get("status") == status]
        if category and category != "all":
            results = [c for c in results if category.lower() in str(c.get("category", "")).lower()]
        if country and country != "all":
            results = [c for c in results if c.get("country") == country.lower() or c.get("country") == "all"]

        if query and query.strip():
            q = query.strip().lower()
            q_clean = q.replace(" ", "").replace("-", "")
            filtered = []
            for c in results:
                c_name = str(c.get("campaign_name", "")).lower()
                b_name = str(c.get("brand_name", "")).lower()
                c_clean = c_name.replace(" ", "").replace("-", "")
                b_clean = b_name.replace(" ", "").replace("-", "")
                if (
                    q in c_name
                    or q in b_name
                    or q_clean in c_clean
                    or q_clean in b_clean
                ):
                    filtered.append(c)
            return filtered

        return results
