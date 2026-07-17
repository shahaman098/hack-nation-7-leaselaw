from __future__ import annotations

import html
import json
from typing import Any

from hackforge.models import (
    CandidateIdea,
    CollisionReport,
    CompetitionBrief,
    EvaluationResult,
    EvidenceSource,
    IdeaLineage,
    MechanismCard,
    OpportunityCard,
)


def build_idea_landscape(
    *,
    brief: CompetitionBrief,
    sources: list[EvidenceSource],
    opportunities: list[OpportunityCard],
    mechanisms: list[MechanismCard],
    archive: dict[str, Any],
    lineage: list[IdeaLineage],
    collisions: list[CollisionReport],
    evaluation: EvaluationResult,
    outputs: list[CandidateIdea],
    rejected: list[dict[str, str]],
) -> str:
    collision_by = {report.candidate_id: report for report in collisions}
    source_rows = "".join(
        "<tr>"
        f"<td>{_e(source.source_kind)}</td><td><a href='{_e(source.url)}'>{_e(source.title or source.url)}</a></td>"
        f"<td><span class='pill {source.fetch_status}'>{_e(source.fetch_status)}</span></td>"
        f"<td>{_e(source.excerpt[:280])}</td></tr>"
        for source in sources
    )
    final_cards = "".join(
        _idea_card(idea, rank, collision_by.get(idea.id)) for rank, idea in enumerate(outputs, 1)
    )
    killed_rows = "".join(
        f"<tr><td><code>{_e(row.get('id', ''))}</code></td><td>{_e(row.get('reason', ''))}</td></tr>"
        for row in rejected
    )
    lineage_rows = "".join(
        f"<tr><td><code>{_e(item.idea_id)}</code></td><td>{_e(', '.join(item.parent_ids) or 'initial')}</td>"
        f"<td>{item.mutation_round}</td><td>{_e(item.mutation_target)}</td></tr>"
        for item in lineage
    )
    coverage = archive.get("occupied_cells", 0)
    payload = {
        "brief": brief.model_dump(),
        "outputs": [idea.model_dump() for idea in outputs],
        "archive": archive,
        "evaluation": evaluation.model_dump(),
    }
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HackForge idea landscape — {_e(brief.name)}</title>
<style>
:root{{--ink:#172033;--muted:#61708a;--paper:#f4f7fb;--card:#fff;--accent:#5b45e0;--line:#dce3ee;--bad:#a93636;--good:#19734c}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 system-ui,-apple-system,sans-serif}}
main{{max-width:1180px;margin:auto;padding:40px 24px 80px}} h1{{font-size:clamp(32px,6vw,64px);line-height:1;margin:.2em 0}}
h2{{margin-top:48px}} .eyebrow{{color:var(--accent);font-weight:750;text-transform:uppercase;letter-spacing:.12em}}
.metrics,.finals{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}} .metric,.idea{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 8px 30px #1d2a4410}}
.metric b{{display:block;font-size:32px}} .rank{{font-size:12px;color:var(--accent);font-weight:800}} .idea h3{{font-size:23px;margin:.25em 0}}
.idea dl{{display:grid;grid-template-columns:115px 1fr;gap:8px;margin:16px 0}} dt{{color:var(--muted)}} dd{{margin:0}}
table{{width:100%;border-collapse:collapse;background:var(--card);border-radius:14px;overflow:hidden}} th,td{{padding:11px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}} th{{color:var(--muted);font-size:12px;text-transform:uppercase}}
.scroll{{overflow:auto}} .pill{{padding:2px 8px;border-radius:99px;background:#e6ebf2}} .pill.ok{{background:#dff5e9;color:var(--good)}} .pill.failed,.pill.blocked{{background:#fae2e2;color:var(--bad)}}
code{{font-size:12px}} a{{color:var(--accent)}} details{{background:var(--card);border:1px solid var(--line);padding:16px;border-radius:14px}}
</style></head><body><main>
<div class="eyebrow">HackForge winning-idea search</div><h1>{_e(brief.name)}</h1>
<p>This report distinguishes retrieved evidence, generated search material, external validation, and final judging. Public projects are collision evidence—not inspiration anchors.</p>
<section class="metrics">
<div class="metric"><b>{len(sources)}</b>research sources</div><div class="metric"><b>{len(opportunities)}</b>opportunity cards</div>
<div class="metric"><b>{len(mechanisms)}</b>mechanism cards</div><div class="metric"><b>{coverage}</b>occupied archive cells</div>
</section>
<h2>Winner and structurally different backups</h2><section class="finals">{final_cards}</section>
<h2>Research evidence</h2><div class="scroll"><table><thead><tr><th>Kind</th><th>Source</th><th>Status</th><th>Excerpt</th></tr></thead><tbody>{source_rows}</tbody></table></div>
<h2>Search lineage</h2><div class="scroll"><table><thead><tr><th>Idea</th><th>Parent</th><th>Round</th><th>Target</th></tr></thead><tbody>{lineage_rows}</tbody></table></div>
<h2>Killed and outcompeted concepts</h2><div class="scroll"><table><thead><tr><th>Idea</th><th>Reason</th></tr></thead><tbody>{killed_rows}</tbody></table></div>
<h2>Archive data</h2><details><summary>Inspect complete machine-readable report data</summary><pre id="data"></pre></details>
<script type="application/json" id="payload">{_json_for_script(payload)}</script>
<script>document.getElementById('data').textContent=JSON.stringify(JSON.parse(document.getElementById('payload').textContent),null,2)</script>
</main></body></html>"""


def _idea_card(idea: CandidateIdea, rank: int, collision: CollisionReport | None) -> str:
    role = "Winner" if rank == 1 else f"Backup {rank - 1}"
    analogue = "No public analogue found"
    if collision and collision.nearest_analogues:
        closest = collision.nearest_analogues[0]
        analogue = f"{closest.name} ({closest.source}); risk {collision.collision_risk}"
    gates = sum(1 for gate in idea.gate_results if gate.status in {"pass", "not_applicable"})
    return (
        f"<article class='idea'><div class='rank'>{role}</div><h3>{_e(idea.working_title)}</h3>"
        f"<p>{_e(idea.visible_transformation)}</p><dl>"
        f"<dt>User</dt><dd>{_e(idea.primary_user)}</dd><dt>Mechanism</dt><dd>{_e(idea.imported_mechanism)}</dd>"
        f"<dt>Action</dt><dd>{_e(idea.last_mile_action)}</dd><dt>Demo</dt><dd>{_e(idea.killer_demo)}</dd>"
        f"<dt>Evidence</dt><dd>{len(idea.evidence_ids)} cited sources</dd><dt>Gates</dt><dd>{gates}/{len(idea.gate_results)} passed</dd>"
        f"<dt>Analogue</dt><dd>{_e(analogue)}</dd></dl></article>"
    )


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _json_for_script(value: object) -> str:
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
