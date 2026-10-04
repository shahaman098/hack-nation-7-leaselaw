"""HTML shells for LeaseLaw UI (Exa-inspired)."""

from __future__ import annotations

_HEAD = """
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="/static/css/app.css"/>
"""


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
      <a class="logo" href="/"><span class="logo-mark" aria-hidden="true"></span> LeaseLaw</a>
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
        <h3 data-i18n="changeTests">Change tests</h3>
        <div class="test-strip">
          <button class="test-btn" data-test="T1">T1 before</button>
          <button class="test-btn" data-test="T1b">T1 after</button>
          <button class="test-btn" data-test="T2">T2 Hoboken</button>
          <button class="test-btn" data-test="T3">T3 FAIR</button>
          <button class="test-btn" data-test="T4">T4 MA pending</button>
          <button class="test-btn" data-test="T5">T5 no rent cap</button>
        </div>
      </div>
      <div class="card">
        <h3>Corpus</h3>
        <div class="big">{n_addresses}</div>
        <p class="meta-row">addresses · <strong>{n_rules}</strong> rules extracted</p>
      </div>
    </section>

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
      <a class="logo" href="/"><span class="logo-mark"></span> LeaseLaw</a>
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
