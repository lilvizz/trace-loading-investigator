from typing import Any


class InvestigationReportBuilder:
    """
    Converts the raw TRACE investigation into a stable,
    UI-friendly report.
    """

    def build(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:

        container = investigation["container"]
        requirement = investigation["requirement"]
        reasoning = investigation["reasoning"]
        triage = investigation["triage"]
        plan = investigation["plan"]

        return {
            "title": "LOADING INVESTIGATION",

            "container": {
                "id": container["container_id"],
                "loading_date": container["loading_date"],
                "destination": container["destination"],
                "status": container["loading_status"],
            },

            "assessment": {
                "conclusion": reasoning["conclusion"],
                "confidence": reasoning["confidence"],
                "priority": triage["priority"],
                "requires_human_verification": (
                    reasoning["requires_human_verification"]
                ),
            },

            "requirement": {
                "material_id": requirement["material_id"],
                "required_quantity": (
                    requirement["required_quantity"]
                ),
                "required_composition_grade": (
                    requirement["required_composition_grade"]
                ),
            },

            "investigation_plan": {
                "questions": plan["questions"],
                "unresolved_questions": (
                    plan["unresolved_questions"]
                ),
                "investigation_complete": (
                    plan["investigation_complete"]
                ),
            },

            "findings": investigation["findings"],

            "evidence": investigation["evidence"],

            "evidence_gaps": triage["evidence_gaps"],

            "reason": reasoning["reason"],

            "recommended_action": (
                triage["recommended_action"]
            ),

            "supporting_evidence": (
                reasoning["supporting_evidence"]
            ),
        }