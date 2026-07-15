# HackForge

**A reproducible hackathon research and collision laboratory — not an AI idea chatbot.**

Private decision system for:

- Competition intelligence and crowding blacklists
- Isolated cross-domain ideation lanes
- **FAISS + Devpost corpus collision detection**
- Independent feasibility review
- Blind multi-role judging with disagreement surfaced
- Experimental memory across runs

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,collision]"

cp .env.example .env
# add OPENAI_API_KEY / ANTHROPIC_API_KEY for live LLM passes

# Offline dry-run
hackforge analyse fixtures/sample-hackathon.md --dry-run

# Build local collision corpus + FAISS index (does not commit dumps)
hackforge corpus pull --source local
hackforge corpus build-index --max-records 2000

# Optional large HF pulls (Alpha-Hack / twango / alvanlii / HackRep metadata)
hackforge corpus pull --source all --limit 5000
hackforge corpus build-index

# Collision-only on an existing run
hackforge collide runs/<slug>/ 
hackforge collide runs/<slug>/ --live --llm
```

Outputs land in `runs/YYYY-MM-DD-<slug>/`.

## Collision product surface

| Command | Purpose |
|---------|---------|
| `hackforge corpus pull` | Normalize HF Devpost corpora into `corpora/cache/` |
| `hackforge corpus build-index` | FAISS index under `corpora/indexes/` |
| `hackforge collide` | Dimensional + FAISS (+ optional live) audit |
| `hackforge research winners \| exists` | Live Devpost (Python client) |
| `hackforge eval` | Promptfoo config + baseline benchmark |

**Hard rule:** Alpha-Hack is used as **corpus fuel only**. Its strategy generator is not wired into ideation.

## Providers

Live LLM calls route through **LiteLLM** when `hackforge[collision]` is installed (`HACKFORGE_USE_LITELLM=1`). Dry-run fixtures still work without keys.

## Promptfoo (optional Node)

```bash
brew install node   # once
hackforge eval      # writes evals/promptfoo/ and runs npx promptfoo when available
```

## Langfuse (optional)

```bash
docker compose -f docker-compose.langfuse.yml up -d
# set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST
```

## Pipeline

1. Ingest brief / URL  
2. Competition intelligence + crowding blacklist  
3. Isolated ideation (4 disciplinary lenses)  
4. Normalize + cluster  
5. **Collision engine** — FAISS prefilter → dimensional scores → LLM auditor  
6. Feasibility (+ HackRep stack priors)  
7. Blind multi-role judge  
8. Decision dossier + `run-manifest.json`

## Docs

- [`docs/finalist-evaluation-handbook.md`](docs/finalist-evaluation-handbook.md)
- [`docs/deferred-ui.md`](docs/deferred-ui.md)

## License

Private. All rights reserved.
