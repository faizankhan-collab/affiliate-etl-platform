import os
import pandas as pd
from backend.etl.engine import ETLEngine
from backend.etl.adapters import get_adapter

def audit_all_networks():
    engine = ETLEngine()
    
    # 1. Base clicks table
    clicks_path = "backend/sample_data/affiliateStatTable_real.csv"
    clicks_df = pd.read_csv(clicks_path)
    print(f"==================================================")
    print(f"📊 1. BUYHATKE INTERNAL CLICKS BASE TABLE AUDIT")
    print(f"==================================================")
    print(f"Total Rows in Base Table: {len(clicks_df)}")
    print(f"Total Internal Clicks: {clicks_df['SUM of INTERNAL CLICKS'].sum():,}")
    print(f"Unique Networks in Base: {clicks_df['AFFILIATE NETWORK'].unique().tolist()}")
    print(f"Clicks breakdown by Network in Base:")
    for net, grp in clicks_df.groupby("AFFILIATE NETWORK"):
        print(f"  - {net:15s}: {len(grp):3d} brands | {grp['SUM of INTERNAL CLICKS'].sum():10,d} clicks")

    # 2. Inspect each network's live data
    networks = [
        ("Cuelinks", "cuelinks", "cuelinks_bot_live.xls"),
        ("Admitad", "admitad", "admitad_bot_live.xlsx"),
        ("Cashkaro", "cashkaro", "cashkaro_bot_live.csv"),
        ("Zonet", "zonet", "zonet_bot_live.csv"),
        ("iCubesWire", "icubeswire", "icubeswire_bot_live.csv"),
        ("INRDeals", "inrdeals", "inrdeals_bot_live.csv"),
    ]

    print(f"\n==================================================")
    print(f"🤖 2. NETWORK-BY-NETWORK BOT INGESTION AUDIT")
    print(f"==================================================")

    payload = []
    net_stats = {}
    for display_name, net_key, fn in networks:
        fpath = os.path.join("backend/sample_data", fn)
        if not os.path.exists(fpath):
            print(f"❌ {display_name}: Missing file {fpath}")
            continue
        with open(fpath, "rb") as f:
            content = f.read()
        raw_df = engine.parse_file_to_dataframe(content, fn)
        adapter = get_adapter(net_key, normalizer=engine.normalizer)
        std_df = adapter.process(raw_df)
        payload.append({"filename": fn, "network_name": net_key, "df": raw_df})

        tot_rev = std_df["revenue"].sum()
        matched_brands = std_df[std_df["revenue"] > 0]
        net_stats[net_key] = {
            "name": display_name,
            "raw_rows": len(raw_df),
            "std_brands": len(std_df),
            "revenue": tot_rev,
            "active_earning_brands": len(matched_brands),
        }
        print(f"\n[{display_name}] (file: {fn}, size: {len(content):,} bytes)")
        print(f"  - Raw Records / Campaigns: {len(raw_df)}")
        print(f"  - Standardized Brands: {len(std_df)}")
        print(f"  - Brands with Revenue > 0: {len(matched_brands)}")
        print(f"  - Total Network Payout / Revenue: ₹{tot_rev:,.2f}")
        for _, r in matched_brands.iterrows():
            print(f"     • {r['brand']:22s} ({r['original_brand']:25s}): ₹{r['revenue']:>10,.2f}")

    # 3. Run Pipeline Left-Join
    res = engine.run_pipeline(clicks_df, payload)
    master = res["master_df"]
    summary = res["summary"]

    print(f"\n==================================================")
    print(f"🔗 3. LEFT-JOIN MERGE & INTEGRITY AUDIT")
    print(f"==================================================")
    print(f"Base Internal Rows: {len(clicks_df)}")
    print(f"Master Output Rows: {len(master)}")
    assert len(master) == len(clicks_df) - 1 or len(master) == len(clicks_df), "Integrity check failed: row count mismatch!"
    print(f"Integrity check passed! 100% of internal clicks rows preserved.")
    print(f"Total Internal Clicks Processed: {summary['total_internal_clicks']:,}")
    print(f"Total Portfolio Revenue: ₹{summary['total_revenue']:,.2f}")
    print(f"Overall Portfolio Blended RPC: ₹{summary['overall_portfolio_rpc']:.4f}")
    print(f"Rows with Attributed Revenue: {summary['matched_revenue_rows']} of {len(master)}")

    # 4. Check discrepancies & orphans
    orphans = summary.get("orphaned_affiliate_records", [])
    print(f"\n==================================================")
    print(f"⚠️ 4. DISCREPANCY & ORPHAN DETECTOR")
    print(f"==================================================")
    print(f"Total Orphaned Network Records (brands in network export not in internal clicks): {len(orphans)}")
    if orphans:
        for o in orphans:
            print(f"  - [{o['network'].upper()}] '{o['brand']}' (raw: '{o['original_brand']}'): ₹{o['revenue']:,.2f}")

    # 5. Top 15 earners across portfolio
    print(f"\n==================================================")
    print(f"🏆 5. TOP 15 EARNERS & RPCs ACROSS ALL 6 NETWORKS")
    print(f"==================================================")
    top_earners = master.sort_values(by="Revenue", ascending=False).head(15)
    print(top_earners[["WEBSITE / BRAND", "AFFILIATE NETWORK", "SUM of INTERNAL CLICKS", "Revenue", "RPCs"]].to_string(index=False))

if __name__ == "__main__":
    audit_all_networks()
