"""
Healthcare Claim Finalization — Agentic AI System
===================================================
Multi-agent pipeline that autonomously processes, validates,
adjudicates, and finalises health insurance claims.

Agents:
  1. ClaimIngestionAgent      — parse & normalise raw claim data
  2. EligibilityAgent         — verify member coverage & benefits
  3. MedicalCodingAgent       — validate ICD-10 / CPT / HCPCS codes
  4. FraudDetectionAgent      — score claim for anomalies / fraud signals
  5. AdjudicationAgent        — apply business rules & calculate payment
  6. ComplianceAgent          — HIPAA / CMS regulatory checks
  7. ClaimFinalizationAgent   — finalise, persist & notify stakeholders
  8. OrchestratorAgent        — coordinates all agents end-to-end
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("ClaimOrchestrator")


# ──────────────────────────────────────────────
# Domain models
# ──────────────────────────────────────────────

class ClaimStatus(str, Enum):
    RECEIVED   = "RECEIVED"
    VALIDATING = "VALIDATING"
    ADJUDICATING = "ADJUDICATING"
    APPROVED   = "APPROVED"
    DENIED     = "DENIED"
    PENDING    = "PENDING_REVIEW"
    FINALIZED  = "FINALIZED"


@dataclass
class Claim:
    claim_id: str
    member_id: str
    provider_npi: str
    service_date: str
    diagnosis_codes: List[str]       # ICD-10
    procedure_codes: List[str]       # CPT / HCPCS
    billed_amount: float
    status: ClaimStatus = ClaimStatus.RECEIVED
    approved_amount: float = 0.0
    denial_reason: Optional[str] = None
    audit_trail: List[Dict] = field(default_factory=list)

    def add_audit(self, agent: str, action: str, detail: str = ""):
        self.audit_trail.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent,
            "action": action,
            "detail": detail,
        })


@dataclass
class AgentResult:
    agent_name: str
    passed: bool
    payload: Dict[str, Any]
    message: str


# ──────────────────────────────────────────────
# Individual Agents
# ──────────────────────────────────────────────

class ClaimIngestionAgent:
    """Parses and normalises raw claim payload."""

    NAME = "ClaimIngestionAgent"

    def run(self, raw: Dict) -> AgentResult:
        logger.info("[%s] Ingesting claim …", self.NAME)
        required = {"member_id", "provider_npi", "service_date",
                    "diagnosis_codes", "procedure_codes", "billed_amount"}
        missing = required - raw.keys()
        if missing:
            return AgentResult(self.NAME, False, {}, f"Missing fields: {missing}")

        claim = Claim(
            claim_id=raw.get("claim_id", str(uuid.uuid4())),
            member_id=raw["member_id"],
            provider_npi=raw["provider_npi"],
            service_date=raw["service_date"],
            diagnosis_codes=raw["diagnosis_codes"],
            procedure_codes=raw["procedure_codes"],
            billed_amount=float(raw["billed_amount"]),
        )
        claim.add_audit(self.NAME, "INGESTED", "Claim parsed and normalised")
        return AgentResult(self.NAME, True, {"claim": claim}, "Claim ingested successfully")


class EligibilityAgent:
    """Verifies member eligibility and active coverage."""

    NAME = "EligibilityAgent"

    # Simulated eligibility DB
    ELIGIBLE_MEMBERS = {"M001", "M002", "M003", "M100"}

    def run(self, claim: Claim) -> AgentResult:
        logger.info("[%s] Checking eligibility for member %s …", self.NAME, claim.member_id)
        eligible = claim.member_id in self.ELIGIBLE_MEMBERS
        claim.add_audit(self.NAME, "ELIGIBILITY_CHECK", f"Eligible={eligible}")
        if not eligible:
            claim.status = ClaimStatus.DENIED
            claim.denial_reason = "Member not eligible or coverage lapsed"
        return AgentResult(self.NAME, eligible, {"member_id": claim.member_id},
                           "Eligible" if eligible else claim.denial_reason)


class MedicalCodingAgent:
    """Validates ICD-10 diagnosis and CPT procedure codes."""

    NAME = "MedicalCodingAgent"

    VALID_ICD10 = {"Z00.00", "J06.9", "I10", "E11.9", "M54.5"}
    VALID_CPT   = {"99213", "99214", "99215", "93000", "71046"}

    def run(self, claim: Claim) -> AgentResult:
        logger.info("[%s] Validating medical codes …", self.NAME)
        invalid_dx  = [c for c in claim.diagnosis_codes  if c not in self.VALID_ICD10]
        invalid_cpt = [c for c in claim.procedure_codes  if c not in self.VALID_CPT]
        passed = not invalid_dx and not invalid_cpt
        detail = f"Invalid ICD-10: {invalid_dx}, Invalid CPT: {invalid_cpt}" if not passed else "All codes valid"
        claim.add_audit(self.NAME, "CODE_VALIDATION", detail)
        if not passed:
            claim.status = ClaimStatus.DENIED
            claim.denial_reason = detail
        return AgentResult(self.NAME, passed, {"invalid_dx": invalid_dx, "invalid_cpt": invalid_cpt}, detail)


class FraudDetectionAgent:
    """Scores the claim for potential fraud signals."""

    NAME = "FraudDetectionAgent"

    def run(self, claim: Claim) -> AgentResult:
        logger.info("[%s] Running fraud detection …", self.NAME)
        score = 0
        flags = []

        if claim.billed_amount > 10_000:
            score += 40; flags.append("High billed amount")
        if len(claim.procedure_codes) > 5:
            score += 20; flags.append("Unusual procedure volume")
        if claim.provider_npi in {"BAD_NPI_001"}:
            score += 50; flags.append("Provider on watchlist")

        risk_level = "LOW" if score < 30 else "MEDIUM" if score < 60 else "HIGH"
        passed = risk_level != "HIGH"
        claim.add_audit(self.NAME, "FRAUD_SCORE", f"Score={score} Risk={risk_level} Flags={flags}")
        if not passed:
            claim.status = ClaimStatus.PENDING
        return AgentResult(self.NAME, passed,
                           {"score": score, "risk": risk_level, "flags": flags},
                           f"Fraud risk: {risk_level}")


class AdjudicationAgent:
    """Applies payer business rules and calculates the approved payment."""

    NAME = "AdjudicationAgent"

    # Simulated fee schedule (CPT → allowed amount)
    FEE_SCHEDULE = {"99213": 150.0, "99214": 210.0, "99215": 280.0,
                    "93000": 95.0,  "71046": 320.0}
    COINSURANCE   = 0.80   # plan pays 80 %

    def run(self, claim: Claim) -> AgentResult:
        logger.info("[%s] Adjudicating claim …", self.NAME)
        claim.status = ClaimStatus.ADJUDICATING
        allowed = sum(self.FEE_SCHEDULE.get(c, 0) for c in claim.procedure_codes)
        approved = round(allowed * self.COINSURANCE, 2)
        claim.approved_amount = approved
        claim.status = ClaimStatus.APPROVED
        claim.add_audit(self.NAME, "ADJUDICATED",
                        f"Allowed={allowed} Approved={approved} (80% coinsurance)")
        return AgentResult(self.NAME, True,
                           {"allowed": allowed, "approved": approved},
                           f"Claim approved for ${approved:.2f}")


class ComplianceAgent:
    """Ensures HIPAA and CMS regulatory compliance."""

    NAME = "ComplianceAgent"

    def run(self, claim: Claim) -> AgentResult:
        logger.info("[%s] Running compliance checks …", self.NAME)
        issues = []
        if not claim.member_id:
            issues.append("Missing member identifier (HIPAA §164.514)")
        if not claim.provider_npi or len(claim.provider_npi) != 10:
            issues.append("Invalid NPI format (CMS requirement)")
        passed = len(issues) == 0
        claim.add_audit(self.NAME, "COMPLIANCE_CHECK", str(issues) if issues else "Passed")
        return AgentResult(self.NAME, passed, {"issues": issues},
                           "Compliance passed" if passed else f"Issues: {issues}")


class ClaimFinalizationAgent:
    """Persists the final claim record and triggers notifications."""

    NAME = "ClaimFinalizationAgent"

    def run(self, claim: Claim) -> AgentResult:
        logger.info("[%s] Finalising claim %s …", self.NAME, claim.claim_id)
        claim.status = ClaimStatus.FINALIZED
        claim.add_audit(self.NAME, "FINALIZED",
                        f"Final status={claim.status} Approved=${claim.approved_amount:.2f}")
        # In production: write to DB, publish to message broker, trigger EOB generation
        summary = {
            "claim_id": claim.claim_id,
            "member_id": claim.member_id,
            "status": claim.status.value,
            "approved_amount": claim.approved_amount,
            "audit_trail": claim.audit_trail,
        }
        logger.info("[%s] Claim finalized: %s", self.NAME, json.dumps(summary, indent=2))
        return AgentResult(self.NAME, True, summary, "Claim finalized and stakeholders notified")


# ──────────────────────────────────────────────
# Orchestrator Agent
# ──────────────────────────────────────────────

class ClaimOrchestratorAgent:
    """
    Coordinates all specialised agents in sequence.
    On failure at any step the pipeline short-circuits and records the denial.
    """

    def __init__(self):
        self.ingestion    = ClaimIngestionAgent()
        self.eligibility  = EligibilityAgent()
        self.coding       = MedicalCodingAgent()
        self.fraud        = FraudDetectionAgent()
        self.adjudication = AdjudicationAgent()
        self.compliance   = ComplianceAgent()
        self.finalization = ClaimFinalizationAgent()

    def process(self, raw_claim: Dict) -> Dict:
        logger.info("═" * 60)
        logger.info("ORCHESTRATOR: Starting claim processing pipeline")
        logger.info("═" * 60)

        # Step 1 — Ingest
        result = self.ingestion.run(raw_claim)
        if not result.passed:
            return {"error": result.message, "stage": "INGESTION"}
        claim: Claim = result.payload["claim"]

        # Step 2 — Eligibility
        if not self.eligibility.run(claim).passed:
            return self._deny(claim)

        # Step 3 — Medical Coding
        if not self.coding.run(claim).passed:
            return self._deny(claim)

        # Step 4 — Fraud Detection
        if not self.fraud.run(claim).passed:
            return self._pending(claim)

        # Step 5 — Compliance
        if not self.compliance.run(claim).passed:
            return self._deny(claim)

        # Step 6 — Adjudication
        self.adjudication.run(claim)

        # Step 7 — Finalization
        final = self.finalization.run(claim)
        return final.payload

    def _deny(self, claim: Claim) -> Dict:
        claim.status = ClaimStatus.DENIED
        claim.add_audit("Orchestrator", "PIPELINE_HALTED", claim.denial_reason or "Denied")
        return {"claim_id": claim.claim_id, "status": "DENIED",
                "reason": claim.denial_reason, "audit_trail": claim.audit_trail}

    def _pending(self, claim: Claim) -> Dict:
        claim.status = ClaimStatus.PENDING
        claim.add_audit("Orchestrator", "PIPELINE_HALTED", "Routed to manual review")
        return {"claim_id": claim.claim_id, "status": "PENDING_REVIEW",
                "reason": "High fraud risk score — manual review required",
                "audit_trail": claim.audit_trail}


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    sample_claim = {
        "claim_id": "CLM-2024-00123",
        "member_id": "M001",
        "provider_npi": "1234567890",
        "service_date": "2024-07-15",
        "diagnosis_codes": ["I10", "E11.9"],
        "procedure_codes": ["99214", "93000"],
        "billed_amount": 450.00,
    }

    orchestrator = ClaimOrchestratorAgent()
    outcome = orchestrator.process(sample_claim)
    print("\n─── FINAL OUTCOME ───")
    print(json.dumps(outcome, indent=2, default=str))
