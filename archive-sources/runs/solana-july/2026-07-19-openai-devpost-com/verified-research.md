# Verified research: OpenAI Build Week

## Facts
- [high] The submission deadline is July 21, 2026 at 5:00 PM Pacific Time. _(source: https://openai.devpost.com/ lines 82, 328; https://openai.devpost.com/details/dates lines 103-104)_
- [high] The schedule page lists submissions from July 13, 2026 at 9:00 AM PDT to July 21, 2026 at 5:00 PM PDT, judging from July 22, 2026 at 9:00 AM PDT to August 09, 2026 at 5:00 PM PDT, and winners announced August 12, 2026 at 2:00 PM PDT. _(source: https://openai.devpost.com/details/dates lines 99-106)_
- [high] The official rules list registration from July 9, 2026 at 10:00 AM PT to July 21, 2026 at 5:00 PM PT, submission from July 13, 2026 at 9:00 AM PT to July 21, 2026 at 5:00 PM PT, judging from July 22, 2026 at 10:00 AM PT to August 5, 2026 at 5:00 PM PT, and winners announced on or around August 12, 2026 at 2:00 PM PT. _(source: https://openai.devpost.com/rules lines 104-112)_
- [high] The hackathon is online, public, managed by Devpost, sponsored by OpenAI, and tagged Machine Learning/AI, DevOps, and Productivity. _(source: https://openai.devpost.com/ lines 313-323)_
- [high] Eligible participants must be at least the age of majority in their residence and in supported countries/territories that support OpenAI API services, subject to exclusions including jurisdictions where U.S. or local law prohibits participation or prize receipt. _(source: https://openai.devpost.com/rules lines 118-128 and untrusted evidence rules eligibility text)_
- [high] Projects must be built with Codex and GPT-5.6 and fit one of four tracks: Apps for Your Life, Work and Productivity, Developer Tools, or Education. _(source: https://openai.devpost.com/ lines 345-360; https://openai.devpost.com/rules lines 254-264)_
- [high] Projects must install and run consistently on their intended platform and function as depicted in the video or text description. _(source: https://openai.devpost.com/rules Project Requirements text in supplied evidence; https://openai.devpost.com/rules lines 182-204 for submission requirements)_
- [high] Pre-existing projects are allowed only if meaningfully extended during the submission period, with documentation distinguishing prior work from new work and evidence such as timestamped Codex session logs or dated commit history. _(source: https://openai.devpost.com/rules lines 179-181; https://openai.devpost.com/details/faqs lines 109-110)_
- [high] Submissions require a working project, category, text description, under-3-minute public YouTube demo with audio covering what was built and how Codex and GPT-5.6 were used, repository URL, README, and /feedback Codex Session ID. _(source: https://openai.devpost.com/ lines 361-376; https://openai.devpost.com/rules lines 182-204)_
- [high] Judges may test projects but are not required to; they may use the demo link, sandbox, or test account provided. _(source: https://openai.devpost.com/details/faqs lines 125-127)_
- [high] No changes can be made to submissions after the Submission Period ends on July 21, 2026 at 5:00 PM PT. _(source: https://openai.devpost.com/details/faqs lines 129-131; https://openai.devpost.com/rules lines 243-250)_
- [high] Stage One judging is pass/fail for baseline viability, theme fit, and reasonable application of required APIs/SDKs featured in the hackathon. _(source: https://openai.devpost.com/rules lines 251-255)_
- [high] Stage Two uses four equally weighted criteria: Technological Implementation, Design, Potential Impact, and Quality of the Idea. _(source: https://openai.devpost.com/rules lines 256-264)_
- [high] Tie-breaking follows the listed criterion order, starting with Technological Implementation, then subsequent listed criteria as needed. _(source: https://openai.devpost.com/rules lines 267-268)_
- [high] The project gallery was not published at time of access, so previous or current finalist/winner analysis from the gallery was unavailable. _(source: https://openai.devpost.com/project-gallery lines 100-108)_
- [high] The Resources page states all available $100 Codex credits had been given out, while the event still welcomes free-tier participation. _(source: https://openai.devpost.com/resources lines 99-105)_
- [high] The official GPT-5.6 docs describe Programmatic Tool Calling, multi-agent beta, explicit prompt caching, persisted reasoning, max reasoning effort, pro mode, token efficiency, frontend design improvements, intent understanding, and original image detail handling. _(source: https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6 lines 779-798)_
- [high] The GPT-5.6 docs recommend the Responses API for reasoning, tool-calling, and multi-turn workflows and describe model choices gpt-5.6-sol, gpt-5.6-terra, and gpt-5.6-luna. _(source: https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6 lines 814-823)_
- [high] Codex can be used from ChatGPT desktop, ChatGPT web, Codex CLI, Codex IDE extension, and Codex cloud according to the ChatGPT Learn quickstart navigation and setup content. _(source: https://learn.chatgpt.com/docs/quickstart lines 408-414 and 756-793)_

## Inference
- Technical Implementation is strategically decisive despite equal weights because it is both an equal Stage Two criterion and the first tie-break criterion. — Rules say Stage Two criteria are equally weighted, but tie-breaking starts with the first listed criterion, Technological Implementation.
- Runnable, judge-friendly demos are strategically important because judges may not build the project from scratch and are not required to test it. — FAQ says judges may test but are not required to and will use provided demo/sandbox/test account if they do.
- Projects that merely wrap GPT-5.6 or mention Codex decoratively are weak fits. — Rules and FAQ require meaningful Codex and GPT-5.6 use, demo narration, README explanation, and /feedback evidence.
- The strongest sponsor alignment is likely demonstrable Codex-accelerated engineering plus GPT-5.6 capabilities such as tool-heavy workflows, multi-agent coordination, reasoning, prompt caching, or polished frontend/product experience. — Judging emphasizes Codex use, non-trivial implementation, coherent product experience, impact, and novelty; OpenAI docs highlight these GPT-5.6/Codex capabilities.
- Education may have an expert strategic lens because the judge list includes OpenAI VP of Education Leah Belsky. — The overview page lists judge roles, including a VP of Education, but no per-track judging assignments are published.
- High participant count implies heavy collision pressure around broad AI assistant archetypes and template-like productivity/education apps. — The overview and tabs show roughly 42,000 participants, and the tracks map directly onto common AI hackathon archetypes.

## Missing
- No published current project gallery, finalists, or winners were available for direct crowding analysis.
- No rubric point totals, score sheets, or numeric weights beyond 'equally weighted' were published.
- No official dataset list or sponsor-provided dataset was identified.
- No explicit API usage requirement was found beyond required Codex and GPT-5.6 use; Codex credits are not API credits.
- No maximum team-size rule was found, but first-place DevDay/Exchange passes are limited to up to two team members.
- No detailed judging process allocation by track or judge was published.
- No exact submission form fields beyond the listed requirements and /feedback Session ID were independently accessible without login.

## Potentially stale
- Participant count varies across accessed pages and source captures, approximately 41,996 to 42,037, so treat it as dynamic.
- Credits availability changed: overview/rules describe requesting by July 17, 2026 at 12:00 PM PT, while Resources says all available credits have been given out; as of July 19, 2026 the request deadline has passed.
- Judging period dates conflict between the official rules, ending August 5, 2026 at 5:00 PM PT, and the schedule page, ending August 09, 2026 at 5:00 PM PDT.
- Supported-country eligibility depends on OpenAI's supported countries list, which can change.
- GPT-5.6 model capabilities and model-family naming are current only as of the official docs access and may change.
- Project gallery/public submission availability may change after managers publish it or after the submission deadline.

## Crowding map
### High collision
- AI study tutor / quiz / flashcard generator
- Generic mental-health companion or wellness chatbot
- Resume / LinkedIn optimiser
- Document / PDF summariser
- Meeting notes / productivity chatbot
- Generic workflow automation chatbot for teams
- Generic customer-support chatbot
- Generic analytics dashboard without action or state change
- Generic DevOps assistant over logs or CI output
- Generic agentic code reviewer without runnable integration depth
- Generic chatbot wrapper over GPT-5.6 or Codex
- Recommendation list with no last-mile action
- Dashboard-only analytics without an irreversible state change
- Generic family/travel/personal-finance assistant
### Medium collision
- Scholarship / grant / benefits eligibility navigator
- Emergency information assistant / crisis tip sheet
- Automated sales outreach multi-agent SDR
- Generic opportunity board for students/job seekers
- Campaign fatigue / ops anomaly dashboard with rewritten ads
- Test generation or QA assistant without deep repo integration
- Security scanner summary UI without remediation workflow
- Teacher lesson-plan generator
- Personal productivity planner with calendar/task summaries
- Creative writing or image-prompt companion
- Recent similar title: Neilblaze
### Potentially underexplored
- Appeal-pathway reconstruction
- Constraint-based resource allocation under official rules
- Administrative error prevention / form failure-chain detection
- Eligibility inconsistency detection across agencies
- Procedural fairness / case-queue priority simulation
- Demo-failure surface minimisation for live presentations
- Judge-testability hardening workflows
- Evidence-backed Codex contribution traceability
- Multi-step tool workflows with auditable state transitions
- Human approval and review loops for irreversible actions
### Do not build
- Any 'navigator' that only ranks and drafts applications from scattered PDFs
- Any personal crisis action planner that maps risk data to a checklist and safe route
- Any ops doctor that uploads CSV and labels campaigns healthy/fatigued
- Any generic chatbot wrapper over sponsor APIs
- Any dashboard-only project that never changes external state or completes a workflow
- Any clone of common tutor, flashcard, resume, PDF, meeting-notes, or wellness assistant patterns
- Any demo that cannot be run, tested, or understood without judges rebuilding from scratch
- Any project relying on unauthorized third-party data, copyrighted media, trademarks, or unclear licensing
