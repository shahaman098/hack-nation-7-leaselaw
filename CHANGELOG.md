# Changelog

## 0.5.0

- Generalized HackForge from a hackathon-specific engine into a competition-agnostic strategy and idea-selection engine.
- Added structured competition requirements for technology/platform, data, artifacts, demos, timeboxes, teams, eligibility, tracks, sponsors, and other constraints.
- Separated mandatory technology from encouraged technology and replaced provider-specific candidate fields with generic `technology_roles` and `requirement_satisfaction` maps.
- Reworked hard gates so absent requirements are `not_applicable`; data, demo, track, technology, and delivery constraints block only when the current competition makes them relevant.
- Added credible support for organizer-provided/local/fixture/sensor/user-supplied data rather than requiring public HTTP datasets.
- Reworked feasibility and blind judging to use the actual competition constraints and official judging criteria/weights instead of universal software-hackathon assumptions.
- Removed fixed five-day, solo-builder, sponsor-tech, OpenAI Build Week, GPT-5.6, and Codex entry assumptions from competition logic.
- Broadened ideation lanes and proof modes to support software, hardware, physical prototypes, research, data competitions, pitches, grants, service/process design, and other permitted entry formats.
- Made GitHub, Devpost, FAISS, and semantic collision research optional enrichment by default with explicit strict-mode flags.
- Made default crowding patterns advisory and removed global product-topology bans from isolated ideation.
- Updated diagnostics, environment defaults, documentation, and tests for generic competition operation.
- Pinned mypy below 2.3 so the declared Python 3.9 typing target remains supported.

## 0.4.0

- Added authenticated Codex execution and automatic keyless provider selection.
- Added source-backed competition crawling and public-project collision research.
- Added opportunity/mechanism search, sparse quality-diversity archives, directed mutation,
  fail-closed gates, direct pairwise judging, and three diverse recommendations.
- Added the self-contained idea landscape report and complete search artifacts.
- Added installed-wheel runtime resources, private atomic artifacts, lifecycle journaling,
  crawler SSRF/size safeguards, strict CI typing, and clean-wheel smoke testing.
- Added first-class DeepSeek V4 routing through LiteLLM and DeepSeek-aware diagnostics.
