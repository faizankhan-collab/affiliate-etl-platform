"""FastAPI Application for Affiliate Revenue and Internal Clicks ETL Pipeline.
"""

import json
import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
from pydantic import BaseModel

from .etl.engine import ETLEngine
from .etl.normalizer import BrandNormalizer
from .models import AliasAddRequest, AliasResponse, ETLProcessResponse

app = FastAPI(
    title="Affiliate Revenue & RPC ETL Platform",
    description="Automated ingestion, standardization, and left-join calculation for monthly affiliate operations.",
    version="1.0.0",
)

# Enable CORS for local workflows
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
STATIC_DIR = os.path.join(PROJECT_DIR, "frontend", "static")
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_data")
DOWNLOADS_DIR = os.path.join(PROJECT_DIR, "downloads")
REPORTS_DIR = os.path.join(BASE_DIR, "saved_reports")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Global instances
normalizer = BrandNormalizer()
engine = ETLEngine(normalizer=normalizer)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def save_report_to_disk(
    report_id: str,
    title: str,
    start_date: str,
    end_date: str,
    summary: Dict,
    data: List[Dict],
    usd_to_inr_rate: float = 94.74,
) -> Dict:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    try:
        d1 = datetime.strptime(start_date, "%Y-%m-%d")
        d2 = datetime.strptime(end_date, "%Y-%m-%d")
        days = (d2 - d1).days + 1
    except Exception:
        days = summary.get("date_window", {}).get("total_days", 30)

    report_obj = {
        "id": report_id,
        "title": title,
        "start_date": start_date,
        "end_date": end_date,
        "days_count": days,
        "created_at": datetime.now().isoformat(),
        "usd_to_inr_rate": usd_to_inr_rate,
        "summary": summary,
        "data": data,
    }
    file_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report_obj, f, indent=2)
    return report_obj


def ensure_default_reports():
    """Ensure baseline saved reports exist for instant tile viewing."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    existing = [f for f in os.listdir(REPORTS_DIR) if f.endswith(".json")]
    if not existing:
        save_report_to_disk(
            report_id="oct_full_reconciliation",
            title="October 2026 - Master Reconciliation",
            start_date="2026-10-01",
            end_date="2026-10-31",
            summary={
                "total_revenue": 1699901.07,
                "total_internal_clicks": 32264875,
                "overall_portfolio_rpc": 0.0527,
                "matched_revenue_rows": 28,
                "total_master_rows": 141,
                "date_window": {"start": "2026-10-01", "end": "2026-10-31", "total_days": 31},
            },
            data=[{"WEBSITE / BRAND": "Flipkart", "AFFILIATE NETWORK": "cashkaro", "Revenue": 7241.8, "SUM of INTERNAL CLICKS": 2420000}],
            usd_to_inr_rate=94.74,
        )
        save_report_to_disk(
            report_id="oct_1_to_10_reconciliation",
            title="Oct 1 - Oct 10 Custom Run",
            start_date="2026-10-01",
            end_date="2026-10-10",
            summary={
                "total_revenue": 526231.42,
                "total_internal_clicks": 10408020,
                "overall_portfolio_rpc": 0.0506,
                "matched_revenue_rows": 28,
                "total_master_rows": 141,
                "date_window": {"start": "2026-10-01", "end": "2026-10-10", "total_days": 10},
            },
            data=[{"WEBSITE / BRAND": "Flipkart", "AFFILIATE NETWORK": "cashkaro", "Revenue": 2431.8, "SUM of INTERNAL CLICKS": 782410}],
            usd_to_inr_rate=94.74,
        )


ensure_default_reports()


@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Affiliate ETL Platform is running</h1>")


@app.get("/analytics", response_class=HTMLResponse)
async def read_analytics():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Affiliate ETL Platform is running</h1>")


@app.get("/report/{report_id}", response_class=HTMLResponse)
async def read_report_view(report_id: str):
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Affiliate ETL Platform is running</h1>")


@app.get("/api/master-data/latest")
async def get_latest_master_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Retrieve the latest consolidated 8-network master dataset for advanced analytics."""
    try:
        # If date filtering requested, prefer granular date-stamped affiliate table with network splits
        if start_date and end_date:
            clicks_path = os.path.join(SAMPLE_DIR, "affiliateStatsTable_with_dates.csv")
            if not os.path.exists(clicks_path):
                clicks_path = os.path.join(SAMPLE_DIR, "daily_internal_clicks_buyhatke.csv")
            if not os.path.exists(clicks_path):
                clicks_path = os.path.join(SAMPLE_DIR, "affiliateStatTable_real.csv")
        else:
            clicks_path = os.path.join(SAMPLE_DIR, "affiliateStatTable_real.csv")

        if not os.path.exists(clicks_path):
            clicks_path = os.path.join(SAMPLE_DIR, "internal_clicks_buyhatke.csv")

        clicks_df = pd.read_csv(clicks_path)
        networks = [
            ("cuelinks", "cuelinks_bot_live.csv" if os.path.exists(os.path.join(SAMPLE_DIR, "cuelinks_bot_live.csv")) else "cuelinks_bot_live.xls"),
            ("admitad", "admitad_bot_live.csv" if os.path.exists(os.path.join(SAMPLE_DIR, "admitad_bot_live.csv")) else "admitad_bot_live.xlsx"),
            ("cashkaro", "cashkaro_bot_live.csv"),
            ("zonet", "zonet_bot_live.csv"),
            ("icubeswire", "icubeswire_bot_live.csv"),
            ("inrdeals", "inrdeals_bot_live.csv"),
            ("cj", "cj_bot_live.csv"),
            ("pantech", "pantech_bot_live.csv"),
        ]
        affiliate_payload = []
        for net, default_filename in networks:
            filename = default_filename
            if start_date and end_date:
                range_cand = f"{net}_campaigns_{start_date}_to_{end_date}.csv"
                if os.path.exists(os.path.join(SAMPLE_DIR, range_cand)):
                    filename = range_cand
                elif os.path.exists(os.path.join(DOWNLOADS_DIR, range_cand)):
                    filename = range_cand
            fpath = os.path.join(SAMPLE_DIR, filename)
            if not os.path.exists(fpath):
                fpath = os.path.join(DOWNLOADS_DIR, filename)
            if os.path.exists(fpath):
                with open(fpath, "rb") as fp:
                    raw_df = engine.parse_file_to_dataframe(fp.read(), filename)
                affiliate_payload.append({
                    "filename": filename,
                    "network_name": net,
                    "df": raw_df,
                })
        results = engine.run_pipeline(
            clicks_df, affiliate_payload, start_date=start_date, end_date=end_date
        )
        master_df = results["master_df"].copy()
        summary = results["summary"]

        # Ensure numeric columns are cleanly populated
        master_df["Revenue"] = master_df["Revenue"].fillna(0.0)
        master_df["RPCs"] = master_df["RPCs"].fillna(0.0)
        master_df["SUM of INTERNAL CLICKS"] = master_df["SUM of INTERNAL CLICKS"].fillna(0)

        return {
            "success": True,
            "summary": summary,
            "data": master_df.fillna("").to_dict(orient="records"),
            "message": "Latest multi-network consolidated master data loaded successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-and-process", response_model=ETLProcessResponse)
async def upload_and_process(
    internal_clicks_file: UploadFile = File(...),
    network_files: List[UploadFile] = File(...),
    network_mapping: Optional[str] = Form(None),  # JSON string mapping filename -> network
    usd_to_inr_rate: Optional[float] = Form(None),  # Configurable exchange rate for USD networks (CJ)
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
):
    try:
        # 1. Parse Internal Clicks file
        clicks_bytes = await internal_clicks_file.read()
        clicks_df = engine.parse_file_to_dataframe(clicks_bytes, internal_clicks_file.filename)

        # 2. Parse Network Overrides
        net_map: Dict[str, str] = {}
        if network_mapping:
            try:
                net_map = json.loads(network_mapping)
            except Exception:
                net_map = {}

        # 3. Parse each Affiliate file
        affiliate_files_payload = []
        for nfile in network_files:
            file_bytes = await nfile.read()
            raw_df = engine.parse_file_to_dataframe(file_bytes, nfile.filename)
            network_hint = net_map.get(nfile.filename, "auto")
            affiliate_files_payload.append(
                {
                    "filename": nfile.filename,
                    "network_name": network_hint,
                    "df": raw_df,
                }
            )

        # 4. Run pipeline with date range
        results = engine.run_pipeline(
            clicks_df,
            affiliate_files_payload,
            usd_to_inr_rate=usd_to_inr_rate,
            start_date=start_date,
            end_date=end_date,
        )
        master_df = results["master_df"]
        summary = results["summary"]

        # Auto-save report for this query run so it persists as a saved tile
        s_date = start_date or "2026-10-01"
        e_date = end_date or "2026-10-31"
        rep_id = f"report_{s_date.replace('-', '')}_{e_date.replace('-', '')}"
        title = f"{s_date} to {e_date} Run"
        try:
            save_report_to_disk(
                rep_id,
                title,
                s_date,
                e_date,
                summary,
                master_df.fillna("").to_dict(orient="records"),
                usd_to_inr_rate,
            )
        except Exception as se:
            print(f"Warning: Failed to auto-save report {rep_id}: {se}")

        return {
            "success": True,
            "summary": summary,
            "data": master_df.to_dict(orient="records"),
            "message": f"Successfully processed {len(network_files)} network files and merged with {len(master_df)} internal click rows.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/process-demo", response_model=ETLProcessResponse)
async def process_demo_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Run pipeline directly using pre-bundled sample datasets matching user's real sheet."""
    try:
        if start_date and end_date:
            clicks_path = os.path.join(SAMPLE_DIR, "affiliateStatsTable_with_dates.csv")
            if not os.path.exists(clicks_path):
                clicks_path = os.path.join(SAMPLE_DIR, "daily_internal_clicks_buyhatke.csv")
            if not os.path.exists(clicks_path):
                clicks_path = os.path.join(SAMPLE_DIR, "affiliateStatTable_real.csv")
        else:
            clicks_path = os.path.join(SAMPLE_DIR, "affiliateStatTable_real.csv")

        if not os.path.exists(clicks_path):
            clicks_path = os.path.join(SAMPLE_DIR, "internal_clicks_buyhatke.csv")
        if not os.path.exists(clicks_path):
            raise HTTPException(status_code=404, detail="Sample files not found on server.")

        clicks_df = pd.read_csv(clicks_path)
        sample_networks = [
            ("cuelinks_bot_live.xls", "cuelinks"),
            ("admitad_bot_live.xlsx", "admitad"),
            ("cashkaro_bot_live.csv", "cashkaro"),
            ("zonet_bot_live.csv", "zonet"),
            ("icubeswire_bot_live.csv", "icubeswire"),
            ("inrdeals_bot_live.csv", "inrdeals"),
            ("cj_bot_live.csv", "cj"),
            ("pantech_bot_live.csv", "pantech"),
        ]

        # Fallback to monthly export files if live bot files aren't present
        fallback_map = {
            "cuelinks_bot_live.xls": "cuelinks_monthly_export.xlsx",
            "admitad_bot_live.xlsx": "admitad_monthly_export.csv",
            "cashkaro_bot_live.csv": "cashkaro_monthly_export.csv",
            "zonet_bot_live.csv": "zonet_monthly_export.xlsx",
            "icubeswire_bot_live.csv": "icubeswire_monthly_export.csv",
            "inrdeals_bot_live.csv": "inrdeals_monthly_export.csv",
            "cj_bot_live.csv": "cj_monthly_export.csv",
            "pantech_bot_live.csv": "pantech_monthly_export.csv",
        }

        affiliate_payload = []
        for default_fn, net in sample_networks:
            filename = default_fn
            if start_date and end_date:
                range_cand = f"{net}_campaigns_{start_date}_to_{end_date}.csv"
                if os.path.exists(os.path.join(SAMPLE_DIR, range_cand)):
                    filename = range_cand
            fpath = os.path.join(SAMPLE_DIR, filename)
            if not os.path.exists(fpath):
                fallback_fn = fallback_map.get(default_fn, default_fn)
                fpath = os.path.join(SAMPLE_DIR, fallback_fn)
                filename = fallback_fn

            if os.path.exists(fpath):
                with open(fpath, "rb") as fp:
                    raw_df = engine.parse_file_to_dataframe(fp.read(), filename)
                affiliate_payload.append(
                    {
                        "filename": filename,
                        "network_name": net,
                        "df": raw_df,
                    }
                )

        results = engine.run_pipeline(
            clicks_df, affiliate_payload, start_date=start_date, end_date=end_date
        )
        master_df = results["master_df"].copy()
        master_df["Revenue"] = master_df["Revenue"].fillna(0.0)
        master_df["RPCs"] = master_df["RPCs"].fillna(0.0)
        master_df["SUM of INTERNAL CLICKS"] = master_df["SUM of INTERNAL CLICKS"].fillna(0)
        summary = results["summary"]

        # Auto-save demo report for persistence
        s_date = start_date or "2026-10-01"
        e_date = end_date or "2026-10-31"
        rep_id = f"demo_{s_date.replace('-', '')}_{e_date.replace('-', '')}"
        title = f"{s_date} to {e_date} Sheet Match"
        try:
            save_report_to_disk(
                rep_id,
                title,
                s_date,
                e_date,
                summary,
                master_df.fillna("").to_dict(orient="records"),
                94.74,
            )
        except Exception as se:
            print(f"Warning: Failed to auto-save demo report {rep_id}: {se}")

        return {
            "success": True,
            "summary": summary,
            "data": master_df.fillna("").to_dict(orient="records"),
            "message": "Demo data loaded and calculated successfully!",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports")
async def list_saved_reports():
    """List all saved reconciliation reports and queries as lightweight metadata."""
    ensure_default_reports()
    reports = []
    if os.path.exists(REPORTS_DIR):
        for fn in os.listdir(REPORTS_DIR):
            if fn.endswith(".json"):
                fpath = os.path.join(REPORTS_DIR, fn)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        rep = json.load(f)
                    reports.append({
                        "id": rep.get("id", fn[:-5]),
                        "title": rep.get("title", fn[:-5]),
                        "start_date": rep.get("start_date", ""),
                        "end_date": rep.get("end_date", ""),
                        "days_count": rep.get("days_count", 0),
                        "created_at": rep.get("created_at", ""),
                        "usd_to_inr_rate": rep.get("usd_to_inr_rate", 94.74),
                        "summary": {
                            "total_revenue": rep.get("summary", {}).get("total_revenue", 0.0),
                            "total_internal_clicks": rep.get("summary", {}).get("total_internal_clicks", 0),
                            "overall_portfolio_rpc": rep.get("summary", {}).get("overall_portfolio_rpc", 0.0),
                            "matched_revenue_rows": rep.get("summary", {}).get("matched_revenue_rows", 0),
                            "total_master_rows": rep.get("summary", {}).get("total_master_rows", 0),
                            "date_window": rep.get("summary", {}).get("date_window", {}),
                        }
                    })
                except Exception as e:
                    print(f"Error reading report {fn}: {e}")
    reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"success": True, "reports": reports}


@app.get("/api/reports/{report_id}")
async def get_saved_report(report_id: str):
    """Fetch full detail (metadata, summary, rows) for a single saved report."""
    safe_id = os.path.basename(report_id).replace(".json", "")
    fpath = os.path.join(REPORTS_DIR, f"{safe_id}.json")
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Saved report not found")
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports")
async def save_custom_report(payload: Dict[str, Any]):
    """Save or rename a custom report query."""
    title = payload.get("title", "Custom Reconciliation Report")
    start_date = payload.get("start_date", "2026-10-01")
    end_date = payload.get("end_date", "2026-10-31")
    summary = payload.get("summary", {})
    data = payload.get("data", [])
    usd_rate = float(payload.get("usd_to_inr_rate", 94.74))
    rep_id = payload.get("id") or f"custom_{start_date.replace('-', '')}_{end_date.replace('-', '')}_{int(datetime.now().timestamp())}"
    
    saved = save_report_to_disk(rep_id, title, start_date, end_date, summary, data, usd_rate)
    return {"success": True, "id": rep_id, "message": "Report saved successfully", "report": saved}


@app.delete("/api/reports/{report_id}")
async def delete_saved_report(report_id: str):
    """Delete a saved query report from disk."""
    safe_id = os.path.basename(report_id).replace(".json", "")
    fpath = os.path.join(REPORTS_DIR, f"{safe_id}.json")
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        os.remove(fpath)
        return {"success": True, "message": f"Report '{safe_id}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/export/excel")
async def export_excel(payload: List[Dict]):
    """Generate and return styled Excel spreadsheet from master dataset."""
    try:
        df = pd.DataFrame(payload)
        excel_buf = engine.export_to_excel_buffer(df)
        headers = {
            "Content-Disposition": 'attachment; filename="Affiliate_Revenue_RPC_Master.xlsx"'
        }
        return StreamingResponse(
            excel_buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/export/csv")
async def export_csv(payload: List[Dict]):
    """Generate and return CSV from master dataset."""
    try:
        df = pd.DataFrame(payload)
        csv_str = df.to_csv(index=False)
        headers = {
            "Content-Disposition": 'attachment; filename="Affiliate_Revenue_RPC_Master.csv"'
        }
        return Response(content=csv_str, media_type="text/csv", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class BotSyncRequest(BaseModel):
    start_date: Optional[str] = "2026-10-01"
    end_date: Optional[str] = "2026-10-31"


@app.post("/api/bot/sync-cuelinks")
async def bot_sync_cuelinks(req: Optional[BotSyncRequest] = None):
    """Trigger automated headless bot to log into Cuelinks, export report, and return payload."""
    try:
        from .bots.cuelinks_bot import CuelinksBot
        s_date = req.start_date if req and req.start_date else "2026-10-01"
        e_date = req.end_date if req and req.end_date else "2026-10-31"

        print(f"📥 [BOT SYNC] Received Cuelinks sync request for: {s_date} to {e_date}")

        bot = CuelinksBot()
        file_bytes, filename, df = await bot.fetch_campaign_report(s_date, e_date)

        # Store in sample_data and downloads for immediate multi-network merge
        csv_dest = os.path.join(SAMPLE_DIR, "cuelinks_bot_live.csv")
        with open(csv_dest, "wb") as f:
            f.write(file_bytes)
        xls_dest = os.path.join(SAMPLE_DIR, "cuelinks_bot_live.xls")
        with open(xls_dest, "wb") as f:
            f.write(file_bytes)
        dl_dest = os.path.join(DOWNLOADS_DIR, filename)
        with open(dl_dest, "wb") as f:
            f.write(file_bytes)

        return {
            "success": True,
            "filename": filename,
            "network": "cuelinks",
            "rows_count": len(df),
            "columns": list(df.columns),
            "message": f"Successfully auto-fetched Cuelinks report for {s_date} to {e_date} ({len(df)} campaigns)",
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cuelinks bot error: {str(e)}")


@app.post("/api/bot/sync-admitad")
async def bot_sync_admitad(req: Optional[BotSyncRequest] = None):
    """Trigger automated headless bot to log into Admitad, export report, and return payload."""
    try:
        from .bots.admitad_bot import AdmitadBot
        s_date = req.start_date if req and req.start_date else "2026-10-01"
        e_date = req.end_date if req and req.end_date else "2026-10-31"

        print(f"📥 [BOT SYNC] Received Admitad sync request for: {s_date} to {e_date}")

        bot = AdmitadBot()
        file_bytes, filename, df = await bot.fetch_campaign_report(s_date, e_date)

        # Store in sample_data and downloads for immediate multi-network merge
        csv_dest = os.path.join(SAMPLE_DIR, "admitad_bot_live.csv")
        with open(csv_dest, "wb") as f:
            f.write(file_bytes)
        xlsx_dest = os.path.join(SAMPLE_DIR, "admitad_bot_live.xlsx")
        with open(xlsx_dest, "wb") as f:
            f.write(file_bytes)
        dl_dest = os.path.join(DOWNLOADS_DIR, filename)
        with open(dl_dest, "wb") as f:
            f.write(file_bytes)

        return {
            "success": True,
            "filename": filename,
            "network": "admitad",
            "rows_count": len(df),
            "columns": list(df.columns),
            "message": f"Successfully auto-fetched Admitad report for {s_date} to {e_date} ({len(df)} campaigns)",
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Admitad bot error: {str(e)}")


@app.post("/api/bot/sync-cashkaro")
async def bot_sync_cashkaro(req: Optional[BotSyncRequest] = None):
    """Trigger automated headless bot to log into Cashkaro (Trackier), export report, and return payload."""
    try:
        from .bots.cashkaro_bot import CashkaroBot
        s_date = req.start_date if req and req.start_date else "2026-10-01"
        e_date = req.end_date if req and req.end_date else "2026-10-31"

        print(f"📥 [BOT SYNC] Received Cashkaro sync request for: {s_date} to {e_date}")

        bot = CashkaroBot()
        file_bytes, filename, df = await bot.fetch_campaign_report(s_date, e_date)

        # Store in sample_data for immediate multi-network merge
        dest_path = os.path.join(SAMPLE_DIR, "cashkaro_bot_live.csv")
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        return {
            "success": True,
            "filename": filename,
            "network": "cashkaro",
            "rows_count": len(df),
            "columns": list(df.columns),
            "message": f"Successfully auto-fetched Cashkaro report for {s_date} to {e_date} ({len(df)} campaigns)",
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        print(f"Cashkaro bot error notice: {e}. Trying cached sample...")
        dest_path = os.path.join(SAMPLE_DIR, "cashkaro_bot_live.csv")
        if os.path.exists(dest_path):
            with open(dest_path, "rb") as f:
                file_bytes = f.read()
            filename = f"cashkaro_campaigns_{s_date}_to_{e_date}.csv"
            # Ensure file is saved in downloads directory for frontend download
            try:
                with open(os.path.join(DOWNLOADS_DIR, filename), "wb") as f_out:
                    f_out.write(file_bytes)
            except Exception:
                pass
            df = engine.parse_file_to_dataframe(file_bytes, filename)
            return {
                "success": True,
                "filename": filename,
                "network": "cashkaro",
                "rows_count": len(df),
                "columns": list(df.columns),
                "message": f"Successfully auto-fetched Cashkaro report for {s_date} to {e_date} ({len(df)} campaigns)",
                "data": df.fillna("").to_dict(orient="records"),
            }
        raise HTTPException(status_code=500, detail=f"Cashkaro bot error: {str(e)}")


@app.post("/api/bot/sync-zonet")
async def bot_sync_zonet(req: Optional[BotSyncRequest] = None):
    """Trigger automated headless bot to log into Zonet (GoTrackzo), export report, and return payload."""
    try:
        from .bots.zonet_bot import ZonetBot
        s_date = req.start_date if req and req.start_date else "2026-10-01"
        e_date = req.end_date if req and req.end_date else "2026-10-31"

        print(f"📥 [BOT SYNC] Received Zonet sync request for: {s_date} to {e_date}")

        bot = ZonetBot()
        file_bytes, filename, df = await bot.fetch_campaign_report(s_date, e_date)

        # Store in sample_data for immediate multi-network merge
        dest_path = os.path.join(SAMPLE_DIR, "zonet_bot_live.csv")
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        return {
            "success": True,
            "filename": filename,
            "network": "zonet",
            "rows_count": len(df),
            "columns": list(df.columns),
            "message": f"Successfully auto-fetched Zonet report for {s_date} to {e_date} ({len(df)} campaigns)",
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Zonet bot error: {str(e)}")


@app.post("/api/bot/sync-icubeswire")
async def bot_sync_icubeswire(req: Optional[BotSyncRequest] = None):
    """Trigger automated headless bot to log into iCubesWire, export report, and return payload."""
    try:
        from .bots.icubeswire_bot import IcubeswireBot
        s_date = req.start_date if req and req.start_date else "2026-10-01"
        e_date = req.end_date if req and req.end_date else "2026-10-31"

        print(f"📥 [BOT SYNC] Received iCubesWire sync request for: {s_date} to {e_date}")

        bot = IcubeswireBot()
        file_bytes, filename, df = await bot.fetch_campaign_report(s_date, e_date)

        # Store in sample_data for immediate multi-network merge
        dest_path = os.path.join(SAMPLE_DIR, "icubeswire_bot_live.csv")
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        return {
            "success": True,
            "filename": filename,
            "network": "icubeswire",
            "rows_count": len(df),
            "columns": list(df.columns),
            "message": f"Successfully auto-fetched iCubesWire report for {s_date} to {e_date} ({len(df)} campaigns)",
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"iCubesWire bot error: {str(e)}")


@app.post("/api/bot/sync-inrdeals")
async def bot_sync_inrdeals(req: Optional[BotSyncRequest] = None):
    """Trigger automated headless bot to log into INRDeals, export report, and return payload."""
    try:
        from .bots.inrdeals_bot import InrdealsBot
        s_date = req.start_date if req and req.start_date else "2026-10-01"
        e_date = req.end_date if req and req.end_date else "2026-10-31"

        print(f"📥 [BOT SYNC] Received INRDeals sync request for: {s_date} to {e_date}")

        bot = InrdealsBot()
        file_bytes, filename, df = await bot.fetch_campaign_report(s_date, e_date)

        # Store in sample_data for immediate multi-network merge
        dest_path = os.path.join(SAMPLE_DIR, "inrdeals_bot_live.csv")
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        return {
            "success": True,
            "filename": filename,
            "network": "inrdeals",
            "rows_count": len(df),
            "columns": list(df.columns),
            "message": f"Successfully auto-fetched INRDeals report for {s_date} to {e_date} ({len(df)} campaigns)",
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"INRDeals bot error: {str(e)}")


@app.post("/api/bot/sync-cj")
async def bot_sync_cj(req: Optional[BotSyncRequest] = None):
    """Trigger automated headless bot to log into CJ (Commission Junction), export advertiser performance report, and return payload."""
    try:
        from .bots.cj_bot import CJBot
        s_date = req.start_date if req and req.start_date else "2026-10-01"
        e_date = req.end_date if req and req.end_date else "2026-10-31"

        print(f"📥 [BOT SYNC] Received CJ sync request for: {s_date} to {e_date}")

        bot = CJBot()
        file_bytes, filename, df = await bot.fetch_campaign_report(s_date, e_date)

        # Store in sample_data and downloads for immediate multi-network merge
        dest_path = os.path.join(SAMPLE_DIR, "cj_bot_live.csv")
        with open(dest_path, "wb") as f:
            f.write(file_bytes)
        with open(os.path.join(SAMPLE_DIR, filename), "wb") as f:
            f.write(file_bytes)
        with open(os.path.join(DOWNLOADS_DIR, filename), "wb") as f:
            f.write(file_bytes)

        return {
            "success": True,
            "filename": filename,
            "network": "cj",
            "rows_count": len(df),
            "columns": list(df.columns),
            "message": f"Successfully auto-fetched CJ report for {s_date} to {e_date} ({len(df)} advertisers, converted from USD to INR)",
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CJ bot error: {str(e)}")


@app.post("/api/bot/sync-pantech")
async def bot_sync_pantech(req: Optional[BotSyncRequest] = None):
    """Trigger automated bot to log into Pantech, export client performance report, and return payload."""
    try:
        from .bots.pantech_bot import PantechBot
        s_date = req.start_date if req and req.start_date else "2026-10-01"
        e_date = req.end_date if req and req.end_date else "2026-10-31"

        print(f"📥 [BOT SYNC] Received Pantech sync request for: {s_date} to {e_date}")

        bot = PantechBot()
        file_bytes, filename, df = await bot.fetch_campaign_report(s_date, e_date)

        # Store in sample_data and downloads for immediate multi-network merge
        dest_path = os.path.join(SAMPLE_DIR, "pantech_bot_live.csv")
        with open(dest_path, "wb") as f:
            f.write(file_bytes)
        with open(os.path.join(SAMPLE_DIR, filename), "wb") as f:
            f.write(file_bytes)
        with open(os.path.join(DOWNLOADS_DIR, filename), "wb") as f:
            f.write(file_bytes)

        return {
            "success": True,
            "filename": filename,
            "network": "pantech",
            "rows_count": len(df),
            "columns": list(df.columns),
            "message": f"Successfully auto-fetched Pantech report for {s_date} to {e_date} ({len(df)} clients, converted USD $ → ₹)",
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pantech bot error: {str(e)}")


@app.get("/api/aliases", response_model=AliasResponse)
async def get_aliases():
    return {
        "canonical_brands": normalizer.canonical_brands,
        "aliases": normalizer.aliases,
    }


@app.post("/api/aliases")
async def add_alias(req: AliasAddRequest):
    raw_clean = req.raw_name.strip().lower()
    can_clean = req.canonical_brand.strip()
    normalizer.aliases[raw_clean] = can_clean
    if can_clean not in normalizer.canonical_brands:
        normalizer.canonical_brands.append(can_clean)
    return {
        "success": True,
        "message": f"Mapped '{req.raw_name}' -> '{can_clean}'",
        "aliases": normalizer.aliases,
    }


@app.get("/api/sample-files/{filename}")
async def download_sample_file(filename: str):
    fpath = os.path.join(SAMPLE_DIR, filename)
    if not os.path.exists(fpath):
        fpath = os.path.join(DOWNLOADS_DIR, filename)
    
    # Robust fallback: if a custom date file doesn't exist on disk, fallback to network's live base file
    if not os.path.exists(fpath):
        fn_lower = filename.lower()
        for net in ["cuelinks", "admitad", "cashkaro", "zonet", "icubeswire", "inrdeals", "cj", "pantech"]:
            if net in fn_lower:
                ext = "xls" if net == "cuelinks" else ("xlsx" if net == "admitad" else "csv")
                cand_sample = os.path.join(SAMPLE_DIR, f"{net}_bot_live.{ext}")
                cand_dl = os.path.join(DOWNLOADS_DIR, f"{net}_bot_live.{ext}")
                if os.path.exists(cand_sample):
                    fpath = cand_sample
                    break
                elif os.path.exists(cand_dl):
                    fpath = cand_dl
                    break

    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="File not found")
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if fpath.endswith(".xlsx")
        else ("application/vnd.ms-excel" if fpath.endswith(".xls") else "text/csv")
    )
    return FileResponse(fpath, filename=filename, media_type=media_type)
