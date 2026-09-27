from typing import Any


class InvestigationPlanner:
    """
    Builds and updates the investigation plan.

    The planner starts with the questions required for a loading
    investigation and identifies which questions remain unresolved
    after evidence has been collected.
    """

    def plan(
        self,
        loading: dict[str, Any],
    ) -> dict[str, Any]:

        material_id = loading["material_id"]
        required_quantity = loading["required_quantity"]
        required_grade = loading["required_composition_grade"]

        questions = [
            {
                "id": "Q1",
                "question": (
                    "What material is required for this loading operation?"
                ),
                "target": material_id,
            },
            {
                "id": "Q2",
                "question": (
                    "Which batches contain the required material?"
                ),
                "target": material_id,
            },
            {
                "id": "Q3",
                "question": (
                    "Which physical bundles are associated with "
                    "those batches?"
                ),
                "target": material_id,
            },
            {
                "id": "Q4",
                "question": (
                    "Do the available physical bundles satisfy "
                    "the required composition grade?"
                ),
                "target": required_grade,
            },
            {
                "id": "Q5",
                "question": (
                    "Is sufficient qualifying quantity available "
                    "for the loading requirement?"
                ),
                "target": required_quantity,
            },
            {
                "id": "Q6",
                "question": (
                    "Are there documented operational events, "
                    "waivers, or substitutions that explain "
                    "an apparent discrepancy?"
                ),
                "target": material_id,
            },
        ]

        return {
            "container_id": loading["container_id"],
            "material_id": material_id,
            "required_quantity": required_quantity,
            "required_composition_grade": required_grade,
            "questions": questions,
        }

    def update(
        self,
        plan: dict[str, Any],
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Mark investigation questions as answered or unresolved
        using the evidence collected.
        """

        findings = investigation["findings"]
        evidence = investigation["evidence"]

        statuses = {}

        statuses["Q1"] = self._material_status(
            investigation
        )

        statuses["Q2"] = self._batch_status(
            investigation
        )

        statuses["Q3"] = self._bundle_status(
            evidence
        )

        statuses["Q4"] = self._grade_status(
            findings,
            evidence,
        )

        statuses["Q5"] = self._quantity_status(
            findings
        )

        statuses["Q6"] = self._exception_status(
            evidence,
            findings,
        )

        updated_questions = []

        for question in plan["questions"]:

            status = statuses[question["id"]]

            updated_questions.append(
                {
                    **question,
                    "status": status["status"],
                    "reason": status["reason"],
                }
            )

        unresolved = [
            question
            for question in updated_questions
            if question["status"] != "ANSWERED"
        ]

        return {
            **plan,
            "questions": updated_questions,
            "unresolved_questions": unresolved,
            "investigation_complete": not unresolved,
        }

    @staticmethod
    def _material_status(
        investigation: dict[str, Any],
    ) -> dict[str, str]:

        material_id = investigation["requirement"]["material_id"]

        if material_id:
            return {
                "status": "ANSWERED",
                "reason": (
                    f"Loading requirement identifies material "
                    f"{material_id}."
                ),
            }

        return {
            "status": "UNRESOLVED",
            "reason": "No material identifier was established.",
        }

    @staticmethod
    def _batch_status(
        investigation: dict[str, Any],
    ) -> dict[str, str]:

        batch_ids = {
            item["batch_id"]
            for item in investigation["evidence"]
            if (
                item["type"] == "PHYSICAL_BUNDLE"
                and item.get("batch_id")
            )
        }

        if batch_ids:
            return {
                "status": "ANSWERED",
                "reason": (
                    f"Evidence links physical bundles to "
                    f"{len(batch_ids)} batch record(s)."
                ),
            }

        return {
            "status": "UNRESOLVED",
            "reason": (
                "No resolvable batch linkage was established."
            ),
        }

    @staticmethod
    def _bundle_status(
        evidence: list[dict[str, Any]],
    ) -> dict[str, str]:

        bundle_ids = {
            item["bundle_id"]
            for item in evidence
            if (
                item["type"] == "PHYSICAL_BUNDLE"
                and item.get("bundle_id")
            )
        }

        if bundle_ids:
            return {
                "status": "ANSWERED",
                "reason": (
                    f"{len(bundle_ids)} physical bundle record(s) "
                    "were identified."
                ),
            }

        return {
            "status": "UNRESOLVED",
            "reason": (
                "No physical bundle record was identified."
            ),
        }

    @staticmethod
    def _grade_status(
        findings: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> dict[str, str]:

        mismatches = [
            finding
            for finding in findings
            if finding["type"] == "GRADE_MISMATCH"
        ]

        if not mismatches:
            return {
                "status": "ANSWERED",
                "reason": (
                    "No composition-grade mismatch was identified."
                ),
            }

        has_approved_substitution = any(
            item["type"] == "OPERATIONAL_EVENT"
            and "approved substitute"
            in item.get("description", "").lower()
            for item in evidence
        )

        if has_approved_substitution:
            return {
                "status": "ANSWERED",
                "reason": (
                    "A composition-grade mismatch was identified, "
                    "but an explicit approved substitution explains "
                    "the exception."
                ),
            }

        return {
            "status": "UNRESOLVED",
            "reason": (
                "One or more bundles have a composition grade "
                "that does not match the loading requirement."
            ),
        }

    @staticmethod
    def _quantity_status(
        findings: list[dict[str, Any]],
    ) -> dict[str, str]:

        insufficient = [
            finding
            for finding in findings
            if finding["type"] == "REQUIREMENT_UNSATISFIED"
        ]

        if insufficient:
            return {
                "status": "UNRESOLVED",
                "reason": (
                    "The investigated qualifying quantity does not "
                    "satisfy the loading requirement."
                ),
            }

        return {
            "status": "ANSWERED",
            "reason": (
                "No qualifying-quantity shortfall was identified."
            ),
        }

    @staticmethod
    def _exception_status(
        evidence: list[dict[str, Any]],
        findings: list[dict[str, Any]],
    ) -> dict[str, str]:

        has_mismatch = any(
            finding["type"] == "GRADE_MISMATCH"
            for finding in findings
        )

        if not has_mismatch:
            return {
                "status": "ANSWERED",
                "reason": (
                    "No discrepancy requiring an exception "
                    "explanation was identified."
                ),
            }

        has_waiver = any(
            item["type"] == "OPERATIONAL_EVENT"
            and "approved substitute"
            in item.get("description", "").lower()
            for item in evidence
        )

        if has_waiver:
            return {
                "status": "ANSWERED",
                "reason": (
                    "An explicit approved substitution was found "
                    "in the operational evidence."
                ),
            }

        return {
            "status": "UNRESOLVED",
            "reason": (
                "A discrepancy exists, but no explicit approved "
                "substitution or waiver was found."
            ),
        }