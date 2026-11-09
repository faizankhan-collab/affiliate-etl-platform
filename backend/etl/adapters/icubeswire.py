"""Icubeswire Affiliate Network Adapter.
Handles Icubeswire campaign offers and publisher payout exports.
Considers payout (approved + pending payout) as the monthly revenue.
"""

from typing import List, Optional
import pandas as pd
from ..base import BaseNetworkAdapter, clean_currency_series, find_column


class IcubeswireAdapter(BaseNetworkAdapter):
    network_name: str = "icubeswire"

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
                "offer name",
                "campaign",
                "campaign name",
                "offer",
                "advertiser",
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
                "offer id",
                "affiliate id",
                "affiliate name",
            ],
        )
        if not brand_col:
            raise ValueError(
                f"Icubeswire adapter could not find campaign/brand column. Available columns: {list(working.columns)}"
            )

        # 2. Filter out footer / summary rows (e.g. 'Total')
        offer_id_col = find_column(working, ["offer id", "camp id", "campaign id", "id"])
        if offer_id_col:
            working = working[
                ~working[offer_id_col]
                .astype(str)
                .str.strip()
                .str.lower()
                .isin(["total", "totals", "avg", "average", "summary", "nan", "none", ""])
            ]

        working = working[
            ~working[brand_col]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["total", "totals", "avg", "average", "summary", "nan", "none", ""])
        ].copy()

        # 3. Detect Payout / Revenue column
        approved_col = find_column(
            working,
            candidates=["approved payout", "approved_payout", "approved commission", "approved_commission"],
            exclude_keywords=["sale amount", "sales", "clicks", "conversions", "rate", "cr", "pending", "cancelled"],
        )

        pending_col = find_column(
            working,
            candidates=["pending payout", "pending_payout", "pending commission", "pending_commission"],
            exclude_keywords=["conversions", "clicks", "actions", "sale amount", "approved", "cancelled"],
        )

        general_payout_col = find_column(
            working,
            candidates=["gross payout", "payout", "revenue", "publisher payout", "commission"],
            exclude_keywords=["sale amount", "sales", "clicks", "conversions", "rate", "cr"],
        )

        if approved_col and pending_col and approved_col != pending_col:
            rev_appr = clean_currency_series(working[approved_col])
            rev_pend = clean_currency_series(working[pending_col])
            working["_clean_rev"] = rev_appr + rev_pend
        elif approved_col:
            working["_clean_rev"] = clean_currency_series(working[approved_col])
        elif pending_col:
            working["_clean_rev"] = clean_currency_series(working[pending_col])
        elif general_payout_col:
            working["_clean_rev"] = clean_currency_series(working[general_payout_col])
        else:
            raise ValueError(
                f"Icubeswire adapter could not find Payout/Revenue column. Available columns: {list(working.columns)}"
            )

        # 4. Status filtering if transactional status is present
        status_col = find_column(
            working,
            candidates=["status", "conversion status", "order status"],
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
