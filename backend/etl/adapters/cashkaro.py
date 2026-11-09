"""Cashkaro Affiliate Network Adapter.
Handles Cashkaro performance reports and retailer exports generically.
Considers pending payout and confirmed payout as monthly revenue.
"""

from typing import Optional
import pandas as pd
from ..base import BaseNetworkAdapter, clean_currency_series, find_column


class CashkaroAdapter(BaseNetworkAdapter):
    network_name: str = "cashkaro"

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(
                columns=["brand", "network", "revenue", "original_brand", "is_matched"]
            )

        working = df.copy()

        # 1. Detect Brand/Campaign Column
        brand_col = find_column(
            working,
            candidates=[
                "campaign",
                "campaign name",
                "store name",
                "retailer",
                "store",
                "merchant",
                "brand",
            ],
            exclude_keywords=[
                "clicks",
                "conversions",
                "cr",
                "epc",
                "amount",
                "payout",
                "date",
                "id",
                "type",
                "rate",
                "sale",
            ],
        )
        if not brand_col:
            raise ValueError(
                f"Cashkaro adapter could not find brand/campaign column. Available columns: {list(working.columns)}"
            )

        # Filter out summary/total/average footer rows early
        brand_mask = ~working[brand_col].astype(str).str.strip().str.lower().isin(
            ["total", "totals", "avg", "average", "summary", ""]
        )
        working = working[brand_mask].copy()

        # 2. Extract Revenue (Pending Payout is considered monthly revenue)
        pending_col = find_column(
            working,
            candidates=[
                "pendingpayout in inr",
                "pending payout",
                "pending commission",
                "pending cashback",
            ],
            exclude_keywords=["conversions", "clicks", "sale"],
        )

        payout_col = find_column(
            working,
            candidates=[
                "payout in inr",
                "payout",
                "confirmed commission",
                "commission",
                "earnings",
                "cashback",
                "revenue",
            ],
            exclude_keywords=["pending", "conversions", "clicks", "sale"],
        )

        if pending_col and payout_col:
            rev_pending = clean_currency_series(working[pending_col])
            rev_payout = clean_currency_series(working[payout_col])
            working["_clean_rev"] = rev_pending + rev_payout
        elif pending_col:
            working["_clean_rev"] = clean_currency_series(working[pending_col])
        elif payout_col:
            working["_clean_rev"] = clean_currency_series(working[payout_col])
        else:
            raise ValueError(
                f"Cashkaro adapter could not find payout/revenue column. Available columns: {list(working.columns)}"
            )

        # 3. Status filter if present
        status_col = find_column(
            working,
            candidates=["status", "order status", "state"],
            exclude_keywords=["type", "id"],
        )
        if status_col and status_col in working.columns:
            status_series = working[status_col].astype(str).str.lower().str.strip()
            invalid_mask = status_series.isin(["declined", "cancelled", "canceled", "rejected", "failed"])
            working = working[~invalid_mask]

        # 4. Standardize brands & aggregate
        results = []
        for _, row in working.iterrows():
            raw_b = str(row[brand_col]).strip() if pd.notna(row[brand_col]) else ""
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
