"""Deterministic, versioned medical-safety and editorial review engine."""

import re

from content_os.models.content import ContentDraft, SafetyFinding, SafetyReview
from content_os.models.evidence import EvidenceOutput

SAFETY_RULESET_VERSION = "task-6a-v1"

_PERSONALIZED_INSTRUCTION = re.compile(
    r"\b(?:you have|you are diagnosed with|your diagnosis is|"
    r"you should\s+(?:start|stop|take|avoid|increase|decrease|change))\b",
    re.IGNORECASE,
)
_MEDICATION_DOSE_INSTRUCTION = re.compile(
    r"\b(?:start|stop|take|increase|decrease|change|raise|lower)\b"
    r"[^.\n]{0,80}(?:"
    r"\b\d+(?:\.\d+)?\s*(?:mcg|mg|g|ml|units?)\b"
    r"|"
    r"\b(?:insulin|metformin)\b(?:[^.\n]{0,40}\b(?:dose|dosage)\b)?"
    r"|"
    r"\b(?:medication|medicine)\b[^.\n]{0,40}\b(?:dose|dosage)\b"
    r"|"
    r"\b(?:dose|dosage)\b[^.\n]{0,40}\b(?:medication|medicine)\b)",
    re.IGNORECASE,
)
_ABSOLUTE_CLAIM = re.compile(
    r"\b(?:always|never|completely prevents?|eliminates? the risk)\b",
    re.IGNORECASE,
)
_CURE_OR_GUARANTEE = re.compile(
    r"\b(?:cures?|guaranteed|guarantees?|100\s*% effective)\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")


class MedicalEditorialReviewEngine:
    """Apply a deliberately small, reproducible ruleset to educational content."""

    def review(self, draft: ContentDraft, evidence: EvidenceOutput) -> SafetyReview:
        findings: list[SafetyFinding] = []
        supported_source_ids = {
            source_id
            for claim in evidence.claims
            if claim.structurally_supported
            for source_id in claim.source_ids
        }
        review_text = f"{draft.title}\n{draft.body}"

        if not draft.body.strip() or not supported_source_ids:
            findings.append(
                self._finding(
                    "evidence",
                    "blocking",
                    "no_supported_claims",
                    "Draft has no structurally supported claims.",
                )
            )
        if not draft.cited_source_ids:
            findings.append(
                self._finding(
                    "evidence",
                    "blocking",
                    "missing_citations",
                    "Draft must cite at least one supplied source.",
                )
            )

        unsupported = sorted(set(draft.cited_source_ids) - supported_source_ids)
        if unsupported:
            findings.append(
                self._finding(
                    "evidence",
                    "blocking",
                    "unsupported_source_reference",
                    "Every draft citation must link to structurally supported evidence.",
                    ", ".join(unsupported),
                )
            )

        if "not medical advice" not in draft.disclaimer.lower():
            findings.append(
                self._finding(
                    "medical_safety",
                    "blocking",
                    "missing_disclaimer",
                    "Educational medical disclaimer is required.",
                )
            )

        self._append_pattern_finding(
            findings,
            review_text,
            _PERSONALIZED_INSTRUCTION,
            "medical_safety",
            "blocking",
            "personalized_medical_instruction",
            "Personalized diagnostic or treatment instructions are not permitted.",
        )
        self._append_pattern_finding(
            findings,
            review_text,
            _MEDICATION_DOSE_INSTRUCTION,
            "medical_safety",
            "blocking",
            "medication_dose_instruction",
            "Medication initiation or dose-change instructions are not permitted.",
        )
        self._append_pattern_finding(
            findings,
            review_text,
            _ABSOLUTE_CLAIM,
            "editorial",
            "warning",
            "absolute_medical_claim",
            "Replace absolute medical language with evidence-calibrated wording.",
        )
        self._append_pattern_finding(
            findings,
            review_text,
            _CURE_OR_GUARANTEE,
            "editorial",
            "warning",
            "cure_or_guarantee_language",
            "Cure or guaranteed-outcome language requires editorial revision.",
        )

        unclear_sentence = next(
            (
                sentence.strip()
                for sentence in _SENTENCE.findall(draft.body)
                if len(sentence.split()) > 40
            ),
            None,
        )
        if unclear_sentence:
            findings.append(
                self._finding(
                    "editorial",
                    "warning",
                    "editorial_clarity",
                    "Sentence exceeds 40 words; consider splitting it for a general audience.",
                    unclear_sentence,
                )
            )

        return SafetyReview(
            approved=not any(finding.severity == "blocking" for finding in findings),
            findings=findings,
            ruleset_version=SAFETY_RULESET_VERSION,
        )

    @staticmethod
    def _finding(
        category: str,
        severity: str,
        code: str,
        message: str,
        matched_text: str | None = None,
    ) -> SafetyFinding:
        return SafetyFinding(
            category=category,
            severity=severity,
            code=code,
            message=message,
            matched_text=matched_text,
            ruleset_version=SAFETY_RULESET_VERSION,
        )

    def _append_pattern_finding(
        self,
        findings: list[SafetyFinding],
        body: str,
        pattern: re.Pattern[str],
        category: str,
        severity: str,
        code: str,
        message: str,
    ) -> None:
        match = pattern.search(body)
        if match:
            findings.append(
                self._finding(category, severity, code, message, match.group(0))
            )
