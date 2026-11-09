import os
import pandas as pd
from backend.etl.engine import ETLEngine
from backend.etl.adapters import get_adapter

def check_all_unmatched():
    engine = ETLEngine()
    clicks_df = pd.read_csv("backend/sample_data/affiliateStatTable_real.csv")
    
    networks = [
        ("Cuelinks", "cuelinks", "cuelinks_bot_live.xls"),
        ("Admitad", "admitad", "admitad_bot_live.xlsx"),
        ("Cashkaro", "cashkaro", "cashkaro_bot_live.csv"),
        ("Zonet", "zonet", "zonet_bot_live.csv"),
        ("iCubesWire", "icubeswire", "icubeswire_bot_live.csv"),
        ("INRDeals", "inrdeals", "inrdeals_bot_live.csv"),
    ]
    
    payload = []
    print("=== UNMATCHED BRANDS WITH REVENUE > 0 IN ADAPTERS ===")
    for dname, nkey, fn in networks:
        fpath = os.path.join("backend/sample_data", fn)
        with open(fpath, "rb") as f:
            content = f.read()
        raw_df = engine.parse_file_to_dataframe(content, fn)
        adapter = get_adapter(nkey, normalizer=engine.normalizer)
        std_df = adapter.process(raw_df)
        payload.append({"filename": fn, "network_name": nkey, "df": raw_df})
        
        unmatched_earning = std_df[(~std_df["is_matched"]) & (std_df["revenue"] > 0)]
        if not unmatched_earning.empty:
            print(f"\n[{dname}] Unmatched earning brands:")
            print(unmatched_earning[["brand", "original_brand", "revenue"]].to_string())
            
    res = engine.run_pipeline(clicks_df, payload)
    orphans = res["summary"]["orphaned_affiliate_records"]
    print("\n=== ORPHANED BRANDS WITH REVENUE > 0 IN PIPELINE ===")
    for o in orphans:
        if o["revenue"] > 0:
            print(f"  [{o['network']}] Brand: '{o['brand']}' | Raw: '{o['original_brand']}' | Revenue: ₹{o['revenue']:,.2f}")

if __name__ == "__main__":
    check_all_unmatched()
