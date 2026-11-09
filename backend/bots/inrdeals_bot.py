"""Automated Ingestion Bot for INRDeals.
Uses Playwright to authenticate with INRDeals Publisher portal (https://inrdeals.com/login),
manage session state, query month-wise merchant performance and payout metrics,
and export standardized campaign-level data.
"""

import asyncio
import io
import os
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv
import pandas as pd

from ..etl.engine import ETLEngine

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

INRDEALS_LOGIN_URL = "https://inrdeals.com/login"
SESSION_FILE = BASE_DIR / ".inrdeals_session.json"
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


class InrdealsBot:
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        headless: bool = True,
    ):
        self.username = username or os.getenv("INRDEALS_USERNAME")
        self.password = password or os.getenv("INRDEALS_PASSWORD")
        self.headless = headless
        if not self.username or not self.password:
            raise ValueError(
                "INRDeals credentials not found. Please set INRDEALS_USERNAME and INRDEALS_PASSWORD in .env"
            )

    async def _handle_login(self, page, context) -> None:
        """Handles INRDeals publisher login flow."""
        print(f"Initiating INRDeals login flow for: {self.username}")
        await page.goto(INRDEALS_LOGIN_URL, wait_until="networkidle", timeout=45000)

        # Fill credentials in #login form
        await page.wait_for_selector("#login input[name='login']", timeout=20000)
        await page.fill("#login input[name='login']", self.username)
        await page.fill("#login input[name='password']", self.password)

        # Submit login form directly
        async with page.expect_navigation(timeout=30000):
            await page.evaluate("() => document.getElementById('login').submit()")

        # Wait until publisher dashboard is reached
        await page.wait_for_url(lambda u: "/publisher" in u or "/dashboard" in u, timeout=25000)
        await context.storage_state(path=str(SESSION_FILE))
        print(f"Successfully logged into INRDeals and saved session to {SESSION_FILE}")

    async def fetch_campaign_report(
        self,
        start_date: str = "2026-10-01",
        end_date: str = "2026-10-31",
    ) -> Tuple[bytes, str, pd.DataFrame]:
        """
        Automated end-to-end fetch:
        1. Login or reuse authenticated session state
        2. Format custom month date range for performance and transaction reports
        3. Scrape merchant performance table (Merchant, Clicks, Transactions, Total Amount)
        4. Also download detailed transaction report Excel if available
        5. Return file bytes, filename, and parsed DataFrame
        """
        from playwright.async_api import async_playwright

        # Format dates:
        # e.g. start_date "2026-10-01" -> year 2026, month 10, day 01
        sy, sm, sd = start_date.split("-")
        ey, em, ed = end_date.split("-")
        custom_date_perf = f"{sm}/{sd}/{sy}-{em}/{ed}/{ey}"
        tx_date_range = f"{sm}-{sd}-{sy}_{em}-{ed}-{ey}"

        perf_url = f"https://inrdeals.com/publisher/performance/report?date=null&custom_date={custom_date_perf}"
        tx_url = f"https://inrdeals.com/publisher/reports/null/{tx_date_range}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )

            storage_state = str(SESSION_FILE) if SESSION_FILE.exists() else None
            context = await browser.new_context(
                storage_state=storage_state,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1440, "height": 900},
            )

            page = await context.new_page()

            # Check if session is valid by navigating to dashboard
            need_login = True
            if storage_state:
                try:
                    await page.goto("https://inrdeals.com/publisher/dashboard", wait_until="networkidle", timeout=30000)
                    if "/login" not in page.url and "/publisher" in page.url:
                        need_login = False
                        print("Reusing active INRDeals session")
                except Exception as e:
                    print(f"Session validation check failed: {e}")

            if need_login:
                await self._handle_login(page, context)

            print(f"Navigating to INRDeals Performance Report: {perf_url}")
            await page.goto(perf_url, wait_until="networkidle", timeout=45000)

            # Scrape merchant performance table
            rows_data = await page.evaluate("""() => {
                const rows = Array.from(document.querySelectorAll('table tbody tr'));
                return rows.map(tr => {
                    const tds = Array.from(tr.querySelectorAll('td'));
                    return tds.map(td => td.innerText.trim());
                }).filter(r => r.length >= 4);
            }""")

            records = []
            for r in rows_data:
                merchant = r[0]
                clicks = r[1].replace(",", "")
                txs = r[2].replace(",", "")
                amount = r[3].replace("₹", "").replace(",", "").strip()
                records.append({
                    "Merchant": merchant,
                    "Clicks": int(clicks) if clicks.isdigit() else 0,
                    "Transactions": int(txs) if txs.isdigit() else 0,
                    "Total Amount": float(amount) if amount else 0.0,
                })

            # Also attempt to download transaction excel for detailed records backup
            try:
                print(f"Checking transaction report backup: {tx_url}")
                await page.goto(tx_url, wait_until="networkidle", timeout=35000)
                export_btn = await page.query_selector("button:has-text('Export to Excel')")
                if export_btn:
                    async with page.expect_download(timeout=15000) as dl_info:
                        await export_btn.click()
                    dl = await dl_info.value
                    tx_backup_path = DOWNLOADS_DIR / f"inrdeals_tx_backup_{start_date}_{end_date}.xlsx"
                    await dl.save_as(str(tx_backup_path))
                    print(f"Saved detailed transaction backup to {tx_backup_path}")
            except Exception as e:
                print(f"Transaction backup download skipped or not available: {e}")

            # Save updated storage state
            await context.storage_state(path=str(SESSION_FILE))
            await browser.close()

            # Create DataFrame
            if records:
                df_report = pd.DataFrame(records)
            else:
                df_report = pd.DataFrame(columns=["Merchant", "Clicks", "Transactions", "Total Amount"])

            filename = f"inrdeals_campaigns_{start_date}_{end_date}.csv"
            out_path = DOWNLOADS_DIR / filename
            df_report.to_csv(out_path, index=False)
            print(f"Saved INRDeals performance report to {out_path} ({len(df_report)} campaigns)")

            # Also save live copy for ETL platform
            live_copy_path = BASE_DIR / "backend" / "sample_data" / "inrdeals_bot_live.csv"
            df_report.to_csv(live_copy_path, index=False)

            with open(out_path, "rb") as f:
                csv_bytes = f.read()

            engine = ETLEngine()
            df_standardized = engine.parse_file_to_dataframe(csv_bytes, filename)

            return csv_bytes, filename, df_standardized


if __name__ == "__main__":
    bot = InrdealsBot()
    data, fname, df = asyncio.run(bot.fetch_campaign_report("2026-10-01", "2026-10-31"))
    print("\n--- Standardized INRDeals Data (October 2026) ---")
    print(df.to_string())
