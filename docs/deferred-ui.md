# Deferred UI

Web and API apps under `apps/web` and `apps/api` are **intentionally deferred**.

Ship a thin local run viewer only after:

1. The CLI pipeline is reliable
2. The baseline benchmark shows better diversity, fewer crowded archetypes, more named datasets, and stronger human preference than naïve “give me ten ideas”

Until then, inspect `runs/<slug>/` artifacts directly.
