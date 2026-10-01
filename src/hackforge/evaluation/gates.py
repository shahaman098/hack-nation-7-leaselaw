from __future__ import annotations

import re

from hackforge.models import CandidateIdea, CompetitionBrief, EvidenceSource, GateResult

REQUIRED_GATES = (
    "evidence_backed",
    "required_technology_fit",
    "requirement_compliance",
    "data_viability",
    "delivery_feasible",
    "demo_fit",
    "specific_track_fit",
)


def evaluate_gates(
    idea: CandidateIdea,
    brief: CompetitionBrief,
    evidence: list[EvidenceSource],
) -> list[GateResult]:
    evidence_by_id = {source.id: source for source in evidence}
    cited = [evidence_by_id[source_id] for source_id in idea.evidence_ids if source_id in evidence_by_id]
    accessible_citations = [source for source in cited if source.fetch_status == "ok" and source.verified]

    results = [
        _result(
            "evidence_backed",
            bool(accessible_citations),
            "At least one cited source was retrieved and verified"
            if accessible_citations
            else "No cited evidence ID resolves to a retrieved verified source",
            [source.id for source in accessible_citations],
        ),
        _technology_gate(idea, brief),
        _requirement_gate(idea, brief),
        _data_gate(idea, brief, accessible_citations),
        _delivery_gate(idea, brief),
        _demo_gate(idea, brief),
        _track_gate(idea, brief),
    ]
    idea.gate_results = results
    return results


def passes_gates(idea: CandidateIdea) -> bool:
    by_name = {result.gate: result for result in idea.gate_results}
    return all(
        by_name.get(name) is not None and by_name[name].status in {"pass", "not_applicable"}
        for name in REQUIRED_GATES
    )


def gate_failures(idea: CandidateIdea) -> list[str]:
    return [result.gate for result in idea.gate_results if result.status in {"fail", "unverified"}]


def _technology_gate(idea: CandidateIdea, brief: CompetitionBrief) -> GateResult:
    required = brief.mandatory_technologies()
    if not required:
        return GateResult(
            gate="required_technology_fit",
            status="not_applicable",
            reason="Competition has no mandatory technology or platform requirement",
        )

    missing: list[str] = []
    decorative: list[str] = []
    for technology in required:
        role = _role_for_technology(idea.technology_roles, technology)
        if not role:
            missing.append(technology)
            continue
        blob = role.lower()
        weak = any(
            phrase in blob
            for phrase in ("optional", "could use", "nice to have", "if time", "decorative", "logo only")
        )
        if len(role.split()) < 6 or weak:
            decorative.append(technology)

    passed = not missing and not decorative
    detail = []
    if missing:
        detail.append("missing material roles: " + ", ".join(missing))
    if decorative:
        detail.append("roles appear non-material: " + ", ".join(decorative))
    if not detail:
        detail.append("every mandatory technology/platform has a material implementation role")
    return _result("required_technology_fit", passed, "; ".join(detail))


def _requirement_gate(idea: CandidateIdea, brief: CompetitionBrief) -> GateResult:
    # Participant eligibility is an operator/preflight concern, not a property of
    # a generated idea. All other mandatory rules may require a concept/submission plan.
    required = [
        requirement
        for requirement in brief.requirements
        if requirement.required and requirement.category != "eligibility"
    ]
    artifact_keys = [f"artifact:{artifact}" for artifact in brief.submission_artifacts]
    if not required and not artifact_keys:
        return GateResult(
            gate="requirement_compliance",
            status="not_applicable",
            reason="No concept-level mandatory requirements or submission artifacts were parsed",
        )

    missing: list[str] = []
    for requirement in required:
        explanation = idea.requirement_satisfaction.get(requirement.id, "").strip()
        if not explanation:
            missing.append(requirement.id)
    for key in artifact_keys:
        if not idea.requirement_satisfaction.get(key, "").strip():
            missing.append(key)

    return _result(
        "requirement_compliance",
        not missing,
        "All concept-level mandatory requirements have an implementation/submission plan"
        if not missing
        else "Missing requirement plans: " + ", ".join(missing),
    )


def _data_gate(
    idea: CandidateIdea,
    brief: CompetitionBrief,
    accessible_citations: list[EvidenceSource],
) -> GateResult:
    requires_data = bool(brief.data_requirements) or any(
        requirement.required and requirement.category == "data" for requirement in brief.requirements
    )
    if not idea.data_sources:
        if requires_data:
            return _result(
                "data_viability",
                False,
                "Competition requires data use but the concept names no credible data source",
            )
        return GateResult(
            gate="data_viability",
            status="not_applicable",
            reason="Concept and competition do not require an external dataset",
        )

    status = _normalize_gate_data_status(idea.data_access_status)
    named_urls = [source for source in idea.data_sources if re.search(r"https?://", source)]
    non_urls = [source for source in idea.data_sources if source not in named_urls]
    cited_urls = {source.url for source in accessible_citations}
    cited_hosts = {_url_host(url) for url in cited_urls}
    verified_urls = [
        url
        for url in named_urls
        if url in cited_urls or (_url_host(url) and _url_host(url) in cited_hosts)
    ]
    urls_ok = len(verified_urls) == len(named_urls)
    non_url_status_ok = status in {
        "verified",
        "available",
        "provided",
        "local",
        "fixture",
        "generated_fixture",
        "synthetic_fixture",
        "sensor",
        "user_supplied",
    }
    non_urls_ok = not non_urls or (non_url_status_ok and bool(idea.data_access_plan.strip()))
    # If non-URL fixture/local access is credible, do not fail solely because a
    # competition resource page URL was blocked by WAF / anti-bot challenges.
    if (
        not urls_ok
        and non_urls_ok
        and non_urls
        and status in {"local", "fixture", "generated_fixture", "synthetic_fixture", "provided", "user_supplied"}
    ):
        urls_ok = True
    passed = urls_ok and non_urls_ok and (bool(named_urls) or bool(non_urls))

    if passed:
        reason = "Named data access is credible for the competition and concept"
    elif named_urls and not urls_ok:
        reason = "One or more public data URLs were not verified against cited evidence"
    else:
        reason = "Non-URL data was named without a credible access status and access plan"
    return _result(
        "data_viability",
        passed,
        reason,
        [source.id for source in accessible_citations],
    )


def _normalize_gate_data_status(status: str) -> str:
    text = (status or "").strip().lower()
    allowed = {
        "verified",
        "available",
        "provided",
        "local",
        "fixture",
        "generated_fixture",
        "synthetic_fixture",
        "sensor",
        "user_supplied",
        "not_required",
        "unverified",
        "not_applicable",
    }
    if text in allowed:
        return text
    first = re.split(r"[\s:;,.]+", text, maxsplit=1)[0]
    if first in allowed:
        return first
    if any(token in text for token in ("fixture", "datapack", "sample data", "quickstart", "synthetic")):
        return "fixture"
    if any(token in text for token in ("user-supplied", "user supplied", "entrant", "team-provided")):
        return "user_supplied"
    if "local" in text or "repository" in text:
        return "local"
    if "provided" in text or "official resource" in text:
        return "provided"
    if "available" in text or "permitted" in text or "viable" in text or "credible" in text:
        return "available"
    return text


def _url_host(url: str) -> str:
    match = re.match(r"https?://([^/]+)/?", url.strip(), flags=re.I)
    return match.group(1).lower() if match else ""


def _delivery_gate(idea: CandidateIdea, brief: CompetitionBrief) -> GateResult:
    constrained = bool(brief.build_window or brief.deadline or brief.team_size) or any(
        requirement.required and requirement.category in {"timebox", "team"}
        for requirement in brief.requirements
    )
    if not constrained:
        return GateResult(
            gate="delivery_feasible",
            status="not_applicable",
            reason="No build-window, deadline, or team delivery constraint was parsed",
        )

    text = idea.minimum_demonstrable_loop.strip()
    blob = text.lower()
    has_sequence = any(
        token in blob
        for token in (
            "build",
            "implement",
            "produce",
            "prepare",
            "train",
            "test",
            "validate",
            "measure",
            "submit",
            "present",
            "prototype",
            "core",
            "output",
        )
    )
    passed = len(text.split()) >= 8 and has_sequence
    constraints = ", ".join(
        value for value in (brief.build_window, brief.deadline, brief.team_size) if value
    )
    return _result(
        "delivery_feasible",
        passed,
        text or f"No delivery plan supplied for constraints: {constraints or 'structured requirement'}",
    )


def _demo_gate(idea: CandidateIdea, brief: CompetitionBrief) -> GateResult:
    if not _brief_requires_demo(brief):
        return GateResult(
            gate="demo_fit",
            status="not_applicable",
            reason="Competition does not require or explicitly score a demo/prototype/presentation proof",
        )
    passed = bool(idea.killer_demo and idea.demo_proof and _observable(idea.demo_proof))
    return _result(
        "demo_fit",
        passed,
        idea.demo_proof or "Competition calls for observable proof but no credible demo/prototype proof was supplied",
    )


def _track_gate(idea: CandidateIdea, brief: CompetitionBrief) -> GateResult:
    if not brief.tracks:
        return GateResult(
            gate="specific_track_fit",
            status="not_applicable",
            reason="Competition has no parsed tracks",
        )
    fit = idea.track_fit.lower().strip()
    passed = any(fit in track.lower() or track.lower() in fit for track in brief.tracks if fit)
    return _result(
        "specific_track_fit",
        passed,
        f"Declared track {idea.track_fit!r}; official tracks: {', '.join(brief.tracks)}",
    )


def _brief_requires_demo(brief: CompetitionBrief) -> bool:
    if brief.demo_requirements:
        return True
    if any(
        requirement.required and requirement.category == "demo" for requirement in brief.requirements
    ):
        return True
    criteria_blob = " ".join(
        f"{criterion.name} {criterion.notes}" for criterion in brief.judging_criteria
    ).lower()
    artifacts_blob = " ".join(brief.submission_artifacts).lower()
    return any(
        token in criteria_blob or token in artifacts_blob
        for token in ("demo", "prototype", "presentation", "pitch", "working project", "video")
    )


def _role_for_technology(roles: dict[str, str], technology: str) -> str:
    wanted = _norm(technology)
    for key, value in roles.items():
        key_norm = _norm(key)
        if wanted == key_norm or wanted in key_norm or key_norm in wanted:
            return value.strip()
    return ""


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _observable(text: str) -> bool:
    blob = text.lower()
    return any(
        token in blob
        for token in (
            "before",
            "after",
            "show",
            "display",
            "emit",
            "measure",
            "compare",
            "change",
            "reduce",
            "increase",
            "prototype",
            "present",
            "demonstrate",
            "result",
        )
    )


def _result(
    gate: str,
    passed: bool,
    reason: str,
    evidence_ids: list[str] | None = None,
) -> GateResult:
    return GateResult(
        gate=gate,
        status="pass" if passed else "fail",
        reason=reason,
        evidence_ids=evidence_ids or [],
    )
