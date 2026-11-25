"""Unit tests for Air India Direct (Special OWN) integration.
Tests adapter, network detection, normalization, bot logic, and end-to-end ETL merge.
"""

import unittest
import pandas as pd
from backend.etl.adapters.airindia import AirIndiaAdapter
from backend.etl.adapters import detect_network_from_filename_or_df, get_adapter
from backend.etl.normalizer import BrandNormalizer
from backend.etl.engine import ETLEngine
from backend.bots.airindia_bot import AirIndiaBot, DEFAULT_AIRINDIA_RECORDS


class TestAirIndiaIntegration(unittest.TestCase):
    def setUp(self):
        self.normalizer = BrandNormalizer()
        self.adapter = AirIndiaAdapter(normalizer=self.normalizer)
        self.engine = ETLEngine(normalizer=self.normalizer)

    def test_network_detection(self):
        # Filename detection
        self.assertEqual(detect_network_from_filename_or_df("airindia_bot_live.csv"), "airindia")
        self.assertEqual(detect_network_from_filename_or_df("air_india_campaigns_2026-10-01_to_2026-10-31.csv"), "airindia")

        # Column signature detection
        df_sig = pd.DataFrame(columns=["Day", "Visits", "Flight Booking - Orders"])
        self.assertEqual(detect_network_from_filename_or_df("unknown_export.csv", df_sig), "airindia")

    def test_network_normalization_to_special_own(self):
        # Must normalize to Special (OWN) to match internal clicks table
        self.assertEqual(self.normalizer.normalize_network("airindia"), "Special (OWN)")
        self.assertEqual(self.normalizer.normalize_network("Air India"), "Special (OWN)")
        self.assertEqual(self.normalizer.normalize_network("special (own)"), "Special (OWN)")

    def test_adapter_with_orders_and_payout_calculation(self):
        # Raw table simulating Adobe Analytics DoD Funnel
        df_raw = pd.DataFrame({
            "Date": ["2026-10-26", "2026-10-25"],
            "Campaign": ["AirIndia", "AirIndia"],
            "Visits": [115, 108],
            "Flight Booking - Orders": [7, 6],
        })

        processed = self.adapter.process(df_raw)
        self.assertEqual(len(processed), 1)
        row = processed.iloc[0]

        # Brand standardized to AirIndia, network to Special (OWN)
        self.assertEqual(row["brand"], "AirIndia")
        self.assertEqual(row["network"], "Special (OWN)")
        # 7 + 6 = 13 orders
        self.assertEqual(row["transactions"], 13)
        # 13 orders * ₹150 contracted payout = ₹1,950.00
        self.assertEqual(row["revenue"], 1950.0)

    def test_adapter_with_precomputed_payout(self):
        df_raw = pd.DataFrame({
            "Date": ["2026-10-26", "2026-10-25"],
            "Campaign": ["AirIndia", "AirIndia"],
            "Visits": [115, 108],
            "Orders": [7, 6],
            "Payout": [1050.0, 900.0],
        })

        processed = self.adapter.process(df_raw)
        row = processed.iloc[0]
        self.assertEqual(row["transactions"], 13)
        self.assertEqual(row["revenue"], 1950.0)

    def test_end_to_end_merge_with_internal_clicks(self):
        # Base internal clicks table containing AirIndia under Special (OWN)
        clicks_df = pd.DataFrame({
            "WEBSITE / BRAND": ["AirIndia", "AirIndia", "Amazon"],
            "AFFILIATE NETWORK": ["Special (OWN)", "cuelinks", "Special (OWN)"],
            "SUM of INTERNAL CLICKS": [757, 1200, 5000],
        })

        # Air India bot report: 32 orders @ ₹150 = ₹4,800.00
        airindia_df = pd.DataFrame({
            "Date": ["2026-10-26", "2026-10-25", "2026-10-24", "2026-10-23", "2026-10-22", "2026-10-21", "2026-10-20"],
            "Campaign": ["AirIndia"] * 7,
            "Visits": [115, 108, 128, 130, 132, 110, 138],
            "Orders": [7, 6, 4, 2, 4, 3, 6],
            "Payout": [1050.0, 900.0, 600.0, 300.0, 600.0, 450.0, 900.0],
        })

        affiliate_files = [
            {
                "filename": "airindia_campaigns_2026-10-20_to_2026-10-26.csv",
                "network_name": "airindia",
                "df": airindia_df,
            }
        ]

        result = self.engine.run_pipeline(clicks_df, affiliate_files)
        master_df = result["master_df"]

        # Expected 6 columns
        expected_cols = [
            "WEBSITE / BRAND",
            "AFFILIATE NETWORK",
            "SUM of INTERNAL CLICKS",
            "Revenue",
            "Conversion Ratio",
            "RPCs",
        ]
        self.assertEqual(list(master_df.columns), expected_cols)

        # Locate AirIndia Special (OWN) row
        ai_own = master_df[
            (master_df["WEBSITE / BRAND"] == "AirIndia") &
            (master_df["AFFILIATE NETWORK"] == "Special (OWN)")
        ]
        self.assertEqual(len(ai_own), 1)
        row = ai_own.iloc[0]

        # 757 internal clicks, 32 orders, ₹4800 revenue
        self.assertEqual(row["SUM of INTERNAL CLICKS"], 757)
        self.assertAlmostEqual(row["Revenue"], 4800.0, places=2)
        # CR = (32 / 757) * 100% = 4.23%
        expected_cr = round((32 / 757) * 100.0, 2)
        self.assertAlmostEqual(row["Conversion Ratio"], expected_cr, places=2)
        # RPC = 4800 / 757 = 6.3408...
        expected_rpc = round(4800.0 / 757, 2)
        self.assertAlmostEqual(row["RPCs"], expected_rpc, places=2)


if __name__ == "__main__":
    unittest.main()
