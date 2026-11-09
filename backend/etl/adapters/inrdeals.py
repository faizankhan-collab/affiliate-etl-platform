"""INRDeals Affiliate Network Adapter.
Handles INRDeals performance reports and transaction exports.
Maps merchants/stores to canonical brands, aggregates payout/commission as revenue.
"""

from typing import List, Optional
import pandas as pd
from ..base import BaseNetworkAdapter, clean_currency_series, find_column


class InrdealsAdapter(BaseNetworkAdapter):
    network_name: str = "inrdeals"

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(
                columns=["brand", "network", "revenue", "original_brand", "is_matched"]
            )

        working = df.copy()

        # 1. Detect Brand / Store / Merchant column
        brand_col = find_column(
            working,
            candidates=[
                "merchant",
                "store",
                "store name",
                "campaign",
                "campaign name",
                "advertiser",
                "brand",
            ],
            exclude_keywords=[
                "status",
                "clicks",
                "actions",
                "transactions",
                "conversions",
                "rate",
                "cr",
                "amount",
                "payout",
                "commission",
                "date",
                "url",
                "sub id",
                "transaction id",
            ],
        )
        if not brand_col:
            raise ValueError(
                f"INRDeals adapter could not find merchant/store column. Available columns: {list(working.columns)}"
            )

        # 2. Filter out footer / summary rows (e.g. 'Total', 'Summary', empty)
        working = working[
            ~working[brand_col]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["total", "totals", "avg", "average", "summary", "nan", "none", ""])
        ].copy()

        # 3. Detect Payout / Revenue / Commission column
        payout_col = find_column(
            working,
            candidates=[
                "total amount",
                "commission",
                "payout",
                "approved payout",
                "revenue",
                "amount",
                "earnings",
            ],
            exclude_keywords=["sale amount", "sales", "clicks", "transactions", "conversions", "rate", "cr"],
        )
        if not payout_col:
            raise ValueError(
                f"INRDeals adapter could not find revenue/payout column. Available columns: {list(working.columns)}"
            )

        working["_clean_rev"] = clean_currency_series(working[payout_col])

        # 4. Filter status if individual transactions with status exist (ignore cancelled/declined)
        status_col = find_column(
            working,
            candidates=["status", "transaction status", "order status"],
            exclude_keywords=["campaign", "merchant", "store"],
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
