"""Pydantic request and response schemas for the Affiliate ETL API.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MasterRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    brand: str = Field(..., alias="WEBSITE / BRAND")
    network: str = Field(..., alias="AFFILIATE NETWORK")
    internal_clicks: int = Field(..., alias="SUM of INTERNAL CLICKS")
    revenue: float = Field(..., alias="Revenue")
    rpcs: float = Field(..., alias="RPCs")


class OrphanedRecord(BaseModel):
    brand: str
    network: str
    revenue: float
    original_brand: str


class ProcessingLog(BaseModel):
    filename: str
    detected_network: str
    status: str
    records_count: Optional[int] = None
    total_revenue: Optional[float] = None
    error_message: Optional[str] = None


class SummaryMetrics(BaseModel):
    total_revenue: float
    total_internal_clicks: int
    overall_portfolio_rpc: float
    total_master_rows: int
    matched_revenue_rows: int
    orphaned_affiliate_records: List[OrphanedRecord]
    network_processing_logs: List[ProcessingLog]
    internal_clicks_diag: Dict[str, Any]
    date_range: Optional[str] = "Full Period"
    is_date_filtered: Optional[bool] = False
    start_date: Optional[str] = ""
    end_date: Optional[str] = ""


class ETLProcessResponse(BaseModel):
    success: bool
    summary: SummaryMetrics
    data: List[Dict[str, Any]]
    message: Optional[str] = "Pipeline processed successfully"


class AliasAddRequest(BaseModel):
    raw_name: str
    canonical_brand: str


class AliasResponse(BaseModel):
    canonical_brands: List[str]
    aliases: Dict[str, str]


class SavedReportMetadata(BaseModel):
    id: str
    title: str
    start_date: str
    end_date: str
    days_count: Optional[int] = 0
    created_at: str
    summary: Dict[str, Any]
    usd_to_inr_rate: Optional[float] = 94.74


class SavedReportDetail(SavedReportMetadata):
    data: List[Dict[str, Any]]

