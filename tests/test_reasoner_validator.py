from pathlib import Path

from trace_loading.data_loader import ManufacturingData
from trace_loading.investigator import LoadingInvestigator
from trace_loading.reasoner import InvestigationReasoner


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def get_investigation(container_id: str) -> dict:
    data = ManufacturingData(DATA_DIR)
    investigator = LoadingInvestigator(data)
    return investigator.investigate(container_id)


def test_validator_blocks_false_no_exception():
    investigation = get_investigation("CNT-5203")

    fake_gemini_result = {
        "conclusion": "NO_EXCEPTION",
        "confidence": 0.99,
        "requires_human_verification": False,
        "reason": "Everything looks good.",
        "evidence_gap": None,
        "recommended_action": "Proceed.",
        "supporting_evidence": [],
    }

    result = InvestigationReasoner._validate_against_evidence(
        fake_gemini_result,
        investigation,
    )

    assert result["conclusion"] == "UNRESOLVED"
    assert result["requires_human_verification"] is True


def test_validator_removes_hallucinated_evidence():
    investigation = get_investigation("CNT-5207")

    fake_gemini_result = {
        "conclusion": "NO_EXCEPTION",
        "confidence": 0.95,
        "requires_human_verification": False,
        "reason": "The bundles satisfy the requirement.",
        "evidence_gap": None,
        "recommended_action": "Proceed.",
        "supporting_evidence": [
            "BND-9037A",
            "BND-FAKE-999",
            "EVENT-FAKE-123",
        ],
    }

    result = InvestigationReasoner._validate_against_evidence(
        fake_gemini_result,
        investigation,
    )

    assert "BND-9037A" in result["supporting_evidence"]
    assert "BND-FAKE-999" not in result["supporting_evidence"]
    assert "EVENT-FAKE-123" not in result["supporting_evidence"]


def test_validator_blocks_unverified_legitimate_exception():
    investigation = get_investigation("CNT-5203")

    fake_gemini_result = {
        "conclusion": "LEGITIMATE_EXCEPTION",
        "confidence": 0.99,
        "requires_human_verification": False,
        "reason": "A substitution was apparently approved.",
        "evidence_gap": None,
        "recommended_action": "Proceed.",
        "supporting_evidence": [],
    }

    result = InvestigationReasoner._validate_against_evidence(
        fake_gemini_result,
        investigation,
    )

    assert result["conclusion"] == "UNRESOLVED"
    assert result["requires_human_verification"] is True
    assert result["confidence"] <= 0.70