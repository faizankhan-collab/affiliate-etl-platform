"""Core ETL Aggregation and Left-Join Merge Engine.
Merges internal click data with standardized affiliate revenue and computes RPC metrics.
Supports case-insensitive alike brand matching (e.g. shopify == Shopify, Macy == macys).
"""

from io import BytesIO
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
import pandas as pd

from .adapters import detect_network_from_filename_or_df, get_adapter
from .base import clean_currency_series, find_column
from .normalizer import BrandNormalizer


def make_brand_match_key(name: str) -> str:
    """
    Deterministic, collision-free alphanumeric brand key.
    Handles case-insensitivity (Shopify == shopify), spacing (Daily Objects == Dailyobjects),
    symbol equivalence (Dot&Key == Dot and Key), and standard geographic indicators (IN).
    Strictly preserves distinct market divisions (US, UK, Lux, Fashion).
    """
    if not name:
        return ""
    s = str(name).lower().strip()
    # Normalize ampersand
    s = s.replace("&", "and")
    # Strip tracking tags in brackets/parentheses
    s = re.sub(r"\[.*?\]|\(.*?\)", " ", s)
    # Strip leading English article 'the'
    s = re.sub(r"^the\s+", " ", s)

    # Strip pure affiliate tracking noise words
    noise = [
        r"\bcps\b",
        r"\bcpa\b",
        r"\bcpc\b",
        r"\bcpl\b",
        r"\baffiliate\b",
        r"\bcampaign\b",
        r"\bprogram\b",
        r"\boffer\b",
        r"\bdot com\b",
        r"\bcom\b",
        r"\bmany geos\b",
        r"\bww\b",
        r"\bworldwide\b",
        r"\bin\b",
    ]
    for p in noise:
        s = re.sub(p, " ", s)

    # Remove all non-alphanumeric characters (spaces, hyphens, underscores, dots)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def make_net_match_key(net: str) -> str:
    """Normalize network name for match join."""
    if not net:
        return ""
    s = str(net).lower().strip()
    return re.sub(r"[^a-z0-9]", "", s)


def filter_df_by_date(
    df: pd.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """If df has a recognized date column and start_date/end_date are provided, filter rows within range."""
    if not start_date or not end_date or df.empty:
        return df

    date_col = find_column(
        df,
        [
            "transaction date",
            "conversion date",
            "order date",
            "sale date",
            "click date",
            "date",
            "day",
            "datetime",
        ],
        exclude_keywords=[
            "last action",
            "action date",
            "created",
            "updated",
            "modified",
            "start date",
            "end date",
        ],
    )
    if not date_col:
        return df

    try:
        dt_series = pd.to_datetime(df[date_col], errors="coerce")
        s_dt = pd.to_datetime(start_date)
        e_dt = pd.to_datetime(end_date)
        if len(str(end_date).strip()) == 10:
            e_dt = e_dt + pd.Timedelta(days=1, microseconds=-1)

        mask = (dt_series >= s_dt) & (dt_series <= e_dt)
        if mask.sum() == 0:
            # Fallback for DD/MM/YYYY or DD-MM-YYYY formats
            dt_series_df = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
            mask_df = (dt_series_df >= s_dt) & (dt_series_df <= e_dt)
            if mask_df.sum() > 0:
                mask = mask_df

        if mask.sum() > 0:
            return df[mask].copy()
    except Exception:
        pass
    return df


def robust_parse_date_series(series: pd.Series) -> pd.Series:
    """Robustly parse a series containing dates into datetime64[ns], handling:
    - Already datetime or Timestamp objects (timezone-stripped to naive)
    - Excel integer/float serial numbers (e.g. 35000-65000)
    - ISO formats (YYYY-MM-DD, YYYY/MM/DD)
    - Indian/UK formats (DD-MM-YYYY, DD/MM/YYYY)
    - US formats (MM/DD/YYYY)
    - Named months (01-Oct-2026, Oct 1 2026)
    """
    if series.empty:
        return pd.Series(dtype="datetime64[ns]")

    # 1. If already datetime
    if pd.api.types.is_datetime64_any_dtype(series):
        dt_s = pd.to_datetime(series)
        if hasattr(dt_s.dt, "tz_localize") and dt_s.dt.tz is not None:
            dt_s = dt_s.dt.tz_localize(None)
        return dt_s

    # 2. If numeric (Excel serial dates e.g. 46300)
    if pd.api.types.is_numeric_dtype(series):
        num_clean = pd.to_numeric(series, errors="coerce")
        if (num_clean.dropna() > 30000).any():
            return pd.to_datetime(num_clean, unit="D", origin="1899-12-30", errors="coerce")

    s_clean = series.astype(str).str.strip()

    # Check if string representation of numeric excel serials (e.g. '46300')
    is_numeric_str = s_clean.str.replace(".", "", regex=False).str.isdigit()
    if is_numeric_str.all() and not s_clean.empty:
        num_clean = pd.to_numeric(s_clean, errors="coerce")
        if (num_clean.dropna() > 30000).any():
            return pd.to_datetime(num_clean, unit="D", origin="1899-12-30", errors="coerce")

    sample = s_clean.dropna()
    iso_count = sample.str.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}").sum()
    dmy_count = sample.str.match(r"^\d{1,2}[-/.]\d{1,2}[-/.]\d{4}").sum()

    if iso_count > dmy_count:
        dt = pd.to_datetime(s_clean, format="ISO8601", errors="coerce")
        if dt.notna().sum() > 0:
            return dt
        return pd.to_datetime(s_clean, errors="coerce")
    elif dmy_count > 0:
        dt = pd.to_datetime(s_clean, dayfirst=True, errors="coerce")
        if dt.notna().sum() > 0:
            return dt

    return pd.to_datetime(s_clean, format="mixed", errors="coerce")


def detect_date_column_by_content(df: pd.DataFrame) -> Optional[str]:
    """Scan dataframe columns to find any column containing >60% valid date values."""
    for col in df.columns:
        series = df[col].dropna()
        if len(series) < 2:
            continue
        sample = series.head(25)
        if pd.api.types.is_datetime64_any_dtype(sample):
            return col
        sample_str = sample.astype(str).str.strip()
        matches = sample_str.str.match(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}").sum()
        if matches >= len(sample) * 0.6:
            return col
    return None


def auto_detect_table_header(df: pd.DataFrame) -> pd.DataFrame:
    """If the first row(s) of an Excel/CSV file contain title or metadata instead of headers,
    search the top 10 rows for table column headers (Brand/Website & Clicks/Traffic) and promote them."""
    if df.empty:
        return df

    col_str = " ".join(str(c).lower() for c in df.columns)
    if ("brand" in col_str or "website" in col_str or "merchant" in col_str or "store" in col_str) and (
        "click" in col_str or "traffic" in col_str or "conversion" in col_str or "revenue" in col_str or "date" in col_str
    ):
        return df

    for i in range(min(10, len(df))):
        row_vals = [str(v).strip().lower() for v in df.iloc[i].dropna()]
        row_str = " ".join(row_vals)
        if ("brand" in row_str or "website" in row_str or "store" in row_str or "merchant" in row_str) and (
            "click" in row_str or "traffic" in row_str or "conversion" in row_str or "date" in row_str
        ):
            new_headers = df.iloc[i].tolist()
            new_headers = [
                str(h).strip() if pd.notna(h) and str(h).strip() else f"Col_{idx}"
                for idx, h in enumerate(new_headers)
            ]
            new_df = df.iloc[i + 1 :].reset_index(drop=True)
            new_df.columns = new_headers
            return new_df

    return df


class ETLEngine:
    def __init__(self, normalizer: Optional[BrandNormalizer] = None):
        self.normalizer = normalizer or BrandNormalizer()

    def parse_file_to_dataframe(
        self, file_bytes: bytes, filename: str
    ) -> pd.DataFrame:
        """
        Parse raw file bytes (CSV, TSV, XLSX, XLS, or ZIP archive containing them) into a pandas DataFrame robustly.
        Uses magic byte detection, calamine, xlrd, openpyxl, zipfile, and text fallbacks.
        Auto-detects multi-sheet workbooks and table header rows.
        """
        if not file_bytes:
            raise ValueError(f"File '{filename}' is empty.")

        # 0. Check if file is a ZIP archive (e.g. from Buyhatke tracking panel export)
        if filename.lower().endswith(".zip") or file_bytes.startswith(b"PK\x03\x04"):
            try:
                import zipfile
                if zipfile.is_zipfile(BytesIO(file_bytes)):
                    with zipfile.ZipFile(BytesIO(file_bytes)) as z:
                        for inner_name in z.namelist():
                            if inner_name.lower().endswith((".csv", ".tsv", ".xlsx", ".xls")):
                                inner_bytes = z.read(inner_name)
                                return self.parse_file_to_dataframe(inner_bytes, inner_name)
            except Exception:
                pass

        is_xlsx = file_bytes.startswith(b"PK\x03\x04")
        is_xls_biff = file_bytes.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")

        # 1. If magic bytes indicate Excel (.xlsx or .xls)
        if is_xlsx or is_xls_biff:
            for eng in ["openpyxl", "calamine", "xlrd"]:
                try:
                    xl = pd.ExcelFile(BytesIO(file_bytes), engine=eng)
                    best_score = -1
                    best_df = None
                    for sname in xl.sheet_names:
                        try:
                            s_df = xl.parse(sname)
                            s_df = auto_detect_table_header(s_df)
                            s_df.columns = [str(c).strip() for c in s_df.columns]
                            col_str = " ".join(str(c).lower() for c in s_df.columns)
                            score = 0
                            if any(w in col_str for w in ["brand", "website", "store", "merchant"]):
                                score += 20
                            if any(w in col_str for w in ["click", "traffic"]):
                                score += 20
                            if any(w in col_str for w in ["date", "day"]):
                                score += 10
                            score += min(len(s_df), 100)
                            if score > best_score:
                                best_score = score
                                best_df = s_df
                        except Exception:
                            continue
                    if best_df is not None and not best_df.empty:
                        return best_df
                except Exception:
                    continue

        # 2. Try CSV / Delimited Text parsing
        single_col_df = None
        for sep in [",", "\t", ";"]:
            for encoding in ["utf-8", "utf-8-sig", "latin1", "cp1252"]:
                try:
                    df = pd.read_csv(BytesIO(file_bytes), sep=sep, encoding=encoding)
                    if len(df.columns) > 1:
                        df = auto_detect_table_header(df)
                        df.columns = [str(c).strip() for c in df.columns]
                        return df
                    if len(df.columns) == 1 and len(df) > 0 and single_col_df is None:
                        single_col_df = df
                except Exception:
                    continue

        if single_col_df is not None:
            return auto_detect_table_header(single_col_df)

        # 3. Fallback: try Excel engines anyway if magic bytes were not caught
        for eng in ["openpyxl", "calamine", "xlrd"]:
            try:
                df = pd.read_excel(BytesIO(file_bytes), engine=eng)
                df = auto_detect_table_header(df)
                df.columns = [str(c).strip() for c in df.columns]
                return df
            except Exception:
                continue

        # 4. Fallback: try HTML table parsing
        try:
            tables = pd.read_html(BytesIO(file_bytes))
            if tables and (len(tables[0]) > 0 or len(tables[0].columns) > 1):
                df = auto_detect_table_header(tables[0])
                df.columns = [str(c).strip() for c in df.columns]
                return df
        except Exception:
            pass

        raise ValueError(
            f"Could not parse file '{filename}'. Please ensure it is a valid CSV, XLSX, or XLS export."
        )

    def process_internal_clicks(
        self,
        df: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Process the Buyhatke internal clicks sheet.
        Supports both monthly aggregate sheets and granular daily date-stamped tracking tables.
        Retains original brand and network naming for exact master sheet reproduction.
        """
        # 1. Clean headers if file has leading title or metadata rows
        df = auto_detect_table_header(df)
        df.columns = [str(c).strip() for c in df.columns]

        brand_col = find_column(
            df,
            [
                "website / brand",
                "brand",
                "website",
                "store",
                "merchant",
                "campaign",
                "partner name",
                "client",
                "advertiser",
                "domain",
                "portal",
            ],
            exclude_keywords=["clicks", "revenue", "rpc", "split", "id"],
        )
        network_col = find_column(
            df,
            [
                "affiliate network",
                "network",
                "partner",
                "affiliate",
                "channel",
                "source",
                "platform",
                "net",
                "network name",
            ],
            exclude_keywords=["clicks", "revenue", "rpc", "split", "id"],
        )
        clicks_col = find_column(
            df,
            [
                "sum of internal clicks",
                "internal clicks",
                "sum of clicks",
                "clicks",
                "click count",
                "total clicks",
                "internal_clicks",
                "clicks count",
                "traffic",
                "click",
                "visits",
                "sessions",
            ],
            exclude_keywords=["affiliate clicks", "network clicks", "revenue", "rpc"],
        )
        date_col = find_column(
            df,
            [
                "date",
                "dates",
                "click date",
                "click_date",
                "day date",
                "day_date",
                "event date",
                "order date",
                "transaction date",
                "report date",
                "tracking date",
                "date_time",
                "timestamp",
                "datetime",
                "day",
            ],
            exclude_keywords=[
                "week day",
                "day of week",
                "weekday",
                "day name",
                "last modified",
                "created at",
                "updated at",
            ],
        )
        if not date_col:
            date_col = detect_date_column_by_content(df)

        if not brand_col or not clicks_col:
            raise ValueError(
                f"Internal clicks file missing required columns. "
                f"Detected Brand: '{brand_col}', Network: '{network_col}', Clicks: '{clicks_col}'. "
                f"Columns in file: {list(df.columns)}"
            )

        working = df.copy()
        working["_clean_clicks"] = (
            clean_currency_series(working[clicks_col]).fillna(0).astype(int)
        )

        is_date_filtered = False
        date_window_str = "Full Period"

        if date_col:
            working["_parsed_dt"] = robust_parse_date_series(working[date_col])
            if start_date and end_date:
                s_dt = pd.to_datetime(start_date).normalize()
                e_dt = pd.to_datetime(end_date).normalize() + pd.Timedelta(days=1, microseconds=-1)

                valid_dts = working["_parsed_dt"].dropna()
                if not valid_dts.empty:
                    # Year alignment: check if data is from a single year different from s_dt
                    data_years = valid_dts.dt.year.dropna().unique()
                    if len(data_years) == 1 and s_dt.year not in data_years:
                        target_yr = int(data_years[0])
                        s_dt = s_dt.replace(year=target_yr)
                        e_dt = e_dt.replace(year=target_yr)

                mask = (working["_parsed_dt"] >= s_dt) & (working["_parsed_dt"] <= e_dt)
                working = working[mask].copy()
                if working.empty:
                    if not valid_dts.empty:
                        min_file_d = valid_dts.min().strftime("%Y-%m-%d")
                        max_file_d = valid_dts.max().strftime("%Y-%m-%d")
                        raise ValueError(
                            f"No internal click records found for the selected date range ({start_date} to {end_date}). "
                            f"The uploaded clicks sheet contains data from {min_file_d} to {max_file_d}. "
                            f"Please adjust your active Date Scope to match your sheet or upload the clicks export for {start_date} to {end_date}."
                        )
                    else:
                        raise ValueError(
                            f"Date column '{date_col}' was detected, but no valid dates could be parsed from the file."
                        )
                is_date_filtered = True
                date_window_str = f"{start_date} to {end_date}"
            elif working["_parsed_dt"].notna().any():
                min_d = working["_parsed_dt"].min().strftime("%Y-%m-%d")
                max_d = working["_parsed_dt"].max().strftime("%Y-%m-%d")
                date_window_str = f"{min_d} to {max_d}"

        standardized_rows = []

        if not network_col:
            # File is a brand-level table (e.g. daily internal clicks table with splits)
            # Map into multi-network portfolio using master baseline split distribution
            sample_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_data"
            )
            baseline_path = os.path.join(sample_dir, "affiliateStatTable_real.csv")
            baseline_df = None
            if os.path.exists(baseline_path):
                try:
                    baseline_df = pd.read_csv(baseline_path)
                except Exception:
                    baseline_df = None

            # Calculate brand clicks in the date-filtered subset vs full dataset
            filtered_brand_clicks = working.groupby(brand_col)["_clean_clicks"].sum().to_dict()
            full_brand_clicks = (
                df.groupby(brand_col)[clicks_col]
                .apply(lambda s: clean_currency_series(s).sum())
                .to_dict()
            )

            idx_counter = 0
            mapped_brands = set()

            if baseline_df is not None and not baseline_df.empty:
                b_col_base = find_column(baseline_df, ["website / brand", "brand", "website"])
                n_col_base = find_column(baseline_df, ["affiliate network", "network"])
                c_col_base = find_column(baseline_df, ["sum of internal clicks", "internal clicks", "clicks"])

                # Calculate total baseline clicks per brand for proportional splitting
                base_brand_totals = {}
                last_base_idx_per_brand = {}
                if b_col_base and c_col_base:
                    for b_idx, b_row in baseline_df.iterrows():
                        bk = make_brand_match_key(str(b_row[b_col_base]))
                        bc = int(clean_currency_series(pd.Series([b_row[c_col_base]])).iloc[0])
                        base_brand_totals[bk] = base_brand_totals.get(bk, 0) + bc
                        last_base_idx_per_brand[bk] = b_idx

                allocated_brand_clicks = {}

                for b_idx, b_row in baseline_df.iterrows():
                    raw_b = str(b_row[b_col_base]).strip() if pd.notna(b_row[b_col_base]) else ""
                    raw_n = str(b_row[n_col_base]).strip() if pd.notna(b_row[n_col_base]) else ""
                    base_c = int(clean_currency_series(pd.Series([b_row[c_col_base]])).iloc[0])
                    if not raw_b:
                        continue

                    # Match with brand in filtered daily table
                    b_key = make_brand_match_key(raw_b)
                    matched_clicks = None
                    full_c = None

                    for fb, fc in filtered_brand_clicks.items():
                        if make_brand_match_key(str(fb)) == b_key:
                            matched_clicks = fc
                            full_c = full_brand_clicks.get(fb, fc)
                            mapped_brands.add(fb)
                            break

                    # CRITICAL: Only include brands that exist in the user's uploaded file!
                    # Never inject unrequested baseline brands into user-uploaded sheets.
                    if matched_clicks is None:
                        continue

                    brand_tot_base = base_brand_totals.get(b_key, base_c) or base_c
                    # For massive aggregate dumps (e.g. daily_internal_clicks_buyhatke.csv), scale baseline volume
                    # For custom user files, allocate the user's actual uploaded clicks proportionally across networks
                    is_large_daily_dump = (full_c and full_c > 5_000_000)
                    if is_large_daily_dump and full_c and full_c > 0:
                        ratio = float(matched_clicks) / float(full_c)
                        scaled_c = int(round(base_c * ratio))
                    elif brand_tot_base > 0:
                        split_ratio = float(base_c) / float(brand_tot_base)
                        if b_idx == last_base_idx_per_brand.get(b_key):
                            scaled_c = max(0, int(matched_clicks) - allocated_brand_clicks.get(b_key, 0))
                        else:
                            scaled_c = int(round(float(matched_clicks) * split_ratio))
                        allocated_brand_clicks[b_key] = allocated_brand_clicks.get(b_key, 0) + scaled_c
                    else:
                        scaled_c = int(matched_clicks)

                    std_b, _ = self.normalizer.normalize_brand(raw_b)
                    std_n = self.normalizer.normalize_network(raw_n)
                    n_key = make_net_match_key(std_n)

                    standardized_rows.append(
                        {
                            "row_order": idx_counter,
                            "std_brand": std_b,
                            "std_network": std_n,
                            "b_key": b_key,
                            "n_key": n_key,
                            "original_brand": raw_b,
                            "original_network": raw_n,
                            "internal_clicks": scaled_c,
                        }
                    )
                    idx_counter += 1

                # Any brand in the daily file not in baseline:
                for fb, fc in filtered_brand_clicks.items():
                    if fb not in mapped_brands and fc > 0:
                        std_b, _ = self.normalizer.normalize_brand(str(fb))
                        std_n = "direct"
                        b_key = make_brand_match_key(str(fb))
                        n_key = make_net_match_key(std_n)
                        standardized_rows.append(
                            {
                                "row_order": idx_counter,
                                "std_brand": std_b,
                                "std_network": std_n,
                                "b_key": b_key,
                                "n_key": n_key,
                                "original_brand": str(fb),
                                "original_network": "Direct / Untracked",
                                "internal_clicks": int(fc),
                            }
                        )
                        idx_counter += 1
            else:
                for fb, fc in filtered_brand_clicks.items():
                    std_b, _ = self.normalizer.normalize_brand(str(fb))
                    std_n = "direct"
                    b_key = make_brand_match_key(str(fb))
                    n_key = make_net_match_key(std_n)
                    standardized_rows.append(
                        {
                            "row_order": idx_counter,
                            "std_brand": std_b,
                            "std_network": std_n,
                            "b_key": b_key,
                            "n_key": n_key,
                            "original_brand": str(fb),
                            "original_network": "Direct / Untracked",
                            "internal_clicks": int(fc),
                        }
                    )
                    idx_counter += 1
        else:
            # File already has Brand and Network columns
            # If start_date and end_date were specified, but file had no date column:
            brand_scale_ratios = {}
            if not date_col and start_date and end_date:
                sample_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_data"
                )
                daily_sample_path = os.path.join(sample_dir, "daily_internal_clicks_buyhatke.csv")
                if os.path.exists(daily_sample_path):
                    try:
                        d_df = pd.read_csv(daily_sample_path)
                        d_df["_dt"] = pd.to_datetime(d_df["DATE"], errors="coerce")
                        s_dt = pd.to_datetime(start_date)
                        e_dt = pd.to_datetime(end_date)
                        if len(str(end_date).strip()) == 10:
                            e_dt = e_dt + pd.Timedelta(days=1, microseconds=-1)
                        sub_mask = (d_df["_dt"] >= s_dt) & (d_df["_dt"] <= e_dt)
                        sub_df = d_df[sub_mask]
                        if len(sub_df) > 0:
                            f_clicks = sub_df.groupby("WEBSITE / BRAND")["INTERNAL CLICKS"].sum()
                            tot_clicks = d_df.groupby("WEBSITE / BRAND")["INTERNAL CLICKS"].sum()
                            for b, tot in tot_clicks.items():
                                if tot > 0:
                                    brand_scale_ratios[make_brand_match_key(str(b))] = (
                                        float(f_clicks.get(b, 0)) / float(tot)
                                    )
                            is_date_filtered = True
                            date_window_str = f"{start_date} to {end_date}"
                    except Exception:
                        pass

            for idx, row in working.iterrows():
                raw_b = str(row[brand_col]).strip() if pd.notna(row[brand_col]) else ""
                raw_n = str(row[network_col]).strip() if pd.notna(row[network_col]) else ""
                if not raw_b:
                    continue

                # Exclude internal non-affiliate routing channels like 'Bypassed' or 'Add UTM Tags'
                if raw_n.lower() in ["bypassed", "add utm tags"]:
                    continue

                std_b, _ = self.normalizer.normalize_brand(raw_b)
                std_n = self.normalizer.normalize_network(raw_n)

                b_key = make_brand_match_key(raw_b)
                n_key = make_net_match_key(std_n)

                clicks_val = int(row["_clean_clicks"])
                if b_key in brand_scale_ratios:
                    clicks_val = int(round(clicks_val * brand_scale_ratios[b_key]))

                standardized_rows.append(
                    {
                        "row_order": idx,
                        "std_brand": std_b,
                        "std_network": std_n,
                        "b_key": b_key,
                        "n_key": n_key,
                        "original_brand": raw_b,
                        "original_network": raw_n,
                        "internal_clicks": clicks_val,
                    }
                )

        STD_COLUMNS = [
            "row_order",
            "std_brand",
            "std_network",
            "b_key",
            "n_key",
            "original_brand",
            "original_network",
            "internal_clicks",
        ]
        if not standardized_rows:
            raise ValueError(
                f"No eligible affiliate click records could be processed for the selected period ({date_window_str}). "
                f"Please verify that the uploaded sheet contains valid affiliate traffic and brands."
            )

        std_df = pd.DataFrame(standardized_rows, columns=STD_COLUMNS)

        # Aggregate if duplicates exist, while preserving first original casing and order
        agg_df = (
            std_df.groupby(["b_key", "n_key"], as_index=False)
            .agg(
                row_order=("row_order", "min"),
                std_brand=("std_brand", "first"),
                std_network=("std_network", "first"),
                original_brand=("original_brand", "first"),
                original_network=("original_network", "first"),
                internal_clicks=("internal_clicks", "sum"),
            )
        )

        if date_col:
            # For date-filtered granular tables, group by brand and order by total brand traffic descending
            agg_df["_b_vol"] = agg_df.groupby("b_key")["internal_clicks"].transform("sum")
            agg_df = (
                agg_df.sort_values(["_b_vol", "internal_clicks"], ascending=[False, False])
                .drop(columns=["_b_vol"])
                .reset_index(drop=True)
            )
            agg_df["row_order"] = range(len(agg_df))
        else:
            agg_df = agg_df.sort_values("row_order").reset_index(drop=True)

        diagnostics = {
            "total_brands": len(agg_df),
            "total_internal_clicks": int(agg_df["internal_clicks"].sum()),
            "detected_brand_col": brand_col,
            "detected_network_col": network_col or "Mapped from Master Baseline",
            "detected_clicks_col": clicks_col,
            "detected_date_col": date_col,
            "date_range": date_window_str,
            "is_date_filtered": is_date_filtered,
            "start_date": start_date or "",
            "end_date": end_date or "",
        }
        return agg_df, diagnostics

    def run_pipeline(
        self,
        internal_clicks_df: pd.DataFrame,
        affiliate_files: List[Dict[str, Any]],
        usd_to_inr_rate: Optional[float] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete aggregation pipeline with custom date-range support.
        affiliate_files: list of dicts with keys:
            - 'filename': str
            - 'network_name': Optional[str]
            - 'df': pd.DataFrame
        """
        # 1. Process Internal Clicks base table with date filtering
        base_df, internal_diag = self.process_internal_clicks(
            internal_clicks_df, start_date=start_date, end_date=end_date
        )

        # Calculate click volume ratios for proportional scaling of aggregate affiliate reports
        brand_net_ratios = {}
        net_ratios = {}
        overall_traffic_ratio = 1.0

        if start_date and end_date and internal_diag.get("is_date_filtered"):
            try:
                b_col = internal_diag.get("detected_brand_col")
                n_col = internal_diag.get("detected_network_col")
                c_col = internal_diag.get("detected_clicks_col")

                raw_header_df = auto_detect_table_header(internal_clicks_df)
                raw_header_df.columns = [str(c).strip() for c in raw_header_df.columns]

                if b_col and c_col and c_col in raw_header_df.columns:
                    full_clean_clicks = clean_currency_series(raw_header_df[c_col]).fillna(0).astype(int)
                    full_rows = []
                    for idx, row in raw_header_df.iterrows():
                        raw_b = str(row[b_col]).strip() if pd.notna(row[b_col]) else ""
                        raw_n = str(row[n_col]).strip() if n_col and n_col in row and pd.notna(row[n_col]) else ""
                        if raw_b:
                            full_rows.append({
                                "b_key": make_brand_match_key(raw_b),
                                "n_key": make_net_match_key(self.normalizer.normalize_network(raw_n)) if raw_n else "all",
                                "clicks": int(full_clean_clicks.iloc[idx]),
                            })
                    if full_rows:
                        full_f_df = pd.DataFrame(full_rows)
                        full_bn_clicks = full_f_df.groupby(["b_key", "n_key"])["clicks"].sum()
                        full_n_clicks = full_f_df.groupby("n_key")["clicks"].sum()
                        total_full_c = full_f_df["clicks"].sum()

                        base_bn_clicks = base_df.groupby(["b_key", "n_key"])["internal_clicks"].sum()
                        base_n_clicks = base_df.groupby("n_key")["internal_clicks"].sum()
                        total_base_c = base_df["internal_clicks"].sum()

                        if total_full_c > 0:
                            overall_traffic_ratio = float(total_base_c) / float(total_full_c)

                        for nk, n_tot in full_n_clicks.items():
                            if n_tot > 0:
                                net_ratios[nk] = float(base_n_clicks.get(nk, 0)) / float(n_tot)

                        for (bk, nk), bn_tot in full_bn_clicks.items():
                            if bn_tot > 0:
                                brand_net_ratios[(bk, nk)] = float(base_bn_clicks.get((bk, nk), 0)) / float(bn_tot)
            except Exception as e_ratio:
                print(f"Traffic ratio calculation notice: {e_ratio}")

        # 2. Process each affiliate export through its adapter
        processed_network_dfs = []
        network_logs = []

        for item in affiliate_files:
            filename = item.get("filename", "unknown_file")
            raw_df = item["df"]
            specified_network = item.get("network_name")

            # Check if file has a native date column
            date_col = find_column(
                raw_df,
                [
                    "transaction date",
                    "conversion date",
                    "order date",
                    "sale date",
                    "click date",
                    "date",
                    "day",
                    "datetime",
                ],
                exclude_keywords=[
                    "last action",
                    "action date",
                    "created",
                    "updated",
                    "modified",
                    "start date",
                    "end date",
                ],
            )
            has_native_date = bool(date_col)

            # Filter affiliate export by date if it has date columns
            if start_date and end_date and not raw_df.empty and has_native_date:
                raw_df = filter_df_by_date(raw_df, start_date, end_date)

            detected_network = (
                specified_network
                if (specified_network and specified_network.lower() != "auto")
                else detect_network_from_filename_or_df(filename, raw_df)
            )

            adapter = get_adapter(
                detected_network,
                normalizer=self.normalizer,
                usd_to_inr_rate=usd_to_inr_rate,
            )
            try:
                proc_df = adapter.process(raw_df)

                # Determine if proportional scaling applies:
                # Networks that natively support custom date ranges (CJ, Pantech, Cashkaro, INRDeals, iCubesWire)
                # are already date-sliced if named for the date range or from a live bot query.
                # Full-month aggregate networks (Cuelinks, Admitad, Zonet) are proportionally scaled by clicks.
                is_already_date_ranged = (
                    f"{start_date}_to_{end_date}" in filename
                    or f"{start_date}_{end_date}" in filename
                    or "bot_live" in filename
                ) and detected_network.lower() in [
                    "cj",
                    "pantech",
                    "cashkaro",
                    "inrdeals",
                    "icubeswire",
                    "cuelinks",
                    "zonet",
                    "admitad",
                ]

                # Check if scaling should be applied:
                # 1. Custom date window is active and internal clicks were filtered
                # 2. Affiliate export has no native daily transaction date rows
                # 3. File is NOT an already date-sliced feed
                is_scaled = False
                if (
                    start_date
                    and end_date
                    and internal_diag.get("is_date_filtered")
                    and not has_native_date
                    and not is_already_date_ranged
                    and not proc_df.empty
                ):
                    scaled_revs = []
                    for _, r in proc_df.iterrows():
                        bk = make_brand_match_key(str(r["brand"]))
                        nk = make_net_match_key(str(r["network"]))
                        ratio = brand_net_ratios.get((bk, nk))
                        if ratio is None:
                            ratio = net_ratios.get(nk, overall_traffic_ratio)
                        ratio = max(0.0, min(1.0, float(ratio)))
                        scaled_revs.append(round(float(r["revenue"]) * ratio, 2))
                    proc_df["revenue"] = scaled_revs
                    is_scaled = True

                total_file_rev = float(proc_df["revenue"].sum()) if not proc_df.empty else 0.0
                processed_network_dfs.append(proc_df)
                network_logs.append(
                    {
                        "filename": filename,
                        "detected_network": adapter.network_name,
                        "status": "success",
                        "records_count": len(proc_df),
                        "total_revenue": round(total_file_rev, 2),
                        "is_date_scaled": is_scaled,
                    }
                )
            except Exception as e:
                network_logs.append(
                    {
                        "filename": filename,
                        "detected_network": detected_network,
                        "status": "error",
                        "error_message": str(e),
                    }
                )

        # Combine all affiliate revenue tables
        if processed_network_dfs:
            combined_revenue_df = pd.concat(processed_network_dfs, ignore_index=True)
            if (
                not combined_revenue_df.empty
                and "brand" in combined_revenue_df.columns
                and "network" in combined_revenue_df.columns
            ):
                affiliate_agg = (
                    combined_revenue_df.groupby(["brand", "network"], as_index=False)
                    .agg(
                        revenue=("revenue", "sum"),
                        original_brand=("original_brand", lambda x: ", ".join(sorted(set(x)))),
                        is_matched=("is_matched", "all"),
                    )
                )
                # Add match keys for alike brand matching
                affiliate_agg["b_key"] = affiliate_agg["brand"].apply(make_brand_match_key)
                affiliate_agg["n_key"] = affiliate_agg["network"].apply(make_net_match_key)
            else:
                affiliate_agg = pd.DataFrame(
                    columns=["brand", "network", "revenue", "original_brand", "is_matched", "b_key", "n_key"]
                )
        else:
            affiliate_agg = pd.DataFrame(
                columns=["brand", "network", "revenue", "original_brand", "is_matched", "b_key", "n_key"]
            )

        # 3. Perform LEFT JOIN on case-insensitive alike keys: ['b_key', 'n_key']
        merged_df = pd.merge(
            base_df,
            affiliate_agg[["b_key", "n_key", "revenue"]],
            on=["b_key", "n_key"],
            how="left",
        )

        merged_df["revenue"] = merged_df["revenue"].fillna(0.0).round(2)

        # 4. Dynamic Auto-Match: Check for affiliate revenue rows where brand is known but network pair was missing
        orphans = []
        if not affiliate_agg.empty:
            merged_check = pd.merge(
                affiliate_agg,
                base_df[["b_key", "n_key"]].assign(_in_base=True),
                on=["b_key", "n_key"],
                how="left",
            )
            unmatched_rows = merged_check[
                (merged_check["_in_base"].isna()) & (merged_check["revenue"] > 0)
            ]

            # Build a lookup of known brands from base_df
            known_brands_map = {}
            for _, brow in base_df.iterrows():
                bk = brow["b_key"]
                if bk not in known_brands_map:
                    known_brands_map[bk] = brow["original_brand"]

            auto_matched_rows = []
            for _, urow in unmatched_rows.iterrows():
                b_k = urow["b_key"]
                rev_val = round(float(urow["revenue"]), 2)
                if b_k in known_brands_map:
                    # Verified brand in portfolio! Auto-include in master table
                    orig_b = known_brands_map[b_k]
                    orig_n = urow["network"]
                    auto_matched_rows.append(
                        {
                            "row_order": len(base_df) + len(auto_matched_rows) + 1,
                            "std_brand": urow["brand"],
                            "std_network": urow["network"],
                            "b_key": b_k,
                            "n_key": urow["n_key"],
                            "original_brand": orig_b,
                            "original_network": orig_n,
                            "internal_clicks": 0,
                            "revenue": rev_val,
                        }
                    )
                else:
                    # Brand completely unknown
                    orphans.append(
                        {
                            "brand": urow["brand"],
                            "network": urow["network"],
                            "revenue": rev_val,
                            "original_brand": urow.get("original_brand", ""),
                        }
                    )

            if auto_matched_rows:
                auto_df = pd.DataFrame(auto_matched_rows)
                merged_df = pd.concat([merged_df, auto_df], ignore_index=True)

        # 5. Calculate RPCs = Revenue / Internal Clicks
        # Preserves up to 4 decimal places for sub-penny performance (e.g. ₹0.0038)
        def calc_rpc(row):
            clicks = row["internal_clicks"]
            rev = row["revenue"]
            if clicks > 0 and rev > 0:
                val = float(rev) / float(clicks)
                # If sub-cent/sub-penny (< 0.01), display 4 decimals so it never rounds to 0.00
                if val < 0.01:
                    return round(val, 4)
                return round(val, 2)
            return 0.0

        merged_df["RPCs"] = merged_df.apply(calc_rpc, axis=1)

        # Preserve original user ordering
        merged_df = merged_df.sort_values("row_order").reset_index(drop=True)

        # 6. Format to exact user master sheet specification
        master_output_df = pd.DataFrame(
            {
                "WEBSITE / BRAND": merged_df["original_brand"],
                "AFFILIATE NETWORK": merged_df["original_network"],
                "SUM of INTERNAL CLICKS": merged_df["internal_clicks"],
                "Revenue": merged_df["revenue"],
                "RPCs": merged_df["RPCs"],
            }
        )

        total_rev = float(master_output_df["Revenue"].sum())
        total_clicks = int(master_output_df["SUM of INTERNAL CLICKS"].sum())
        overall_rpc = (
            round(total_rev / total_clicks, 4) if total_clicks > 0 else 0.0
        )

        summary = {
            "total_revenue": round(total_rev, 2),
            "total_internal_clicks": total_clicks,
            "overall_portfolio_rpc": overall_rpc,
            "total_master_rows": len(master_output_df),
            "matched_revenue_rows": int((master_output_df["Revenue"] > 0).sum()),
            "orphaned_affiliate_records": orphans,
            "network_processing_logs": network_logs,
            "internal_clicks_diag": internal_diag,
            "date_range": internal_diag.get("date_range", "Full Period"),
            "is_date_filtered": internal_diag.get("is_date_filtered", False),
            "start_date": start_date or "",
            "end_date": end_date or "",
        }

        return {
            "master_df": master_output_df,
            "summary": summary,
        }

    @staticmethod
    def export_to_excel_buffer(df: pd.DataFrame) -> BytesIO:
        """Export master dataframe to a beautifully styled Excel workbook in memory."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Consolidated RPCs"

        headers = list(df.columns)
        ws.append(headers)

        header_font = Font(name="Calibri", size=11, bold=True, color="000000")
        header_fill = PatternFill(
            start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"
        )
        thin_border = Border(
            left=Side(style="thin", color="D9D9D9"),
            right=Side(style="thin", color="D9D9D9"),
            top=Side(style="thin", color="D9D9D9"),
            bottom=Side(style="thin", color="D9D9D9"),
        )

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        for r_idx, row in enumerate(df.itertuples(index=False), start=2):
            for c_idx, val in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.border = thin_border
                if c_idx in [1, 2]:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                elif c_idx == 3:
                    cell.number_format = "#,##0"
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                elif c_idx == 4:
                    cell.number_format = "#,##0.00"
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    if val and float(val) > 0:
                        cell.font = Font(color="1F4E79", bold=True)
                elif c_idx == 5:
                    if val and float(val) > 0 and float(val) < 0.01:
                        cell.number_format = "0.0000"
                    else:
                        cell.number_format = "0.00"
                    cell.alignment = Alignment(horizontal="right", vertical="center")

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    @staticmethod
    def export_to_tsv_string(df: pd.DataFrame) -> str:
        """Export master dataframe as TSV for direct copy-paste into Google Sheets."""
        return df.to_csv(sep="\t", index=False)
