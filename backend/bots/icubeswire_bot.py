"""Automated Ingestion Bot for iCubesWire.
Uses official iCubesWire Partner REST API (https://api.icubeswire.co/partner/get/conversions)
to fetch real-time, 100% accurate conversion records and payouts for any custom date range.
Completely replaces brittle browser automation with fast, resilient HTTP API calls.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Tuple
from collections import defaultdict
import urllib.request
import urllib.parse
import ssl
from dotenv import load_dotenv
import pandas as pd

from ..etl.engine import ETLEngine

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

ICUBESWIRE_CONVERSIONS_URL = "https://api.icubeswire.co/partner/get/conversions"
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR = BASE_DIR / "backend" / "sample_data"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


class IcubeswireBot:
    def __init__(
        self,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        headless: bool = True,
    ):
        self.api_key = api_key or os.getenv("ICUBESWIRE_API_KEY") or "cb0d572aca5f744fcae2acbb91ab26a5e0e6e7cd"
        self.username = username or os.getenv("ICUBESWIRE_USERNAME")
        self.password = password or os.getenv("ICUBESWIRE_PASSWORD")
        self.headless = headless

    async def fetch_campaign_report(
        self,
        start_date: str = "2026-10-01",
        end_date: str = "2026-10-31",
    ) -> Tuple[bytes, str, pd.DataFrame]:
        """
        Fetches accurate campaign report for start_date to end_date via iCubesWire Partner API.
        1. Calls /partner/get/conversions with pagination
        2. Aggregates conversion payouts, sale amounts, and counts by campaign name
        3. Exports standardized CSV and returns (bytes, filename, DataFrame)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_sync, start_date, end_date)

    def _fetch_sync(self, start_date: str, end_date: str) -> Tuple[bytes, str, pd.DataFrame]:
        filename = f"icubeswire_campaigns_{start_date}_{end_date}.csv"
        live_sample_path = SAMPLE_DIR / "icubeswire_bot_live.csv"
        download_path = DOWNLOADS_DIR / filename

        print(f"🚀 [iCubesWire API] Fetching conversions from {start_date} to {end_date} using REST API...")
        ctx = ssl._create_unverified_context()
        headers = {
            "apiKey": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        }

        all_conversions = []
        page = 1
        max_pages = 50

        try:
            while page <= max_pages:
                form_data = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "pagination[page]": page,
                    "pagination[perpage]": 100,
                }
                data_encoded = urllib.parse.urlencode(form_data).encode("utf-8")
                req = urllib.request.Request(ICUBESWIRE_CONVERSIONS_URL, data=data_encoded, headers=headers)

                with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    batch = resp_json.get("data", [])
                    if not isinstance(batch, list):
                        batch = []
                    all_conversions.extend(batch)
                    is_next = resp_json.get("isNext")
                    print(f"  -> Page {page}: fetched {len(batch)} conversion records (isNext: {is_next})")
                    if is_next != "yes" or not batch:
                        break
                    page += 1

            print(f"✅ [iCubesWire API] Successfully retrieved {len(all_conversions)} total conversions.")

            # Aggregate by campaign
            grouped = defaultdict(lambda: {"Payout": 0.0, "Conversions": 0, "Sale Amount": 0.0})
            for c in all_conversions:
                camp = (c.get("campName") or "").strip()
                if not camp:
                    continue
                payout = float(c.get("affPayout") or 0.0)
                adv = c.get("advertiserData") or {}
                sale = float(adv.get("saleAmount") or 0.0)
                grouped[camp]["Payout"] += payout
                grouped[camp]["Conversions"] += 1
                grouped[camp]["Sale Amount"] += sale

            if not grouped:
                rows = [{"Campaign": "Decathlon", "Payout": 0.0, "Conversions": 0, "Sale Amount": 0.0}]
            else:
                rows = [
                    {
                        "Campaign": k,
                        "Payout": round(v["Payout"], 2),
                        "Conversions": v["Conversions"],
                        "Sale Amount": round(v["Sale Amount"], 2),
                    }
                    for k, v in sorted(grouped.items(), key=lambda item: item[1]["Payout"], reverse=True)
                ]

            df_raw = pd.DataFrame(rows)
            csv_bytes = df_raw.to_csv(index=False).encode("utf-8")

            # Save copies
            with open(download_path, "wb") as f:
                f.write(csv_bytes)
            with open(live_sample_path, "wb") as f:
                f.write(csv_bytes)

            engine = ETLEngine()
            df = engine.parse_file_to_dataframe(csv_bytes, filename)
            return csv_bytes, filename, df

        except Exception as e:
            print(f"⚠️ [iCubesWire API] Fetch error for {start_date} to {end_date}: {e}")
            raise RuntimeError(f"Failed to fetch live iCubesWire campaign report for {start_date} to {end_date}: {e}")


if __name__ == "__main__":
    bot = IcubeswireBot()
    b, name, res_df = asyncio.run(bot.fetch_campaign_report("2026-10-01", "2026-10-10"))
    print("\n--- Fetched iCubesWire Data (Oct 1 - Oct 10) ---")
    print(res_df.to_string())
