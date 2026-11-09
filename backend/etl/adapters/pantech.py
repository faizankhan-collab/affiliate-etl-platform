"""Pantech (https://publisher.pantech.digital/) Network Adapter.
Handles Pantech Publisher Portal performance reports and client/offer exports.
Maps Pantech Clients/Offers to canonical Buyhatke brands, converts USD payouts
to Indian Rupee (INR) at configurable/standard exchange rates, and aggregates revenue.
"""

import os
from typing import List, Optional
import pandas as pd
from ..base import BaseNetworkAdapter, clean_currency_series, find_column


# Default exchange rate matching Google Finance / Morningstar market rate ($1 USD = ₹94.74 INR)
DEFAULT_USD_TO_INR: float = 94.73965


class PantechAdapter(BaseNetworkAdapter):
    network_name: str = "Pantech"

    def __init__(self, normalizer=None, usd_to_inr_rate: Optional[float] = None):
        super().__init__(normalizer=normalizer)
        env_rate = os.getenv("USD_TO_INR_RATE")
        if usd_to_inr_rate is not None:
            self.usd_to_inr_rate = float(usd_to_inr_rate)
        elif env_rate:
            try:
                self.usd_to_inr_rate = float(env_rate)
            except ValueError:
                self.usd_to_inr_rate = DEFAULT_USD_TO_INR
        else:
            self.usd_to_inr_rate = DEFAULT_USD_TO_INR

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(
                columns=["brand", "network", "revenue", "original_brand", "is_matched"]
            )

        working = df.copy()

        # 1. Detect Brand / Client column
        brand_col = find_column(
            working,
            candidates=[
                "client name",
                "client",
                "clientlabel",
                "client_name",
                "campaign",
                "campaign name",
                "merchant",
                "brand",
                "offer",
            ],
            exclude_keywords=[
                "id",
                "conversions",
                "orders",
                "clicks",
                "gmv",
                "payout",
                "commission",
                "currency",
                "date",
            ],
        )
        if not brand_col:
            raise ValueError(
                f"Pantech adapter could not find client/brand column. Available columns: {list(working.columns)}"
            )

        # 2. Filter out footer / summary rows
        working = working[
            ~working[brand_col]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["total", "totals", "avg", "average", "summary", "nan", "none", ""])
        ].copy()

        # 3. Detect Payout / Revenue column
        payout_col = find_column(
            working,
            candidates=[
                "payout (usd)",
                "payout",
                "approved payout",
                "commission (usd)",
                "commission",
                "revenue",
                "earnings",
            ],
            exclude_keywords=["gmv", "conversions", "orders", "clicks"],
        )
        if not payout_col:
            raise ValueError(
                f"Pantech adapter could not find payout/revenue column. Available columns: {list(working.columns)}"
            )

        # Clean raw currency/numeric series
        clean_usd = clean_currency_series(working[payout_col])

        # 4. Currency conversion: Pantech operates in USD ($)
        # Convert to INR (₹)
        is_usd = (
            "usd" in payout_col.lower()
            or "currency" in [c.lower() for c in working.columns]
            or True
        )

        if is_usd:
            working["_clean_rev"] = (clean_usd * self.usd_to_inr_rate).round(2)
        else:
            working["_clean_rev"] = clean_usd.round(2)

        # 5. Standardize brands & aggregate
        results = []
        for _, row in working.iterrows():
            raw_b = str(row[brand_col]).strip() if pd.notna(row[brand_col]) else ""
            if not raw_b or raw_b.lower() in ["total", "totals", "nan", "none"]:
                continue

            std_b, is_matched = self.normalizer.normalize_brand(raw_b)
            if std_b == "TOTAL_SKIP":
                continue

            results.append(
                {
                    "brand": std_b,
                    "network": self.network_name,
                    "revenue": float(row["_clean_rev"]),
                    "original_brand": raw_b,
                    "is_matched": is_matched,
                }
            )

        res_df = pd.DataFrame(results)
        if res_df.empty:
            return pd.DataFrame(
                columns=["brand", "network", "revenue", "original_brand", "is_matched"]
            )

        return (
            res_df.groupby(["brand", "network"], as_index=False)
            .agg(
                revenue=("revenue", "sum"),
                original_brand=("original_brand", lambda x: ", ".join(sorted(set(x)))),
                is_matched=("is_matched", "all"),
            )
        )
