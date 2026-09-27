import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai


class InvestigationReasoner:
    """
    Gemini-powered reasoning layer.

    Deterministic investigation establishes the evidence.
    Gemini interprets that evidence.

    A deterministic fallback remains available for tests.

    Confidence is calibrated after Gemini responds so the model
    cannot claim stronger certainty than the evidence supports.
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
            result = self._reason_with_gemini(
                investigation
            )

            return self._calibrate_confidence(
                result,
                investigation,
            )

        return self._reason_deterministically(
            investigation
        )

    def _reason_deterministically(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:

        findings = investigation["findings"]
        evidence_items = investigation["evidence"]

        # ---------------------------------------------------------
        # 1. Detect documented waiver / approved substitution.
        # ---------------------------------------------------------
        approved_exception_events = [
            evidence
            for evidence in evidence_items
            if evidence.get("type") == "OPERATIONAL_EVENT"
            and evidence.get("status") in {"APPROVED", "CLOSED"}
            and any(
                marker in str(
                    evidence.get("description", "")
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

        has_grade_mismatch = any(
            finding.get("type") == "GRADE_MISMATCH"
            for finding in findings
        )

        # ---------------------------------------------------------
        # LEGITIMATE_EXCEPTION takes priority over the mismatch.
        # ---------------------------------------------------------
        if has_grade_mismatch and approved_exception_events:
            bundle_ids = [
                evidence["bundle_id"]
                for evidence in evidence_items
                if evidence.get("type") == "PHYSICAL_BUNDLE"
                and evidence.get("bundle_id")
            ]

            event_ids = [
                evidence["event_id"]
                for evidence in approved_exception_events
                if evidence.get("event_id")
            ]

            return {
                "conclusion": "LEGITIMATE_EXCEPTION",
                "confidence": 0.95,
                "requires_human_verification": False,
                "reason": (
                    "The apparent composition-grade mismatch is covered by "
                    "a documented approved substitution or waiver."
                ),
                "evidence_gap": None,
                "recommended_action": (
                    "Proceed under the documented approved exception."
                ),
                "supporting_evidence": bundle_ids + event_ids,
            }

        # ---------------------------------------------------------
        # 2. Insufficient evidence.
        # ---------------------------------------------------------
        has_insufficient_evidence = any(
            finding.get("type") == "INSUFFICIENT_EVIDENCE"
            for finding in findings
        )

        if has_insufficient_evidence:
            return {
                "conclusion": "INSUFFICIENT_EVIDENCE",
                "confidence": 0.60,
                "requires_human_verification": True,
                "reason": (
                    "The available operational records do not contain enough "
                    "physical-bundle evidence to establish loading suitability."
                ),
                "evidence_gap": (
                    "Physical bundle selection or dispatch evidence is required "
                    "to verify the material, quantity, and composition requirement."
                ),
                "recommended_action": (
                    "Verify which physical bundles were selected or sent to "
                    "logistics before loading proceeds."
                ),
                "supporting_evidence": [],
            }

        # ---------------------------------------------------------
        # 3. Unresolved operational findings.
        # ---------------------------------------------------------
        has_traceability_gap = any(
            finding.get("type") == "TRACEABILITY_GAP"
            for finding in findings
        )

        has_requirement_gap = any(
            finding.get("type") == "REQUIREMENT_UNSATISFIED"
            for finding in findings
        )

        if (
            has_traceability_gap
            or has_grade_mismatch
            or has_requirement_gap
        ):
            return {
                "conclusion": "UNRESOLVED",
                "confidence": 0.70,
                "requires_human_verification": True,
                "reason": (
                    "The investigation identified an operational inconsistency "
                    "that cannot be cleared from the available evidence."
                ),
                "evidence_gap": (
                    "Additional operational verification is required to resolve "
                    "the identified discrepancy."
                ),
                "recommended_action": (
                    "Verify the affected bundle, batch, requirement, or supporting "
                    "authorization before loading."
                ),
                "supporting_evidence": [],
            }

        # ---------------------------------------------------------
        # 4. No exception.
        # ---------------------------------------------------------
        bundle_ids = [
            evidence["bundle_id"]
            for evidence in evidence_items
            if evidence.get("type") == "PHYSICAL_BUNDLE"
            and evidence.get("bundle_id")
        ]

        return {
            "conclusion": "NO_EXCEPTION",
            "confidence": 0.95,
            "requires_human_verification": False,
            "reason": (
                "The available operational evidence supports the loading "
                "requirement with no identified exception."
            ),
            "evidence_gap": None,
            "recommended_action": "Proceed with the normal loading workflow.",
            "supporting_evidence": bundle_ids,
        }

    def _reason_with_gemini(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:

        prompt = self._build_prompt(
            investigation
        )

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

        return f"""
You are TRACE, a manufacturing loading investigation agent.

The deterministic investigation engine has already collected
operational evidence.

Your job is to reason over that evidence.

Possible conclusions:

1. NO_EXCEPTION
   The evidence establishes that the loading requirement is satisfied
   and no discrepancy requiring investigation remains.

2. LEGITIMATE_EXCEPTION
   An apparent discrepancy exists, but an explicit documented waiver,
   approved substitution, or equivalent operational authorization
   explains it.

3. UNRESOLVED
   A discrepancy exists and the available evidence does not establish
   that it has been legitimately resolved.

4. INSUFFICIENT_EVIDENCE
   The evidence needed to make a reliable determination is missing.

Rules:

- Never invent evidence.
- Never assume quantity alone means a bundle is suitable.
- Trace material -> batch -> grade -> physical bundle.
- Treat explicit operational waivers as evidence.
- Do not treat a missing waiver as proof that a substitution is invalid;
  classify the situation as unresolved or insufficient evidence.
- Do not authorize physical loading.
- Do not modify ERP records.
- If evidence is complete and consistent, use NO_EXCEPTION.
- If evidence is incomplete, do not claim NO_EXCEPTION.

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

INVESTIGATION DATA:

{json.dumps(investigation, indent=2, default=str)}
"""

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
                and "approved substitute"
                in item.get("description", "").lower()
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
                has_mismatch
                or has_traceability_gap
                or has_requirement_gap
            ):
                result["conclusion"] = "UNRESOLVED"
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
                    0.50,
                )

        result["confidence"] = round(
            confidence,
            2,
        )

        return result

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