"""Unit tests for Ajio Direct (Special OWN) integration.
Tests adapter, network detection, normalization, bot logic, and end-to-end ETL merge.
"""

import unittest
import pandas as pd
from backend.etl.adapters.ajio import AjioAdapter
from backend.etl.adapters import detect_network_from_filename_or_df
from backend.etl.normalizer import BrandNormalizer
from backend.etl.engine import ETLEngine
from backend.bots.ajio_bot import AjioBot, DEFAULT_AJIO_RECORDS


class TestAjioIntegration(unittest.TestCase):
    def setUp(self):
        self.normalizer = BrandNormalizer()
        self.adapter = AjioAdapter(normalizer=self.normalizer)
        self.engine = ETLEngine(normalizer=self.normalizer)

    def test_network_detection(self):
        # Filename detection
        self.assertEqual(detect_network_from_filename_or_df("ajio_bot_live.csv"), "ajio")
        self.assertEqual(detect_network_from_filename_or_df("ajio_campaigns_2026-11-01_to_2026-11-15.csv"), "ajio")

    def test_network_normalization_to_special_own(self):
        # Must normalize to Special (OWN) to match internal clicks table
        self.assertEqual(self.normalizer.normalize_network("ajio direct"), "Special (OWN)")
        self.assertEqual(self.normalizer.normalize_network("ajio (own)"), "Special (OWN)")
        self.assertEqual(self.normalizer.normalize_network("Special (OWN)"), "Special (OWN)")

    def test_adapter_with_orders_and_payout(self):
        # Raw table simulating Trackier API report
        df_raw = pd.DataFrame({
            "Date": ["2026-11-15", "2026-11-14"],
            "Campaign": ["Ajio", "Ajio"],
            "Clicks": [14426, 14655],
            "Orders": [27, 26],
            "Payout": [4608.02, 4231.49],
        })

        processed = self.adapter.process(df_raw)
        self.assertEqual(len(processed), 1)
        row = processed.iloc[0]

        # Brand standardized to Ajio, network to Special (OWN)
        self.assertEqual(row["brand"], "Ajio")
        self.assertEqual(row["network"], "Special (OWN)")
        # 27 + 26 = 53 orders
        self.assertEqual(row["transactions"], 53)
        # 4608.02 + 4231.49 = 8839.51
        self.assertAlmostEqual(row["revenue"], 8839.51, places=2)

    def test_end_to_end_merge_with_internal_clicks(self):
        # Base internal clicks table containing Ajio under Special (OWN)
        clicks_df = pd.DataFrame({
            "WEBSITE / BRAND": ["Ajio", "Ajio", "Amazon"],
            "AFFILIATE NETWORK": ["Special (OWN)", "cashkaro", "Special (OWN)"],
            "SUM of INTERNAL CLICKS": [25425, 4000, 5000],
        })

        ajio_df = pd.DataFrame({
            "Date": ["2026-11-01", "2026-11-02"],
            "Campaign": ["Ajio", "Ajio"],
            "Clicks": [7520, 6895],
            "Orders": [31, 29],
            "Payout": [4816.72, 4411.50],
        })

        affiliate_files = [
            {
                "filename": "ajio_campaigns_2026-11-01_to_2026-11-02.csv",
                "network_name": "ajio",
                "df": ajio_df,
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

        # Ajio on Special (OWN) row
        ajio_row = master_df[
            (master_df["WEBSITE / BRAND"] == "Ajio")
            & (master_df["AFFILIATE NETWORK"] == "Special (OWN)")
        ].iloc[0]

        self.assertEqual(ajio_row["SUM of INTERNAL CLICKS"], 25425)
        # 4816.72 + 4411.50 = 9228.22
        self.assertAlmostEqual(ajio_row["Revenue"], 9228.22, places=2)
        # 60 orders / 25425 clicks = 0.23598% -> 0.24%
        self.assertEqual(ajio_row["Conversion Ratio"], 0.24)
        # 9228.22 / 25425 = 0.36295 -> 0.36
        self.assertEqual(ajio_row["RPCs"], 0.36)


if __name__ == "__main__":
    unittest.main()
