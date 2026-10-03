# Winner verification notes

## fal × Sequoia video hackathon (verified 2026-10-03, first place only)

fal's official X account quote-tweeted the creator's Pamplemousse post naming it
"the first place winner" (https://x.com/fal/status/2079046655354302714, fetched);
christianluoma.com self-confirms ("winner of Fal x Sequoia hackathon"). No other
placement was ever published: the organizer recap promised winner posts that never
named projects, all public Cerebral Valley gallery URLs 404 (gallery is
login-gated per its API payload), fal's blog/events pages have nothing, and
Wayback has no snapshots. Winner denominator = first place only, documented in
`cases.json`. Description fields use fetched evidence only (creator post text,
hashtags, YouTube title); the Seedance 2 model attribution comes from the
creator's #seedance2 hashtag and is flagged as an inference.

## UK Parliament / EasyA (searched exhaustively 2026-10-03: UNVERIFIED)

No fetched page names any winning project. Eventbrite page is password-walled
post-event; EasyA's own site never published an event page (live + Wayback);
easya.devpost.com is 404 and Devpost's search API has no such hackathon (the
Devpost premise was wrong for this event); Genfinity published only the Aug 11
preview; crypto press has nothing; @easya_app's X timeline is reachable only for
Sep 30+ posts. If an official list exists, it is on EasyA's authenticated social
channels around 2026-09-04/05. Case remains `verified: false` and blocked.

## HackNation first-place descriptions (researched 2026-10-03, afternoon)

Placement evidence remains the organizer Instagram carousel (below). Description
evidence per first-place team, from pages actually fetched:

| Project | Description source (fetched) | Fields covered | Win tie |
| --- | --- | --- | --- |
| Haggl | https://haggl.ai | user/problem/mechanism: merchant-side agent-negotiation (embed script + `haggl-negotiate` meta tag exposing WebMCP tools/MCP server, DKIM-signed buyer evidence, per-segment ceiling, 10% fee) | organizer carousel + name/theme match only |
| Meridian | https://github.com/ThonyAnt/vc-brain | user/problem/mechanism: fund graph + reasoning layer for VC decisions; README states "1st place submission (VC track) at the 6th Global AI Hackathon" | self-cited on fetched page |
| RealDoor | https://devpost.com/software/realdoor + https://hack-nation-drab.vercel.app | user/problem/mechanism: LIHTC application-readiness copilot (allowlisted LLM extraction, deterministic HUD MTSP income math, human decides) | live domain contains hack-nation; Devpost page itself lists only OpenAI Build Week |
| Vera AI | (team member LinkedIn post confirms win + team only) | NONE — no user/problem/mechanism source found | organizer carousel + LinkedIn |
| Amira | team member LinkedIn post (fetched, names 1st place in the challenge) | user/problem only; mechanism UNKNOWN beyond label | self-cited on fetched page |
| Ambr | https://ambr-genome.com | user/problem/mechanism: FASTA resistance prediction, gene-traced calls, LIKELY_WORK/LIKELY_FAIL/NO_CALL fails closed | organizer carousel + challenge match; site never names HackNation |

Conclusion: with Vera AI undescribed and Amira's mechanism unknown, the
six-winner denominator is still not fully evidenced. `hack-nation` remains
`verified: false` and stays blocked from the live batch. The Devpost gallery
remains unpublished ("The hackathon managers haven't published this gallery
yet").

## HackNation (reviewed 2026-10-03)

Official source: https://www.instagram.com/p/DblRB9sCPQd

The organizer's six carousel podium images were retrieved and visually reviewed.
The caption says six winning teams; each challenge image actually shows three
places. The transcription below preserves that distinction rather than silently
choosing a denominator:

| Challenge | First | Second | Third |
| --- | --- | --- | --- |
| The Negotiator | Haggl | Pacta – AI Negotiator Infrastructure | Handshake |
| The VC Brain | Meridian – Your AI VC Copilot | FirstSignal: Centralized Venture Capital Brain | AiriBrain – the AI Brain for VC |
| RealDoor – Application-Readiness Copilot | RealDoor – Affordable Housing Made Simple | RealDoor Application Readiness Journey | RealDoor_V1 |
| Data Legend: Building the Trust Layer for Indian Healthcare | Vera AI – The Trust Layer for Indian Healthcare Systems | Savife | CareAxiom |
| Foundation Models for Women's Hormonal Health | Amira: Evidence Intelligence Platform | Infradian | Project not named; participant Fatin Amanina Azis |
| Genome Firewall: an AI Defense System against Superbugs | Ambr – AI Model for Bacterial Resistances | AMRShield Sentinel: Project Genome Firewall | Gatcha |

This resolves the previously inaccessible names, **not** the benchmark case.
Project descriptions establishing user/problem/mechanism are still required;
the sponsor challenge alone is not evidence of each implementation's mechanism.
An all-podium denominator also needs the unnamed third-place project resolved.
Keep `verified=false` until these requirements and the winner definition are
settled before a confirmatory run. No training-cutoff claim follows from these
images or their publication date.
