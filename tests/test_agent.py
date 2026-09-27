from pathlib import Path

from src.trace_loading.agent import InvestigationAgent
from src.trace_loading.data_loader import ManufacturingData


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_agent_runs_case_033():

    data = ManufacturingData(DATA_DIR)

    agent = InvestigationAgent(
        data,
        use_gemini=False,
    )

    result = agent.investigate("CNT-5203")

    assert result["title"] == "LOADING INVESTIGATION"

    assert result["container"]["id"] == "CNT-5203"

    assert result["requirement"]["material_id"] == "MAT-10036"

    assert result["assessment"]["conclusion"] == "UNRESOLVED"

    assert (
        result["assessment"]["requires_human_verification"]
        is True
    )

    assert result["assessment"]["priority"] == "HIGH"

    assert result["findings"]

    assert result["evidence"]

    assert result["evidence_gaps"]

    assert result["recommended_action"]

    plan = result["investigation_plan"]

    assert len(plan["questions"]) == 6

    assert len(plan["unresolved_questions"]) == 3

    assert plan["investigation_complete"] is False