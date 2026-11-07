# SUBMIT NOW — HackOS + Google Form (copy/paste)

**You must be logged in** to [app.hack-nation.ai](https://app.hack-nation.ai) and your Google account.  
Agents cannot click Submit on your behalf without your session.

## Verified links (2026-10-04)

| Field | Value |
|-------|--------|
| **Challenge** | 02 — RealPage: Rental Housing Law Navigator |
| **Project title** | LeaseLaw Navigator |
| **GitHub** | https://github.com/shahaman098/hack-nation-7-leaselaw |
| **Live demo** | https://leaselaw-navigator.onrender.com |
| **Health** | https://leaselaw-navigator.onrender.com/health |
| **Eval API** | https://leaselaw-navigator.onrender.com/api/eval → **5/5**, gold **10/10** |
| **Event ID** (if asked) | `4ee144f2-dd47-4613-9290-cf3e47509011` |
| **Google Form** | https://forms.gle/VnivSgAJ2w5bZyJW9 |

## One-liner

Address-level rental housing law with citations, as-of dates, and deterministic change tracking (T1–T5).

## Long description (HackOS / Form)

LeaseLaw Navigator reads the official RealPage starter corpus, extracts verified rule records (literal quoted spans), resolves 500 sample addresses to applicable rules with an as-of date, and reports change-test address sets. Harness: T1–T5 **5/5**, gold fixtures **10/10**. Outputs: `rules.json`, `lookups.json`, `changes.json`. **Not legal advice.**

## Eval / score summary (paste in form)

```
T1–T5 change tests: 5/5 PASS
Gold benchmarks: 10/10 PASS
Submission JSON: template-shaped lookups (500 addresses) + changes (T1–T5 affected_address_ids)
Rules: 50 extracted · 49/50 literal quoted_span (HOB-ALG-01 link-only evidence gap)
Avg ~8 applicable rule rows per address (post noise cleanup)
Official score.py: not in participant pack — harness panel on /api/eval
```

## Videos (required — fill before submit)

Upload **Team**, **Demo**, **Technical** MP4 to YouTube/Drive (unlisted OK), then paste URLs:

| Slot | Local path (after `bash scripts/video/run_all.sh`) |
|------|------------------------------------------------------|
| Team | `docs/hn7-submission-pack/videos/out/final/hn7-team.mp4` |
| Demo | `docs/hn7-submission-pack/videos/out/final/hn7-demo.mp4` |
| Technical | `docs/hn7-submission-pack/videos/out/final/hn7-technical.mp4` |

**Team name:** _[your HackOS team name — create solo team if needed]_

**Video Team URL:** _______________  
**Video Demo URL:** _______________  
**Video Technical URL:** _______________

## HackOS checklist

1. https://app.hack-nation.ai → create/join team (solo OK)
2. Select challenge **02 RealPage**
3. Paste GitHub + live URL above
4. Upload or link three videos
5. Submit project
6. Then complete Google Form (same URLs)

## Google Form

Open: https://forms.gle/VnivSgAJ2w5bZyJW9  
Paste the same GitHub, live URL, video links, and eval summary.

---

**Disclaimer (include if there is a notes field):** Not legal advice. Demo/research prototype for Hack-Nation 7 Track 02.
