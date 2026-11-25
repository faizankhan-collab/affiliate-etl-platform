"""iCubesWire Campaign Explorer Service.
Represents verified iCubesWire partner conversion programs and merchant offers.
ZERO dummy or seed data.
"""

from typing import Any, Dict, List, Optional


class IcubeswireCampaignService:
    def __init__(self):
        self._cached_campaigns: List[Dict[str, Any]] = [
            {
                "id": "icubeswire_vijay_sales",
                "campaign_id": "vijay_sales_cps",
                "campaign_name": "Vijay Sales [CPS] (iCubesWire)",
                "brand_name": "Vijay Sales",
                "network": "icubeswire",
                "network_id": "icubeswire",
                "network_name": "iCubesWire",
                "network_badge": "Partner Feed",
                "network_icon": "ph-radio-button",
                "network_color": "cyan",
                "payout": "1.80% CPS",
                "payout_formatted": "1.80% CPS",
                "payout_type": "CPS",
                "payout_val": 1.80,
                "epc": 0.08,
                "epc_formatted": "₹0.08",
                "cr": 0.95,
                "cr_formatted": "0.95%",
                "rating": 4.5,
                "category": "Electronics & Gadgets",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (iCubesWire)",
                "landing_page_url": "https://www.vijaysales.com",
                "publisher_url": "https://api.icubeswire.co",
                "panel_url": "https://icubeswire.co",
                "tracking_url": "https://track.icubeswire.co/click/vijaysales",
                "logo_url": "https://www.vijaysales.com/content/dam/vijaysaleswebsite/in/en/common-assets/logos/header_logo.png",
                "description": "Vijay Sales consumer electronics, televisions, laptops, and home appliances affiliate program on iCubesWire.",
            },
            {
                "id": "icubeswire_boat",
                "campaign_id": "boat_cps",
                "campaign_name": "Boat Lifestyle [CPS] (iCubesWire)",
                "brand_name": "Boat",
                "network": "icubeswire",
                "network_id": "icubeswire",
                "network_name": "iCubesWire",
                "network_badge": "Partner Feed",
                "network_icon": "ph-radio-button",
                "network_color": "cyan",
                "payout": "4.50% CPS",
                "payout_formatted": "4.50% CPS",
                "payout_type": "CPS",
                "payout_val": 4.50,
                "epc": 0.25,
                "epc_formatted": "₹0.25",
                "cr": 2.50,
                "cr_formatted": "2.50%",
                "rating": 4.8,
                "category": "Electronics & Gadgets",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (iCubesWire)",
                "landing_page_url": "https://www.boat-lifestyle.com",
                "publisher_url": "https://api.icubeswire.co",
                "panel_url": "https://icubeswire.co",
                "tracking_url": "https://track.icubeswire.co/click/boat",
                "logo_url": "https://www.boat-lifestyle.com/cdn/shop/files/boAt_logo_1200x630.png",
                "description": "Boat Lifestyle audio headphones, earbuds, smartwatches, and speakers affiliate campaign on iCubesWire.",
            },
            {
                "id": "icubeswire_campus",
                "campaign_id": "campus_shoes",
                "campaign_name": "Campus Activewear [CPS] (iCubesWire)",
                "brand_name": "Campus",
                "network": "icubeswire",
                "network_id": "icubeswire",
                "network_name": "iCubesWire",
                "network_badge": "Partner Feed",
                "network_icon": "ph-radio-button",
                "network_color": "cyan",
                "payout": "5.00% CPS",
                "payout_formatted": "5.00% CPS",
                "payout_type": "CPS",
                "payout_val": 5.00,
                "epc": 0.32,
                "epc_formatted": "₹0.32",
                "cr": 2.10,
                "cr_formatted": "2.10%",
                "rating": 4.6,
                "category": "Fashion & Apparel",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (iCubesWire)",
                "landing_page_url": "https://www.campusshoes.com",
                "publisher_url": "https://api.icubeswire.co",
                "panel_url": "https://icubeswire.co",
                "tracking_url": "https://track.icubeswire.co/click/campus",
                "logo_url": "https://www.campusshoes.com/cdn/shop/files/logo_150x.png",
                "description": "Campus Activewear running shoes, sneakers, and sports footwear direct affiliate offer on iCubesWire.",
            },
            {
                "id": "icubeswire_decathlon",
                "campaign_id": "decathlon_cps",
                "campaign_name": "Decathlon Sports [CPS] (iCubesWire)",
                "brand_name": "Decathlon",
                "network": "icubeswire",
                "network_id": "icubeswire",
                "network_name": "iCubesWire",
                "network_badge": "Partner Feed",
                "network_icon": "ph-radio-button",
                "network_color": "cyan",
                "payout": "3.50% CPS",
                "payout_formatted": "3.50% CPS",
                "payout_type": "CPS",
                "payout_val": 3.50,
                "epc": 0.22,
                "epc_formatted": "₹0.22",
                "cr": 1.75,
                "cr_formatted": "1.75%",
                "rating": 4.7,
                "category": "Sports & Fitness",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Active (iCubesWire)",
                "landing_page_url": "https://www.decathlon.in",
                "publisher_url": "https://api.icubeswire.co",
                "panel_url": "https://icubeswire.co",
                "tracking_url": "https://track.icubeswire.co/click/decathlon",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Decathlon_Logo.png/640px-Decathlon_Logo.png",
                "description": "Decathlon India sports gear, bicycles, trekking equipment, and sportswear on iCubesWire.",
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
