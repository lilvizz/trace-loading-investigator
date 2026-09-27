from typing import Any


class InvestigationTriage:
    """
    Converts investigation findings into operational triage.

    The loading schedule's operational priority is authoritative.
    """

    def triage(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:

        container = investigation["container"]
        findings = investigation["findings"]
        evidence = investigation["evidence"]
        reasoning = investigation.get("reasoning", {})

        evidence_gaps = self._identify_evidence_gaps(
            findings,
            evidence,
            reasoning,
        )

        urgency = self._calculate_urgency(
            container,
            findings,
        )

        return {
            "priority": urgency["priority"],
            "urgency_reason": urgency["reason"],
            "evidence_gaps": evidence_gaps,
            "requires_human_verification": reasoning.get(
                "requires_human_verification",
                True,
            ),
            "recommended_action": self._recommended_action(
                findings,
                reasoning,
            ),
        }

    @staticmethod
    def _identify_evidence_gaps(
        findings: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
        reasoning: dict[str, Any],
    ) -> list[dict[str, Any]]:

        gaps: list[dict[str, Any]] = []

        has_approved_substitution = any(
            item.get("type") == "OPERATIONAL_EVENT"
            and "approved substitute"
            in item.get("description", "").lower()
            for item in evidence
        )

        for finding in findings:
            finding_type = finding.get("type")

            if finding_type == "TRACEABILITY_GAP":
                gaps.append(
                    {
                        "type": "TRACEABILITY",
                        "description": (
                            f"Bundle {finding['bundle_id']} references "
                            f"batch {finding['batch_id']}, but the "
                            "corresponding ERP batch record is unavailable."
                        ),
                    }
                )

            elif finding_type == "GRADE_MISMATCH":
                if not has_approved_substitution:
                    gaps.append(
                        {
                            "type": "SUITABILITY",
                            "description": (
                                f"Bundle {finding['bundle_id']} does not "
                                f"match the required composition grade "
                                f"{finding['required_grade']}."
                            ),
                        }
                    )

            elif finding_type == "REQUIREMENT_UNSATISFIED":
                gaps.append(
                    {
                        "type": "REQUIREMENT",
                        "description": (
                            f"Only {finding['qualifying_quantity']:g} EA "
                            f"qualify against the required "
                            f"{finding['required_quantity']:g} EA."
                        ),
                    }
                )

        reasoning_gap = reasoning.get("evidence_gap")

        if reasoning_gap:
            gaps.append(
                {
                    "type": "REASONING",
                    "description": reasoning_gap,
                }
            )

        return gaps

    @staticmethod
    def _calculate_urgency(
        container: dict[str, Any],
        findings: list[dict[str, Any]],
    ) -> dict[str, str]:

        operational_priority = str(
            container.get("priority", "")
        ).upper()

        loading_status = str(
            container.get("loading_status", "")
        ).upper()

        has_issue = bool(findings)

        if operational_priority == "HIGH":
            return {
                "priority": "HIGH",
                "reason": (
                    "The loading schedule marks this operation as "
                    "HIGH priority and an investigation finding "
                    "requires attention."
                ),
            }

        if operational_priority == "MEDIUM":
            return {
                "priority": "MEDIUM",
                "reason": (
                    "The loading schedule marks this operation as "
                    "MEDIUM priority."
                ),
            }

        if operational_priority == "LOW":
            return {
                "priority": "LOW",
                "reason": (
                    "The loading schedule marks this operation as "
                    "LOW priority."
                ),
            }

        if has_issue and loading_status == "PARTIALLY_READY":
            return {
                "priority": "HIGH",
                "reason": (
                    "The operation is partially ready and has an "
                    "investigation finding requiring attention."
                ),
            }

        if has_issue:
            return {
                "priority": "MEDIUM",
                "reason": (
                    "An investigation finding requires attention."
                ),
            }

        return {
            "priority": "LOW",
            "reason": (
                "No investigation finding currently requires "
                "urgent human attention."
            ),
        }

    @staticmethod
    def _recommended_action(
        findings: list[dict[str, Any]],
        reasoning: dict[str, Any],
    ) -> str:

        recommended_action = reasoning.get("recommended_action")

        if recommended_action:
            return recommended_action

        if any(
            finding.get("type") == "TRACEABILITY_GAP"
            for finding in findings
        ):
            return (
                "Verify the referenced batch and bundle records "
                "before loading."
            )

        if any(
            finding.get("type") == "GRADE_MISMATCH"
            for finding in findings
        ):
            return (
                "Verify the required grade and any approved "
                "substitution before loading."
            )

        if any(
            finding.get("type") == "REQUIREMENT_UNSATISFIED"
            for finding in findings
        ):
            return (
                "Identify qualifying bundles that satisfy the "
                "loading requirement before loading."
            )

        return (
            "Perform human verification if the loading operation "
            "requires additional evidence."
        )