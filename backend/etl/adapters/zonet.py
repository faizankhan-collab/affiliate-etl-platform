"""Zonet Affiliate Network Adapter.
Handles Zonet monthly revenue and campaign exports.
Considers payout (or approved + pending payout) as the monthly revenue.
"""

from typing import List, Optional
import pandas as pd
from ..base import BaseNetworkAdapter, clean_currency_series, find_column


class ZonetAdapter(BaseNetworkAdapter):
    network_name: str = "zonet"

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(
                columns=["brand", "network", "revenue", "original_brand", "is_matched"]
            )

        working = df.copy()

        # 1. Detect Brand / Campaign column
        brand_col = find_column(
            working,
            candidates=[
                "campaign",
                "campaign name",
                "offer",
                "offer name",
                "advertiser",
                "landing page name",
                "brand",
                "merchant",
            ],
            exclude_keywords=[
                "status",
                "clicks",
                "actions",
                "conversions",
                "rate",
                "cr",
                "amount",
                "payout",
                "date",
                "url",
                "type",
                "terms",
                "store_id",
            ],
        )
        if not brand_col:
            raise ValueError(
                f"Zonet adapter could not find campaign/brand column. Available columns: {list(working.columns)}"
            )

        # 2. Filter out summary/total/average footer rows early
        brand_mask = ~working[brand_col].astype(str).str.strip().str.lower().isin(
            ["total", "totals", "avg", "average", "summary", ""]
        )
        working = working[brand_mask].copy()

        # 3. Detect Payout / Revenue column
        # Specific user requirement: "payout needs to be considered as the revenue"
        payout_col = find_column(
            working,
            candidates=[
                "payout",
                "approved payout",
                "total payout",
                "revenue",
                "commission",
                "earnings",
            ],
            exclude_keywords=["sale amount", "sales", "clicks", "conversions", "rate", "cr"],
        )

        pending_col = find_column(
            working,
            candidates=["pending payout", "pending commission"],
            exclude_keywords=["conversions", "clicks", "actions"],
        )

        if payout_col and pending_col:
            rev_payout = clean_currency_series(working[payout_col])
            rev_pending = clean_currency_series(working[pending_col])
            working["_clean_rev"] = rev_payout + rev_pending
        elif payout_col:
            working["_clean_rev"] = clean_currency_series(working[payout_col])
        elif pending_col:
            working["_clean_rev"] = clean_currency_series(working[pending_col])
        else:
            raise ValueError(
                f"Zonet adapter could not find Payout/Revenue column. Available columns: {list(working.columns)}"
            )

        # 4. Status filtering if applicable
        # Note: Do not drop paused/inactive campaigns if they earned revenue during the month.
        # Only drop explicitly rejected or cancelled transactions if a transactional status is present.
        status_col = find_column(
            working,
            candidates=["order status", "transaction status", "conversion status"],
            exclude_keywords=["campaign", "channel"],
        )
        if status_col and status_col in working.columns:
            status_series = working[status_col].astype(str).str.lower().str.strip()
            invalid_mask = status_series.isin(["declined", "cancelled", "canceled", "rejected", "failed"])
            working = working[~invalid_mask]

        # 5. Standardize brands & aggregate
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
