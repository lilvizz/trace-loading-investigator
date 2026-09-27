from pathlib import Path

from src.trace_loading.data_loader import ManufacturingData
from src.trace_loading.investigation_plan import (
    InvestigationPlanner,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_case_033_creates_investigation_plan():

    data = ManufacturingData(DATA_DIR)

    loading = data.get_loading("CNT-5203")

    planner = InvestigationPlanner()

    plan = planner.plan(loading)

    assert plan["container_id"] == "CNT-5203"

    assert plan["material_id"] == "MAT-10036"

    assert plan["required_quantity"] == 80

    assert plan["required_composition_grade"] == "GRADE_A"

    assert len(plan["questions"]) == 6

    question_ids = {
        question["id"]
        for question in plan["questions"]
    }

    assert question_ids == {
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "Q5",
        "Q6",
    }


def test_case_033_updates_investigation_state():

    investigator = __import__(
        "src.trace_loading.investigator",
        fromlist=["LoadingInvestigator"],
    ).LoadingInvestigator

    data = ManufacturingData(DATA_DIR)

    loading = data.get_loading("CNT-5203")

    planner = InvestigationPlanner()

    investigation = investigator(data).investigate(
        "CNT-5203"
    )

    plan = planner.plan(loading)

    updated = planner.update(
        plan,
        investigation,
    )

    statuses = {
        question["id"]: question["status"]
        for question in updated["questions"]
    }

    assert statuses["Q1"] == "ANSWERED"
    assert statuses["Q2"] == "ANSWERED"
    assert statuses["Q3"] == "ANSWERED"
    assert statuses["Q4"] == "UNRESOLVED"
    assert statuses["Q5"] == "UNRESOLVED"
    assert statuses["Q6"] == "UNRESOLVED"

    assert updated["investigation_complete"] is False

    assert len(updated["unresolved_questions"]) == 3