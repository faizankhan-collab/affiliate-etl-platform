"""Unit tests for the Affiliate ETL Engine and Adapters.
"""

import os
import unittest
import pandas as pd

from backend.etl.engine import ETLEngine
from backend.etl.normalizer import BrandNormalizer


class TestAffiliateETL(unittest.TestCase):
    def setUp(self):
        self.sample_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "backend", "sample_data"
        )
        self.engine = ETLEngine()

    def test_brand_normalization(self):
        norm = BrandNormalizer()
        self.assertEqual(norm.normalize_brand("Flipkart CPS [IN]")[0], "Flipkart")
        self.assertEqual(norm.normalize_brand("Tata CliQ [IN]")[0], "TatacliQ")
        self.assertEqual(norm.normalize_brand("Nykaa Fashion [IN]")[0], "NykaaFashion")
        self.assertEqual(norm.normalize_brand("Amazon.in")[0], "Amazon")
        self.assertEqual(norm.normalize_brand("Amazon US Associates")[0], "Amazon US")
        self.assertEqual(norm.normalize_brand("Ajio Luxe")[0], "Ajio Lux")

    def test_full_pipeline_against_sample_datasets(self):
        # 1. Load internal clicks
        clicks_path = os.path.join(self.sample_dir, "internal_clicks_buyhatke.csv")
        clicks_df = pd.read_csv(clicks_path)

        # 2. Prepare network files
        affiliate_files = [
            {
                "filename": "cuelinks_monthly_export.xlsx",
                "network_name": "cuelinks",
                "df": pd.read_excel(os.path.join(self.sample_dir, "cuelinks_monthly_export.xlsx")),
            },
            {
                "filename": "admitad_monthly_export.csv",
                "network_name": "admitad",
                "df": pd.read_csv(os.path.join(self.sample_dir, "admitad_monthly_export.csv")),
            },
            {
                "filename": "zonet_monthly_export.xlsx",
                "network_name": "zonet",
                "df": pd.read_excel(os.path.join(self.sample_dir, "zonet_monthly_export.xlsx")),
            },
            {
                "filename": "cashkaro_monthly_export.csv",
                "network_name": "cashkaro",
                "df": pd.read_csv(os.path.join(self.sample_dir, "cashkaro_monthly_export.csv")),
            },
            {
                "filename": "icubeswire_monthly_export.csv",
                "network_name": "icubeswire",
                "df": pd.read_csv(os.path.join(self.sample_dir, "icubeswire_monthly_export.csv")),
            },
        ]

        result = self.engine.run_pipeline(clicks_df, affiliate_files)
        master_df = result["master_df"]
        summary = result["summary"]

        self.assertFalse(master_df.empty)
        self.assertEqual(summary["total_master_rows"], len(clicks_df))

        # Check Flipkart + Cuelinks
        fk_cue = master_df[
            (master_df["WEBSITE / BRAND"] == "Flipkart")
            & (master_df["AFFILIATE NETWORK"] == "cuelinks")
        ].iloc[0]
        self.assertAlmostEqual(fk_cue["Revenue"], 339899.70, places=2)
        self.assertEqual(fk_cue["RPCs"], 0.22)

        # Check Flipkart + Zonet
        fk_zone = master_df[
            (master_df["WEBSITE / BRAND"] == "Flipkart")
            & (master_df["AFFILIATE NETWORK"] == "zonet")
        ].iloc[0]
        self.assertAlmostEqual(fk_zone["Revenue"], 344830.00, places=2)
        self.assertEqual(fk_zone["RPCs"], 0.23)

        # Check Amazon + Zonet
        amz_zone = master_df[
            (master_df["WEBSITE / BRAND"] == "Amazon")
            & (master_df["AFFILIATE NETWORK"] == "zonet")
        ].iloc[0]
        self.assertAlmostEqual(amz_zone["Revenue"], 25221.88, places=2)
        self.assertEqual(amz_zone["RPCs"], 0.19)

        # Check Myntra + Admitad
        myn_adm = master_df[
            (master_df["WEBSITE / BRAND"] == "Myntra")
            & (master_df["AFFILIATE NETWORK"] == "admitad")
        ].iloc[0]
        self.assertAlmostEqual(myn_adm["Revenue"], 158114.54, places=2)
        self.assertEqual(myn_adm["RPCs"], 0.15)

        # Check TatacliQ + Admitad
        tata_adm = master_df[
            (master_df["WEBSITE / BRAND"] == "TatacliQ")
            & (master_df["AFFILIATE NETWORK"] == "admitad")
        ].iloc[0]
        self.assertAlmostEqual(tata_adm["Revenue"], 32595.67, places=2)
        self.assertEqual(tata_adm["RPCs"], 0.10)

        # Check Vijay Sales + Icubeswire
        vijay_icube = master_df[
            (master_df["WEBSITE / BRAND"] == "Vijay Sales")
            & (master_df["AFFILIATE NETWORK"] == "icubeswire")
        ].iloc[0]
        self.assertAlmostEqual(vijay_icube["Revenue"], 3205.00, places=2)
        self.assertEqual(vijay_icube["RPCs"], 0.02)

        # Check Excel export buffer creation
        buf = self.engine.export_to_excel_buffer(master_df)
        self.assertGreater(buf.getbuffer().nbytes, 1000)

        # Check TSV export
        tsv = self.engine.export_to_tsv_string(master_df)
        self.assertIn("Flipkart\tcuelinks\t1560054\t339899.7\t0.22", tsv)

    def test_zonet_real_adapter(self):
        zonet_path = os.path.join(self.sample_dir, "zonet_real.csv")
        clicks_path = os.path.join(self.sample_dir, "affiliateStatTable_real.csv")
        if not os.path.exists(zonet_path) or not os.path.exists(clicks_path):
            return

        clicks_df = pd.read_csv(clicks_path)
        zonet_df = pd.read_csv(zonet_path)

        result = self.engine.run_pipeline(
            clicks_df,
            [{"filename": "zonet_real.csv", "network_name": "auto", "df": zonet_df}]
        )
        master_df = result["master_df"]

        # 1. Flipkart Zonet: 2,580,457 clicks, ₹1,743,121.62 payout, RPC ~ 0.68
        fk_zonet = master_df[
            (master_df["WEBSITE / BRAND"] == "Flipkart")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "zonet")
        ].iloc[0]
        self.assertAlmostEqual(fk_zonet["Revenue"], 1743121.62, places=2)
        self.assertEqual(fk_zonet["RPCs"], 0.68)

        # 2. Amazon Zonet: 3,168,116 clicks, ₹1,450,692.79 payout, RPC ~ 0.46
        amz_zonet = master_df[
            (master_df["WEBSITE / BRAND"] == "Amazon")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "zonet")
        ].iloc[0]
        self.assertAlmostEqual(amz_zonet["Revenue"], 1450692.79, places=2)
        self.assertEqual(amz_zonet["RPCs"], 0.46)

        # 3. Amazon US Zonet: 72,560 clicks, ₹0.00 payout, RPC = 0.00
        amz_us = master_df[
            (master_df["WEBSITE / BRAND"] == "Amazon US")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "zonet")
        ].iloc[0]
        self.assertEqual(amz_us["Revenue"], 0.00)
        self.assertEqual(amz_us["RPCs"], 0.00)

        # 4. Myntra Zonet is cleanly matched into master table
        myntra_zonet = master_df[
            (master_df["WEBSITE / BRAND"] == "Myntra")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "zonet")
        ].iloc[0]
        self.assertAlmostEqual(myntra_zonet["Revenue"], 126332.34, places=2)

    def test_icubeswire_live_adapter(self):
        icubes_path = os.path.join(self.sample_dir, "icubeswire_bot_live.csv")
        clicks_path = os.path.join(self.sample_dir, "affiliateStatTable_real.csv")
        if not os.path.exists(icubes_path) or not os.path.exists(clicks_path):
            return

        clicks_df = pd.read_csv(clicks_path)
        icubes_df = pd.read_csv(icubes_path)

        result = self.engine.run_pipeline(
            clicks_df,
            [{"filename": "icubeswire_bot_live.csv", "network_name": "icubeswire", "df": icubes_df}]
        )
        master_df = result["master_df"]

        # 1. Boat Lifestyle iCubeswire: revenue parsed and matched
        boat_row = master_df[
            (master_df["WEBSITE / BRAND"] == "Boat Lifestyle")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "icubeswire")
        ].iloc[0]
        self.assertGreater(boat_row["Revenue"], 1000.0)

        # 2. Vijay Sales iCubeswire: revenue parsed and matched
        vijay_row = master_df[
            (master_df["WEBSITE / BRAND"] == "Vijay Sales")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "icubeswire")
        ].iloc[0]
        self.assertGreaterEqual(vijay_row["Revenue"], 0.0)

        # 3. Campus Shoes iCubeswire: verified non-zero revenue
        campus_row = master_df[
            (master_df["WEBSITE / BRAND"] == "Campus Shoes")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "icubeswire")
        ].iloc[0]
        self.assertGreater(campus_row["Revenue"], 1000.0)

        # 4. Decathlon iCubeswire: verified non-zero revenue
        decathlon_row = master_df[
            (master_df["WEBSITE / BRAND"] == "Decathlon")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "icubeswire")
        ].iloc[0]
        self.assertGreater(decathlon_row["Revenue"], 100.0)

    def test_inrdeals_live_adapter(self):
        inr_path = os.path.join(self.sample_dir, "inrdeals_bot_live.csv")
        clicks_path = os.path.join(self.sample_dir, "affiliateStatTable_real.csv")
        if not os.path.exists(inr_path) or not os.path.exists(clicks_path):
            return

        clicks_df = pd.read_csv(clicks_path)
        inr_df = pd.read_csv(inr_path)

        result = self.engine.run_pipeline(
            clicks_df,
            [{"filename": "inrdeals_bot_live.csv", "network_name": "inrdeals", "df": inr_df}]
        )
        master_df = result["master_df"]

        # 1. H&M INR Deals: verified non-zero revenue
        hm_row = master_df[
            (master_df["WEBSITE / BRAND"] == "H&M")
            & (master_df["AFFILIATE NETWORK"].str.lower().str.replace(" ", "") == "inrdeals")
        ].iloc[0]
        self.assertGreater(hm_row["Revenue"], 5000.0)
        self.assertIn(round(hm_row["Revenue"], 2), [10070.14, 10687.27])

        # 2. Dyson INR Deals: verified non-zero revenue
        dyson_row = master_df[
            (master_df["WEBSITE / BRAND"] == "Dyson")
            & (master_df["AFFILIATE NETWORK"].str.lower().str.replace(" ", "") == "inrdeals")
        ].iloc[0]
        self.assertGreater(dyson_row["Revenue"], 500.0)

    def test_cashkaro_dermaco_match(self):
        ck_path = os.path.join(self.sample_dir, "cashkaro_campaigns_2026-10-01_to_2026-10-10.csv")
        if not os.path.exists(ck_path):
            ck_path = os.path.join(self.sample_dir, "cashkaro_bot_live.csv")
        clicks_path = os.path.join(self.sample_dir, "affiliateStatTable_real.csv")
        if not os.path.exists(ck_path) or not os.path.exists(clicks_path):
            return

        clicks_df = pd.read_csv(clicks_path)
        ck_df = pd.read_csv(ck_path)

        result = self.engine.run_pipeline(
            clicks_df,
            [{"filename": os.path.basename(ck_path), "network_name": "cashkaro", "df": ck_df}]
        )
        master_df = result["master_df"]

        # Dermaco Cashkaro: 726 clicks, ₹492.23 revenue, RPC 0.68
        derma_row = master_df[
            (master_df["WEBSITE / BRAND"] == "Dermaco")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "cashkaro")
        ].iloc[0]
        self.assertAlmostEqual(derma_row["Revenue"], 492.23, places=2)
        self.assertEqual(derma_row["RPCs"], 0.68)
        self.assertEqual(derma_row["SUM of INTERNAL CLICKS"], 726)

    def test_cj_adapter_and_usd_conversion(self):
        cj_path = os.path.join(self.sample_dir, "cj_campaigns_2026-10-01_to_2026-10-10.csv")
        if not os.path.exists(cj_path):
            cj_path = os.path.join(self.sample_dir, "cj_bot_live.csv")
        clicks_path = os.path.join(self.sample_dir, "affiliateStatTable_real.csv")
        if not os.path.exists(cj_path) or not os.path.exists(clicks_path):
            return

        clicks_df = pd.read_csv(clicks_path)
        cj_df = pd.read_csv(cj_path)

        from backend.etl.adapters.cj import CJAdapter
        adapter = CJAdapter(usd_to_inr_rate=94.73965)
        processed = adapter.process(cj_df)

        # 1. Verify USD to INR conversion dynamically against raw export
        myntra_cj = processed[processed["brand"] == "Myntra"].iloc[0]
        raw_usd_str = str(cj_df[cj_df["Advertiser Name"].str.contains("Myntra", case=False)]["Publisher Commission (USD)"].iloc[0])
        myntra_raw_usd = float(raw_usd_str.replace("$", "").replace(",", ""))
        expected_inr = round(myntra_raw_usd * 94.73965, 2)
        self.assertAlmostEqual(myntra_cj["revenue"], expected_inr, places=2)
        self.assertTrue(myntra_cj["is_matched"])

        if "Sharafdg.uae" in processed["brand"].values:
            sharaf_cj = processed[processed["brand"] == "Sharafdg.uae"].iloc[0]
            self.assertEqual(sharaf_cj["revenue"], 0.0)
            self.assertTrue(sharaf_cj["is_matched"])

        # 2. Pipeline merge with Buyhatke base sheet
        result = self.engine.run_pipeline(
            clicks_df,
            [{"filename": "cj_bot_live.csv", "network_name": "cj", "df": cj_df}],
            usd_to_inr_rate=94.73965,
        )
        master_df = result["master_df"]
        summary = result["summary"]

        # Ensure preservation of base sheet rows
        self.assertGreaterEqual(len(master_df), 140)

        # Sharafdg.uae, cj in master table
        sharaf_master = master_df[
            (master_df["WEBSITE / BRAND"] == "Sharafdg.uae")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "cj")
        ].iloc[0]
        self.assertEqual(sharaf_master["SUM of INTERNAL CLICKS"], 694)
        self.assertEqual(sharaf_master["Revenue"], 0.0)
        self.assertEqual(sharaf_master["RPCs"], 0.0)

        # Myntra on CJ is cleanly matched in master table
        myntra_cj_master = master_df[
            (master_df["WEBSITE / BRAND"] == "Myntra")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "cj")
        ].iloc[0]
        self.assertAlmostEqual(myntra_cj_master["Revenue"], expected_inr, places=2)

    def test_pantech_adapter_and_usd_conversion(self):
        pan_fixture = os.path.join(self.sample_dir, "pantech_campaigns_2026-10-01_to_2026-10-31.csv")
        pan_path = pan_fixture if os.path.exists(pan_fixture) else os.path.join(self.sample_dir, "pantech_bot_live.csv")
        clicks_path = os.path.join(self.sample_dir, "affiliateStatTable_real.csv")
        if not os.path.exists(pan_path) or not os.path.exists(clicks_path):
            return

        clicks_df = pd.read_csv(clicks_path)
        pan_df = pd.read_csv(pan_path)

        from backend.etl.adapters.pantech import PantechAdapter
        adapter = PantechAdapter(usd_to_inr_rate=94.73965)
        processed = adapter.process(pan_df)

        # 1. Verify USD to INR conversion
        fk_pan = processed[processed["brand"] == "Flipkart"].iloc[0]
        # $410.75 * 94.73965 = ₹38,914.31
        self.assertAlmostEqual(fk_pan["revenue"], 38914.31, places=2)
        self.assertTrue(fk_pan["is_matched"])

        ajio_pan = processed[processed["brand"] == "Ajio"].iloc[0]
        raw_usd_str = str(pan_df[pan_df["Client Name"].str.contains("Ajio", case=False)]["Payout (USD)"].iloc[0])
        ajio_raw_usd = float(raw_usd_str.replace("$", "").replace(",", ""))
        expected_ajio_inr = round(ajio_raw_usd * 94.73965, 2)
        self.assertAlmostEqual(ajio_pan["revenue"], expected_ajio_inr, places=2)
        self.assertTrue(ajio_pan["is_matched"])

        # 2. Pipeline merge with Buyhatke base sheet
        result = self.engine.run_pipeline(
            clicks_df,
            [{"filename": "pantech_bot_live.csv", "network_name": "pantech", "df": pan_df}],
            usd_to_inr_rate=94.73965,
        )
        master_df = result["master_df"]

        # Ensure 100% preservation of base sheet rows
        self.assertGreaterEqual(len(master_df), 140)

        # Flipkart, Pantech in master table: 2,764,090 clicks, ₹38,914.31 revenue, RPC: 0.01
        fk_master = master_df[
            (master_df["WEBSITE / BRAND"] == "Flipkart")
            & (master_df["AFFILIATE NETWORK"].str.lower() == "pantech")
        ].iloc[0]
        self.assertEqual(fk_master["SUM of INTERNAL CLICKS"], 2764090)
        self.assertAlmostEqual(fk_master["Revenue"], 38914.31, places=2)
        self.assertEqual(fk_master["RPCs"], 0.01)

    def test_daily_clicks_date_filtering_and_custom_rpc(self):
        daily_path = os.path.join(self.sample_dir, "daily_internal_clicks_buyhatke.csv")
        pan_fixture = os.path.join(self.sample_dir, "pantech_campaigns_2026-10-01_to_2026-10-31.csv")
        pan_path = pan_fixture if os.path.exists(pan_fixture) else os.path.join(self.sample_dir, "pantech_bot_live.csv")
        if not os.path.exists(daily_path) or not os.path.exists(pan_path):
            return

        daily_df = pd.read_csv(daily_path)
        pan_df = pd.read_csv(pan_path)

        # 1. Test Custom Date Range: Oct 1 - Oct 10
        res_10 = self.engine.run_pipeline(
            daily_df,
            [{"filename": "pantech_bot_live.csv", "network_name": "pantech", "df": pan_df}],
            usd_to_inr_rate=94.73965,
            start_date="2026-10-01",
            end_date="2026-10-10",
        )
        self.assertTrue(res_10["summary"]["is_date_filtered"])
        self.assertEqual(res_10["summary"]["start_date"], "2026-10-01")
        self.assertEqual(res_10["summary"]["end_date"], "2026-10-10")

        m_10 = res_10["master_df"]
        pan_row_10 = m_10[
            (m_10["WEBSITE / BRAND"] == "Flipkart")
            & (m_10["AFFILIATE NETWORK"].str.lower() == "pantech")
        ].iloc[0]
        # Exact proportional allocation: 2,764,090 * 53.718% = 1,484,825 clicks
        self.assertEqual(pan_row_10["SUM of INTERNAL CLICKS"], 1484825)
        self.assertAlmostEqual(pan_row_10["Revenue"], 38914.31, places=2)
        self.assertEqual(pan_row_10["RPCs"], 0.03)

        # 2. Test Full Month: Oct 1 - Oct 31
        res_full = self.engine.run_pipeline(
            daily_df,
            [{"filename": "pantech_bot_live.csv", "network_name": "pantech", "df": pan_df}],
            usd_to_inr_rate=94.73965,
            start_date="2026-10-01",
            end_date="2026-10-31",
        )
        m_full = res_full["master_df"]
        pan_row_full = m_full[
            (m_full["WEBSITE / BRAND"] == "Flipkart")
            & (m_full["AFFILIATE NETWORK"].str.lower() == "pantech")
        ].iloc[0]
        self.assertEqual(pan_row_full["SUM of INTERNAL CLICKS"], 2764090)
        self.assertAlmostEqual(pan_row_full["Revenue"], 38914.31, places=2)
        self.assertEqual(pan_row_full["RPCs"], 0.01)

    def test_granular_affiliate_stats_with_dates(self):
        dates_path = os.path.join(self.sample_dir, "affiliateStatsTable_with_dates.csv")
        pan_fixture = os.path.join(self.sample_dir, "pantech_campaigns_2026-10-01_to_2026-10-31.csv")
        pan_path = pan_fixture if os.path.exists(pan_fixture) else os.path.join(self.sample_dir, "pantech_bot_live.csv")
        if not os.path.exists(dates_path) or not os.path.exists(pan_path):
            return

        dates_df = pd.read_csv(dates_path)
        pan_df = pd.read_csv(pan_path)

        # Test custom 11-day slice: Oct 10 - Oct 20
        res = self.engine.run_pipeline(
            dates_df,
            [{"filename": "pantech_bot_live.csv", "network_name": "pantech", "df": pan_df}],
            usd_to_inr_rate=94.73965,
            start_date="2026-10-10",
            end_date="2026-10-20",
        )
        m_df = res["master_df"]
        self.assertTrue(res["summary"]["is_date_filtered"])

        # Flipkart Pantech clicks for exact Oct 10-20 range: 1,931,175
        fk_pan = m_df[
            (m_df["WEBSITE / BRAND"] == "Flipkart")
            & (m_df["AFFILIATE NETWORK"].str.lower() == "pantech")
        ].iloc[0]
        self.assertEqual(fk_pan["SUM of INTERNAL CLICKS"], 1931175)
        self.assertAlmostEqual(fk_pan["Revenue"], 38914.31, places=2)

    def test_custom_10_day_date_range_clicks_and_revenue_scaling(self):
        """Verify 10-day custom slice (Oct 1 to Oct 10): clicks match Image 2 exactly and aggregate revenue scales."""
        dates_path = os.path.join(self.sample_dir, "affiliateStatsTable_with_dates.csv")
        admitad_path = os.path.join(self.sample_dir, "admitad_bot_live.xlsx")
        cuelinks_path = os.path.join(self.sample_dir, "cuelinks_bot_live.xls")
        if not os.path.exists(dates_path) or not os.path.exists(admitad_path):
            return

        dates_df = pd.read_csv(dates_path)
        with open(admitad_path, "rb") as f:
            ad_df = self.engine.parse_file_to_dataframe(f.read(), "admitad_bot_live.xlsx")
        with open(cuelinks_path, "rb") as f:
            cue_df = self.engine.parse_file_to_dataframe(f.read(), "cuelinks_bot_live.xls")

        res = self.engine.run_pipeline(
            dates_df,
            [
                {"filename": "admitad_monthly_export.xlsx", "network_name": "admitad", "df": ad_df},
                {"filename": "cuelinks_monthly_export.xls", "network_name": "cuelinks", "df": cue_df},
            ],
            start_date="2026-10-01",
            end_date="2026-10-10",
        )
        m_df = res["master_df"]
        summary = res["summary"]

        # 1. Total 10-day clicks must be 10,130,831
        self.assertEqual(summary["total_internal_clicks"], 10130831)

        # 2. Key brand clicks must match Image 2 exactly
        fk_adgama = m_df[
            (m_df["WEBSITE / BRAND"] == "Flipkart")
            & (m_df["AFFILIATE NETWORK"].str.lower() == "adgama")
        ].iloc[0]
        self.assertEqual(fk_adgama["SUM of INTERNAL CLICKS"], 653474)

        myntra_admitad = m_df[
            (m_df["WEBSITE / BRAND"] == "Myntra")
            & (m_df["AFFILIATE NETWORK"].str.lower() == "admitad")
        ].iloc[0]
        self.assertEqual(myntra_admitad["SUM of INTERNAL CLICKS"], 470556)

        tatacliq_admitad = m_df[
            (m_df["WEBSITE / BRAND"] == "TatacliQ")
            & (m_df["AFFILIATE NETWORK"].str.lower() == "admitad")
        ].iloc[0]
        self.assertEqual(tatacliq_admitad["SUM of INTERNAL CLICKS"], 219689)

        # 3. Revenue must be scaled proportionally (not full month)
        self.assertTrue(summary["network_processing_logs"][0]["is_date_scaled"])
        self.assertTrue(summary["network_processing_logs"][1]["is_date_scaled"])
        self.assertGreater(summary["network_processing_logs"][0]["total_revenue"], 0)
        self.assertGreater(summary["network_processing_logs"][1]["total_revenue"], 0)

    def test_saved_reports_crud(self):
        """Verify saved reports persistence: list, fetch, create, and delete."""
        import asyncio
        from backend.app import list_saved_reports, get_saved_report, save_custom_report, delete_saved_report

        async def run_crud():
            # 1. List pre-seeded reports
            listed = await list_saved_reports()
            self.assertTrue(listed["success"])
            self.assertGreaterEqual(len(listed["reports"]), 2)

            # 2. Fetch full detail of first report
            rep_id = listed["reports"][0]["id"]
            detail = await get_saved_report(rep_id)
            self.assertEqual(detail["id"], rep_id)
            self.assertIn("data", detail)
            self.assertIn("summary", detail)
            self.assertGreater(len(detail["data"]), 0)

            # 3. Create a test saved report
            test_id = "test_crud_report_2026"
            save_res = await save_custom_report({
                "id": test_id,
                "title": "Test CRUD Report",
                "start_date": "2026-10-01",
                "end_date": "2026-10-05",
                "summary": {"total_revenue": 1234.56, "total_internal_clicks": 50000},
                "data": [{"WEBSITE / BRAND": "Flipkart", "Revenue": 1234.56}],
            })
            self.assertTrue(save_res["success"])

            # Verify it exists
            fetch_res = await get_saved_report(test_id)
            self.assertEqual(fetch_res["title"], "Test CRUD Report")
            self.assertEqual(fetch_res["summary"]["total_revenue"], 1234.56)

            # 4. Delete test report
            del_res = await delete_saved_report(test_id)
            self.assertTrue(del_res["success"])

        asyncio.run(run_crud())

    def test_empty_affiliate_csv_parsing_and_pipeline(self):
        """Verify that CSV exports with valid headers but 0 rows are parsed cleanly and do not crash pipeline."""
        empty_cj_csv = (
            b"Advertiser CID,Advertiser Name,Advertiser Category,Publisher Commission (USD),"
            b"Sale Amount (USD),Items,Sales,Leads,Clicks,Impressions,CTR,CR,CPM (USD),EPC (USD)\n"
        )
        # 1. Test parsing directly
        df = self.engine.parse_file_to_dataframe(empty_cj_csv, "cj_campaigns_empty.csv")
        self.assertEqual(len(df), 0)
        self.assertGreater(len(df.columns), 1)

        # 2. Test pipeline execution with 0-row file
        clicks_path = os.path.join(self.sample_dir, "affiliateStatTable_real.csv")
        if os.path.exists(clicks_path):
            clicks_df = pd.read_csv(clicks_path)
            res = self.engine.run_pipeline(
                clicks_df,
                [{"filename": "cj_campaigns_empty.csv", "network_name": "cj", "df": df}],
                usd_to_inr_rate=94.74,
            )
            self.assertIn("master_df", res)
            self.assertGreaterEqual(len(res["master_df"]), 140)
            self.assertEqual(res["summary"]["network_processing_logs"][0]["status"], "success")
            self.assertEqual(res["summary"]["network_processing_logs"][0]["records_count"], 0)


if __name__ == "__main__":
    unittest.main()
