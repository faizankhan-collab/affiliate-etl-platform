"""Generate synthetic sample datasets based exactly on the user's master spreadsheet.
Useful for testing the ETL pipeline and providing pre-packaged samples in the web UI.
"""

import os
import pandas as pd


def generate_all_samples(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Internal Clicks (Buyhatke Tracking Panel Export)
    internal_clicks_data = [
        {"WEBSITE / BRAND": "Amazon", "AFFILIATE NETWORK": "Special (Extra1)", "SUM of INTERNAL CLICKS": 2818490},
        {"WEBSITE / BRAND": "Amazon", "AFFILIATE NETWORK": "Special (OWN)", "SUM of INTERNAL CLICKS": 2116323},
        {"WEBSITE / BRAND": "Amazon", "AFFILIATE NETWORK": "zonet", "SUM of INTERNAL CLICKS": 132268},
        {"WEBSITE / BRAND": "Flipkart", "AFFILIATE NETWORK": "cuelinks", "SUM of INTERNAL CLICKS": 1560054},
        {"WEBSITE / BRAND": "Flipkart", "AFFILIATE NETWORK": "zonet", "SUM of INTERNAL CLICKS": 1481475},
        {"WEBSITE / BRAND": "Flipkart", "AFFILIATE NETWORK": "adgama", "SUM of INTERNAL CLICKS": 1420961},
        {"WEBSITE / BRAND": "Flipkart", "AFFILIATE NETWORK": "cashkaro", "SUM of INTERNAL CLICKS": 50877},
        {"WEBSITE / BRAND": "Flipkart", "AFFILIATE NETWORK": "Pantech", "SUM of INTERNAL CLICKS": 45940},
        {"WEBSITE / BRAND": "Myntra", "AFFILIATE NETWORK": "admitad", "SUM of INTERNAL CLICKS": 1070073},
        {"WEBSITE / BRAND": "Myntra", "AFFILIATE NETWORK": "affinity", "SUM of INTERNAL CLICKS": 267432},
        {"WEBSITE / BRAND": "Myntra", "AFFILIATE NETWORK": "cashkaro", "SUM of INTERNAL CLICKS": 0},
        {"WEBSITE / BRAND": "Ajio", "AFFILIATE NETWORK": "Special (OWN)", "SUM of INTERNAL CLICKS": 529816},
        {"WEBSITE / BRAND": "Ajio", "AFFILIATE NETWORK": "admitad", "SUM of INTERNAL CLICKS": 0},
        {"WEBSITE / BRAND": "TatacliQ", "AFFILIATE NETWORK": "admitad", "SUM of INTERNAL CLICKS": 326754},
        {"WEBSITE / BRAND": "Reliance Digital", "AFFILIATE NETWORK": "affinity", "SUM of INTERNAL CLICKS": 203318},
        {"WEBSITE / BRAND": "Vijay Sales", "AFFILIATE NETWORK": "icubeswire", "SUM of INTERNAL CLICKS": 131394},
        {"WEBSITE / BRAND": "Nykaa", "AFFILIATE NETWORK": "admitad", "SUM of INTERNAL CLICKS": 109250},
        {"WEBSITE / BRAND": "NykaaFashion", "AFFILIATE NETWORK": "admitad", "SUM of INTERNAL CLICKS": 103245},
        {"WEBSITE / BRAND": "firstcry", "AFFILIATE NETWORK": "cashkaro", "SUM of INTERNAL CLICKS": 32123},
        {"WEBSITE / BRAND": "firstcry", "AFFILIATE NETWORK": "Special (OWN)", "SUM of INTERNAL CLICKS": 32079},
        {"WEBSITE / BRAND": "firstcry", "AFFILIATE NETWORK": "admitad", "SUM of INTERNAL CLICKS": 15454},
        {"WEBSITE / BRAND": "Shopsy", "AFFILIATE NETWORK": "admitad", "SUM of INTERNAL CLICKS": 47273},
        {"WEBSITE / BRAND": "Shopsy", "AFFILIATE NETWORK": "affinity", "SUM of INTERNAL CLICKS": 15295},
        {"WEBSITE / BRAND": "Shopsy", "AFFILIATE NETWORK": "digimodo", "SUM of INTERNAL CLICKS": 13810},
        {"WEBSITE / BRAND": "Amazon US", "AFFILIATE NETWORK": "zonet", "SUM of INTERNAL CLICKS": 72560},
        {"WEBSITE / BRAND": "Ajio Lux", "AFFILIATE NETWORK": "cashkaro", "SUM of INTERNAL CLICKS": 66824},
    ]
    pd.DataFrame(internal_clicks_data).to_csv(
        os.path.join(output_dir, "internal_clicks_buyhatke.csv"), index=False
    )

    # 2. Cuelinks Export (.xlsx)
    cuelinks_data = [
        {"Campaign Name": "Flipkart CPS [India]", "Merchant": "Flipkart", "Status": "Approved", "Approved Commission": "₹ 3,39,899.70", "Date": "2026-10-31"},
        {"Campaign Name": "Some Other Brand", "Merchant": "OtherBrand", "Status": "Declined", "Approved Commission": "0.00", "Date": "2026-10-31"},
    ]
    pd.DataFrame(cuelinks_data).to_excel(
        os.path.join(output_dir, "cuelinks_monthly_export.xlsx"), index=False
    )

    # 3. Admitad Export (.csv)
    admitad_data = [
        {"Advcampaign": "Myntra CPS [IN]", "Status": "Confirmed", "Payment": "158114.54", "Currency": "INR"},
        {"Advcampaign": "Tata CliQ [IN]", "Status": "Confirmed", "Payment": "32595.67", "Currency": "INR"},
        {"Advcampaign": "Nykaa [IN]", "Status": "Confirmed", "Payment": "6147.56", "Currency": "INR"},
        {"Advcampaign": "Nykaa Fashion [IN]", "Status": "Confirmed", "Payment": "3331.25", "Currency": "INR"},
        {"Advcampaign": "Firstcry [IN]", "Status": "Confirmed", "Payment": "935.00", "Currency": "INR"},
        {"Advcampaign": "Shopsy CPS", "Status": "Confirmed", "Payment": "2548.42", "Currency": "INR"},
        {"Advcampaign": "Ajio CPS", "Status": "Confirmed", "Payment": "0.00", "Currency": "INR"},
    ]
    pd.DataFrame(admitad_data).to_csv(
        os.path.join(output_dir, "admitad_monthly_export.csv"), index=False
    )

    # 4. Zonet Export (.xlsx)
    zonet_data = [
        {"Campaign": "Amazon India CPS", "Advertiser": "Amazon IN", "Revenue": "25,221.88", "Status": "Approved"},
        {"Campaign": "Flipkart CPS", "Advertiser": "Flipkart", "Revenue": "344830.00", "Status": "Approved"},
        {"Campaign": "Amazon US Associates", "Advertiser": "Amazon US", "Revenue": "0.00", "Status": "Approved"},
    ]
    pd.DataFrame(zonet_data).to_excel(
        os.path.join(output_dir, "zonet_monthly_export.xlsx"), index=False
    )

    # 5. Cashkaro Export (.csv)
    cashkaro_data = [
        {"Store Name": "Flipkart", "Retailer": "Flipkart India", "Confirmed Commission": "5770.80", "Status": "Approved"},
        {"Store Name": "Myntra", "Retailer": "Myntra", "Confirmed Commission": "5.11", "Status": "Approved"},
        {"Store Name": "Firstcry", "Retailer": "Firstcry", "Confirmed Commission": "2232.00", "Status": "Approved"},
        {"Store Name": "Ajio Luxe", "Retailer": "Ajio Lux", "Confirmed Commission": "0.00", "Status": "Approved"},
    ]
    pd.DataFrame(cashkaro_data).to_csv(
        os.path.join(output_dir, "cashkaro_monthly_export.csv"), index=False
    )

    # 6. ICubesWire Export (.csv)
    icubes_data = [
        {"Offer Name": "Vijay Sales CPS", "Campaign": "Vijay Sales", "Approved Payout": "3205.00", "Status": "Approved"},
    ]
    pd.DataFrame(icubes_data).to_csv(
        os.path.join(output_dir, "icubeswire_monthly_export.csv"), index=False
    )

    print("Sample datasets successfully generated in:", output_dir)


if __name__ == "__main__":
    generate_all_samples(os.path.dirname(os.path.abspath(__file__)))
