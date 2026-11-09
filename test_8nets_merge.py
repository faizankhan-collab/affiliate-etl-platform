import pandas as pd
from backend.etl.engine import ETLEngine

def test_eight_network_merge():
    engine = ETLEngine()
    
    clicks_df = pd.read_csv("backend/sample_data/affiliateStatTable_real.csv")
    print(f"Loaded internal clicks: {len(clicks_df)} rows")
    
    network_payload = []
    
    # 1. Cuelinks
    with open("backend/sample_data/cuelinks_bot_live.xls", "rb") as f:
        c_bytes = f.read()
    network_payload.append({
        "filename": "cuelinks_bot_live.xls",
        "network_name": "cuelinks",
        "df": engine.parse_file_to_dataframe(c_bytes, "cuelinks_bot_live.xls")
    })
    
    # 2. Admitad
    with open("backend/sample_data/admitad_bot_live.xlsx", "rb") as f:
        a_bytes = f.read()
    network_payload.append({
        "filename": "admitad_bot_live.xlsx",
        "network_name": "admitad",
        "df": engine.parse_file_to_dataframe(a_bytes, "admitad_bot_live.xlsx")
    })
    
    # 3. Cashkaro
    with open("backend/sample_data/cashkaro_bot_live.csv", "rb") as f:
        k_bytes = f.read()
    network_payload.append({
        "filename": "cashkaro_bot_live.csv",
        "network_name": "cashkaro",
        "df": engine.parse_file_to_dataframe(k_bytes, "cashkaro_bot_live.csv")
    })
    
    # 4. Zonet
    with open("backend/sample_data/zonet_bot_live.csv", "rb") as f:
        z_bytes = f.read()
    network_payload.append({
        "filename": "zonet_bot_live.csv",
        "network_name": "zonet",
        "df": engine.parse_file_to_dataframe(z_bytes, "zonet_bot_live.csv")
    })
    
    # 5. iCubesWire
    with open("backend/sample_data/icubeswire_bot_live.csv", "rb") as f:
        i_bytes = f.read()
    network_payload.append({
        "filename": "icubeswire_bot_live.csv",
        "network_name": "icubeswire",
        "df": engine.parse_file_to_dataframe(i_bytes, "icubeswire_bot_live.csv")
    })
    
    # 6. INRDeals
    with open("backend/sample_data/inrdeals_bot_live.csv", "rb") as f:
        inr_bytes = f.read()
    network_payload.append({
        "filename": "inrdeals_bot_live.csv",
        "network_name": "inrdeals",
        "df": engine.parse_file_to_dataframe(inr_bytes, "inrdeals_bot_live.csv")
    })
    
    # 7. CJ (Commission Junction)
    with open("backend/sample_data/cj_bot_live.csv", "rb") as f:
        cj_bytes = f.read()
    network_payload.append({
        "filename": "cj_bot_live.csv",
        "network_name": "cj",
        "df": engine.parse_file_to_dataframe(cj_bytes, "cj_bot_live.csv")
    })
    
    # 8. Pantech
    with open("backend/sample_data/pantech_bot_live.csv", "rb") as f:
        pan_bytes = f.read()
    network_payload.append({
        "filename": "pantech_bot_live.csv",
        "network_name": "pantech",
        "df": engine.parse_file_to_dataframe(pan_bytes, "pantech_bot_live.csv")
    })
    
    res = engine.run_pipeline(clicks_df, network_payload)
    master = res["master_df"]
    summary = res["summary"]
    
    print("\n=== 8-NETWORK MERGE SUMMARY ===")
    print(f"Total Master Rows: {summary['total_master_rows']}")
    print(f"Matched Revenue Rows: {summary['matched_revenue_rows']}")
    print(f"Total Internal Clicks: {summary['total_internal_clicks']:,}")
    print(f"Total Affiliate Revenue: ₹{summary['total_revenue']:,.2f}")
    print(f"Overall Blended RPC: ₹{summary['overall_portfolio_rpc']:.4f}")
    
    print("\n=== Flipkart Pantech Row in Master DataFrame ===")
    pan_rows = master[master["AFFILIATE NETWORK"].str.lower().str.replace(" ", "") == "pantech"]
    print(pan_rows[["WEBSITE / BRAND", "AFFILIATE NETWORK", "SUM of INTERNAL CLICKS", "Revenue", "RPCs"]].to_string())

if __name__ == "__main__":
    test_eight_network_merge()
