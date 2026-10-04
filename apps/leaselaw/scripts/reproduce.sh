#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -q -r requirements.txt
export LEASELAW_OFFLINE=1
python3 -m src.llm_extract --offline
python3 -m src.export_outputs
python3 -m src.eval_harness
python3 -m pytest tests -q
