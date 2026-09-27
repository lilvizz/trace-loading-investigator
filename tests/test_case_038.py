from pathlib import Path

from src.trace_loading.data_loader import ManufacturingData
from src.trace_loading.investigator import LoadingInvestigator


def test_case_038_exposes_grade_mismatch_and_waiver_evidence():
    data_dir = Path(__file__).resolve().parents[1] / "data"

    data = ManufacturingData(data_dir)
    investigator = LoadingInvestigator(data)

    result = investigator.investigate("CNT-5208")

    assert result["container"]["container_id"] == "CNT-5208"

    assert result["requirement"]["material_id"] == "MAT-10035"
    assert result["requirement"]["required_quantity"] == 80
    assert result["requirement"]["required_composition_grade"] == "GRADE_A"

    mismatches = [
        finding
        for finding in result["findings"]
        if finding["type"] == "GRADE_MISMATCH"
    ]

    assert len(mismatches) == 1

    assert mismatches[0]["bundle_id"] == "BND-9038"
    assert mismatches[0]["batch_id"] == "B-10035-01"
    assert mismatches[0]["actual_grade"] == "GRADE_B"
    assert mismatches[0]["required_grade"] == "GRADE_A"

    waiver_events = [
        event
        for event in result["evidence"]
        if (
            event["type"] == "OPERATIONAL_EVENT"
            and event["event_id"] == "EVT-7003"
        )
    ]

    assert len(waiver_events) == 1

    waiver = waiver_events[0]

    assert waiver["reference_id"] == "CNT-5208"
    assert "GRADE_B" in waiver["description"]
    assert "GRADE_A" in waiver["description"]
    assert "approved substitute" in waiver["description"]