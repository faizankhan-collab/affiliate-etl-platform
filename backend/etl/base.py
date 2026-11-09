"""Base Adapter interface and shared transformation utilities for affiliate networks.
"""

from abc import ABC, abstractmethod
import re
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd

from .normalizer import BrandNormalizer


def clean_currency_series(series: pd.Series) -> pd.Series:
    """Clean currency string values to float (handles ₹, $, commas, negative signs, nulls)."""
    if series.dtype in [np.float64, np.int64, float, int]:
        return series.fillna(0.0).astype(float)

    def _to_float(val):
        if pd.isna(val) or val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        if not s or s in ["-", "N/A", "null", "None"]:
            return 0.0
        # Remove currency symbols and formatting commas
        s = re.sub(r"[₹$,\s]", "", s)
        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    return series.apply(_to_float)


def find_column(
    df: pd.DataFrame,
    candidates: List[str],
    exclude_keywords: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Find matching column name from candidates.
    1. Tests exact case-insensitive matches on all candidates first.
    2. Drops any columns containing exclude_keywords.
    3. Tests whole-word regex on remaining columns.
    """
    lower_cols = {col.strip().lower(): col for col in df.columns}
    excludes = [w.lower() for w in (exclude_keywords or [])]

    # Filter out columns with negative keywords if any
    valid_cols = {}
    for k, v in lower_cols.items():
        if any(w in k for w in excludes):
            continue
        valid_cols[k] = v

    # 1. Exact matches first
    for candidate in candidates:
        cand_lower = candidate.strip().lower()
        if cand_lower in valid_cols:
            return valid_cols[cand_lower]

    # 2. Whole-word / boundary regex on valid columns
    for candidate in candidates:
        cand_lower = candidate.strip().lower()
        pattern = r"\b" + re.escape(cand_lower) + r"\b"
        for col_lower, actual_col in valid_cols.items():
            if re.search(pattern, col_lower):
                return actual_col

    # 3. Substring fallback if still not found
    for candidate in candidates:
        cand_lower = candidate.strip().lower()
        for col_lower, actual_col in valid_cols.items():
            if cand_lower in col_lower:
                return actual_col

    return None


class BaseNetworkAdapter(ABC):
    """Abstract base class for network-specific ETL adapters."""

    network_name: str = "Generic"

    def __init__(self, normalizer: Optional[BrandNormalizer] = None):
        self.normalizer = normalizer or BrandNormalizer()

    @abstractmethod
    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process the raw dataframe into a standardized dataframe with columns:
        ['brand', 'network', 'revenue', 'original_brand', 'is_matched']
        """
        pass
