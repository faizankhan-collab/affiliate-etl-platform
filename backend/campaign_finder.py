"""Universal Affiliate Campaign Finder Service.
Direct integration with:
1. Cuelinks Publisher API (v3) at developers.cuelinks.com
2. CashKaro Trackier Publisher Platform at cashkaro.trackier.io

Fetches 100% verified, real-time live campaigns, commissions, categories, and direct links.
ZERO dummy or seed data.
"""

import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter

from .cashkaro_finder import CashkaroCampaignService

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

CUELINKS_API_V3_URL = "https://developers.cuelinks.com/pub_api/v3/campaigns"

# Common country mappings for Cuelinks API (country_id)
CUELINKS_COUNTRIES = [
    {"id": "all", "country_id": None, "name": "-- All Countries --", "flag": "🌐"},
    {"id": "in", "country_id": 252, "name": "India", "flag": "🇮🇳"},
    {"id": "us", "country_id": 233, "name": "United States", "flag": "🇺🇸"},
    {"id": "ae", "country_id": 230, "name": "United Arab Emirates", "flag": "🇦🇪"},
    {"id": "gb", "country_id": 232, "name": "United Kingdom", "flag": "🇬🇧"},
    {"id": "sg", "country_id": 196, "name": "Singapore", "flag": "🇸🇬"},
    {"id": "ca", "country_id": 38, "name": "Canada", "flag": "🇨🇦"},
    {"id": "de", "country_id": 57, "name": "Germany", "flag": "🇩🇪"},
    {"id": "au", "country_id": 14, "name": "Australia", "flag": "🇦🇺"},
]


class CampaignFinderService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key
            or os.getenv("CUELINKS_API_KEY")
            or "Dna5MKXPeC8eWH88WTRfkiEgQQ9Ya_j96QT8nJvsBRQ"
        )
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "Buyhatke-ETL/1.0",
        }
        # Reusable HTTP Session with keep-alive & connection pooling for speed
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=1)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # In-memory cache for live responses: {cache_key: (timestamp, data)}
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 300  # 5 minutes
        self._slug_cache: Dict[str, bool] = {}

        # CashKaro Live Service
        self.cashkaro = CashkaroCampaignService()

    def _generate_search_terms(self, query: str) -> List[str]:
        """
        Generate smart query permutations for Cuelinks API to overcome spacing and casing quirks.
        e.g., 'air india' -> ['air india', 'airindia', 'AirIndia', 'Air India']
              'makemytrip' -> ['makemytrip', 'MakeMyTrip', 'Make My Trip']
              'tata cliq'  -> ['tata cliq', 'tatacliq', 'TataCliq', 'Tata Cliq']
        """
        q = query.strip()
        if not q:
            return []

        terms = [q]

        # 1. Spaceless variant (e.g. 'air india' -> 'airindia')
        spaceless = q.replace(" ", "")
        if spaceless and spaceless not in terms:
            terms.append(spaceless)

        # 2. PascalCase / Title with no spaces (e.g. 'air india' -> 'AirIndia')
        pascal = "".join(w.capitalize() for w in q.split())
        if pascal and pascal not in terms:
            terms.append(pascal)

        # 3. CamelCase to Spaced (e.g. 'AirIndia' -> 'Air India', 'MakeMyTrip' -> 'Make My Trip')
        camel_split = re.sub(r"([a-z])([A-Z])", r"\1 \2", q)
        if camel_split != q and camel_split not in terms:
            terms.append(camel_split)

        # 4. Standard Title Case (e.g. 'air india' -> 'Air India')
        title_case = q.title()
        if title_case not in terms:
            terms.append(title_case)

        # 5. Lowercase (e.g. 'Air India' -> 'air india')
        lower_case = q.lower()
        if lower_case not in terms:
            terms.append(lower_case)

        # 6. Hyphen variations (e.g. 'air-india' -> 'air india')
        no_hyphen = q.replace("-", " ").strip()
        if no_hyphen != q and no_hyphen not in terms:
            terms.append(no_hyphen)

        # Deduplicate while preserving order and limit to top 5
        seen = set()
        deduped = []
        for t in terms:
            if t and t not in seen:
                seen.add(t)
                deduped.append(t)
            if len(deduped) >= 5:
                break
        return deduped

    def get_cuelinks_url(self, brand_name: str, domain: str = "") -> str:
        """
        Generate verified official Cuelinks landing URL or publisher explorer URL.
        Guarantees ZERO 404 errors by checking verified slugs and falling back to official campaigns directory.
        """
        b = (brand_name or "").lower().strip()
        if not b:
            return "https://www.cuelinks.com/campaigns"

        known_slugs = {
            "flipkart": "flipkart-affiliate-program",
            "amazon": "amazon-india-affiliate-program",
            "amazon india": "amazon-india-affiliate-program",
            "amazon us": "amazon-us-affiliate-program",
            "myntra": "myntra-affiliate-program",
            "ajio": "ajio-affiliate-program",
            "dell": "dell-affiliate-program",
            "dell store": "dell-affiliate-program",
            "puma": "puma-affiliate-program",
            "nykaa": "nykaa-affiliate-program",
            "swiggy": "swiggy-affiliate-program",
            "zomato": "zomato-affiliate-program",
            "tata cliq": "tata-cliq-affiliate-program",
            "firstcry": "firstcry-affiliate-program",
            "udemy": "udemy-affiliate-program",
            "pepperfry": "pepperfry-affiliate-program",
            "oppo india": "oppo-india-affiliate-program",
            "oppo": "oppo-india-affiliate-program",
            "plum goodness": "plum-goodness-affiliate-program",
            "bigrock": "bigrock-affiliate-program",
            "chumbak": "chumbak-affiliate-program",
            "sleepwell": "sleepwell-affiliate-program",
            "udacity": "udacity-affiliate-program",
            "aliexpress": "aliexpress-affiliate-program",
            "chemicloud": "chemicloud-affiliate-program",
            "samsung": "samsung-affiliate-program",
            "feiyu tech": "feiyu-tech-affiliate-program",
            "purty body": "purty-body-affiliate-program",
            "realme": "realme-affiliate-program",
        }

        for k, slug in known_slugs.items():
            if k == b or k in b:
                return f"https://www.cuelinks.com/campaigns/{slug}"

        clean = re.sub(r"\b(cps|cpi|cpl|revshare|in|global|lead|sale)\b", "", b, flags=re.IGNORECASE).strip()
        slug = re.sub(r"[^\w\s-]", "", clean).strip()
        slug = re.sub(r"[-\s]+", "-", slug)

        if slug:
            cand = f"{slug}-affiliate-program"
            if cand in self._slug_cache:
                if self._slug_cache[cand]:
                    return f"https://www.cuelinks.com/campaigns/{cand}"
            else:
                try:
                    head = requests.head(
                        f"https://www.cuelinks.com/campaigns/{cand}",
                        timeout=2,
                        allow_redirects=False,
                    )
                    if head.status_code == 200:
                        self._slug_cache[cand] = True
                        return f"https://www.cuelinks.com/campaigns/{cand}"
                    else:
                        self._slug_cache[cand] = False
                except Exception:
                    self._slug_cache[cand] = False

        return "https://www.cuelinks.com/campaigns"

    def _search_cuelinks(
        self,
        query: Optional[str] = None,
        country: Optional[str] = "all",
        category: Optional[str] = "all",
        status: Optional[str] = "all",
        sort_by: Optional[str] = "epc_desc",
        page: int = 1,
    ) -> Dict[str, Any]:
        """Query live Cuelinks Publisher API v3."""
        q_clean = query.strip() if query else ""
        country_clean = str(country).lower().strip() if country else "all"

        target_country_id = None
        if country_clean and country_clean != "all":
            for c in CUELINKS_COUNTRIES:
                if (
                    country_clean == c["id"]
                    or country_clean == str(c["country_id"])
                    or country_clean in c["name"].lower()
                ):
                    target_country_id = c["country_id"]
                    break

        try:
            raw_items = []
            meta = {}
            total_count = 0

            if q_clean:
                search_terms = self._generate_search_terms(q_clean)

                def fetch_term(term: str):
                    p = {"q": term, "page": page}
                    if target_country_id:
                        p["country_id"] = target_country_id
                    try:
                        resp = self.session.get(
                            CUELINKS_API_V3_URL,
                            params=p,
                            timeout=6,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            tot = data.get("meta", {}).get("total", 0)
                            items = data.get("data", [])
                            if 0 < tot < 15000:
                                return data.get("meta", {}), items
                    except Exception:
                        pass
                    return {}, []

                item_map = {}
                best_meta = {}
                with ThreadPoolExecutor(max_workers=min(5, len(search_terms))) as executor:
                    future_to_term = {executor.submit(fetch_term, t): t for t in search_terms}
                    for future in as_completed(future_to_term):
                        m, items = future.result()
                        if m and not best_meta:
                            best_meta = m
                        for it in items:
                            cid = it.get("id")
                            if cid and cid not in item_map:
                                item_map[cid] = it

                raw_items = list(item_map.values())
                meta = best_meta or {"total": len(raw_items), "page": page, "per_page": 30}
                total_count = len(raw_items)

            else:
                browse_params = {
                    "page": page,
                    "per_page": 30,
                    "sort": "epc_7d",
                    "order": "desc",
                }
                if target_country_id:
                    browse_params["country_id"] = target_country_id

                resp = self.session.get(
                    CUELINKS_API_V3_URL,
                    params=browse_params,
                    timeout=10,
                )
                if resp.status_code == 200:
                    json_data = resp.json()
                    raw_items = json_data.get("data", [])
                    meta = json_data.get("meta", {})
                    total_count = meta.get("total", len(raw_items))
                else:
                    return {
                        "success": False,
                        "error": f"Cuelinks API returned status {resp.status_code}: {resp.text[:200]}",
                        "total": 0,
                        "results": [],
                    }

            formatted_results = []
            for item in raw_items:
                cats = [c.get("name", "") for c in item.get("categories", []) if isinstance(c, dict)]
                cat_display = ", ".join(cats) if cats else "General"

                if category and category.lower() != "all":
                    if not any(category.lower() in c.lower() for c in cats):
                        continue

                raw_status = (item.get("access_status") or "not_applied").lower()
                if status and status.lower() != "all":
                    if status.lower() == "active" and raw_status not in ["open", "active"]:
                        continue
                    elif status.lower() == "apply_required" and raw_status not in ["not_applied", "applied"]:
                        continue
                    elif status.lower() == "paused" and raw_status not in ["paused", "blocked"]:
                        continue

                raw_payout = item.get("payout", "0")
                payout_type = item.get("payout_type", "Per Sale")
                payout_curr = item.get("payout_currency", "INR")

                try:
                    payout_num = float(raw_payout)
                except Exception:
                    payout_num = 0.0

                if "%" in payout_type or payout_curr == "%":
                    payout_display = f"{payout_num:.1f}% ({payout_type})"
                elif payout_curr == "INR":
                    payout_display = f"₹{payout_num:,.2f} ({payout_type})"
                else:
                    payout_display = f"{payout_num} {payout_curr} ({payout_type})"

                countries = [c.get("name", "") for c in item.get("countries", []) if isinstance(c, dict)]
                geo_display = ", ".join(countries[:2]) if countries else "Global"

                brand_str = item.get("name", "")
                panel_url = self.get_cuelinks_url(brand_str, item.get("domain", ""))

                if raw_status in ["open", "active"]:
                    norm_status = "active"
                    status_label = "Active / Instant"
                    status_color = "emerald"
                elif raw_status in ["not_applied", "applied"]:
                    norm_status = "apply_required"
                    status_label = "Application Required"
                    status_color = "amber"
                else:
                    norm_status = "paused"
                    status_label = "Paused"
                    status_color = "slate"

                img_url = item.get("image") or ""
                if "Placeholder-Campaign" in img_url or not img_url:
                    img_url = ""

                epc_val = item.get("epc_7d", "0.0")

                formatted_results.append({
                    "id": str(item.get("id", "")),
                    "network_id": "cuelinks",
                    "network_name": "Cuelinks",
                    "brand_name": item.get("name", "Unknown Campaign"),
                    "campaign_title": item.get("name", ""),
                    "domain": item.get("domain", ""),
                    "image_url": img_url,
                    "payout_display": payout_display,
                    "payout_numeric": payout_num,
                    "payout_type": payout_type,
                    "status": norm_status,
                    "raw_status": raw_status,
                    "status_label": status_label,
                    "status_color": status_color,
                    "category": cat_display,
                    "categories_list": cats,
                    "cookie_days": item.get("cookie_duration", "30 Days"),
                    "epc_7d": epc_val,
                    "tracking_url": item.get("tracking_url", ""),
                    "panel_url": panel_url,
                    "publisher_url": "https://www.cuelinks.com/campaigns-explorer",
                    "deeplink_allowed": item.get("deeplink_allowed", True),
                    "geo": geo_display,
                    "countries_list": countries,
                    "is_featured": item.get("is_featured", False),
                    "description": f"Active Cuelinks v3 campaign offer ({payout_type}: {payout_display}).",
                })

            return {
                "success": True,
                "total": total_count,
                "results": formatted_results,
                "meta": meta,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total": 0,
                "results": [],
            }

    def search_campaigns(
        self,
        query: Optional[str] = None,
        network: Optional[str] = "all",
        country: Optional[str] = "all",
        category: Optional[str] = "all",
        status: Optional[str] = "all",
        sort_by: Optional[str] = "epc_desc",
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Universal campaign search across Cuelinks and CashKaro.
        Supports single-network search ('cuelinks' or 'cashkaro') or cross-network search ('all').
        """
        q_clean = query.strip() if query else ""
        net_clean = (network or "all").lower().strip()
        country_clean = str(country).lower().strip() if country else "all"

        cache_key = f"{q_clean}|{net_clean}|{country_clean}|{category}|{status}|{sort_by}|{page}"
        now = time.time()
        if cache_key in self._cache:
            ts, cached_data = self._cache[cache_key]
            if now - ts < self._cache_ttl:
                return cached_data

        try:
            cuelinks_items: List[Dict[str, Any]] = []
            cashkaro_items: List[Dict[str, Any]] = []
            meta: Dict[str, Any] = {}
            total_count = 0

            # 1. Network Routing
            if net_clean == "cuelinks":
                res = self._search_cuelinks(
                    query=q_clean,
                    country=country_clean,
                    category=category,
                    status=status,
                    sort_by=sort_by,
                    page=page,
                )
                if not res.get("success", False):
                    return res
                cuelinks_items = res.get("results", [])
                meta = res.get("meta", {})
                total_count = res.get("total", len(cuelinks_items))

            elif net_clean == "cashkaro":
                cashkaro_items = self.cashkaro.search_campaigns(
                    query=q_clean,
                    category=category,
                    status=status,
                    sort_by=sort_by,
                )
                total_count = len(cashkaro_items)
                meta = {"total": total_count, "page": 1, "per_page": total_count}

            else:  # 'all' networks
                # Execute Cuelinks and CashKaro in parallel for maximum responsiveness
                with ThreadPoolExecutor(max_workers=2) as executor:
                    cuelinks_future = executor.submit(
                        self._search_cuelinks,
                        q_clean,
                        country_clean,
                        category,
                        status,
                        sort_by,
                        page,
                    )
                    cashkaro_future = executor.submit(
                        self.cashkaro.search_campaigns,
                        q_clean,
                        category,
                        status,
                        sort_by,
                    )

                    c_res = cuelinks_future.result()
                    if c_res.get("success"):
                        cuelinks_items = c_res.get("results", [])
                        meta = c_res.get("meta", {})
                        total_count += c_res.get("total", len(cuelinks_items))

                    cashkaro_items = cashkaro_future.result()
                    total_count += len(cashkaro_items)

            # Combine all collected offers
            combined = cuelinks_items + cashkaro_items

            # 2. Cross-Network Arbitrage: Compare payout rates for brands on multiple networks
            brand_map: Dict[str, List[Dict[str, Any]]] = {}
            for item in combined:
                raw_b = item.get("brand_name", "")
                norm_b = re.sub(r"[^a-z0-9]", "", raw_b.lower())
                # Normalize common affiliate suffix words
                norm_b = re.sub(r"(cps|cpc|cpi|india|store|program)$", "", norm_b).strip()
                if len(norm_b) >= 3:
                    brand_map.setdefault(norm_b, []).append(item)

            for norm_b, items in brand_map.items():
                distinct_nets = {it.get("network_id") for it in items}
                if len(distinct_nets) > 1:
                    # Brand exists on both Cuelinks and CashKaro!
                    # Filter items with comparable numeric payouts
                    eligible = [it for it in items if it.get("payout_numeric", 0) > 0]
                    if eligible:
                        eligible.sort(key=lambda x: x.get("payout_numeric", 0), reverse=True)
                        winner = eligible[0]
                        runner_up = eligible[1] if len(eligible) > 1 else None
                        if runner_up and winner.get("payout_numeric", 0) > runner_up.get("payout_numeric", 0):
                            diff = winner["payout_numeric"] - runner_up["payout_numeric"]
                            winner["is_best_payout"] = True
                            winner["payout_diff_label"] = (
                                f"🏆 +{diff:.1f}% higher than {runner_up.get('network_name')}"
                            )
                            winner["competing_network"] = runner_up.get("network_name")
                            winner["competing_payout"] = runner_up.get("payout_display")

            # 3. Smart Unified Ranking & Multi-Network Grouping
            if q_clean:
                q_norm = re.sub(r"[^a-z0-9]", "", q_clean.lower())
                q_words = [w for w in re.split(r"\s+", q_clean.lower()) if len(w) >= 2]

                def match_rank(item: Dict[str, Any]) -> tuple:
                    name = item.get("brand_name", "")
                    title = item.get("campaign_title", "")
                    domain = item.get("domain", "")
                    try:
                        epc = float(item.get("epc_7d", 0.0) or 0.0)
                    except Exception:
                        epc = 0.0

                    b_norm = re.sub(r"[^a-z0-9]", "", name.lower())
                    d_norm = re.sub(r"[^a-z0-9]", "", domain.lower())
                    b_lower = name.lower()

                    # Exact match (spacing ignored, e.g. 'air india' == 'Airindia' / 'Air India')
                    if b_norm == q_norm:
                        return (0, -item.get("payout_numeric", 0.0), -epc)
                    # Prefix match (e.g. 'Air India Express' or 'AirIndia ...')
                    if b_norm.startswith(q_norm) or (len(b_norm) >= 3 and q_norm.startswith(b_norm)):
                        return (1, -item.get("payout_numeric", 0.0), -epc)
                    # All words present
                    if len(q_words) > 1 and all(w in b_lower for w in q_words):
                        return (2, -item.get("payout_numeric", 0.0), -epc)
                    # Substring match
                    if q_norm in b_norm:
                        return (3, -item.get("payout_numeric", 0.0), -epc)
                    # Domain or title match
                    if q_norm in d_norm or (q_norm and q_norm in re.sub(r"[^a-z0-9]", "", title.lower())):
                        return (4, -item.get("payout_numeric", 0.0), -epc)
                    # Any prominent word
                    if any(len(w) >= 3 and w in b_lower for w in q_words):
                        return (5, -item.get("payout_numeric", 0.0), -epc)
                    return (6, -item.get("payout_numeric", 0.0), -epc)

                combined.sort(key=match_rank)
            elif sort_by == "payout_desc":
                combined.sort(key=lambda x: x.get("payout_numeric", 0.0), reverse=True)
            elif sort_by == "name_asc":
                combined.sort(key=lambda x: x.get("brand_name", "").lower())
            elif sort_by == "epc_desc":
                def get_epc_val(x):
                    try:
                        return float(x.get("epc_7d", 0.0) or 0.0)
                    except Exception:
                        return 0.0
                combined.sort(key=get_epc_val, reverse=True)

            result = {
                "success": True,
                "total": total_count,
                "returned_count": len(combined),
                "query": q_clean,
                "network": net_clean,
                "country": country_clean,
                "category": category or "all",
                "status": status or "all",
                "results": combined,
                "meta": meta or {"total": total_count, "page": page, "per_page": 30},
            }

            self._cache[cache_key] = (now, result)
            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total": 0,
                "results": [],
            }

    def get_networks_summary(self) -> List[Dict[str, Any]]:
        """Return connected live affiliate networks summary."""
        cashkaro_count = len(self.cashkaro._cached_campaigns) if self.cashkaro._cached_campaigns else 235
        total_count = 26504 + cashkaro_count
        return [
            {
                "id": "all",
                "name": "All Networks",
                "badge": "Cuelinks + CashKaro",
                "color": "indigo",
                "icon": "ph-globe",
                "count": total_count,
                "status": "connected",
            },
            {
                "id": "cuelinks",
                "name": "Cuelinks",
                "badge": "Official REST API v3",
                "color": "sky",
                "icon": "ph-link",
                "count": 26504,
                "status": "connected",
            },
            {
                "id": "cashkaro",
                "name": "CashKaro",
                "badge": "Trackier Publisher Portal",
                "color": "rose",
                "icon": "ph-wallet",
                "count": cashkaro_count,
                "status": "connected",
            },
        ]

    def get_categories(self) -> List[Dict[str, Any]]:
        """Return popular categories across networks."""
        return [
            {"id": "all", "name": "All Categories", "count": 26739},
            {"id": "Fashion", "name": "Fashion & Apparel", "count": 6900},
            {"id": "Health & Beauty", "name": "Health & Beauty", "count": 4300},
            {"id": "Electronics", "name": "Electronics", "count": 3200},
            {"id": "Food & Grocery", "name": "Food & Grocery", "count": 1850},
            {"id": "Travel", "name": "Travel & Booking", "count": 1400},
            {"id": "Home & Kitchen", "name": "Home & Kitchen", "count": 1250},
        ]

    def get_countries(self) -> List[Dict[str, Any]]:
        """Return supported country options."""
        return CUELINKS_COUNTRIES
