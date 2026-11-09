"""Admitad Affiliate Network Adapter.
Handles Admitad statistics reports and action export files.
Computes monthly revenue as: Payment Sum Open + Payment Sum Approved.
"""

from typing import Optional
import pandas as pd
from ..base import BaseNetworkAdapter, clean_currency_series, find_column
from ..normalizer import BrandNormalizer


class AdmitadAdapter(BaseNetworkAdapter):
    network_name: str = "admitad"

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(
                columns=["brand", "network", "revenue", "original_brand", "is_matched"]
            )

        working = df.copy()

        # 1. Detect Brand Column
        brand_col = find_column(
            working,
            candidates=[
                "adv. campaign",
                "advcampaign",
                "campaign",
                "adv. campaign name",
                "program",
                "advertiser",
                "website",
                "brand",
            ],
            exclude_keywords=[
                "type",
                "id",
                "views",
                "ctr",
                "ecpm",
                "ecpc",
                "cr",
                "clicks",
                "sales",
                "leads",
                "payment",
                "sum",
            ],
        )

        if not brand_col:
            raise ValueError(
                f"Admitad adapter could not detect campaign/brand column. Available columns: {list(working.columns)}"
            )

        # Filter out empty or summary/footer rows
        brand_mask = ~working[brand_col].astype(str).str.strip().str.lower().isin(
            ["total", "totals", "avg", "average", "summary", ""]
        )
        working = working[brand_mask].copy()

        # 2. Extract Revenue:
        # User specification: Payment Sum Open + Payment Sum Approved
        open_col = find_column(
            working,
            candidates=["payment sum open", "sum open", "open payment"],
            exclude_keywords=["declined", "approved"],
        )
        approved_col = find_column(
            working,
            candidates=["payment sum approved", "sum approved", "approved payment"],
            exclude_keywords=["declined", "open"],
        )

        if open_col or approved_col:
            rev_open = clean_currency_series(working[open_col]) if open_col else 0.0
            rev_approved = clean_currency_series(working[approved_col]) if approved_col else 0.0
            working["_clean_rev"] = rev_open + rev_approved
        else:
            # Fallback for legacy transaction exports
            rev_col = find_column(
                working,
                candidates=[
                    "payment",
                    "publisher earnings",
                    "reward",
                    "commission",
                    "payout",
                    "revenue",
                    "cart",
                ],
                exclude_keywords=["declined", "views", "clicks", "sales", "leads"],
            )
            if not rev_col:
                raise ValueError(
                    f"Admitad adapter could not find payment columns. Available columns: {list(working.columns)}"
                )
            working["_clean_rev"] = clean_currency_series(working[rev_col])

        # 3. Status filter if this is a transaction-level report
        status_col = find_column(
            working,
            candidates=["status", "action status", "state"],
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
