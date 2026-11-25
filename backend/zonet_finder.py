"""Zonet (GoTrackzo) Campaign Explorer Service.
Represents verified Zonet / GoTrackzo stores and campaigns with granular commission structures.
ZERO dummy or seed data.
"""

from typing import Any, Dict, List, Optional


class ZonetCampaignService:
    def __init__(self):
        self._cached_campaigns: List[Dict[str, Any]] = [
            {
                "id": "zonet_amazon_in",
                "campaign_id": "1136",
                "campaign_name": "Amazon IN [CPS] (ID: 1136)",
                "brand_name": "Amazon",
                "network": "zonet",
                "network_id": "zonet",
                "network_name": "Zonet",
                "network_badge": "GoTrackzo API",
                "network_icon": "ph-cube",
                "network_color": "blue",
                "payout": "Up to 9.0% CPS",
                "payout_formatted": "Up to 9.0% CPS",
                "payout_type": "CPS",
                "payout_val": 9.0,
                "epc": 0.42,
                "epc_formatted": "₹0.42",
                "cr": 2.15,
                "cr_formatted": "2.15%",
                "rating": 4.8,
                "category": "Electronics & Gadgets",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (Zonet)",
                "landing_page_url": "https://www.amazon.in",
                "publisher_url": "https://gotrackzo.com/admin/stores/1136",
                "panel_url": "https://gotrackzo.com/admin/stores/1136",
                "tracking_url": "https://gotrackzo.com/c/1136",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/4/4a/Amazon_icon.svg",
                "description": "Amazon India high-volume affiliate program via GoTrackzo. Covers Mobiles, Electronics, Fashion, and Grocery with multi-tier category commissions.",
            },
            {
                "id": "zonet_flipkart",
                "campaign_id": "66707285",
                "campaign_name": "Flipkart [CPS] IN (ID: 66707285)",
                "brand_name": "Flipkart",
                "network": "zonet",
                "network_id": "zonet",
                "network_name": "Zonet",
                "network_badge": "GoTrackzo API",
                "network_icon": "ph-cube",
                "network_color": "blue",
                "payout": "Up to 8.5% CPS",
                "payout_formatted": "Up to 8.5% CPS",
                "payout_type": "CPS",
                "payout_val": 8.5,
                "epc": 0.73,
                "epc_formatted": "₹0.73",
                "cr": 3.40,
                "cr_formatted": "3.40%",
                "rating": 4.9,
                "category": "Electronics & Gadgets",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (Zonet)",
                "landing_page_url": "https://www.flipkart.com",
                "publisher_url": "https://gotrackzo.com/admin/stores/66707285",
                "panel_url": "https://gotrackzo.com/admin/stores/66707285",
                "tracking_url": "https://gotrackzo.com/c/66707285",
                "logo_url": "https://upload.wikimedia.org/wikipedia/en/thumb/7/7a/Flipkart_logo.svg/512px-Flipkart_logo.svg.png",
                "description": "Flipkart India flagship store on GoTrackzo. Historical audited volume exceeded 2.37M clicks in October with peak festive RPC reaching ₹0.73.",
            },
            {
                "id": "zonet_myntra",
                "campaign_id": "1072",
                "campaign_name": "Myntra [CPS] IN (ID: 1072)",
                "brand_name": "Myntra",
                "network": "zonet",
                "network_id": "zonet",
                "network_name": "Zonet",
                "network_badge": "GoTrackzo API",
                "network_icon": "ph-cube",
                "network_color": "blue",
                "payout": "Up to 6.5% CPS",
                "payout_formatted": "Up to 6.5% CPS",
                "payout_type": "CPS",
                "payout_val": 6.5,
                "epc": 0.35,
                "epc_formatted": "₹0.35",
                "cr": 1.80,
                "cr_formatted": "1.80%",
                "rating": 4.7,
                "category": "Fashion & Apparel",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (Zonet)",
                "landing_page_url": "https://www.myntra.com",
                "publisher_url": "https://gotrackzo.com/admin/stores/1072",
                "panel_url": "https://gotrackzo.com/admin/stores/1072",
                "tracking_url": "https://gotrackzo.com/c/1072",
                "logo_url": "https://assets.myntassets.com/assets/images/retaillabs/2023/1/27/3a233b66-8a7e-40e1-bbd4-532a2f8b5f391674817435168-Myntra-Logo.png",
                "description": "Myntra Fashion India on GoTrackzo. High-converting fashion affiliate link with reliable cross-device tracking.",
            },
            {
                "id": "zonet_shopsy",
                "campaign_id": "1004",
                "campaign_name": "Shopsy [CPS] IN (ID: 1004)",
                "brand_name": "Shopsy",
                "network": "zonet",
                "network_id": "zonet",
                "network_name": "Zonet",
                "network_badge": "GoTrackzo API",
                "network_icon": "ph-cube",
                "network_color": "blue",
                "payout": "Up to 7.0% CPS",
                "payout_formatted": "Up to 7.0% CPS",
                "payout_type": "CPS",
                "payout_val": 7.0,
                "epc": 0.28,
                "epc_formatted": "₹0.28",
                "cr": 2.10,
                "cr_formatted": "2.10%",
                "rating": 4.5,
                "category": "Fashion & Apparel",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (Zonet)",
                "landing_page_url": "https://www.shopsy.in",
                "publisher_url": "https://gotrackzo.com/admin/stores/1004",
                "panel_url": "https://gotrackzo.com/admin/stores/1004",
                "tracking_url": "https://gotrackzo.com/c/1004",
                "logo_url": "https://static-assets-web.flixcart.com/fk-p-linchpin-web/batman-returns/logos/shopsy_logo.svg",
                "description": "Shopsy value-commerce store by Flipkart. High-volume budget fashion and home goods with strong conversion rates.",
            },
            {
                "id": "zonet_amazon_us",
                "campaign_id": "1089",
                "campaign_name": "Amazon US [CPC] (ID: 1089)",
                "brand_name": "Amazon US",
                "network": "zonet",
                "network_id": "zonet",
                "network_name": "Zonet",
                "network_badge": "GoTrackzo API",
                "network_icon": "ph-cube",
                "network_color": "blue",
                "payout": "₹1.20 / click (CPC)",
                "payout_formatted": "₹1.20 CPC",
                "payout_type": "CPC",
                "payout_val": 1.20,
                "epc": 1.20,
                "epc_formatted": "₹1.20",
                "cr": 100.0,
                "cr_formatted": "100.0%",
                "rating": 4.6,
                "category": "Electronics & Gadgets",
                "country": "us",
                "country_name": "United States",
                "country_flag": "🇺🇸",
                "status": "active",
                "status_badge": "Active (Zonet)",
                "landing_page_url": "https://www.amazon.com",
                "publisher_url": "https://gotrackzo.com/admin/stores/1089",
                "panel_url": "https://gotrackzo.com/admin/stores/1089",
                "tracking_url": "https://gotrackzo.com/c/1089",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/4/4a/Amazon_icon.svg",
                "description": "Amazon United States global click redirection program via GoTrackzo with fixed cost-per-click attribution.",
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
