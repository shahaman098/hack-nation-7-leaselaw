# HackForge

**A reproducible hackathon research and idea-selection laboratory — not an AI idea chatbot.**

Private decision system for:

- Competition intelligence and crowding blacklists
- Isolated cross-domain ideation lanes
- Structural collision detection
- Independent feasibility review
- Blind multi-role judging with disagreement surfaced
- Experimental memory across runs

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Optional: wire providers for live LLM passes
cp .env.example .env
# edit .env with OPENAI_API_KEY and/or ANTHROPIC_API_KEY

# Dry-run (fixtures / no API keys)
hackforge analyse fixtures/sample-hackathon.md --dry-run

# Live analysis
hackforge analyse path/to/hackathon.md
hackforge analyse --url https://example.com/hackathon
```

Outputs land in `runs/YYYY-MM-DD-<slug>/`.

## Pipeline

1. **Ingest** — markdown file, pasted brief, or URL
2. **Competition intelligence** — facts vs inference; crowding map; blacklist
3. **Isolated ideation** — four disciplinary lenses, no cross-lane leakage
4. **Normalize + cluster** — compare structures, not marketing names
5. **Collision audit** — same user / problem / mechanism / data / action / demo
6. **Feasibility** — independent of the ideation model’s self-assessment
7. **Blind judging** — Candidates A/B/C; surface role disagreement
8. **Export** — primary + backup decision dossier + `run-manifest.json`

## Baseline benchmark

```bash
hackforge benchmark evals/benchmark-hackathons/ --dry-run
```

Compares a naïve “give me ten winning ideas” baseline against the full pipeline.

## Layout

See repository tree: `src/hackforge/`, `prompts/`, `schemas/`, `corpora/`, `evals/`, `runs/`.

## Non-goals (v1)

No auth, billing, teams, or polished SaaS UI. Thin local viewer only after the pipeline beats the baseline.

## Docs

- [`docs/finalist-evaluation-handbook.md`](docs/finalist-evaluation-handbook.md) — post-shortlist evaluation only
- [`docs/deferred-ui.md`](docs/deferred-ui.md) — web UI deferral note

## License

Private. All rights reserved.
