from __future__ import annotations

import re

from hackforge.models import CandidateIdea, CompetitionBrief, EvidenceSource, GateResult

REQUIRED_GATES = (
    "evidence_backed",
    "data_accessible_and_verified",
    "required_model_is_material",
    "codex_role_is_material",
    "solo_five_day_loop",
    "observable_demo_proof",
    "specific_track_fit",
    "testable_claim",
)


def evaluate_gates(
    idea: CandidateIdea,
    brief: CompetitionBrief,
    evidence: list[EvidenceSource],
) -> list[GateResult]:
    evidence_by_id = {source.id: source for source in evidence}
    cited = [evidence_by_id[source_id] for source_id in idea.evidence_ids if source_id in evidence_by_id]
    accessible_citations = [source for source in cited if source.fetch_status == "ok" and source.verified]
    build_week = _is_build_week(brief)

    results = [
        _result(
            "evidence_backed",
            bool(accessible_citations),
            "At least one cited source was retrieved and verified"
            if accessible_citations
            else "No cited evidence ID resolves to a retrieved verified source",
            [source.id for source in accessible_citations],
        ),
        _data_gate(idea, accessible_citations),
        _material_role_gate(
            "required_model_is_material",
            idea.gpt_5_6_role,
            required=build_week,
            required_terms=("gpt-5.6", "reason", "infer", "transform", "evaluate", "classif", "extract"),
            label="GPT-5.6",
        ),
        _material_role_gate(
            "codex_role_is_material",
            idea.codex_build_role,
            required=build_week,
            required_terms=("codex", "build", "test", "implement", "session", "debug"),
            label="Codex",
        ),
        _result(
            "solo_five_day_loop",
            _credible_five_day_loop(idea.minimum_demonstrable_loop),
            idea.minimum_demonstrable_loop or "No minimum demonstrable loop supplied",
        ),
        _result(
            "observable_demo_proof",
            bool(idea.killer_demo and idea.demo_proof and _observable(idea.demo_proof)),
            idea.demo_proof or "No observable or measurable demo result supplied",
        ),
        _track_gate(idea, brief),
        _result(
            "testable_claim",
            bool(idea.testable_claim and _testable(idea.testable_claim)),
            idea.testable_claim or "No falsifiable claim supplied",
        ),
    ]
    idea.gate_results = results
    return results


def passes_gates(idea: CandidateIdea) -> bool:
    by_name = {result.gate: result for result in idea.gate_results}
    return all(by_name.get(name) is not None and by_name[name].status in {"pass", "not_applicable"} for name in REQUIRED_GATES)


def gate_failures(idea: CandidateIdea) -> list[str]:
    return [result.gate for result in idea.gate_results if result.status in {"fail", "unverified"}]


def _data_gate(idea: CandidateIdea, accessible_citations: list[EvidenceSource]) -> GateResult:
    status = idea.data_access_status.strip().lower()
    named_urls = [source for source in idea.data_sources if re.search(r"https?://", source)]
    cited_urls = {source.url for source in accessible_citations}
    verified_urls = [url for url in named_urls if url in cited_urls]
    verified = status == "verified" and bool(verified_urls) and len(verified_urls) == len(named_urls)
    passed = bool(idea.data_sources) and verified
    if verified:
        reason = "Every named data URL exactly matches retrieved, verified cited evidence"
    else:
        reason = "Named data was not verified against retrieved evidence; synthetic or proposed data is rejected"
    return _result(
        "data_accessible_and_verified",
        passed,
        reason,
        [source.id for source in accessible_citations],
    )


def _material_role_gate(
    gate: str,
    role: str,
    *,
    required: bool,
    required_terms: tuple[str, ...],
    label: str,
) -> GateResult:
    if not required:
        return GateResult(gate=gate, status="not_applicable", reason=f"{label} is not mandatory for this brief")
    blob = role.lower()
    hits = sum(1 for term in required_terms if term in blob)
    decorative = any(phrase in blob for phrase in ("optional", "could use", "chat interface", "generate copy"))
    passed = len(role.split()) >= 8 and hits >= 2 and not decorative
    return _result(gate, passed, role or f"No material {label} role supplied")


def _track_gate(idea: CandidateIdea, brief: CompetitionBrief) -> GateResult:
    if not brief.tracks:
        return GateResult(gate="specific_track_fit", status="not_applicable", reason="Competition has no parsed tracks")
    fit = idea.track_fit.lower().strip()
    passed = any(fit in track.lower() or track.lower() in fit for track in brief.tracks if fit)
    return _result(
        "specific_track_fit",
        passed,
        f"Declared track {idea.track_fit!r}; official tracks: {', '.join(brief.tracks)}",
    )


def _credible_five_day_loop(text: str) -> bool:
    blob = text.lower()
    has_timebox = any(token in blob for token in ("day 1", "day one", "five-day", "5-day", "days 2", "day 5"))
    has_loop = any(token in blob for token in ("fixture", "input", "transform", "core", "output", "demo", "metric", "test"))
    return len(text.split()) >= 10 and has_timebox and has_loop


def _observable(text: str) -> bool:
    blob = text.lower()
    return any(token in blob for token in ("before", "after", "show", "display", "emit", "measure", "compare", "change", "reduce", "increase"))


def _testable(text: str) -> bool:
    blob = text.lower()
    return any(token in blob for token in ("than", "%", "measure", "accuracy", "time", "fewer", "more", "reduce", "increase", "baseline"))


def _is_build_week(brief: CompetitionBrief) -> bool:
    blob = " ".join(
        [brief.name, brief.theme, *brief.source_urls, *brief.required_or_encouraged_tech]
    ).lower()
    return "build week" in blob or "openai.devpost.com" in blob


def _result(gate: str, passed: bool, reason: str, evidence_ids: list[str] | None = None) -> GateResult:
    return GateResult(
        gate=gate,
        status="pass" if passed else "fail",
        reason=reason,
        evidence_ids=evidence_ids or [],
    )
