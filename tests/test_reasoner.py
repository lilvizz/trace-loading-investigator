from pathlib import Path

from src.trace_loading.data_loader import ManufacturingData
from src.trace_loading.investigator import LoadingInvestigator
from src.trace_loading.reasoner import InvestigationReasoner


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_case_033_is_unresolved():
    data = ManufacturingData(DATA_DIR)
    investigator = LoadingInvestigator(data)
    reasoner = InvestigationReasoner()

    investigation = investigator.investigate("CNT-5203")
    result = reasoner.reason(investigation)

    assert result["conclusion"] == "UNRESOLVED"
    assert result["requires_human_verification"] is True


def test_case_038_is_legitimate_exception():
    data = ManufacturingData(DATA_DIR)
    investigator = LoadingInvestigator(data)
    reasoner = InvestigationReasoner()

    investigation = investigator.investigate("CNT-5208")
    result = reasoner.reason(investigation)

    assert result["conclusion"] == "LEGITIMATE_EXCEPTION"
    assert result["requires_human_verification"] is False
    assert "EVT-7003" in result["supporting_evidence"]