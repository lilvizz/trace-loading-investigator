from pathlib import Path

from src.trace_loading.data_loader import ManufacturingData
from src.trace_loading.investigator import LoadingInvestigator


def test_case_033_detects_grade_mismatch():
    data_dir = Path(__file__).resolve().parents[1] / "data"

    data = ManufacturingData(data_dir)
    investigator = LoadingInvestigator(data)

    result = investigator.investigate("CNT-5203")

    assert result["container"]["container_id"] == "CNT-5203"

    assert result["requirement"]["material_id"] == "MAT-10036"
    assert result["requirement"]["required_quantity"] == 80
    assert result["requirement"]["required_composition_grade"] == "GRADE_A"

    mismatches = [
        finding
        for finding in result["findings"]
        if finding["type"] == "GRADE_MISMATCH"
    ]

    assert mismatches

    actual_grades = {
        finding["actual_grade"]
        for finding in mismatches
    }

    assert actual_grades == {"GRADE_B", "GRADE_C"}

    assert all(
        finding["required_grade"] == "GRADE_A"
        for finding in mismatches
    )

    requirement_findings = [
        finding
        for finding in result["findings"]
        if finding["type"] == "REQUIREMENT_UNSATISFIED"
    ]

    assert requirement_findings

    assert requirement_findings[0]["qualifying_quantity"] == 0