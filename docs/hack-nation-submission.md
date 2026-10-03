# Hack-Nation 7 submission kit (HackForge)

Submit **this repository** as the project: a meta hackathon intelligence CLI, not a single vertical app.

## Demo script (~3 minutes)

1. **Problem (20s):** Hackathons publish tracks and judging weights; most “idea bots” ignore verified winners and clone crowded chat wrappers.
2. **Paste tracks (30s):** Open `fixtures/hack-nation-tracks.md` (swap for kickoff text at event time).
3. **Run (show terminal):**

```bash
source .venv/bin/activate
hackforge analyse \
  --profile hack-nation \
  --input fixtures/hack-nation-tracks.md \
  --provider codex \
  --search-profile fast \
  --no-visual-report
```

4. **Artifacts (90s):** Walk through the run folder:
   - `verified-research.md` / `competition-brief.json` — parsed criteria
   - `winner-patterns.json` — patterns from `corpora/verified-winners/seed.jsonl`
   - `final-recommendation.md` — winner + backups; scroll to **Winner inspiration**
   - `inspiration-report.json` — user/problem/mechanism scores vs cited winners
5. **Close (20s):** “We adapt patterns above the 30% threshold; clone guard fires if all three dimensions align too closely.”

**Fixture dry-run (no API):**

```bash
hackforge analyse \
  --profile hack-nation \
  --input fixtures/hack-nation-tracks.md \
  --dry-run --fixture-bundle fixtures/dry-run-bundle.json \
  --search-profile fast --no-visual-report
```

## Devpost draft

**Title:** HackForge — track analysis with verified winner adaptation

**Tagline:** Paste any hackathon’s tracks; get one winner and two backups grounded in organizer-verified winner patterns—not another chat wrapper.

**What it does**

- Ingests official track text or URLs into a structured competition brief.
- Mines reusable patterns from a curated verified-winner corpus (`corpora/verified-winners/seed.jsonl`).
- Runs sparse quality-diversity ideation, gates, optional collision evidence, and blind judging.
- Scores finalists on **user + problem + mechanism** inspiration vs past winners (`HACKFORGE_INSPIRATION_MIN=0.30`) with a clone guard.

**Built with:** Python, Codex/DeepSeek providers, optional sentence-transformers for collision/MMR.

**Try it:** Clone repo, `pip install -e ".[dev]"`, `hackforge doctor --provider codex --live`, then the analyse command above.

**Video:** Record the demo script; link in Devpost.

## Checklist before submit

- [ ] Replace `fixtures/hack-nation-tracks.md` with official kickoff text if it differs
- [ ] One live `hackforge analyse` run saved under `runs/`
- [ ] Public repo + Apache-2.0 LICENSE
- [ ] Demo video uploaded
- [ ] Devpost form completed (you click Submit)
