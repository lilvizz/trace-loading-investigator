import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai

WAIVER_MARKERS = (
    "approved substitution",
    "approved substitute",
    "substitution approved",
    "waiver approved",
    "approved waiver",
    "deviation approved",
    "approved deviation",
)


def _has_approved_waiver(
    evidence_items: list[dict[str, Any]],
) -> bool:
    return any(
        evidence.get("type") == "OPERATIONAL_EVENT"
        and evidence.get("status") in {"APPROVED", "CLOSED"}
        and any(
            marker in str(
                evidence.get("description", "")
            ).lower()
            for marker in WAIVER_MARKERS
        )
        for evidence in evidence_items
    )


class InvestigationReasoner:
    """
    Gemini-powered reasoning layer.

    Deterministic investigation establishes the evidence.
    Gemini interprets that evidence.

    A deterministic validator runs after Gemini so the model
    cannot contradict authoritative investigation findings or
    cite evidence that does not exist.

    A deterministic fallback remains available for tests.
    """

    def __init__(
        self,
        use_gemini: bool = False,
        model: str = "gemini-3.8-flash",
    ):
        self.use_gemini = use_gemini
        self.model = model
        self.client = None

        if self.use_gemini:
            load_dotenv()

            api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY is not set. "
                    "Add it to the .env file before using Gemini."
                )

            self.client = genai.Client(api_key=api_key)

    def reason(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:

        if self.use_gemini:
            result = self._reason_with_gemini(investigation)
            result = self._validate_against_evidence(
                result,
                investigation,
            )
            return self._calibrate_confidence(
                result,
                investigation,
            )

        return self._reason_deterministically(investigation)

    # ------------------------------------------------------------------
    # Deterministic reasoning
    # ------------------------------------------------------------------

    def _reason_deterministically(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:

        findings = investigation["findings"]
        evidence_items = investigation["evidence"]

        has_insufficient_evidence = any(
            finding.get("type") == "INSUFFICIENT_EVIDENCE"
            for finding in findings
        )

        has_traceability_gap = any(
            finding.get("type") == "TRACEABILITY_GAP"
            for finding in findings
        )

        has_grade_mismatch = any(
            finding.get("type") == "GRADE_MISMATCH"
            for finding in findings
        )

        has_requirement_gap = any(
            finding.get("type") == "REQUIREMENT_UNSATISFIED"
            for finding in findings
        )

        has_open_issue = any(
            finding.get("type") == "OPEN_OPERATIONAL_ISSUE"
            for finding in findings
        )

        has_approved_waiver = _has_approved_waiver(
            evidence_items
        )

        # ---------------------------------------------------------
        # 1. Missing evidence always remains missing.
        # ---------------------------------------------------------

        if has_insufficient_evidence:
            return {
                "conclusion": "INSUFFICIENT_EVIDENCE",
                "confidence": 0.60,
                "requires_human_verification": True,
                "reason": (
                    "The available operational records do not contain "
                    "enough physical-bundle evidence to establish "
                    "loading suitability."
                ),
                "evidence_gap": (
                    "Physical bundle selection or dispatch evidence "
                    "is required to verify the loading requirement."
                ),
                "recommended_action": (
                    "Verify which physical bundles were selected or "
                    "sent to logistics before loading proceeds."
                ),
                "supporting_evidence": [],
            }

        # ---------------------------------------------------------
        # 2. Any unresolved operational issue remains unresolved.
        #
        # A grade waiver cannot clear an unrelated open quality
        # hold, recount, reconciliation, etc.
        # ---------------------------------------------------------

        if (
            has_traceability_gap
            or has_requirement_gap
            or has_open_issue
            or (
                has_grade_mismatch
                and not has_approved_waiver
            )
        ):
            return {
                "conclusion": "UNRESOLVED",
                "confidence": 0.70,
                "requires_human_verification": True,
                "reason": (
                    "The investigation identified an operational "
                    "inconsistency that cannot be cleared from "
                    "the available evidence."
                ),
                "evidence_gap": (
                    "Additional operational verification is required "
                    "to resolve the identified discrepancy."
                ),
                "recommended_action": (
                    "Verify the affected bundle, batch, requirement, "
                    "or supporting operational record before loading."
                ),
                "supporting_evidence": [],
            }

        # ---------------------------------------------------------
        # 3. Grade mismatch with documented waiver.
        #
        # This is only reached if there are no other unresolved
        # findings.
        # ---------------------------------------------------------

        if has_grade_mismatch and has_approved_waiver:
            bundle_ids = [
                evidence["bundle_id"]
                for evidence in evidence_items
                if (
                    evidence.get("type") == "PHYSICAL_BUNDLE"
                    and evidence.get("bundle_id")
                )
            ]

            event_ids = [
                evidence["event_id"]
                for evidence in evidence_items
                if (
                    evidence.get("type") == "OPERATIONAL_EVENT"
                    and evidence.get("event_id")
                    and _has_approved_waiver([evidence])
                )
            ]

            return {
                "conclusion": "LEGITIMATE_EXCEPTION",
                "confidence": 0.95,
                "requires_human_verification": False,
                "reason": (
                    "The apparent composition-grade mismatch is "
                    "covered by a documented approved substitution "
                    "or waiver."
                ),
                "evidence_gap": None,
                "recommended_action": (
                    "Proceed under the documented approved exception."
                ),
                "supporting_evidence": (
                    bundle_ids + event_ids
                ),
            }

        # ---------------------------------------------------------
        # 4. No exception.
        # ---------------------------------------------------------

        bundle_ids = [
            evidence["bundle_id"]
            for evidence in evidence_items
            if (
                evidence.get("type") == "PHYSICAL_BUNDLE"
                and evidence.get("bundle_id")
            )
        ]

        return {
            "conclusion": "NO_EXCEPTION",
            "confidence": 0.95,
            "requires_human_verification": False,
            "reason": (
                "The available operational evidence supports the "
                "loading requirement with no identified exception."
            ),
            "evidence_gap": None,
            "recommended_action": (
                "Proceed with the normal loading workflow."
            ),
            "supporting_evidence": bundle_ids,
        }
    # ------------------------------------------------------------------
    # Gemini reasoning
    # ------------------------------------------------------------------

    def _reason_with_gemini(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:

        prompt = self._build_prompt(investigation)

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        result = self._parse_json(
            response.text.strip()
        )

        self._validate_result(result)

        return result

    def _build_prompt(
        self,
        investigation: dict[str, Any],
    ) -> str:

        plan = investigation.get("plan", {})

        return f"""
You are TRACE, a manufacturing loading investigation agent.

The deterministic investigation engine has already collected
operational evidence.

Your job is to reason over that evidence.

IMPORTANT:
The supplied investigation data is authoritative.
Do not invent records, bundles, batches, quantities, grades,
waivers, or operational events.

INVESTIGATION OBJECTIVE

Determine whether the physical bundles associated with this
loading operation can be trusted against the recorded loading
requirements.

INVESTIGATION PLAN

The investigation contains questions that were explicitly checked.

For each question, distinguish:

- ANSWERED: evidence establishes the answer.
- UNRESOLVED: evidence exists but does not establish the answer.
- Missing evidence: the required record is unavailable.

Do not turn an unanswered question into a positive conclusion.

POSSIBLE CONCLUSIONS

1. NO_EXCEPTION

Use only when the available evidence establishes that the
loading requirement is satisfied and no unresolved discrepancy
remains.

2. LEGITIMATE_EXCEPTION

Use when an apparent discrepancy exists but an explicit,
documented waiver, approved substitution, or equivalent
authorization explains it.

3. UNRESOLVED

Use when a discrepancy exists and the available evidence does
not establish that it has been legitimately resolved.

4. INSUFFICIENT_EVIDENCE

Use when the evidence required to make a reliable determination
is missing.

RULES

- Never invent evidence.
- Never assume quantity alone means a bundle is suitable.
- Trace material -> batch -> grade -> physical bundle.
- Treat explicit operational waivers as evidence.
- A missing waiver is not itself proof of invalidity.
- Do not authorize physical loading.
- Do not modify ERP records.
- If evidence is complete and consistent, use NO_EXCEPTION.
- If evidence is incomplete, do not claim NO_EXCEPTION.
- Supporting evidence must use identifiers that actually appear
  in the supplied evidence.
- If a documented approved substitution exists, it can explain
  an apparent grade mismatch.
- If a physical bundle is referenced but cannot be linked to a
  valid operational record, treat that as unresolved or
  insufficient evidence rather than inventing the linkage.

REASONING PRIORITY

1. Identify the loading requirement.
2. Establish material identity.
3. Establish batch linkage.
4. Establish composition-grade suitability.
5. Establish physical-bundle linkage.
6. Establish quantity sufficiency.
7. Check operational events for waivers, substitutions,
   returns, holds, or other explanations.
8. Identify remaining evidence gaps.
9. Give the narrowest conclusion supported by the evidence.

Return ONLY valid JSON:

{{
  "conclusion": "NO_EXCEPTION" | "LEGITIMATE_EXCEPTION" | "UNRESOLVED" | "INSUFFICIENT_EVIDENCE",
  "confidence": 0.0,
  "requires_human_verification": true,
  "reason": "concise explanation",
  "evidence_gap": "missing evidence, or null",
  "recommended_action": "specific human action, or no additional investigation required",
  "supporting_evidence": ["evidence identifiers"]
}}

Confidence must be between 0.0 and 1.0.

INVESTIGATION PLAN:

{json.dumps(plan, indent=2, default=str)}

INVESTIGATION FINDINGS:

{json.dumps(investigation.get("findings", []), indent=2, default=str)}

EVIDENCE GAPS:

{json.dumps(investigation.get("triage", {}).get("evidence_gaps", []), indent=2, default=str)}

EVIDENCE:

{json.dumps(investigation.get("evidence", []), indent=2, default=str)}
"""

    # ------------------------------------------------------------------
    # Deterministic Gemini validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_against_evidence(
        result: dict[str, Any],
        investigation: dict[str, Any],
    ) -> dict[str, Any]:

        findings = investigation.get("findings", [])
        evidence_items = investigation.get("evidence", [])

        evidence_ids = set()

        for item in evidence_items:
            for key in (
                "event_id",
                "bundle_id",
                "batch_id",
                "material_id",
                "reference_id",
            ):
                value = item.get(key)

                if value:
                    evidence_ids.add(str(value))

        # ---------------------------------------------------------
        # 1. Remove hallucinated supporting evidence IDs.
        # ---------------------------------------------------------
        supplied_supporting = result.get(
            "supporting_evidence",
            [],
        )

        valid_supporting = [
            str(identifier)
            for identifier in supplied_supporting
            if str(identifier) in evidence_ids
        ]

        result["supporting_evidence"] = valid_supporting

        # ---------------------------------------------------------
        # 2. Detect authoritative findings.
        # ---------------------------------------------------------
        has_insufficient_evidence = any(
            finding.get("type") == "INSUFFICIENT_EVIDENCE"
            for finding in findings
        )

        has_traceability_gap = any(
            finding.get("type") == "TRACEABILITY_GAP"
            for finding in findings
        )

        has_grade_mismatch = any(
            finding.get("type") == "GRADE_MISMATCH"
            for finding in findings
        )

        has_requirement_gap = any(
            finding.get("type") == "REQUIREMENT_UNSATISFIED"
            for finding in findings
        )

        has_open_issue = any(
            finding.get("type") == "OPEN_OPERATIONAL_ISSUE"
            for finding in findings
        )

        has_unresolved_finding = (
            has_traceability_gap
            or has_grade_mismatch
            or has_requirement_gap
            or has_open_issue
        )

        has_open_issue = any(
            finding.get("type") == "OPEN_OPERATIONAL_ISSUE"
            for finding in findings
        )
        
        # ---------------------------------------------------------
        # 3. Verify documented exception.
        # ---------------------------------------------------------
        approved_exception_events = [
            item
            for item in evidence_items
            if item.get("type") == "OPERATIONAL_EVENT"
            and item.get("status") in {"APPROVED", "CLOSED"}
            and any(
                marker in str(
                    item.get("description", "")
                ).lower()
                for marker in [
                    "approved substitution",
                    "approved substitute",
                    "substitution approved",
                    "waiver approved",
                    "approved waiver",
                    "deviation approved",
                    "approved deviation",
                ]
            )
        ]

        waiver_exists = bool(approved_exception_events)

        # ---------------------------------------------------------
        # 4. Gemini cannot claim NO_EXCEPTION against evidence.
        # ---------------------------------------------------------
        if result["conclusion"] == "NO_EXCEPTION":
            if has_insufficient_evidence:
                result = InvestigationReasoner._force_insufficient_evidence(
                    result
                )

            elif has_unresolved_finding:
                result = InvestigationReasoner._force_unresolved(
                    result
                )

        # ---------------------------------------------------------
        # 5. Gemini cannot claim LEGITIMATE_EXCEPTION without
        #    a documented exception.
        # ---------------------------------------------------------
        elif result["conclusion"] == "LEGITIMATE_EXCEPTION":
            if not waiver_exists:
                result = InvestigationReasoner._force_unresolved(
                    result,
                    reason=(
                        "Gemini identified a possible exception, but no "
                        "documented approved waiver or substitution was "
                        "found in the supplied evidence."
                    ),
                )

            else:
                result["requires_human_verification"] = False

                waiver_ids = [
                    item["event_id"]
                    for item in approved_exception_events
                    if item.get("event_id")
                ]

                result["supporting_evidence"] = list(
                    dict.fromkeys(
                        result["supporting_evidence"]
                        + waiver_ids
                    )
                )

        # ---------------------------------------------------------
        # 6. INSUFFICIENT_EVIDENCE is always human-verification.
        # ---------------------------------------------------------
        elif result["conclusion"] == "INSUFFICIENT_EVIDENCE":
            result["requires_human_verification"] = True

        # ---------------------------------------------------------
        # 7. UNRESOLVED is always human-verification.
        # ---------------------------------------------------------
        elif result["conclusion"] == "UNRESOLVED":
            result["requires_human_verification"] = True

        return result

    @staticmethod
    def _force_insufficient_evidence(
        result: dict[str, Any],
    ) -> dict[str, Any]:

        result["conclusion"] = "INSUFFICIENT_EVIDENCE"
        result["confidence"] = min(
            float(result.get("confidence", 0.60)),
            0.60,
        )
        result["requires_human_verification"] = True

        if not result.get("evidence_gap"):
            result["evidence_gap"] = (
                "The available evidence is insufficient to establish "
                "loading suitability."
            )

        if not result.get("recommended_action"):
            result["recommended_action"] = (
                "Verify the missing operational evidence before loading."
            )

        return result

    @staticmethod
    def _force_unresolved(
        result: dict[str, Any],
        reason: str | None = None,
    ) -> dict[str, Any]:

        result["conclusion"] = "UNRESOLVED"
        result["confidence"] = min(
            float(result.get("confidence", 0.70)),
            0.70,
        )
        result["requires_human_verification"] = True

        if reason:
            result["reason"] = reason
        elif not result.get("reason"):
            result["reason"] = (
                "The investigation identified an operational "
                "inconsistency that remains unresolved."
            )

        if not result.get("evidence_gap"):
            result["evidence_gap"] = (
                "Additional operational verification is required "
                "before loading."
            )

        if not result.get("recommended_action"):
            result["recommended_action"] = (
                "Verify the unresolved finding before loading."
            )

        return result

    # ------------------------------------------------------------------
    # Confidence calibration
    # ------------------------------------------------------------------

    @staticmethod
    def _calibrate_confidence(
        result: dict[str, Any],
        investigation: dict[str, Any],
    ) -> dict[str, Any]:

        findings = investigation["findings"]

        has_mismatch = any(
            finding["type"] == "GRADE_MISMATCH"
            for finding in findings
        )

        has_traceability_gap = any(
            finding["type"] == "TRACEABILITY_GAP"
            for finding in findings
        )

        has_requirement_gap = any(
            finding["type"] == "REQUIREMENT_UNSATISFIED"
            for finding in findings
        )

        has_insufficient_evidence = any(
            finding["type"] == "INSUFFICIENT_EVIDENCE"
            for finding in findings
        )

        conclusion = result["conclusion"]

        confidence = float(
            result["confidence"]
        )

        if conclusion == "UNRESOLVED":
            if (
                result["evidence_gap"]
                and (
                    has_mismatch
                    or has_traceability_gap
                    or has_requirement_gap
                )
            ):
                confidence = min(
                    confidence,
                    0.80,
                )

            result["requires_human_verification"] = True

        elif conclusion == "INSUFFICIENT_EVIDENCE":
            confidence = min(
                confidence,
                0.60,
            )

            result["requires_human_verification"] = True

        elif conclusion == "LEGITIMATE_EXCEPTION":
            waiver_exists = any(
                item["type"] == "OPERATIONAL_EVENT"
                and item.get("status") in {"APPROVED", "CLOSED"}
                and any(
                    marker in item.get(
                        "description",
                        "",
                    ).lower()
                    for marker in [
                        "approved substitution",
                        "approved substitute",
                        "substitution approved",
                        "waiver approved",
                        "approved waiver",
                        "deviation approved",
                        "approved deviation",
                    ]
                )
                for item in investigation["evidence"]
            )

            if not waiver_exists:
                result["conclusion"] = "UNRESOLVED"
                result["requires_human_verification"] = True
                result["evidence_gap"] = (
                    "No explicit approved substitution or waiver "
                    "was found in the supplied evidence."
                )
                result["recommended_action"] = (
                    "Verify whether an approved substitution or "
                    "waiver exists before loading."
                )

                confidence = min(
                    confidence,
                    0.50,
                )

        elif conclusion == "NO_EXCEPTION":

            if (
                has_insufficient_evidence
                or has_mismatch
                or has_traceability_gap
                or has_requirement_gap
            ):
                result["conclusion"] = (
                    "INSUFFICIENT_EVIDENCE"
                    if has_insufficient_evidence
                    else "UNRESOLVED"
                )

                result["requires_human_verification"] = True

                result["evidence_gap"] = (
                    "The evidence contains an unresolved finding, "
                    "so the operation cannot be classified as "
                    "having no exception."
                )

                result["recommended_action"] = (
                    "Verify the unresolved finding before loading."
                )

                confidence = min(
                    confidence,
                    0.60 if has_insufficient_evidence else 0.50,
                )

        result["confidence"] = round(
            confidence,
            2,
        )

        return result

    # ------------------------------------------------------------------
    # JSON parsing / validation
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(
        text: str,
    ) -> dict[str, Any]:

        cleaned = text.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        try:
            return json.loads(cleaned)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Gemini returned invalid JSON.\n"
                f"Response:\n{cleaned}"
            ) from exc

    @staticmethod
    def _validate_result(
        result: dict[str, Any],
    ) -> None:

        required_fields = {
            "conclusion",
            "confidence",
            "requires_human_verification",
            "reason",
            "evidence_gap",
            "recommended_action",
            "supporting_evidence",
        }

        missing = (
            required_fields - result.keys()
        )

        if missing:
            raise ValueError(
                f"Gemini response is missing fields: "
                f"{sorted(missing)}"
            )

        allowed_conclusions = {
            "NO_EXCEPTION",
            "LEGITIMATE_EXCEPTION",
            "UNRESOLVED",
            "INSUFFICIENT_EVIDENCE",
        }

        if result["conclusion"] not in allowed_conclusions:
            raise ValueError(
                f"Invalid conclusion: "
                f"{result['conclusion']}"
            )

        confidence = result["confidence"]

        if not isinstance(
            confidence,
            (int, float),
        ):
            raise ValueError(
                "Confidence must be numeric."
            )

        if not 0.0 <= float(confidence) <= 1.0:
            raise ValueError(
                "Confidence must be between 0 and 1."
            )

        if not isinstance(
            result["requires_human_verification"],
            bool,
        ):
            raise ValueError(
                "requires_human_verification must be boolean."
            )

        if not isinstance(
            result["supporting_evidence"],
            list,
        ):
            raise ValueError(
                "supporting_evidence must be a list."
            )