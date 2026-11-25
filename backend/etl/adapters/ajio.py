"""Ajio Direct (Special OWN) Network Adapter.
Handles Ajio direct campaign, conversion, and performance reports.
Standardizes brand to 'Ajio' (or sub-brands like 'Ajio Lux') and network to 'Special (OWN)'.
"""

from typing import Optional
import pandas as pd
from ..base import BaseNetworkAdapter, clean_currency_series, find_column


class AjioAdapter(BaseNetworkAdapter):
    network_name: str = "Special (OWN)"

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(
                columns=["brand", "network", "revenue", "transactions", "original_brand", "is_matched"]
            )

        working = df.copy()

        # 1. Detect Brand / Campaign Column
        brand_col = find_column(
            working,
            candidates=[
                "campaign",
                "campaign name",
                "brand",
                "merchant",
                "offer",
                "store",
                "website / brand",
            ],
            exclude_keywords=["orders", "payout", "clicks", "date", "conversions", "revenue"],
        )

        # 2. Detect Transactions / Orders Column
        orders_col = find_column(
            working,
            candidates=[
                "orders",
                "transactions",
                "conversions",
                "total conversions",
                "sales count",
                "approved conversions",
            ],
            exclude_keywords=["visits", "payout", "revenue", "rate", "cr", "amount"],
        )

        # 3. Detect Payout / Revenue / Commission Column
        payout_col = find_column(
            working,
            candidates=[
                "payout",
                "payout in inr",
                "revenue",
                "commission",
                "earnings",
                "total amount",
                "payout (inr)",
                "sale amount",
            ],
            exclude_keywords=["orders", "visits", "clicks", "conversions"],
        )

        # 4. Extract Transactions
        if orders_col:
            clean_orders = clean_currency_series(working[orders_col]).fillna(0).astype(int)
        else:
            clean_orders = pd.Series(0, index=working.index, dtype=int)

        # 5. Extract Revenue
        if payout_col:
            clean_rev = clean_currency_series(working[payout_col]).fillna(0.0)
        else:
            clean_rev = pd.Series(0.0, index=working.index)

        working["_clean_rev"] = clean_rev
        working["_clean_orders"] = clean_orders

        # Filter out summary/total footer rows
        if brand_col:
            brand_mask = ~working[brand_col].astype(str).str.strip().str.lower().isin(
                ["total", "totals", "avg", "average", "summary", ""]
            )
            working = working[brand_mask].copy()

        # 6. Standardize brands & aggregate
        results = []
        for _, row in working.iterrows():
            if brand_col and pd.notna(row[brand_col]):
                raw_b = str(row[brand_col]).strip()
            else:
                raw_b = "Ajio"

            std_b, is_matched = self.normalizer.normalize_brand(raw_b)
            if std_b == "TOTAL_SKIP":
                continue

            results.append(
                {
                    "brand": std_b,
                    "network": self.network_name,
                    "revenue": row["_clean_rev"],
                    "transactions": row["_clean_orders"],
                    "original_brand": raw_b,
                    "is_matched": is_matched,
                }
            )

        if not results:
            return pd.DataFrame(
                columns=["brand", "network", "revenue", "transactions", "original_brand", "is_matched"]
            )

        res_df = pd.DataFrame(results)

        # Group by standardized brand and network
        grouped = (
            res_df.groupby(["brand", "network"], as_index=False)
            .agg(
                {
                    "revenue": "sum",
                    "transactions": "sum",
                    "original_brand": "first",
                    "is_matched": "first",
                }
            )
        )
        return grouped
