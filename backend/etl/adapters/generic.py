"""Generic / Dynamic Affiliate Network Adapter.
Auto-detects brand and revenue columns with negative keyword filtering.
Works for any network (Adgama, Affinity, Pantech, Digimodo, Special Direct, etc.).
"""

from typing import List, Optional
import pandas as pd
from ..base import BaseNetworkAdapter, clean_currency_series, find_column


class GenericAdapter(BaseNetworkAdapter):
    def __init__(
        self,
        network_name: str = "Generic",
        brand_col_override: Optional[str] = None,
        revenue_col_override: Optional[str] = None,
        normalizer=None,
    ):
        super().__init__(normalizer)
        self.network_name = network_name
        self.brand_col_override = brand_col_override
        self.revenue_col_override = revenue_col_override

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(
                columns=["brand", "network", "revenue", "original_brand", "is_matched"]
            )

        working = df.copy()

        # 1. Detect Brand Column with negative exclusions
        brand_col = self.brand_col_override or find_column(
            working,
            candidates=[
                "name",
                "campaign name",
                "merchant",
                "merchant name",
                "store",
                "retailer",
                "advertiser",
                "brand",
                "campaign",
                "offer",
                "website",
            ],
            exclude_keywords=[
                "type",
                "id",
                "channel",
                "url",
                "status",
                "cr",
                "epc",
                "date",
                "amount",
                "clicks",
                "transactions",
            ],
        )

        # 2. Detect Revenue Column
        rev_col = self.revenue_col_override
        if not rev_col:
            for c in working.columns:
                cl = c.lower()
                if "commission" in cl or "payout" in cl or "revenue" in cl or "earnings" in cl:
                    rev_col = c
                    break

        if not rev_col:
            rev_col = find_column(
                working,
                candidates=["revenue", "commission", "payout", "earnings", "cashback", "amount"],
                exclude_keywords=["type", "status", "id", "date"],
            )

        if not brand_col or not rev_col:
            raise ValueError(
                f"Could not auto-detect brand or revenue column for network '{self.network_name}'. "
                f"Detected Brand: '{brand_col}', Revenue: '{rev_col}'. Columns: {list(working.columns)}"
            )

        # Filter out summary/total rows
        brand_mask = ~working[brand_col].astype(str).str.strip().str.lower().isin(
            ["total", "totals", "avg", "average", "summary", ""]
        )
        working = working[brand_mask].copy()

        working["_clean_rev"] = clean_currency_series(working[rev_col])

        # Filter status if present
        status_col = find_column(
            working,
            candidates=["status", "conversion status", "order status", "state"],
            exclude_keywords=["type", "id"],
        )
        if status_col and status_col in working.columns:
            status_series = working[status_col].astype(str).str.lower().str.strip()
            invalid_mask = status_series.isin(["rejected", "declined", "cancelled", "canceled", "failed"])
            working = working[~invalid_mask]

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
