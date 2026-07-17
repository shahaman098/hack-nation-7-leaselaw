# Security policy

## Supported version

Security fixes are applied to the latest 0.4.x release line.

## Reporting

Do not open a public issue containing API keys, competition-private materials, Codex session
content, or generated run artifacts. Report the smallest reproducible description to the
repository owner through a private channel and rotate any credential that may have appeared
in logs or artifacts.

## Trust boundaries

- Competition pages, linked pages, repositories, and corpora are untrusted data.
- HackForge does not follow instructions found inside retrieved content.
- The crawler permits public HTTP(S) destinations only and blocks local/private/reserved IPs,
  credential-bearing URLs, oversized pages, and cross-host crawl expansion.
- Codex runs are ephemeral and use the read-only sandbox.
- Run outputs may contain competition-private data. They are private by default and ignored
  by Git, but operators remain responsible for backups, sharing, and deletion.

HackForge ranks ideas; it does not guarantee a prize and must not be used as the sole basis
for medical, legal, financial, safety-critical, or eligibility decisions.
