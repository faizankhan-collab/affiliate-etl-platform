"""Adapter registry and detection factory.
"""

from typing import Dict, Optional, Type
import pandas as pd

from ..base import BaseNetworkAdapter
from .cuelinks import CuelinksAdapter
from .admitad import AdmitadAdapter
from .cashkaro import CashkaroAdapter
from .zonet import ZonetAdapter
from .icubeswire import IcubeswireAdapter
from .inrdeals import InrdealsAdapter
from .cj import CJAdapter
from .pantech import PantechAdapter
from .generic import GenericAdapter
from ..normalizer import BrandNormalizer

ADAPTER_MAP: Dict[str, Type[BaseNetworkAdapter]] = {
    "cuelinks": CuelinksAdapter,
    "admitad": AdmitadAdapter,
    "cashkaro": CashkaroAdapter,
    "zonet": ZonetAdapter,
    "icubeswire": IcubeswireAdapter,
    "inrdeals": InrdealsAdapter,
    "cj": CJAdapter,
    "pantech": PantechAdapter,
}


def detect_network_from_filename_or_df(
    filename: str, df: Optional[pd.DataFrame] = None
) -> str:
    """Detect affiliate network based on filename or dataframe column signatures."""
    fn_lower = filename.lower()

    # 1. Direct filename checks
    if "cuelinks" in fn_lower or fn_lower.startswith(("campaigns_report", "transactions_report")):
        return "cuelinks"
    if "cashkaro" in fn_lower:
        return "cashkaro"
    if "admitad" in fn_lower:
        return "admitad"
    if "zonet" in fn_lower:
        return "zonet"
    if "icubeswire" in fn_lower or "icubes" in fn_lower:
        return "icubeswire"
    if "inrdeals" in fn_lower or "inr_deals" in fn_lower:
        return "inrdeals"
    if "cj" in fn_lower or "commission_junction" in fn_lower:
        return "cj"
    if "adgama" in fn_lower:
        return "adgama"
    if "affinity" in fn_lower:
        return "affinity"
    if "pantech" in fn_lower:
        return "pantech"

    # 2. DataFrame column signatures
    if df is not None:
        cols_lower = [str(c).lower().strip() for c in df.columns]

        # Cuelinks signature
        if (
            any("#<currency:" in c for c in cols_lower)
            or any("channel id" in c or "channel name" in c for c in cols_lower)
            or ("cr" in cols_lower and "epc" in cols_lower and "transactions" in cols_lower)
            or any("payable commission" in c for c in cols_lower)
        ):
            return "cuelinks"

        # Cashkaro signature
        if (
            any("cashkaro" in c or "cashback" in c for c in cols_lower)
            or any("pendingpayout in inr" in c or "payout in inr" in c for c in cols_lower)
            or any("pending conversions" in c for c in cols_lower)
        ):
            return "cashkaro"

        # Admitad signature
        if (
            any("adv" in c and "campaign" in c for c in cols_lower)
            or any("payment sum" in c for c in cols_lower)
            or any("action id" in c or "tariff" in c for c in cols_lower)
            or ("leads sum" in cols_lower and "sales sum" in cols_lower)
        ):
            return "admitad"

        # Icubeswire signature
        if any("approved payout" in c or "publisher payout" in c or "offer name" in c for c in cols_lower):
            return "icubeswire"

        # INRDeals signature
        if (
            ("merchant" in cols_lower and "total amount" in cols_lower)
            or ("store" in cols_lower and "commission" in cols_lower and "transaction id" in cols_lower)
            or any("inrdeals" in c for c in cols_lower)
        ):
            return "inrdeals"

        # Pantech signature
        if (
            ("client name" in cols_lower and any(p in cols_lower for p in ["payout (usd)", "payout", "gmv (usd)"]))
            or ("client label" in cols_lower and "payout" in cols_lower)
            or any("pantech" in c for c in cols_lower)
        ):
            return "pantech"

        # CJ signature
        if (
            any("advertiser cid" in c for c in cols_lower)
            or any("publisher commission (usd)" in c or "publisher commission" in c for c in cols_lower)
            or ("advertiser name" in cols_lower and "sale amount (usd)" in cols_lower)
        ):
            return "cj"

        # Zonet signature
        if (
            "store_id" in cols_lower
            or ("gross clicks" in cols_lower and "payout" in cols_lower)
            or ("sale amount" in cols_lower and "payout" in cols_lower)
            or ("landing page name" in cols_lower and "redirect type" in cols_lower)
            or ("advertiser" in cols_lower and any(r in cols_lower for r in ["payout", "revenue", "commission"]))
        ):
            return "zonet"

    return "generic"


def get_adapter(
    network_name: str,
    normalizer: Optional[BrandNormalizer] = None,
    brand_col_override: Optional[str] = None,
    revenue_col_override: Optional[str] = None,
    usd_to_inr_rate: Optional[float] = None,
) -> BaseNetworkAdapter:
    """Factory to retrieve the appropriate network adapter instance."""
    norm = normalizer or BrandNormalizer()
    net_key = network_name.strip().lower()

    if net_key in ADAPTER_MAP:
        adapter_cls = ADAPTER_MAP[net_key]
        if net_key in ["cj", "pantech"]:
            return adapter_cls(normalizer=norm, usd_to_inr_rate=usd_to_inr_rate)
        return adapter_cls(normalizer=norm)

    return GenericAdapter(
        network_name=norm.normalize_network(network_name),
        brand_col_override=brand_col_override,
        revenue_col_override=revenue_col_override,
        normalizer=norm,
    )
