# Hack-Nation 6th Global AI Hackathon

In collaboration with MIT Club of Northern California and MIT Club of Germany.

## Context

Teams choose one sponsor challenge and build a working hackathon prototype. Strong submissions must be demo-first, specific to the selected challenge, grounded in real or provided data, and able to show a memorable transformation in about one minute. Avoid generic chatbot wrappers, dashboard-only projects, unsupported AI claims, and sponsor technology used only as decoration.

## Challenge 01 - ElevenLabs: The Negotiator

Build a voice-agent system that gathers real prices by phone, compares itemized quotes, and negotiates a better deal in a phone-priced market such as moving, medical bills, car buying, contractor bids, freight, equipment rental, or wedding vendors.

Required modules:
- Estimator: voice interview using ElevenLabs Agents plus at least one document type; both produce the same confirmed structured job spec.
- Caller: live calls against at least three distinct negotiation styles; every quote captured in structured comparable form with itemized fees.
- Closer: at least one negotiation where price or terms change because of leverage gathered; final report ranks all quotes and cites transcript evidence.

Important controls:
- AI disclosure and honesty constraints.
- Handles interruptions, refusals, vague answers, hang-ups, and "are you a robot?"
- Never invents inventory or fake competing bids.

Likely winning angle: conversation design and real negotiation quality matter more than agent-stack complexity.

## Challenge 02 - Maschmeyer Group: The VC Brain

Build a data- and AI-first venture operating system for Sourcing, Screening, Diligence, and Decision, enabling a human investor to evaluate and deploy $100K checks within 24 hours.

Required capabilities:
- Thesis Engine configurable by sector, stage, geography, check size, ownership target, and risk appetite.
- Smart data collection from pitch decks, GitHub, social signals, launches, papers, patents, hackathons, accelerators, and applications.
- Inbound application flow: deck plus company name minimum.
- Outbound sourcing flow: find founders before formal fundraising and activate them into applications.
- Multi-axis screening: Founder, Market, and Idea-vs-Market scored independently, not averaged; each includes trend.
- Persistent Founder Score that follows a person across applications and updates over time.
- Evidence-backed investment memos and per-claim Trust Scores.

Judging:
- Data Architecture and Intelligence: 30%.
- Intelligent Analysis and Trust: 25%.
- Investment Utility and Execution: 30%.
- UX and Design: 15%.

Likely winning angle: deep sourcing and cold-start founder evaluation, not a polished generic investor dashboard.

## Challenge 03 - RealPage: RealDoor

Build an affordable-housing application-readiness copilot for one metro, one program, and synthetic documents. The AI extracts, explains, retrieves, calculates, and prepares; the renter confirms; a qualified human decides.

Required flow:
- Profile: upload synthetic pay stubs or benefit letters, extract only allowlisted fields with source boxes and confidence, require renter confirmation or correction.
- Understand: use a versioned corpus for one program and rule year, show confirmed value, threshold, formula, source, and effective date, abstain when uncertain, never label the renter eligible.
- Prepare: flag missing or expired items against a gold checklist, let renter preview/edit/download/delete, never auto-send a profile or packet.

Non-negotiables:
- No approval, denial, score, rank, or eligibility decision.
- No hidden proxies or protected-trait inference.
- Consent, correction, privacy, deletion, prompt-injection resistance, and WCAG 2.2 AA accessibility.

Judging:
- Profile accuracy: 25%.
- Rules and math: 25%.
- Safety and privacy: 20%.
- Accessibility: 15%.
- End-to-end usefulness: 15%.

Likely winning angle: correctness, safety controls, deterministic math, and accessibility.

## Challenge 04 - Databricks: Data Legend

Build a Healthcare Facility Intelligence App on Databricks Free Edition that turns 10,000 messy Indian healthcare facility records into decisions a non-technical planner can trust.

Choose one mission track:
- Facility Trust Desk: capability plus region -> ranked facilities with trust signals -> facility citations -> human override with note.
- Medical Desert Planner: capability plus geography -> trust-weighted regional coverage -> drill into facility records behind aggregate -> save scenario.
- Referral Copilot: location plus care need -> evidence-attached shortlist with distance, evidence, gaps -> save shortlist.
- Data Readiness Desk: surface completeness gaps, contradictions, suspicious claims, high-leverage records -> review queue -> persist reviewer decisions.

Required product elements:
- Databricks App live on Free Edition.
- Evidence Engine that extracts structure from messy structured and free-text facility records.
- Trust Scorer that communicates confidence and uncertainty, not just keyword matches.
- Planner workflow that persists notes, overrides, shortlists, scenarios, or review decisions.

Provided dataset:
- 10,000 Indian facility records across 51 columns.
- Fields include description, capability, procedure, equipment, numberDoctors, capacity, yearEstablished, source URLs, and location.
- Important sparsity: numberDoctors about 36.4% coverage, capacity about 25.2%.

Sponsor tech:
- Databricks Apps.
- Agent Bricks / Mosaic AI.
- Genie.
- MLflow 3 tracing.
- AI Search / Vector Search.
- Lakebase for persistence.

Judging:
- Evidence and Trust: 35%.
- Product Judgment: 30%.
- Technical Execution: 25%.
- Ambition: 10%.

Likely winning angle: distinguish true medical deserts from data deserts and show evidence-backed uncertainty a planner can act on.

## Challenge 05 - OpenAI: Foundation Models for Women's Hormonal Health

Build one reusable open-science layer for women's hormonal health: a dataset, benchmark, model, or application that future researchers can build on.

Possible layers:
- Data and Benchmark Infrastructure: standardized multimodal dataset, train/validation/test splits, transparent evaluation, focused prediction tasks such as hormone level, ovulation, menopause stage, or disease-risk prediction.
- AI Model Infrastructure: focused reproducible model for hormone-level or hormonal-state prediction, explainable multimodal integration, or clinical-trial prediction where hormonal variability may affect efficacy or safety.
- Application Infrastructure: regulator-conscious de-identified data contribution, digital hormone journal, voice logging, personalized hormone insights, or digital twin built on reusable datasets/models.

Open-science requirement:
- Publish datasets, benchmarks, source code, model checkpoints, documentation, and evaluation pipelines whenever possible.

Data sources:
- mcPHASES on PhysioNet: Fitbit, continuous glucose monitoring, hormone measurements, menstrual-cycle data, sleep, and symptoms.
- NHANES: reproductive health, thyroid hormones, lab data, nutrition, demographics.

Success criteria:
- Women's health impact.
- Technical excellence.
- Foundation value.

Likely winning angle: a reusable benchmark or evaluation pipeline is stronger than an isolated symptom-tracking app.

## Challenge 06 - OpenAI: Genome Firewall

Build a strictly defensive AI system that takes one quality-checked reconstructed bacterial genome FASTA for one supported species and predicts, for each antibiotic, likely to fail, likely to work, or no-call. Each result must include calibrated confidence and supporting genes or DNA changes.

Required modules:
- Genome Reader: repeatable path from assembled FASTA to AI features using AMRFinderPlus as default annotation; output format specification.
- Predictor: predictions for all antibiotics on each species, with deterministic molecular-target compatibility gate and sequence-homology de-duplication before evaluation.
- Decision Report: Streamlit or Gradio demo with drug, likely fail/work/no-call, calibrated confidence, evidence category, and mandatory "confirm with standard lab testing" message.

Responsibility requirements:
- Strictly defensive; never designs, modifies, or suggests changes to organisms.
- Honest generalization using genetically related groups and held-out data.
- Calibrated confidence and no-call option.
- Separate known resistance genes/DNA changes from statistical associations.
- Human oversight.

Data and tools:
- BV-BRC genome and lab-measured AMR data.
- AMRFinderPlus.
- ResFinder.
- cAMRah.
- Baseline: regularized logistic regression per antibiotic with AMRFinderPlus features.

Evaluation:
- Balanced accuracy, resistant recall, susceptible recall.
- F1, AUROC, PR-AUC per drug.
- Brier score, reliability plot, no-call rate, accuracy after no-call.
- Generalization by genetically related bacterial group.

Likely winning angle: one species and a few antibiotics done honestly with grouped splits, calibration, no-call behavior, and careful defensive framing.

## Shared Strategic Constraints

- Small team, hackathon build window, working demo required.
- A winning project must be judge-legible in under 60 seconds.
- Prefer real computation, state transitions, evidence, trust layers, deterministic checks, and workflow completion over pure chat.
- Sponsor technology should be materially necessary.
- The idea must not be replaceable by opening ChatGPT.
- Strong demo pattern: messy fragmented evidence -> system performs real extraction/computation/verification -> user gets a defensible action or decision-support artifact.
