#!/usr/bin/env bash
# Hack-Nation 7 — HackForge idea search (preflight, dry smoke, or live analyse).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
source .venv/bin/activate

MODE="${1:-live}"
BRIEF="${HACKFORGE_BRIEF:-briefs/hack-nation-7-kickoff.md}"
FALLBACK_BRIEF="fixtures/hack-nation-tracks.md"
SKILLS="${HACKFORGE_SKILLS:-Python, FastAPI, LangGraph, RAG, React, TypeScript, AWS; hackathon wins: NVIDIA London, Gemini UI Navigator}"
# Live runs work without the optional collision stack; tests use the same default.
export HACKFORGE_USE_SENTENCE_TRANSFORMERS="${HACKFORGE_USE_SENTENCE_TRANSFORMERS:-0}"
export HACKFORGE_REQUIRE_SEMANTIC_COLLISION="${HACKFORGE_REQUIRE_SEMANTIC_COLLISION:-0}"

brief_is_placeholder() {
  [[ ! -f "$BRIEF" ]] && return 0
  grep -q "PLACEHOLDER" "$BRIEF" 2>/dev/null && return 0
  return 1
}

resolve_brief() {
  if brief_is_placeholder; then
    if [[ "$MODE" == "live" ]]; then
      echo "ERROR: $BRIEF is missing or still has PLACEHOLDER." >&2
      echo "       Paste official HackOS challenge text before: $0 live" >&2
      exit 1
    fi
    echo "WARN: $BRIEF still placeholder — using $FALLBACK_BRIEF for dry smoke only." >&2
    BRIEF="$FALLBACK_BRIEF"
  fi
}

if [[ "$MODE" == "preflight" ]]; then
  echo "==> doctor (codex, strict, live probe)"
  hackforge doctor --provider codex --strict --live
  echo "==> test-fast"
  make test-fast
  echo "==> dry analyse smoke"
  resolve_brief
  hackforge analyse \
    --profile hack-nation \
    --input "$BRIEF" \
    --dry-run --fixture-bundle fixtures/dry-run-bundle.json \
    --search-profile fast \
    --no-visual-report \
    --output-root runs/preflight-dry
  echo "OK: preflight complete. Paste real tracks, then: $0 live"
  exit 0
fi

resolve_brief

SKILLS_ARGS=()
if [[ -n "$SKILLS" ]]; then
  SKILLS_ARGS=(--skills "$SKILLS")
fi

if [[ "$MODE" == "dry" ]]; then
  exec hackforge analyse \
    --profile hack-nation \
    --input "$BRIEF" \
    --dry-run --fixture-bundle fixtures/dry-run-bundle.json \
    --search-profile fast \
    --no-visual-report \
    "${SKILLS_ARGS[@]}"
fi

if [[ "$MODE" == "live" ]]; then
  echo "==> doctor before live analyse"
  hackforge doctor --provider codex --strict --live
  exec hackforge analyse \
    --profile hack-nation \
    --input "$BRIEF" \
    --provider codex \
    --search-profile fast \
    --no-visual-report \
    "${SKILLS_ARGS[@]}"
fi

echo "Usage: $0 preflight|dry|live" >&2
exit 1
