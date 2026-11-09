import pandas as pd
from backend.etl.engine import ETLEngine

def test_five_network_merge():
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
    
    res = engine.run_pipeline(clicks_df, network_payload)
    master = res["master_df"]
    summary = res["summary"]
    
    print("\n=== 5-NETWORK MERGE SUMMARY ===")
    print(f"Total Master Rows: {summary['total_master_rows']}")
    print(f"Matched Revenue Rows: {summary['matched_revenue_rows']}")
    print(f"Total Internal Clicks: {summary['total_internal_clicks']:,}")
    print(f"Total Affiliate Revenue: ₹{summary['total_revenue']:,.2f}")
    print(f"Overall Blended RPC: ₹{summary['overall_portfolio_rpc']:.4f}")
    
    print("\n=== iCubesWire Rows in Master DataFrame ===")
    ic_rows = master[master["AFFILIATE NETWORK"].str.lower() == "icubeswire"]
    print(ic_rows[["WEBSITE / BRAND", "AFFILIATE NETWORK", "SUM of INTERNAL CLICKS", "Revenue", "RPCs"]].to_string())

if __name__ == "__main__":
    test_five_network_merge()
