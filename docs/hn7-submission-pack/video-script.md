# Video Scripts — LeaseLaw Navigator (Track 02 RealPage)

**Event:** Hack-Nation 7 · Track 02 RealPage  
**Product:** LeaseLaw Navigator  
**Core Rule:** Every video must show the live system and scores.  

---

## 1. Team Video (60s)

**Speaker:** Solo Developer  
**Key Visual:** Camera + Title screen / Home page of LeaseLaw Navigator

> "Hi, I'm competing solo in Hack-Nation 7 on Track 02: RealPage Rental Housing Law Navigator.
>
> Today, multifamily property operators face an unprecedented maze of housing regulations. Municipal, county, and state laws overlap, effective dates shift, algorithmic rent-setting bans are sweeping across jurisdictions, and key parcel records often lack critical facts like unit counts or certificate of occupancy dates.
>
> I built **LeaseLaw Navigator**: an automated, deterministic legal compliance and change-tracking engine. It takes raw assessor parcel data, resolves jurisdictions, ingests official statutory corpora with literal citation verification, evaluates temporal coverage as-of any query date, and tracks legal changes across all 500 benchmark properties.
>
> It strictly adheres to responsible AI design: 'Not legal advice', explicit 'unknown' states when data is insufficient, and conflict flags for open legal questions. Let's look at the demo."

---

## 2. Demo Video (90s – 2m) — *Must show live UI & test scores*

**Key Visuals:** Live Web Application (`http://127.0.0.1:8012` / deployed URL)

> **[0:00 - 0:15] Overview & Responsible Design**  
> "Welcome to LeaseLaw Navigator. Notice our prominent 'Not legal advice' disclaimer and the live test harness card showing **5 out of 5 change tests passing**, **10 out of 10 gold benchmark tests green**, and **100% schema validation**.
>
> **[0:15 - 0:40] Change Test 1: Temporal As-Of Toggle (California AB 325)**  
> Let's look at a Los Angeles property (A0001). Under query date December 31, 2025, California AB 325 on common pricing algorithms shows as **`not_yet_effective`**, with the exact statutory text cited.  
> Now, toggle the as-of date to January 2, 2026. Instantly, AB 325 updates to **`applies`**. Notice that the local LA Rent Stabilization Ordinance is also evaluated, citing the allowable 3% increase.
>
> **[0:40 - 1:00] Change Test 2 & 3: Local Bans & State Preemption (Hoboken vs Jersey City & NJ FAIR)**  
> Next, let's switch to Hoboken (A0002). We see the Hoboken local algorithmic ban applies. Now test New Jersey's statewide FAIR Act. Today, it is not yet effective. When queried as of July 2, 2027, the FAIR Act applies, and LeaseLaw automatically surfaces a **Conflict Flag** warning of potential state preemption of local municipal bans.
>
> **[1:00 - 1:20] Change Test 5 & Section 9 Open Questions**  
> Switch to Boston (A0006). A proposed rent-control ballot measure was struck by the court; LeaseLaw explicitly marks it **`failed`** and never applies a rent cap in Boston or Cambridge.  
> Furthermore, LeaseLaw directly surfaces all **four Section 9 open legal questions**—from Berkeley's dual effective dates under Chapter 13.63 to LA's dual RSO formula dates—with highlighted conflict notes.
>
> **[1:20 - 1:35] Stretch Features: Spanish Translation & Audit Trail**  
> We can toggle to Spanish ('ES') for a plain-language view of all requirements, and click 'Audit trace' to view the complete retrieval provenance, confidence metrics, and deterministic reasoning chain. All 500 addresses and tests are verifiable and reproducible."

---

## 3. Technical Video (120s)

**Key Visuals:** Architecture diagram, terminal running `eval_harness.py`, code in `src/`

> **[0:00 - 0:30] Module A: Automated Extraction Pipeline**  
> "The engine is organized into three decoupled modules:
>
> Module A is our automated extraction pipeline in `src/corpus_automate.py` and `src/verify.py`. It ingests all 54 corpus plain-text documents, parses statutory requirements across 6 schema categories, and enforces a strict verifier: 49 of 50 rules feature literal substring matches in the official text, with 1 explicit link-only evidence gap safely documented for Hoboken. 100% of extracted rules validate against the official RealPage JSON schema.
>
> **[0:30 - 1:00] Module B: Jurisdiction Resolution & Coverage Engine**  
> In Module B, `src/jurisdiction.py` maps mailing cities to incorporated legal municipalities—such as resolving Dorchester to the City of Boston, and Van Nuys to Los Angeles.  
> `src/engine.py` executes deterministic coverage: testing rolling age, unit thresholds, and certificate-of-occupancy cutoffs (such as San Francisco's 1979-06-13 cutoff). If a building was built in 1979, the system returns **`unknown`** rather than guessing. If local rent control applies, it automatically marks statewide AB 1482 as **`superseded`**.
>
> **[1:00 - 1:35] Module C: Change Tracking & Evaluation Harness**  
> Module C runs `src/eval_harness.py` across all 500 assessor properties. It evaluates T1 through T5 deterministic change tests, 10 gold benchmark cases, and exports standard-compliant `rules.json`, `lookups.json`, and `changes.json`.  
> Terminal run: `python3 -m src.eval_harness` exits 0 with 5/5 change tests and 10/10 gold cases passing in under 0.2 seconds.
>
> **[1:35 - 2:00] Reproducibility & Deployment**  
> The entire pipeline reproduces via `./scripts/reproduce.sh`. It is served via a FastAPI backend on port 8012 and packaged in a multi-stage Dockerfile ready for production hosting. LeaseLaw provides auditability, legal precision, and true address-level intelligence."
