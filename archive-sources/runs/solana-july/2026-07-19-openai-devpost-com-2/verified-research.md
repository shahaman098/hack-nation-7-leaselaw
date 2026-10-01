# Verified research: OpenAI Build Week

## Facts
- [high] Registration runs July 9, 2026 10:00 PT to July 21, 2026 17:00 PT; submission period runs July 13, 2026 09:00 PT to July 21, 2026 17:00 PT. _(source: https://openai.devpost.com/rules)_
- [high] The schedule page lists submissions ending July 21, 2026 17:00 PDT, judging July 22, 2026 09:00 PDT to August 09, 2026 17:00 PDT, and winners announced August 12, 2026 14:00 PDT. _(source: https://openai.devpost.com/details/dates)_
- [high] The official rules list judging as July 22, 2026 10:00 PT to August 5, 2026 17:00 PT, creating a discrepancy with the schedule page. _(source: https://openai.devpost.com/rules)_
- [high] Eligible entrants include individuals at least the age of majority in their residence, eligible teams, and eligible organizations in OpenAI API-supported countries or territories, subject to exclusions. _(source: https://openai.devpost.com/rules)_
- [high] Excluded entrants include unsupported or prohibited jurisdictions, including examples Brazil, Quebec, Russia, Crimea, Cuba, Iran, North Korea, Syria, and other OFAC-designated countries, plus promotion entities, judges, related affiliates, and conflicts of interest. _(source: https://openai.devpost.com/rules)_
- [high] Projects must be built with Codex and GPT-5.6 and fit one of four tracks: Apps for Your Life, Work and Productivity, Developer Tools, or Education. _(source: https://openai.devpost.com/rules)_
- [high] Submitted projects must install and run consistently on their intended platform and function as shown in the demo or described in text. _(source: https://openai.devpost.com/rules)_
- [high] Pre-existing projects are allowed only if meaningfully extended using Codex and/or GPT-5.6 after the submission period start; prior work versus new work must be documented with evidence such as logs or commit history. _(source: https://openai.devpost.com/rules)_
- [high] Third-party SDKs, APIs, and data are allowed only when the entrant is authorized to use them under applicable terms or licenses. _(source: https://openai.devpost.com/rules)_
- [high] Submission requires a text description, category, demo video under three minutes, public YouTube link, code repository URL, README, and /feedback Codex Session ID. _(source: https://openai.devpost.com/rules)_
- [high] The demo video must include a clear demo with audio covering what was built and how Codex and GPT-5.6 were used; judges are not required to watch beyond three minutes. _(source: https://openai.devpost.com/rules)_
- [high] Judges may test the project but are not required to; they may judge solely from submission text, images, and video. _(source: https://openai.devpost.com/rules)_
- [high] For plugins or developer tools, submissions must include installation instructions, supported platforms, and a testing path such as a demo instance, sandbox, or test account. _(source: https://openai.devpost.com/rules)_
- [high] The README guidance says Codex collaboration, workflow acceleration, key decisions, and GPT-5.6/Codex contributions are important to Technical Implementation and Quality of the Idea judging. _(source: https://openai.devpost.com/rules)_
- [high] Stage One is a pass/fail viability screen for theme fit and use of required APIs/SDKs; Stage Two uses equally weighted criteria: Technological Implementation, Design, Potential Impact, and Quality of the Idea. _(source: https://openai.devpost.com/rules)_
- [high] Tie-breaks compare the tied submissions by the first listed criterion, then subsequent criteria, then judge vote if still tied. _(source: https://openai.devpost.com/rules)_
- [high] The Devpost Hackathons Plugin is optional and is explicitly not the official source of hackathon information; official rules, website, updates, and notices prevail. _(source: https://openai.devpost.com/rules)_
- [medium] The resources page says all available $100 Codex credits had been given out, while participants could still join using the free tier. _(source: https://openai.devpost.com/resources)_
- [high] The resources page encourages starting with the problem, keeping the repo testable, recording the demo as work progresses, and watching credit usage. _(source: https://openai.devpost.com/resources)_
- [high] The FAQ says each project can be entered into only one track and entrants should choose the closest match. _(source: https://openai.devpost.com/details/faqs)_
- [medium] The FAQ says Free plan users can participate and have access to GPT-5.6 Terra in Codex; GPT-5.6 need only be used for part of the project. _(source: https://openai.devpost.com/details/faqs)_
- [medium] OpenAI Help says GPT-5.6 in Codex includes Terra for Free and Go, and Sol, Terra, and Luna for Plus, Pro, Business, and Enterprise, while OpenAI API availability includes Sol, Terra, and Luna. _(source: https://help.openai.com/en/articles/20001354-gpt-56-in-chatgpt)_
- [medium] OpenAI Help describes Codex as an AI coding agent that can help write, review, and ship code, including pairing locally or delegating work in the cloud. _(source: https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan.pdf)_
- [medium] OpenAI Help describes Codex CLI as a command-line coding agent that can read, modify, and run code locally, with multimodal inputs and an approvals workflow. _(source: https://help.openai.com/en/articles/11096431)_
- [high] The project gallery page had not been published at browse time, so no current submissions, finalists, or winners were available there. _(source: https://openai.devpost.com/project-gallery)_

## Inference
- Technical Implementation is strategically the most important criterion despite equal weights because it is the first tie-break criterion and is reinforced by required Codex/GPT-5.6 evidence in the README, video, and /feedback Session ID. — Rules state equal weighting but tie-breaks start with the first listed criterion; submission requirements repeatedly require specific evidence of Codex and GPT-5.6 use.
- Complete runnable product experience is likely a stronger lane than pure model demo because Design explicitly penalizes technical proofs of concept and testing access may determine whether judges can verify function quickly. — Design criterion asks for a complete coherent product experience, and rules say judges may rely on demo/text if they do not test.
- Projects that expose Codex as a visible build accelerator or audit trail may align better with sponsor priorities than projects where model use is hidden. — README and video must explain where Codex accelerated workflow, key decisions, and GPT-5.6/Codex contribution.
- Underrepresented workflows should emphasize irreversible workflow outcomes, constraint handling, testability, and failure prevention rather than chat wrappers or dashboards. — Judging asks for working non-trivial implementation, credible real-world impact, and novelty; default seed blacklist identifies saturated archetypes.

## Missing
- No public finalist or winner data is available yet for this hackathon because winners are scheduled for August 12, 2026 and the project gallery was unpublished at browse time.
- No numeric point weights beyond 'equally weighted' were published for the four Stage Two judging criteria.
- No official dataset is provided by the hackathon materials.
- No explicit maximum team size is listed, although prize benefits may cap some per-team benefits.
- No detailed list of required GPT-5.6 model variants for eligibility is stated beyond requiring GPT-5.6 use.
- No exact judging rubric scoring scale is published.
- No complete current participant/submission distribution by track is available from the public materials.
- No official clarification found for the conflict between the rules judging end date and schedule-page judging end date.

## Potentially stale
- Participant count on Devpost pages changed across browsed pages and should be treated as volatile.
- The statement that all $100 Codex credits have been distributed may change only if organizers add credits, but at browse time it was posted as exhausted.
- OpenAI plan/model availability and minimum client versions for GPT-5.6 in Codex are current-help-center claims and may change quickly.
- Supported country/territory eligibility depends on the OpenAI API supported-countries page and sanctions/legal changes.
- Judging period end date is inconsistent: official rules say August 5, 2026 17:00 PT, while schedule page says August 09, 2026 17:00 PDT.
- The project gallery was unpublished at browse time and may become available after submissions close.

## Crowding map
### High collision
- AI study tutor / quiz / flashcard generator
- Generic mental-health companion or wellness chatbot
- Resume / LinkedIn optimiser
- Document / PDF summariser
- Meeting notes / productivity chatbot
- Generic chatbot wrapper over GPT-5.6 or Codex
- Generic chatbot wrapper over a sponsor API
- Recommendation list with no last-mile action
- Dashboard-only analytics without an irreversible state change
- Carbon-footprint tracker dashboard
- Symptom checker / triage chatbot
### Medium collision
- Scholarship / grant / benefits eligibility navigator (retrieve -> check -> draft)
- Emergency information assistant / crisis tip sheet
- Automated sales outreach multi-agent SDR
- Generic opportunity board for students/job seekers
- Campaign fatigue / ops anomaly dashboard with rewritten ads
- Basic code review bot without repository-specific execution or test evidence
- Generic workflow automation assistant without production-grade integration depth
- Generic personal finance categorizer or travel planner with no transaction/action loop
- Recent similar title: Neilblaze
### Potentially underexplored
- Appeal-pathway reconstruction
- Constraint-based resource allocation under official rules
- Administrative error prevention / form failure-chain detection
- Eligibility inconsistency detection across agencies
- Procedural fairness / case-queue priority simulation
- Demo-failure surface minimisation for live presentations
- Judge-testability hardening workflows for complex projects
- Codex contribution provenance and build-decision audit trails
- Operational workflows that convert analysis into a verified state change rather than a report
### Do not build
- Any 'navigator' that only ranks and drafts applications from scattered PDFs
- Any personal crisis action planner that maps risk data to a checklist and safe route
- Any ops doctor that uploads CSV and labels campaigns healthy/fatigued
- Any project whose main value is a thin chat UI over GPT-5.6
- Any dashboard-only analytics concept with no durable action, writeback, or tested workflow
- Any education project that is only flashcards, quizzes, summarization, or generic tutoring
- Any developer tool that cannot be installed, tested, or tried without rebuilding from scratch
