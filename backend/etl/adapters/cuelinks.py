"""Cuelinks Affiliate Network Adapter.
Handles Cuelinks brand-level campaign reports and transaction export files.
"""

from typing import Optional
import pandas as pd
from ..base import BaseNetworkAdapter, clean_currency_series, find_column
from ..normalizer import BrandNormalizer


class CuelinksAdapter(BaseNetworkAdapter):
    network_name: str = "cuelinks"

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(
                columns=["brand", "network", "revenue", "original_brand", "is_matched"]
            )

        working = df.copy()

        # 1. Detect Brand Column:
        # Prioritize: 'name', 'campaign name', 'merchant', 'store', 'brand', 'campaign'
        # Explicitly exclude keywords like 'type', 'id', 'channel', 'url', 'status', 'cr', 'epc', 'amount'
        brand_col = find_column(
            working,
            candidates=[
                "name",
                "campaign name",
                "merchant",
                "merchant name",
                "store",
                "brand",
                "campaign",
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

        if not brand_col:
            raise ValueError(
                f"Cuelinks adapter could not detect brand/campaign column. Available columns: {list(working.columns)}"
            )

        # Filter out empty or summary/footer rows
        brand_mask = ~working[brand_col].astype(str).str.strip().str.lower().isin(
            ["total", "totals", "avg", "average", "summary", ""]
        )
        working = working[brand_mask].copy()

        # 2. Detect Commission/Revenue Column
        # In Cuelinks, header contains "commission" (e.g. 'Commission (#<Currency:...>)' or 'Approved Commission')
        rev_col = None
        for col in working.columns:
            if "commission" in col.lower():
                rev_col = col
                break

        if not rev_col:
            rev_col = find_column(
                working,
                candidates=["payout", "revenue", "earnings", "payable commission"],
                exclude_keywords=["type", "status", "id", "date"],
            )

        if not rev_col:
            raise ValueError(
                f"Cuelinks adapter could not detect commission column. Available columns: {list(working.columns)}"
            )

        working["_clean_rev"] = clean_currency_series(working[rev_col])

        # 3. Status filter if this is a transaction-level report
        status_col = find_column(
            working,
            candidates=["status", "conversion status", "order status", "state"],
            exclude_keywords=["channel", "type"],
        )
        if status_col and status_col in working.columns:
            status_series = working[status_col].astype(str).str.lower().str.strip()
            # Drop rejected/cancelled transactions
            invalid_mask = status_series.isin(
                ["rejected", "declined", "cancelled", "canceled", "failed"]
            )
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
