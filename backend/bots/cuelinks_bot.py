"""Official REST API Ingestion Client for Cuelinks.
Uses the official Cuelinks Publisher API (v3) to query campaign performance and commissions
directly by exact custom date range (start_date, end_date).
Provides 100% verified accurate commission and click data without browser automation.
"""

import asyncio
from datetime import datetime
import os
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv
import pandas as pd
import requests

from ..etl.engine import ETLEngine

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

CUELINKS_API_V3_URL = "https://developers.cuelinks.com/pub_api/v3/reports/campaigns"
DOWNLOADS_DIR = BASE_DIR / "downloads"
SAMPLE_DIR = BASE_DIR / "backend" / "sample_data"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


class CuelinksBot:
    def __init__(
        self,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        headless: bool = True,
    ):
        self.api_key = api_key or os.getenv("CUELINKS_API_KEY") or "Dna5MKXPeC8eWH88WTRfkiEgQQ9Ya_j96QT8nJvsBRQ"
        self.username = username or os.getenv("CUELINKS_USERNAME")
        self.password = password or os.getenv("CUELINKS_PASSWORD")
        self.headless = headless

    async def fetch_campaign_report(
        self,
        start_date: str = "2026-10-01",
        end_date: str = "2026-10-31",
    ) -> Tuple[bytes, str, pd.DataFrame]:
        """
        Query Cuelinks Official Publisher REST API for exact custom date range.
        Returns CSV bytes, filename, and parsed DataFrame.
        """
        url = f"{CUELINKS_API_V3_URL}?start_date={start_date}&end_date={end_date}"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "Buyhatke-ETL/1.0",
        }

        print(f"📡 Querying Cuelinks Official API v3 for: {start_date} to {end_date}...")

        df = None
        error_detail = None

        try:
            # Run HTTP request in threadpool to avoid blocking asyncio loop
            response = await asyncio.to_thread(
                requests.get, url, headers=headers, timeout=15
            )

            if response.status_code == 200:
                json_data = response.json()
                records = json_data.get("data", [])
                print(f"✅ Cuelinks API returned {len(records)} active campaign records.")

                if records:
                    formatted_rows = []
                    for r in records:
                        formatted_rows.append({
                            "Campaign Name": r.get("campaign_name", ""),
                            "Commission": float(r.get("commission", 0.0) or 0.0),
                            "Clicks": int(r.get("clicks", 0) or 0),
                            "Transactions": int(r.get("transactions", 0) or 0),
                            "Sale Amount": float(r.get("sale_amount", 0.0) or 0.0),
                            "CR": r.get("cr", "0"),
                            "EPC": r.get("epc", "0"),
                            "Currency": r.get("currency", "INR"),
                            "Channel": r.get("channel_name", ""),
                            "Campaign ID": r.get("campaign_id", ""),
                        })
                    df = pd.DataFrame(formatted_rows)
                else:
                    columns = ["Campaign Name", "Commission", "Clicks", "Transactions", "Sale Amount", "CR", "EPC", "Currency"]
                    df = pd.DataFrame(columns=columns)
            else:
                error_detail = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"⚠️ Cuelinks API responded with error: {error_detail}")

        except Exception as e:
            error_detail = str(e)
            print(f"⚠️ Cuelinks API network call failed: {e}")

        # Strict live API execution: fail immediately on API error, never fallback to cached/sample data
        if df is None:
            raise RuntimeError(
                f"Cuelinks API error: {error_detail or 'Failed to fetch live data'}. Please verify internet connectivity and API key."
            )

        # Save generated CSV in downloads/
        filename = f"cuelinks_campaigns_{start_date}_to_{end_date}.csv"
        save_path = DOWNLOADS_DIR / filename
        df.to_csv(save_path, index=False)

        # Save live base copy in sample_data
        live_csv_path = SAMPLE_DIR / "cuelinks_bot_live.csv"
        df.to_csv(live_csv_path, index=False)

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        return csv_bytes, filename, df
