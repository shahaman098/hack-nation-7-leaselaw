"""HTML shells for LeaseLaw UI — plain language for renters."""

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
  <title>LeaseLaw Navigator — rental rules by address</title>
{_HEAD}
</head>
<body data-page="home">
  <div class="bg-grid" aria-hidden="true"></div>
  <div class="bg-glow" aria-hidden="true"></div>
  <div class="shell">
    <nav class="nav">
{_LOGO}
      <div class="nav-links">
        <button type="button" class="btn-icon" id="theme-toggle" aria-label="Light or dark mode">◐</button>
        <button type="button" class="btn-icon" id="lang-toggle" data-i18n="lang">ES</button>
      </div>
    </nav>

    <header class="hero">
      <p class="disclaimer-banner"><strong data-i18n="notLegal">Not legal advice</strong> · For information only</p>
      <h1 data-i18n="tagline">What rental rules apply to your address?</h1>
      <p class="sub" data-i18n="sub">Plain-language summary with links to the original law text. Pick your address and the date you care about.</p>

      <div class="search-panel">
        <div class="search-row">
          <input type="text" id="search-input" autocomplete="off" data-i18n-placeholder="searchPlaceholder" placeholder="Start typing your street or city…" aria-label="Address search"/>
          <input type="date" id="asof" value="2026-10-01" aria-label="Rules as of"/>
          <button type="button" class="btn-primary" id="lookup-btn" data-i18n="lookup">Check my address</button>
        </div>
        <div class="suggestions" id="suggestions" role="listbox"></div>
        <div class="quick-actions">
          <button type="button" class="chip" id="compare-dates-btn" data-i18n="compareDates">Compare two dates</button>
          <button type="button" class="chip" id="how-btn" data-i18n="howDecided">How we decided</button>
          <button type="button" class="chip" id="open-q-btn" data-i18n="unclearRules">Dates that lawyers disagree on</button>
        </div>
      </div>
    </header>

    <section class="strip strip-human">
      <div class="card">
        <h3 data-i18n="tryExample">Try an example</h3>
        <p class="meta-row card-intro">Tap one — we fill the search for you.</p>
        <div class="test-strip">
          <button class="test-btn" type="button" data-test="T1" data-i18n="exampleCAJan">California — before new 2026 rules</button>
          <button class="test-btn" type="button" data-test="T1b" data-i18n="exampleCAAfter">California — after Jan 1, 2026</button>
          <button class="test-btn" type="button" data-test="T2" data-i18n="exampleHoboken">Hoboken — local tenant rules</button>
          <button class="test-btn" type="button" data-test="T3" data-i18n="exampleNJ">New Jersey — statewide changes (2027)</button>
          <button class="test-btn" type="button" data-test="T4" data-i18n="exampleBoston">Boston — pending bills, no rent cap</button>
        </div>
      </div>
      <div class="card">
        <h3 data-i18n="pickCity">Browse by city</h3>
        <p class="meta-row"><strong>{n_addresses}</strong> <span data-i18n="addressesHint">sample addresses</span> · <strong>{n_rules}</strong> <span data-i18n="rulesHint">housing rules in our library</span></p>
        <div class="city-strip">
          <button type="button" class="city-btn" data-city="San Francisco">San Francisco</button>
          <button type="button" class="city-btn" data-city="Los Angeles">Los Angeles</button>
          <button type="button" class="city-btn" data-city="San Diego">San Diego</button>
          <button type="button" class="city-btn" data-city="Berkeley">Berkeley</button>
          <button type="button" class="city-btn" data-city="Hoboken">Hoboken</button>
          <button type="button" class="city-btn" data-city="Jersey City">Jersey City</button>
          <button type="button" class="city-btn" data-city="Newark">Newark</button>
          <button type="button" class="city-btn" data-city="Boston">Boston</button>
          <button type="button" class="city-btn" data-city="Cambridge">Cambridge</button>
        </div>
      </div>
    </section>

    <section id="open-q-panel" class="open-q-box" style="display:none"></section>

    <section id="results" aria-live="polite"></section>

    <footer class="footer">
      <strong data-i18n="notLegal">Not legal advice</strong><br/>
      <span data-i18n="footerNote">For learning and demos only. Talk to a lawyer or tenant clinic for your situation.</span>
    </footer>
  </div>
  <script type="module" src="/static/js/app.js"></script>
</body>
</html>"""


def pipeline_page_html() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <title>About · LeaseLaw Navigator</title>
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
      <h1 style="max-width:none;margin-left:0">How this tool works</h1>
      <p class="sub" style="margin-left:0">We read public housing laws, match them to your address and move-in date, and show what applies. <strong>Not legal advice.</strong></p>
    </header>
    <div id="pipeline-steps"></div>
  </div>
  <script src="/static/js/pipeline.js"></script>
</body>
</html>"""
