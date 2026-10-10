"""
FastAPI wrapper — exposes the Claim Orchestrator as a REST endpoint.
Deployed as a container on OpenShift.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from claim_orchestrator import ClaimOrchestratorAgent

app = FastAPI(
    title="Healthcare Claim Finalization API",
    description="Agentic AI pipeline for autonomous claim processing",
    version="1.0.0",
)

orchestrator = ClaimOrchestratorAgent()


class ClaimRequest(BaseModel):
    claim_id: str
    member_id: str
    provider_npi: str
    service_date: str
    diagnosis_codes: List[str]
    procedure_codes: List[str]
    billed_amount: float


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "claim-finalization-agent"}


@app.post("/claims/process")
def process_claim(request: ClaimRequest):
    raw = request.model_dump()
    result = orchestrator.process(raw)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@app.get("/claims/{claim_id}/status")
def claim_status(claim_id: str):
    # In production this would query the persistence layer
    return {"claim_id": claim_id, "message": "Query persistence layer for live status"}
