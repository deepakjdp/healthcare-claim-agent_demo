"""Unit tests for the Healthcare Claim Finalization Agent pipeline."""

import pytest
from agents.claim_orchestrator import ClaimOrchestratorAgent


VALID_CLAIM = {
    "claim_id": "CLM-TEST-001",
    "member_id": "M001",
    "provider_npi": "1234567890",
    "service_date": "2024-07-15",
    "diagnosis_codes": ["I10"],
    "procedure_codes": ["99214"],
    "billed_amount": 210.00,
}


@pytest.fixture
def orchestrator():
    return ClaimOrchestratorAgent()


def test_valid_claim_finalizes(orchestrator):
    result = orchestrator.process(VALID_CLAIM)
    assert result["status"] == "FINALIZED"
    assert result["approved_amount"] > 0


def test_ineligible_member_denied(orchestrator):
    claim = {**VALID_CLAIM, "member_id": "M_UNKNOWN"}
    result = orchestrator.process(claim)
    assert result["status"] == "DENIED"


def test_invalid_icd10_denied(orchestrator):
    claim = {**VALID_CLAIM, "diagnosis_codes": ["INVALID_CODE"]}
    result = orchestrator.process(claim)
    assert result["status"] == "DENIED"


def test_high_fraud_score_pending(orchestrator):
    claim = {**VALID_CLAIM, "provider_npi": "BAD_NPI_001"}
    result = orchestrator.process(claim)
    assert result["status"] == "PENDING_REVIEW"


def test_missing_field_returns_error(orchestrator):
    incomplete = {"member_id": "M001"}
    result = orchestrator.process(incomplete)
    assert "error" in result


def test_approved_amount_is_80_percent(orchestrator):
    result = orchestrator.process(VALID_CLAIM)
    # 99214 fee = $210, 80% = $168
    assert result["approved_amount"] == pytest.approx(168.0, rel=1e-3)
