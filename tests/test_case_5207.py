from pathlib import Path

from src.trace_loading.agent import InvestigationAgent
from src.trace_loading.data_loader import ManufacturingData


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_case_5207_is_fully_supported():

    data = ManufacturingData(DATA_DIR)

    agent = InvestigationAgent(
        data,
        use_gemini=False,
    )

    result = agent.investigate("CNT-5207")

    assert result["assessment"]["conclusion"] == (
        "NO_EXCEPTION"
    )

    assert (
        result["assessment"]["requires_human_verification"]
        is False
    )

    assert result["assessment"]["confidence"] == 0.95

    assert result["evidence_gaps"] == []

    assert result["investigation_plan"]["investigation_complete"] is True

    assert result["investigation_plan"]["unresolved_questions"] == []

    assert set(result["supporting_evidence"]) == {
        "BND-9037A",
        "BND-9037B",
        "BND-9037C",
    }