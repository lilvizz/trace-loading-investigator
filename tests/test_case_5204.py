from pathlib import Path

from trace_loading.data_loader import ManufacturingData
from trace_loading.investigator import LoadingInvestigator
from trace_loading.investigation_plan import InvestigationPlanner
from trace_loading.reasoner import InvestigationReasoner


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_case_5204_is_insufficient_evidence():
    data = ManufacturingData(DATA_DIR)

    investigator = LoadingInvestigator(data)
    investigation = investigator.investigate("CNT-5204")

    findings = investigation["findings"]

    assert any(
        finding["type"] == "INSUFFICIENT_EVIDENCE"
        for finding in findings
    )

    assert not any(
        finding["type"] == "REQUIREMENT_UNSATISFIED"
        for finding in findings
    )

    planner = InvestigationPlanner()
    plan = planner.update(
        planner.plan(data.get_loading("CNT-5204")),
        investigation,
    )

    investigation["plan"] = plan

    reasoning = InvestigationReasoner(use_gemini=False).reason(investigation)

    assert reasoning["conclusion"] == "INSUFFICIENT_EVIDENCE"
    assert reasoning["requires_human_verification"] is True
    assert reasoning["confidence"] <= 0.60