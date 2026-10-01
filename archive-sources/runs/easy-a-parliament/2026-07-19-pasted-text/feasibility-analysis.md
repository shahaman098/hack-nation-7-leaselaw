# Feasibility analysis

## concept-c3d4
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: Western Electric run rule implementation on streaming fal request metrics is the core technical contribution — but this is likely too fragile for live demo conditions and can't be verified as working if faked
- Min demo loop: Capture a few fal API calls locally, compute X-bar/R chart from that static dataset, show a dashboard with control limits, and demonstrate a pre-recorded video of the 'circuit breaker' triggering
- Dependencies: Real-time fal API video streaming with sub-second latency needed for SPC anomaly detection — hackathon Wi-Fi/sponsor API rate limits likely insufficient, GPT-5.6 baseline calibration requires historical session data that doesn't exist for unproven endpoint/network conditions in hackathon environment, Pre-generated fallback buffer must be prompt-consistent and generated ahead of failure — requires perfect prediction of what the live stream should have shown
- Notes: This is a demo-failure-proofing tool that will itself fail during the demo because real-time SPC on streaming video APIs requires stable low-latency connections, historical baselining that can't be done cold at hackathon start, and fallback generation that assumes you already have working video output. Circular dependency: you need a reliable fal endpoint to develop the tool that protects against unreliable fal endpoints. The 'killer demo' requires deliberately throttling network — this is dangerous live and likely to crash the entire system rather than gracefully recover. 48 hours is insufficient to tune SPC parameters for a stochastic generative API whose failure modes you can't characterize in advance.

## concept-004-ci
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: The counterfactual estimation engine that takes a generated frame, identifies deviating style attributes against a reference, and formulates a correction prompt for regeneration — this is the novel mechanism and cannot be faked if judges ask to test with their own reference image
- Min demo loop: Hardcode style parameters from a reference image, use GPT-5.6 once to generate a stylized prompt variant, submit to fal, and show the output next to a generic baseline — all computation pre-scripted
- Dependencies: Style-propensity scoring requires training/comparison against artist reference set — no pre-trained model exists, must build from scratch, Counterfactual inpainting needs GPT-5.6 to generate targeted attribute deltas (line weight, palette), but GPT's visual reasoning for 'thicken line weight by 1.4x' is unreliable without pixel-level control, fal API must support targeted regeneration of specific attributes — this is not a standard endpoint capability, requires workaround that may not exist
- Notes: The causal DAG construction for visual style is pure fantasy for a hackathon. Building a directed acyclic graph that meaningfully links 'line weight' to 'visual outcomes' requires domain expertise in both causal inference and computer vision that a 4-person team won't have. The counterfactual estimation ('what would this frame look like if style treatment was fully applied?') is an open research problem, not a weekend project. GPT-5.6 cannot compute 'estimated delta of 1.4x line weight' from pixel analysis — this confuses LLM capabilities with computer vision. The 'causal-style report' with percentage matches implies a quantitative evaluation framework that doesn't exist and can't be validated in 48 hours. The mechanism is theoretically interesting but practically unbuildable at hackathon scale.

## concept-003-des
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: The event simulation log that maps frame timestamps to specific brand constraint violations with audit-trail quality — this requires actual computer vision processing that produces verifiable outputs
- Min demo loop: Hardcode brand rules, pre-process one video into frame timestamps with violation flags, build the grid UI showing those pre-computed results, and demonstrate the violation navigation (click to jump to timestamp) — no live simulation needed
- Dependencies: GPT-5.6 must reliably parse uploaded brand guide PDFs into executable event rules — PDF parsing of design docs is notoriously brittle, especially for visual specs like color swatches and logo placement diagrams, fal-hosted computer vision endpoints for color detection, logo detection, and tone classification must return structured outputs with low latency across many frames — unclear if these endpoints exist or need to be built, Simulation clock for frame-by-frame event processing across 6+ simultaneous videos will hit compute limits very quickly and likely can't run 'live' during demo
- Notes: This is the most buildable of the candidates because the core idea (brand compliance checking) can be reduced to a series of discrete checks that don't require real-time processing. The discrete event simulation framing is academic dressing — what's actually being built is a frame-by-frame checklist with a dashboard. This is achievable if the team scopes ruthlessly: one brand guide, one set of hardcoded rules, pre-processed videos. The main risk is overengineering the 'simulation' abstraction instead of just building the checker. The demo proof requires 8 videos running simultaneously — this could crash a browser, limit to 3-4. GPT-5.6 PDF parsing for brand guidelines is the weakest link; better to manually encode rules for the demo and claim the PDF parser is 'in development.'

## C5
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: The constraint propagation engine that takes a character constraint (e.g., 'warm Kelvin 2500-3500') and narrows it across scenes to prevent drift — this requires the interval arithmetic to actually compute intersecting domains, not just copy-paste prompts
- Min demo loop: Pre-define constraints manually, show a UI that displays narrowed parameter ranges across shots, generate 3-4 images using hardcoded constrained prompts, and demonstrate visual consistency improvement against a manual baseline — constraint solving can be simulated
- Dependencies: GPT-5.6 must correctly parse natural-language shot descriptions into formal visual constraints with interval domains — zero-shot constraint extraction from prose is unreliable and will produce nonsensical intervals, fal Workflow JSON generation must be syntactically perfect and compatible with Grok Imagine/Kling endpoints — API schema mismatches will silently fail video generation, Batch generation of 12 constrained shots requires fal API to handle high volume of requests in quick succession without rate limiting or timeout
- Notes: Buildable if scoped down to a prompt-construction tool rather than a full constraint solver. The interval arithmetic is overkill for a hackathon — what's actually valuable is automated prompt injection from a visual bible. The 'constraint propagation' mechanism is intellectually interesting but the team will likely end up building a template system with some variable substitution, which is fine for demo purposes. Main risk: spending too much time implementing real interval arithmetic instead of shipping a working prompt-chain tool. The CLIP cosine distance evaluation is good and measurable. fal Assets integration is the strongest dependency — if that API works reliably, the demo is achievable. The character face consistency claim ('same face across 12 shots') is the hardest to deliver with current gen AI and may look worse than claimed.

## mut-r4-02-styleforge-verified-counterf
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: Demonstrating a measurable, reproducible delta between a generic prompt baseline and a style-treated output using a consistent metric derived from reference images.
- Min demo loop: User uploads reference images; system generates one frame with a style metric <40%; user clicks 'Treat'; system generates a new frame using a prompt modified by GPT-5.6 analysis of references; metric updates to >70%.
- Dependencies: fal API image generation endpoint must support fine-grained style guidance, GPT-5.6 must produce accurate causal DAG and style-propensity scores from arbitrary reference packs, Reliable metric for style-attribute match percentage exists or can be built in <24h
- Notes: The entire workflow hinges on GPT-5.6's ability to reliably parse unconstrained reference art and output actionable, deterministic style deltas for the fal API. This is an unsolved research problem, not a 48-hour integration task. The causal DAG framing adds complexity theater without proven feasibility. The core promise of measurable, quantifiable style correction is likely unachievable without a pre-built, calibrated scoring harness. High risk of a demo that works only for the pre-tested exemplar inputs.

## mut-r4-03-safecut-real-time-transition
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: Automatically detecting a visually jarring or off-brand morph in an interpolated frame between two approved shots and triggering a targeted regeneration.
- Min demo loop: User provides two keyframes and a brand asset; system generates a transition; system analyzes the transition, flags a single frame as violating a pre-defined rule (luminance spike, logo distortion), and shows the flagged frame.
- Dependencies: Computer vision APIs for frame interpolation and object/brand-logo detection must be available and reliable, Grok Imagine must support region-specific regeneration based on constraint intervals, A robust method for defining and checking safe-visual constraint intervals in real-time must be built
- Notes: While ambitious, the core loop is scoped tighter than other candidates. Frame interpolation and analysis can be simulated or constrained to a very specific, demonstrable failure case (e.g., face morphing). The main risk is integrating Grok Imagine for the 'Auto-Heal' feature under time pressure; the demo can survive by showing the detection and blocking of the transition as the primary value, with the heal as a secondary, potentially pre-rendered action.

## mut-r4-04-scenedoctor-automated-regres
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: Running a pipeline change, re-generating affected scenes, and computing a quantifiable visual drift (treatment effect) against a stored baseline to flag a failure.
- Min demo loop: User stores a baseline for a 2-scene film; user modifies a prompt for scene 2; user runs test suite; system re-generates scene 2; system computes an embedding distance between new and old scene 2 frames; system flags a 'regression' if distance exceeds a threshold and shows a side-by-side diff.
- Dependencies: fal API must support programmatic re-generation of specific scenes with isolated prompt changes, Difference-in-Differences method must be correctly implemented and demonstrable on visual embeddings, Sub-frame visual regressions like 'eye color shift' must be reliably detectable by automated tools (CLIP, color histograms)
- Notes: This project demands robust, reproducible video generation from fal, which is inherently stochastic. Re-generating scenes to reliably detect a subtle, specific change like eye color requires controlling for all other randomness—a massive challenge. The causal framing (causal DAG, DiD) is extreme overkill and a likely source of fatal bugs under the deadline. A simple visual diff tool with a threshold is achievable; this proposal is not.

## mut-r4-05-creditguard-spc-driven-budge
- Delivery risk: **low**
- Kill?: False
- Non-fakeable core: Middleware intercepts an API call, detects a simulated 'credit spike' condition, and programmatically cancels or downgrades a concurrent, lower-priority request.
- Min demo loop: A script runs two parallel processes calling fal API; at a predetermined point, the middleware detects a credit burn rate exceeding a static threshold; it pauses the second process and logs the action; the first process completes successfully.
- Dependencies: fal API must provide reliable, real-time credit consumption and latency metrics per request, Access to multiple fal model endpoints with varying credit costs for downgrade logic
- Notes: This is the most technically feasible project. It operates on a well-defined, numerical domain (credits, latency) and the core logic (check rate, trigger action) is straightforward state management. The 'anomaly' can be manually injected for a flawless demo. The main risk is fal API not providing sufficiently granular credit data in real-time, but a proxy or polling can mitigate that. The constraint is engineering integration, not unsolved research.

## mut-r4-06-conflictstyle-causal-mediato
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: Accepting a text directive and an image, then outputting a minimally altered image that visually reflects the directive via targeted, parameterized edits.
- Min demo loop: User uploads an image and types a feedback phrase; system shows a prompt it will send to an image editor; user triggers edit; a new image is displayed side-by-side with the old one.
- Dependencies: GPT-5.6 must robustly map abstract director feedback ('more hopeful') to specific, actionable visual mediators for an input frame, fal API (inpainting/control) must be able to modify only the identified mediators without degrading the rest of the image, A reliable perceptual metric for abstract concepts like 'Triumph Score' must be implemented
- Notes: The semantic gap between 'more hopeful' and 'adjust lighting angle by 15 degrees, shift palette warmth +10%' is the entire unsolved field of computational creativity. This project proposes to solve it with a single GPT-5.6 call and no training data. The result will be brittle, confusing, or random. The causal framing adds no demonstrable value and increases demo fragility. A simple prompt expansion tool is all that can be built, contradicting the proposal's core novelty.

## mut-r4-07-simevidence-objectively-bran
- Delivery risk: **medium**
- Kill?: False
- Non-fakeable core: Processing a video and programmatically verifying that a specific text string is present, legible, and meets contrast requirements for a sufficient duration, logging any violations with frame-level timestamps.
- Min demo loop: User uploads a video and specifies a text string and duration requirement; system processes video, detects the string, records its display duration; if duration is short, system flags a violation and shows the timestamp of failure.
- Dependencies: Reliable OCR API to detect specific disclaimer text and its duration on screen, Accurate color contrast measurement tool against a video frame's background, GPT-5.6 must parse a PDF rulebook into discrete, executable monitoring rules
- Notes: This project is a specialized, well-scoped automation task. The hardest part is accurate text detection/tracking across frames, which is a known problem with existing libraries. Faking or pre-computing the OCR for a specific demo video is trivial, but the core value is still demonstrated. The 'append-only ledger' is distracting but easily bolted on. The main risk is burning too much time on contrast-ratio math against dynamic backgrounds instead of using an existing library.

## mut-r4-08-biblediff-counterfactual-vis
- Delivery risk: **high**
- Kill?: True
- Non-fakeable core: Quantifying the visual difference between two multi-shot sequences generated with and without a 'bible' constraint and graphing this difference as a metric (CLIP drift) over a timeline.
- Min demo loop: User provides a prompt and a style reference; system generates two short sequences (with/without style); system calculates CLIP embeddings for each frame and graphs the similarity to the first frame over time for both sequences; the constrained line shows less drift.
- Dependencies: fal API must generate two full, multi-shot video sequences with deterministic control vs. no-control protocols in a reasonable time, CLIP embedding must be a sensitive enough metric to isolate character-face drift from other scene changes, Statistical significance (p-value) calculation on a small, stochastic sample of generated videos is methodologically sound and defensible
- Notes: Reliability of video generation is the fatal flaw. Running the 'counterfactual world' generation will likely take too long, consume too many credits, or produce stochastic noise that drowns out the desired signal. The entire premise rests on a controlled experiment that is impossible to conduct cleanly with current generative models. The statistical framing is a smokescreen for an A/B test. This is a data science presentation, not a functional tool building challenge, and is highly likely to fail in a live demo.
