from typing import Any

from .data_loader import ManufacturingData
from .investigation_plan import InvestigationPlanner
from .investigator import LoadingInvestigator
from .reasoner import InvestigationReasoner
from .report import InvestigationReportBuilder
from .triage import InvestigationTriage


class InvestigationAgent:
    """
    Orchestrates a complete TRACE loading investigation.

    Pipeline:

        Loading requirement
              ↓
        Investigation plan
              ↓
        Evidence investigation
              ↓
        Plan update / evidence-gap analysis
              ↓
        Gemini reasoning
              ↓
        Confidence guardrails
              ↓
        Operational triage
              ↓
        Investigation report
    """

    def __init__(
        self,
        data: ManufacturingData,
        use_gemini: bool = False,
    ):
        self.data = data

        self.planner = InvestigationPlanner()

        self.investigator = LoadingInvestigator(
            data
        )

        self.reasoner = InvestigationReasoner(
            use_gemini=use_gemini
        )

        self.triage_engine = InvestigationTriage()

        self.report_builder = InvestigationReportBuilder()

    def investigate(
        self,
        container_id: str,
    ) -> dict[str, Any]:

        # 1. Load the operational requirement.
        loading = self.data.get_loading(
            container_id
        )

        # 2. Create the initial investigation plan.
        initial_plan = self.planner.plan(
            loading
        )

        # 3. Collect deterministic evidence.
        investigation = self.investigator.investigate(
            container_id
        )

        # 4. Update the plan using the evidence collected.
        updated_plan = self.planner.update(
            initial_plan,
            investigation,
        )

        investigation["plan"] = updated_plan

        # 5. Reason over the complete evidence set.
        reasoning = self.reasoner.reason(
            investigation
        )

        investigation["reasoning"] = reasoning

        # 6. Determine operational priority and evidence gaps.
        triage = self.triage_engine.triage(
            investigation
        )

        investigation["triage"] = triage

        # 7. Build the stable report consumed by the UI.
        return self.report_builder.build(
            investigation
        )