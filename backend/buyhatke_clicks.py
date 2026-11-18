"""Buyhatke Live Internal Clicks Service.
Direct integration with the official Buyhatke Tracking Admin Panel API:
https://api.buyhatke.com/buyhatke_tracking/tracking_admin_panel/affiliate_stats_api.php

Provides real-time internal click volume, brand traffic distributions,
network breakdowns, and daily timeseries data for portfolio reconciliation.
ZERO dummy or seed data.
"""

from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
import pandas as pd
import requests
from requests.adapters import HTTPAdapter

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("buyhatke.clicks")

DEFAULT_API_URL = "https://api.buyhatke.com/buyhatke_tracking/tracking_admin_panel/affiliate_stats_api.php"
DEFAULT_API_KEY = "f8c8dfdf17e80be9426efcac96d5e6bec37de301454649b07fdc55052f227482"


class BuyhatkeClicksService:
    """Service to fetch and parse live internal clicks from the Buyhatke tracking platform."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        self.api_key = (
            api_key
            or os.getenv("BUYHATKE_API_KEY")
            or DEFAULT_API_KEY
        )
        self.api_url = (
            api_url
            or os.getenv("BUYHATKE_STATS_URL")
            or DEFAULT_API_URL
        )

        self.headers = {
            "X-API-Key": self.api_key,
            "User-Agent": "Buyhatke-ETL-Reconciler/1.0",
            "Accept": "application/json",
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=1)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._cache_ttl = 180.0  # 3 minutes cache for live stats

    def fetch_raw_stats(
        self,
        from_date: str,
        upto_date: str,
        website: Optional[str] = None,
        group_by: Optional[str] = "position,affiliate_network",
        order_by: Optional[str] = "internal_clicks",
        order: Optional[str] = "DESC",
        page_size: int = 1000,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Execute an authenticated request against Buyhatke affiliate_stats_api.php.
        """
        params: Dict[str, Any] = {
            "from_date": from_date,
            "upto_date": upto_date,
            "page_size": page_size,
            "page": page,
        }
        if website:
            params["website"] = website.strip()
        if group_by:
            params["group_by"] = group_by
        if order_by:
            params["order_by"] = order_by
        if order:
            params["order"] = order

        cache_key = f"{from_date}|{upto_date}|{website or ''}|{group_by or ''}|{order_by or ''}|{order or ''}|{page}|{page_size}"
        now = time.time()
        if cache_key in self._cache:
            ts, cached_val = self._cache[cache_key]
            if now - ts < self._cache_ttl:
                return cached_val

        try:
            resp = self.session.get(self.api_url, params=params, timeout=12)
            if resp.status_code != 200:
                logger.error(f"Buyhatke API HTTP error: {resp.status_code} - {resp.text[:200]}")
                return {
                    "success": False,
                    "error": f"HTTP {resp.status_code}: {resp.text[:150]}",
                    "data": {},
                }

            data = resp.json()
            if not data.get("success", False):
                err_msg = data.get("error", "Unknown API error")
                logger.warning(f"Buyhatke API returned failure: {err_msg}")
                return {"success": False, "error": err_msg, "data": {}}

            self._cache[cache_key] = (now, data)
            return data

        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timed out after 12s", "data": {}}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e), "data": {}}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}", "data": {}}

    def fetch_all_brand_network_clicks(
        self,
        from_date: str,
        upto_date: str,
        website: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch all brand & network click allocations across the date range.
        Handles pagination automatically if records exceed page_size (1000).
        """
        all_rows: List[Dict[str, Any]] = []
        page = 1
        total_clicks = 0
        filters: Dict[str, Any] = {}

        while True:
            resp = self.fetch_raw_stats(
                from_date=from_date,
                upto_date=upto_date,
                website=website,
                group_by="position,affiliate_network",
                order_by="internal_clicks",
                order="DESC",
                page_size=1000,
                page=page,
            )

            if not resp.get("success"):
                return {
                    "success": False,
                    "error": resp.get("error", "Failed to retrieve internal clicks"),
                    "total_clicks": 0,
                    "rows": [],
                }

            d = resp.get("data", {})
            filters = d.get("filters", {})
            totals = d.get("totals", {})
            total_clicks = totals.get("internal_clicks", total_clicks)

            rows = d.get("rows", [])
            all_rows.extend(rows)

            pagination = d.get("pagination", {})
            total_pages = pagination.get("total_pages", 1)

            if page >= total_pages or len(rows) == 0:
                break
            page += 1

        return {
            "success": True,
            "from_date": from_date,
            "upto_date": upto_date,
            "total_clicks": total_clicks,
            "total_rows": len(all_rows),
            "filters": filters,
            "rows": all_rows,
        }

    def get_clicks_dataframe(
        self,
        from_date: str,
        upto_date: str,
        website: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch live clicks and format directly into standardized Master Sheet DataFrame:
        Columns:
        - WEBSITE / BRAND
        - AFFILIATE NETWORK
        - SUM of INTERNAL CLICKS
        - POSITION (Buyhatke merchant ID)
        - NETWORK_ID
        """
        res = self.fetch_all_brand_network_clicks(from_date, upto_date, website)
        if not res.get("success") or not res.get("rows"):
            return pd.DataFrame(
                columns=[
                    "WEBSITE / BRAND",
                    "AFFILIATE NETWORK",
                    "SUM of INTERNAL CLICKS",
                    "POSITION",
                    "NETWORK_ID",
                ]
            )

        records = []
        for r in res["rows"]:
            raw_web = r.get("website_name")
            pos = r.get("position")
            raw_net = r.get("affiliate_network_name")
            net_id = r.get("affiliate_network_id")
            clicks = int(r.get("internal_clicks", 0) or 0)

            # Standardize empty/null brand labels
            brand_name = raw_web.strip() if raw_web else f"Unknown Merchant (ID {pos})" if pos else "Direct Traffic"
            network_name = raw_net.strip() if raw_net else "Direct / Untracked"

            records.append(
                {
                    "WEBSITE / BRAND": brand_name,
                    "AFFILIATE NETWORK": network_name,
                    "SUM of INTERNAL CLICKS": clicks,
                    "POSITION": pos,
                    "NETWORK_ID": net_id,
                }
            )

        df = pd.DataFrame(records)
        return df

    def get_daily_timeseries(
        self,
        from_date: str,
        upto_date: str,
        website: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch daily click trends for a brand or the whole portfolio over time.
        Ideal for charts, anomaly detection, and detecting traffic drops.
        """
        resp = self.fetch_raw_stats(
            from_date=from_date,
            upto_date=upto_date,
            website=website,
            group_by="date",
            order_by="date",
            order="ASC",
            page_size=365,
        )
        if not resp.get("success"):
            return []

        rows = resp.get("data", {}).get("rows", [])
        timeseries = []
        for r in rows:
            timeseries.append(
                {
                    "date": r.get("date"),
                    "week_day": r.get("week_day"),
                    "internal_clicks": int(r.get("internal_clicks", 0) or 0),
                }
            )
        return timeseries

    def get_top_brands_summary(
        self,
        from_date: str,
        upto_date: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetch high-volume brands aggregated by position for executive viewpoints.
        """
        resp = self.fetch_raw_stats(
            from_date=from_date,
            upto_date=upto_date,
            group_by="position",
            order_by="internal_clicks",
            order="DESC",
            page_size=limit,
        )
        if not resp.get("success"):
            return []

        rows = resp.get("data", {}).get("rows", [])
        results = []
        for r in rows:
            pos = r.get("position")
            wname = r.get("website_name") or f"Merchant {pos}"
            clicks = int(r.get("internal_clicks", 0) or 0)
            nets = [n.get("affiliate_network_name") for n in r.get("affiliate_networks", []) if isinstance(n, dict)]
            results.append(
                {
                    "position": pos,
                    "website_name": wname,
                    "internal_clicks": clicks,
                    "networks": nets,
                }
            )
        return results
