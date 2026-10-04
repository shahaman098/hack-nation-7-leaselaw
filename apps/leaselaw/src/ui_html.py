"""HTML shells for LeaseLaw UI (Exa-inspired)."""

from __future__ import annotations

_HEAD = """
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <link rel="icon" href="/static/favicon.svg" type="image/svg+xml"/>
  <link rel="apple-touch-icon" href="/static/logo-mark.svg"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="/static/css/app.css"/>
"""

_LOGO = """
      <a class="logo" href="/">
        <img class="logo-mark-img" src="/static/logo-mark.svg" width="32" height="32" alt=""/>
        <span class="logo-word">
          <span class="logo-name">LeaseLaw</span>
          <span class="logo-tag">Navigator</span>
        </span>
      </a>"""


def home_page(n_addresses: int, n_rules: int) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <title>LeaseLaw Navigator</title>
{_HEAD}
</head>
<body data-page="home">
  <div class="bg-grid" aria-hidden="true"></div>
  <div class="bg-glow" aria-hidden="true"></div>
  <div class="shell">
    <nav class="nav">
{_LOGO}
      <div class="nav-links">
        <a href="/pipeline" data-i18n="pipeline">Pipeline</a>
        <a href="/out/rules.json">rules.json</a>
        <a href="/out/lookups.json">lookups.json</a>
        <a href="/out/changes.json">changes.json</a>
        <button type="button" class="btn-icon" id="theme-toggle" aria-label="Toggle theme">◐</button>
        <button type="button" class="btn-icon" id="lang-toggle" data-i18n="lang">ES</button>
      </div>
    </nav>

    <header class="hero">
      <p class="disclaimer-banner"><strong data-i18n="notLegal">Not legal advice</strong> · Hack-Nation 7 · Track 02 RealPage</p>
      <h1 data-i18n="tagline">Which housing rules apply at this address?</h1>
      <p class="sub" data-i18n="sub">Cited answers from the RealPage corpus · as-of dates · change tests T1–T5</p>

      <div class="search-panel">
        <div class="search-row">
          <input type="text" id="search-input" autocomplete="off" data-i18n-placeholder="searchPlaceholder" placeholder="Search 500 sample addresses…"/>
          <input type="date" id="asof" value="2026-10-01" aria-label="As of"/>
          <button type="button" class="btn-primary" id="lookup-btn" data-i18n="lookup">Lookup</button>
        </div>
        <div class="suggestions" id="suggestions" role="listbox"></div>
        <div class="quick-actions">
          <button type="button" class="chip" id="ab325-btn" data-i18n="ab325">AB325 before / after</button>
          <button type="button" class="chip" id="audit-btn" data-i18n="audit">Audit trace</button>
          <button type="button" class="chip" id="open-q-btn" data-i18n="openQBtn">§9 Open Questions (4)</button>
        </div>
      </div>
    </header>

    <section class="strip">
      <div class="card">
        <h3 data-i18n="scoreTitle">Harness score</h3>
        <div class="big" id="score-big">—</div>
        <p class="meta-row" id="score-sub"></p>
        <div class="pills" id="eval-pills"></div>
      </div>
      <div class="card">
        <h3 data-i18n="changeTests">Change tests & §9 Open Questions</h3>
        <div class="test-strip">
          <button class="test-btn" data-test="T1" title="California AB325 before (2025-12-31)">T1 before</button>
          <button class="test-btn" data-test="T1b" title="California AB325 after (2026-01-02)">T1 after</button>
          <button class="test-btn" data-test="T2" title="Hoboken local algorithmic ban">T2 Hoboken</button>
          <button class="test-btn" data-test="T3" title="NJ FAIR Act effective (2027-07-02)">T3 FAIR</button>
          <button class="test-btn" data-test="T4" title="MA S.2983 / H.5222 pending">T4 MA pending</button>
          <button class="test-btn" data-test="T5" title="MA struck rent ballot">T5 no rent cap</button>
        </div>
        <div class="test-strip" style="margin-top:0.4rem;padding-top:0.4rem;border-top:1px dashed var(--border)">
          <button class="test-btn q-btn" data-q="Q1" title="Berkeley Ch.13.63: March 1, 2026 vs Jan 2026">§9.1 Berkeley Dates</button>
          <button class="test-btn q-btn" data-q="Q2" title="NJ FAIR Act preemption of JC & Hoboken">§9.2 FAIR Preemption</button>
          <button class="test-btn q-btn" data-q="Q3" title="LA RSO formula: 2026-02-02 vs 2026-01-24">§9.3 LA Formula</button>
          <button class="test-btn q-btn" data-q="Q4" title="CA screening fee cap statutory ambiguity">§9.4 Screening Gap</button>
        </div>
      </div>
      <div class="card">
        <h3>Corpus & 9 Cities</h3>
        <div class="big">{n_addresses}</div>
        <p class="meta-row">addresses · <strong>{n_rules}</strong> rules extracted</p>
        <div class="city-strip">
          <button class="city-btn" data-city="San Francisco">SF</button>
          <button class="city-btn" data-city="Los Angeles">LA</button>
          <button class="city-btn" data-city="San Diego">SD</button>
          <button class="city-btn" data-city="Berkeley">Berk</button>
          <button class="city-btn" data-city="Hoboken">Hob</button>
          <button class="city-btn" data-city="Jersey City">JC</button>
          <button class="city-btn" data-city="Newark">Newk</button>
          <button class="city-btn" data-city="Boston">Bos</button>
          <button class="city-btn" data-city="Cambridge">Camb</button>
        </div>
      </div>
    </section>

    <section id="open-q-panel" class="open-q-box" style="display:none"></section>

    <section id="results" aria-live="polite"></section>

    <footer class="footer">
      LeaseLaw Navigator · <strong>Not legal advice</strong> · demo / research only<br/>
      <code>python3 -m src.eval_harness</code> · <a href="/api/eval">/api/eval</a>
    </footer>
  </div>
  <script type="module" src="/static/js/app.js"></script>
</body>
</html>"""


def pipeline_page_html() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <title>Extraction pipeline · LeaseLaw</title>
{_HEAD}
</head>
<body data-page="pipeline">
  <div class="bg-grid" aria-hidden="true"></div>
  <div class="bg-glow" aria-hidden="true"></div>
  <div class="shell page-narrow">
    <nav class="nav">
{_LOGO}
      <a href="/" class="btn-icon" style="text-decoration:none">← Home</a>
    </nav>
    <header class="hero" style="text-align:left;padding-top:1rem">
      <h1 style="max-width:none;margin-left:0">Extraction pipeline</h1>
      <p class="sub" style="margin-left:0">Corpus → extract → verify → rules.json → engine. <strong>Not legal advice.</strong></p>
    </header>
    <div id="pipeline-steps"></div>
    <h3 class="section-title">Audit log (recent)</h3>
    <pre class="json-dump" id="pipeline-data">Loading…</pre>
  </div>
  <script src="/static/js/pipeline.js"></script>
</body>
</html>"""
