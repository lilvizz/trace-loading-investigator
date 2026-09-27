from pathlib import Path

from src.trace_loading.agent import InvestigationAgent
from src.trace_loading.data_loader import ManufacturingData


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_case_038_report_resolves_documented_exception():

    data = ManufacturingData(DATA_DIR)

    agent = InvestigationAgent(
        data,
        use_gemini=False,
    )

    result = agent.investigate("CNT-5208")

    assert result["assessment"]["conclusion"] == (
        "LEGITIMATE_EXCEPTION"
    )

    assert (
        result["assessment"]["requires_human_verification"]
        is False
    )

    assert result["assessment"]["confidence"] == 0.95

    assert result["evidence_gaps"] == []

    assert "EVT-7003" in result["supporting_evidence"]

    plan = result["investigation_plan"]

    assert plan["investigation_complete"] is True

    unresolved_ids = {
        question["id"]
        for question in plan["unresolved_questions"]
    }

    assert "Q4" not in unresolved_ids
    assert "Q6" not in unresolved_ids

    assert unresolved_ids == set()