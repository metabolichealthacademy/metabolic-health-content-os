"""Deterministic, versioned medical-safety and editorial review engine."""

import re

from content_os.models.content import ContentDraft, SafetyFinding, SafetyReview
from content_os.models.evidence import EvidenceOutput

SAFETY_RULESET_VERSION = "task-6a-v1"
_MEDICATION_NAME = r"(?:insulin|metformin)"
_MEDICATION_MODIFIER = (
    r"(?:basal|bolus|rapid(?:-acting)?|long(?:-acting)?|short(?:-acting)?|"
    r"extended(?:-release)?|immediate(?:-release)?)"
)
_MEDICATION_MODIFIERS = rf"(?:(?:{_MEDICATION_MODIFIER})\s+){{0,2}}"
_OPENING_PUNCTUATION = r"(?:[\"'“”‘’(\[]\s*)*"
_IMPERATIVE_LEAD_IN = r"(?:(?:[-*•]|\d+[.)])\s+)?(?:(?:then|next|now)\s+)?(?:please\s+)?"
_IMPERATIVE_PREFIX = (
    rf"(?:(?<=^)|(?<=[.!?]\s)|(?<=\n)|(?<=,\s)|(?<=:\s)|(?<=;\s))"
    rf"{_OPENING_PUNCTUATION}{_IMPERATIVE_LEAD_IN}"
)

_PERSONALIZED_INSTRUCTION = re.compile(
    r"\b(?:you have|you are diagnosed with|your diagnosis is|"
    r"you should\s+(?:start|stop|take|avoid|increase|decrease|change))\b",
    re.IGNORECASE,
)
_MEDICATION_DOSE_INSTRUCTION = re.compile(
    rf"(?:"
    rf"(?:start|stop|take|increase|decrease|change|raise|lower)\b"
    rf"[^.\n]{{0,80}}\b\d+(?:\.\d+)?\s*(?:mcg|mg|g|ml|units?)\b"
    rf"|{_IMPERATIVE_PREFIX}(?:start|stop|take)\s+"
    rf"(?:your\s+|the\s+)?{_MEDICATION_MODIFIERS}{_MEDICATION_NAME}\b"
    rf"|{_IMPERATIVE_PREFIX}(?:increase|decrease|change|raise|lower)\s+"
    rf"(?:your\s+|the\s+)?"
    rf"(?:{_MEDICATION_MODIFIERS}{_MEDICATION_NAME}(?:\s+(?:dose|dosage))?|dose|dosage)\b"
    rf")",
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
        scan_fields = (draft.title, draft.body)
        supported_source_ids = {
            source_id
            for claim in evidence.claims
            if claim.structurally_supported
            for source_id in claim.source_ids
        }
        has_supported_citations = bool(set(draft.cited_source_ids) & supported_source_ids)

        if not draft.body.strip():
            findings.append(
                self._finding(
                    "evidence",
                    "blocking",
                    "no_supported_claims",
                    "Draft body is empty.",
                )
            )
        elif draft.cited_source_ids and not has_supported_citations:
            findings.append(
                self._finding(
                    "evidence",
                    "blocking",
                    "no_supported_claims",
                    "Draft has no structurally supported claims.",
                )
            )
        elif not supported_source_ids:
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

        personalized_match = self._first_match(_PERSONALIZED_INSTRUCTION, *scan_fields)
        if personalized_match:
            findings.append(
                self._finding(
                    "medical_safety",
                    "blocking",
                    "personalized_medical_instruction",
                    "Personalized diagnostic or treatment instructions are not permitted.",
                    personalized_match.group(0),
                )
            )

        medication_match = self._first_match(
            _MEDICATION_DOSE_INSTRUCTION, *scan_fields
        )
        if medication_match:
            findings.append(
                self._finding(
                    "medical_safety",
                    "blocking",
                    "medication_dose_instruction",
                    "Medication initiation or dose-change instructions are not permitted.",
                    medication_match.group(0),
                )
            )
        absolute_claim_match = self._first_match(_ABSOLUTE_CLAIM, *scan_fields)
        if absolute_claim_match:
            findings.append(
                self._finding(
                    "editorial",
                    "warning",
                    "absolute_medical_claim",
                    "Replace absolute medical language with evidence-calibrated wording.",
                    absolute_claim_match.group(0),
                )
            )

        cure_or_guarantee_match = self._first_match(_CURE_OR_GUARANTEE, *scan_fields)
        if cure_or_guarantee_match:
            findings.append(
                self._finding(
                    "editorial",
                    "warning",
                    "cure_or_guarantee_language",
                    "Cure or guaranteed-outcome language requires editorial revision.",
                    cure_or_guarantee_match.group(0),
                )
            )

        unclear_sentence = next(
            (
                sentence.strip()
                for text in scan_fields
                for sentence in _SENTENCE.findall(text)
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

    @staticmethod
    def _first_match(
        pattern: re.Pattern[str], *texts: str
    ) -> re.Match[str] | None:
        for text in texts:
            match = pattern.search(text)
            if match:
                return match
        return None
