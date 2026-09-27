import pytest

from trace_loading.data_loader import ManufacturingData
from trace_loading.investigator import LoadingInvestigator
from trace_loading.investigation_plan import InvestigationPlanner
from trace_loading.reasoner import InvestigationReasoner


DATA_DIR = "data"


@pytest.fixture
def data():
    return ManufacturingData(DATA_DIR)


@pytest.fixture
def investigator(data):
    return LoadingInvestigator(data)


@pytest.fixture
def reasoner():
    return InvestigationReasoner(use_gemini=False)


def conclude(data, reasoner, container_id):
    investigation = LoadingInvestigator(data).investigate(
        container_id
    )

    planner = InvestigationPlanner()

    loading = data.get_loading(container_id)

    plan = planner.plan(loading)
    plan = planner.update(
        plan,
        investigation,
    )

    investigation["plan"] = plan

    return reasoner.reason(investigation)


@pytest.mark.parametrize(
    "container_id",
    [
        "CNT-5105",
        "CNT-5106",
        "CNT-5108",
        "CNT-5112",
    ],
)
def test_missing_physical_evidence_is_not_clean(
    data,
    reasoner,
    container_id,
):
    result = conclude(
        data,
        reasoner,
        container_id,
    )

    assert result["conclusion"] == "INSUFFICIENT_EVIDENCE"


@pytest.mark.parametrize(
    "container_id",
    [
        "CNT-5102",
        "CNT-5103",
        "CNT-5109",
    ],
)
def test_open_operational_issue_is_unresolved(
    data,
    reasoner,
    container_id,
):
    investigation = LoadingInvestigator(
        data
    ).investigate(container_id)

    assert any(
        finding["type"] == "OPEN_OPERATIONAL_ISSUE"
        for finding in investigation["findings"]
    )

    result = conclude(
        data,
        reasoner,
        container_id,
    )

    assert result["conclusion"] == "UNRESOLVED"


def test_container_specific_waiver_does_not_leak(
    data,
):
    events_5110 = data.get_events(
        "MAT-10035",
        "CNT-5110",
    )

    events_5208 = data.get_events(
        "MAT-10035",
        "CNT-5208",
    )

    assert "EVT-7003" not in (
        events_5110["event_id"].values
    )

    assert "EVT-7003" in (
        events_5208["event_id"].values
    )


@pytest.mark.parametrize(
    "container_id",
    [
        "CNT-5111",
        "CNT-5113",
    ],
)
def test_grade_without_requirement_is_not_mismatch(
    data,
    investigator,
    container_id,
):
    investigation = investigator.investigate(
        container_id
    )

    assert (
        investigation["requirement"][
            "required_composition_grade"
        ]
        is None
    )

    assert not any(
        finding["type"] == "GRADE_MISMATCH"
        for finding in investigation["findings"]
    )


@pytest.mark.parametrize(
    "container_id,expected",
    [
        ("CNT-5203", "UNRESOLVED"),
        ("CNT-5204", "INSUFFICIENT_EVIDENCE"),
        ("CNT-5206", "INSUFFICIENT_EVIDENCE"),
        ("CNT-5207", "NO_EXCEPTION"),
        ("CNT-5208", "LEGITIMATE_EXCEPTION"),
    ],
)
def test_existing_cases_remain_correct(
    data,
    reasoner,
    container_id,
    expected,
):
    result = conclude(
        data,
        reasoner,
        container_id,
    )

    assert result["conclusion"] == expected