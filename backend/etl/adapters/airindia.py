"""Air India Direct (Special OWN) Network Adapter.
Handles Air India direct flight booking funnel and campaign reports from Adobe Analytics Workspace.
Direct commercial terms: ₹150 contracted payout per flight booking order.
Standardizes brand to 'AirIndia' and network to 'Special (OWN)'.
"""

from typing import Optional
import pandas as pd
from ..base import BaseNetworkAdapter, clean_currency_series, find_column


class AirIndiaAdapter(BaseNetworkAdapter):
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
                "airline",
                "offer",
            ],
            exclude_keywords=["orders", "visits", "payout", "clicks", "date", "conversions"],
        )

        # 2. Detect Transactions / Orders Column
        orders_col = find_column(
            working,
            candidates=[
                "orders",
                "flight booking - orders",
                "flight booking orders",
                "transactions",
                "conversions",
                "bookings",
                "total conversions",
            ],
            exclude_keywords=["visits", "payout", "revenue", "rate", "cr", "amount"],
        )

        # 3. Detect Payout / Revenue Column
        payout_col = find_column(
            working,
            candidates=[
                "payout",
                "payout in inr",
                "revenue",
                "commission",
                "earnings",
                "total amount",
            ],
            exclude_keywords=["orders", "visits", "clicks", "conversions"],
        )

        # 4. Extract Transactions (Flight Booking Orders)
        if orders_col:
            clean_orders = clean_currency_series(working[orders_col]).fillna(0).astype(int)
        else:
            clean_orders = pd.Series(0, index=working.index, dtype=int)

        # 5. Extract Revenue (At ₹150 per flight booking order if payout not explicitly provided)
        if payout_col:
            clean_rev = clean_currency_series(working[payout_col]).fillna(0.0)
        elif orders_col:
            # Contractual payout: ₹150 per confirmed flight booking order
            clean_rev = clean_orders.astype(float) * 150.0
        else:
            clean_rev = pd.Series(0.0, index=working.index)

        working["_clean_rev"] = clean_rev
        working["_clean_orders"] = clean_orders

        # Filter out summary/total/average footer rows
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
                raw_b = "AirIndia"

            std_b, is_matched = self.normalizer.normalize_brand(raw_b)
            if std_b == "TOTAL_SKIP":
                continue

            results.append(
                {
                    "brand": std_b,
                    "network": self.network_name,
                    "revenue": float(row["_clean_rev"]),
                    "transactions": int(row["_clean_orders"]),
                    "original_brand": raw_b,
                    "is_matched": is_matched,
                }
            )

        res_df = pd.DataFrame(results)
        if res_df.empty:
            return pd.DataFrame(
                columns=["brand", "network", "revenue", "transactions", "original_brand", "is_matched"]
            )

        return (
            res_df.groupby(["brand", "network"], as_index=False)
            .agg(
                revenue=("revenue", "sum"),
                transactions=("transactions", "sum"),
                original_brand=("original_brand", lambda x: ", ".join(sorted(set(x)))),
                is_matched=("is_matched", "all"),
            )
        )
