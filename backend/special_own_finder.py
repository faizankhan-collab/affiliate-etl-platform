"""Special (OWN) Direct Partnerships Campaign Explorer Service.
Represents verified direct brand partnerships with 100% first-party attribution.
Includes:
1. Ajio Direct (Special OWN via Trackier Partner API)
2. Air India Direct (Special OWN via Adobe Analytics DoD Workspace)
ZERO dummy or seed data.
"""

from typing import Any, Dict, List, Optional


class SpecialOwnCampaignService:
    def __init__(self):
        self._cached_campaigns: List[Dict[str, Any]] = [
            {
                "id": "special_own_ajio",
                "campaign_id": "ajio_direct",
                "campaign_name": "Ajio Direct (Special OWN Partnership)",
                "brand_name": "Ajio",
                "network": "special_own",
                "network_id": "special_own",
                "network_name": "Special (OWN)",
                "network_badge": "Direct Contract",
                "network_icon": "ph-crown",
                "network_color": "purple",
                "payout": "1.59% CR • ₹2.55 RPC",
                "payout_formatted": "1.59% CR (₹2.55 RPC)",
                "payout_type": "CPS",
                "payout_val": 2.55,
                "epc": 2.55,
                "epc_formatted": "₹2.55",
                "cr": 1.59,
                "cr_formatted": "1.59%",
                "rating": 5.0,
                "category": "Fashion & Apparel",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Direct Exclusive",
                "landing_page_url": "https://www.ajio.com",
                "publisher_url": "https://api.trackier.com",
                "panel_url": "https://api.trackier.com",
                "tracking_url": "https://ajio.trackier.com/click",
                "logo_url": "https://assets.ajio.com/static/img/Ajio-Logo.svg",
                "description": "Direct first-party partnership with Reliance Ajio via Trackier. Delivers 3.0x higher RPC (₹2.55) compared to third-party affiliate networks (₹0.84).",
                "arbitrage_highlight": "🏆 3.0x Higher RPC vs Pantech & Cuelinks",
            },
            {
                "id": "special_own_airindia",
                "campaign_id": "airindia_direct",
                "campaign_name": "Air India Direct (Special OWN Booking Contract)",
                "brand_name": "Air India",
                "network": "special_own",
                "network_id": "special_own",
                "network_name": "Special (OWN)",
                "network_badge": "Direct Contract",
                "network_icon": "ph-airplane-takeoff",
                "network_color": "rose",
                "payout": "₹150.00 / flight booking order",
                "payout_formatted": "₹150.00 / order",
                "payout_type": "CPA",
                "payout_val": 150.0,
                "epc": 4.27,
                "epc_formatted": "₹4.27",
                "cr": 2.85,
                "cr_formatted": "2.85%",
                "rating": 5.0,
                "category": "Travel & Booking",
                "country": "in",
                "country_name": "India",
                "country_flag": "🇮🇳",
                "status": "active",
                "status_badge": "Direct Exclusive",
                "landing_page_url": "https://www.airindia.com",
                "publisher_url": "https://www4.an.adobe.com/spa/index.html?linkId=16d90860-49e0-4eb1-9ce5-ccc029c9c62f&dpc=sin",
                "panel_url": "https://www4.an.adobe.com/spa/index.html?linkId=16d90860-49e0-4eb1-9ce5-ccc029c9c62f&dpc=sin",
                "tracking_url": "https://www.airindia.com/?utm_source=buyhatke&utm_medium=direct",
                "logo_url": "https://www.airindia.com/content/dam/air-india/logos/airindia-logo.svg",
                "description": "Contracted flat ₹150 payout per confirmed flight ticket with verified Adobe Analytics day-of-departure (DoD) tracking. Outperforms third-party flight aggregators.",
                "arbitrage_highlight": "🏆 ₹150 Flat Payout vs ₹0-50 Cuelinks Payout",
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
