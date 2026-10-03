from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from .data import load_addresses, load_change_tests, load_rules, starter_stats
from .engine import lookup_address

app = FastAPI(
    title="LeaseLaw Navigator",
    description="Hack-Nation 7 Track 02 — RealPage. Not legal advice.",
    version="0.3.0",
)

_OUT = Path(__file__).resolve().parents[1] / "out"


@app.get("/health")
def health() -> dict:
    try:
        stats = starter_stats()
    except FileNotFoundError as e:
        stats = {"error": str(e)}
    return {
        "ok": True,
        "track": "02-realpage",
        "rules": len(load_rules()),
        "addresses": len(load_addresses()),
        "starter": stats,
    }


@app.get("/api/addresses")
def list_addresses(limit: int = 50, state: str | None = None) -> list[dict]:
    rows = load_addresses()
    if state:
        rows = [a for a in rows if a.get("state") == state.upper()]
    return rows[: max(1, min(limit, 500))]


@app.get("/api/change-tests")
def api_change_tests() -> list[dict]:
    return load_change_tests()


@app.get("/api/eval")
def api_eval() -> dict:
    """Judge-visible stand-in until official score.py is in the pack."""
    path = _OUT / "eval-report.json"
    if not path.exists():
        return {
            "passed": 0,
            "total": 0,
            "change_tests": [],
            "note": "Run: python -m src.eval_harness",
            "official_score_py": False,
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    data["official_score_py"] = False
    data["note"] = (
        "Harness T1–T5 (participant no-scoring pack has no score.py). "
        "Not an official RealPage score."
    )
    return data


@app.get("/api/lookup")
def api_lookup(
    address_id: str = Query(...),
    as_of: str = Query("2026-10-01"),
) -> dict:
    addresses = {a["address_id"]: a for a in load_addresses()}
    if address_id not in addresses:
        raise HTTPException(404, f"unknown address_id {address_id}")
    return lookup_address(addresses[address_id], load_rules(), as_of)


@app.get("/api/compare")
def api_compare(
    address_id: str = Query(...),
    before: str = Query("2025-12-31"),
    after: str = Query("2026-01-02"),
) -> dict:
    addresses = {a["address_id"]: a for a in load_addresses()}
    if address_id not in addresses:
        raise HTTPException(404, f"unknown address_id {address_id}")
    rules = load_rules()
    addr = addresses[address_id]
    return {
        "before": lookup_address(addr, rules, before),
        "after": lookup_address(addr, rules, after),
        "disclaimer": "Not legal advice.",
    }


def _demo_addresses() -> list[dict]:
    all_addrs = load_addresses()
    want = [
        ("San Francisco", "CA"),
        ("Los Angeles", "CA"),
        ("Hoboken", "NJ"),
        ("Jersey City", "NJ"),
        ("Newark", "NJ"),
        ("Boston", "MA"),
        ("Cambridge", "MA"),
        ("Berkeley", "CA"),
        ("San Diego", "CA"),
    ]
    picked: list[dict] = []
    for city, state in want:
        hit = next(
            (
                a
                for a in all_addrs
                if a.get("state") == state
                and city.lower()
                in (
                    (a.get("legal_city") or "").lower(),
                    (a.get("postal_city") or "").lower(),
                )
            ),
            None,
        )
        if hit:
            picked.append(hit)
    return picked or all_addrs[:10]


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    addresses = _demo_addresses()
    n = len(load_addresses())
    nr = len(load_rules())
    options = "\n".join(
        f'<option value="{a["address_id"]}">{a.get("street") or a.get("street_address")}, '
        f'{a.get("legal_city") or a.get("postal_city")} {a["state"]} ({a["address_id"]})</option>'
        for a in addresses
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>LeaseLaw Navigator</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Fraunces:opsz,wght@9..144,600&display=swap" rel="stylesheet"/>
  <style>
    :root {{
      --ink: #14201b;
      --muted: #4a5c54;
      --line: #c9d5ce;
      --bg: #eef4f0;
      --panel: #f7faf8;
      --accent: #0d6b5c;
      --warn-bg: #fff6e8;
      --warn-line: #e0b36a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; color: var(--ink);
      font-family: "DM Sans", sans-serif;
      background:
        radial-gradient(900px 420px at 10% -10%, #d7ebe3 0%, transparent 55%),
        radial-gradient(700px 380px at 100% 0%, #e6e2d4 0%, transparent 50%),
        var(--bg);
      min-height: 100vh;
    }}
    main {{ max-width: 960px; margin: 0 auto; padding: 2.25rem 1.25rem 3rem; }}
    .brand {{
      font-family: Fraunces, Georgia, serif;
      font-size: clamp(2rem, 4vw, 2.75rem);
      letter-spacing: -0.02em; margin: 0 0 .35rem;
    }}
    .lede {{ color: var(--muted); margin: 0 0 1.25rem; max-width: 40rem; }}
    .warn {{
      background: var(--warn-bg); border: 1px solid var(--warn-line);
      padding: .85rem 1rem; border-radius: 10px; margin-bottom: 1.25rem;
    }}
    .meta {{ display:flex; gap:1rem; flex-wrap:wrap; color: var(--muted); font-size: .92rem; margin-bottom: 1rem; }}
    .meta strong {{ color: var(--ink); }}
    .score {{
      background: #e8f3ef; border: 1px solid #9fc4b8; border-radius: 12px;
      padding: .9rem 1.1rem; margin-bottom: 1.1rem;
    }}
    .score h2 {{ margin: 0 0 .45rem; font-size: 1rem; }}
    .pills {{ display:flex; flex-wrap:wrap; gap: .4rem; margin: .35rem 0; }}
    .pill {{
      font-size: .78rem; font-weight: 700; padding: .2rem .55rem; border-radius: 999px;
      background: #dce9e3; color: var(--ink);
    }}
    .pill.ok {{ background: #b7e0c8; }}
    .pill.bad {{ background: #f0c4c0; }}
    .score .sub {{ color: var(--muted); font-size: .82rem; margin: .25rem 0 0; }}
    label {{ display:block; margin-top: .15rem; font-weight: 600; font-size: .9rem; }}
    select, input, button {{ font: inherit; padding: .55rem .7rem; margin-top: .3rem; }}
    select, input {{
      border: 1px solid var(--line); border-radius: 8px; background: white; min-width: 16rem;
    }}
    button {{
      background: var(--accent); color: white; border: 0; border-radius: 8px;
      cursor: pointer; font-weight: 600; padding: .65rem 1rem;
    }}
    button.secondary {{ background: #24352f; }}
    .row, .card {{
      display: flex; gap: 1rem; flex-wrap: wrap; align-items: end;
    }}
    .card {{
      background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
      padding: 1rem 1.1rem; box-shadow: 0 1px 2px rgba(20, 32, 27, .06);
    }}
    .hint {{ color: var(--muted); font-size: .85rem; margin: .5rem 0 0; }}
    .foot {{
      color: var(--muted); font-size: .82rem; line-height: 1.5;
      border-top: 1px solid var(--line); margin-top: 1.5rem; padding-top: .75rem;
    }}
    pre {{
      background: var(--panel); border: 1px solid var(--line);
      padding: 1rem; overflow: auto; border-radius: 10px;
      font-size: .85rem; line-height: 1.45; min-height: 12rem; white-space: pre-wrap;
    }}
    button:disabled {{ opacity: .55; cursor: progress; }}
    :focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
    h2 {{ font-size: 1.05rem; margin: 1.5rem 0 .5rem; }}
    @media (max-width: 560px) {{
      select, input, button {{ width: 100%; min-width: 0; }}
      .row, .card {{ flex-direction: column; align-items: stretch; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1 class="brand">LeaseLaw Navigator</h1>
    <p class="lede">Address-level rental housing rules with citations, as-of dates, and Track 02 change tests T1–T5.</p>
    <p class="warn"><strong>Not legal advice.</strong> Hack-Nation 7 · Track 02 RealPage demo / research only.</p>
    <div class="meta">
      <span><strong>{n}</strong> sample addresses</span>
      <span><strong>{nr}</strong> extracted rules</span>
      <span>Eval: T1–T5 harness</span>
    </div>
    <section class="score" id="score" aria-label="Judge score panel">
      <h2>Judge score panel (T1–T5 harness)</h2>
      <div id="scoreline">Loading eval…</div>
      <div class="pills" id="pills"></div>
      <p class="sub" id="scorenote">Stand-in until official score.py is available. Not legal advice.</p>
    </section>
    <div class="card">
      <div>
        <label for="addr">Address</label>
        <select id="addr">{options}</select>
      </div>
      <div>
        <label for="asof">As of</label>
        <input id="asof" type="date" value="2026-10-01"/>
      </div>
      <button id="go" type="button">Lookup</button>
      <button id="toggle" class="secondary" type="button">AB325 before / after</button>
    </div>
    <p class="hint">Every returned rule carries its <strong>source doc id</strong>, <strong>source URL</strong>, and a <strong>quoted span</strong> taken from the corpus text.</p>
    <h2>Result</h2>
    <pre id="out" role="status" aria-live="polite">Select an address and Lookup.</pre>
    <p class="foot">
      LeaseLaw Navigator · Hack-Nation 7 · Track 02 RealPage. <strong>Not legal advice</strong> — demo / research use only.<br/>
      Rules are regenerated with <code>python -m src.extract_rules</code>; change tests T1–T5 with <code>python -m src.eval_harness</code>.
    </p>
  </main>
  <script>
    const out = document.getElementById('out');
    const go = document.getElementById('go');
    const toggle = document.getElementById('toggle');
    function busy(on) {{ go.disabled = on; toggle.disabled = on; }}
    async function render(url) {{
      busy(true);
      out.textContent = 'Loading…';
      try {{
        const r = await fetch(url);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        out.textContent = JSON.stringify(await r.json(), null, 2);
      }} catch (e) {{
        out.textContent = 'Lookup failed: ' + e.message + ' — is the API running on this port?';
      }} finally {{
        busy(false);
      }}
    }}
    async function lookup() {{
      const id = document.getElementById('addr').value;
      const asof = document.getElementById('asof').value;
      await render(`/api/lookup?address_id=${{encodeURIComponent(id)}}&as_of=${{asof}}`);
    }}
    async function compare() {{
      const id = document.getElementById('addr').value;
      await render(`/api/compare?address_id=${{encodeURIComponent(id)}}`);
    }}
    go.onclick = lookup;
    toggle.onclick = compare;
    document.getElementById('asof').addEventListener('keydown', (e) => {{
      if (e.key === 'Enter') lookup();
    }});
    (async function loadEval() {{
      try {{
        const r = await fetch('/api/eval');
        const d = await r.json();
        const line = document.getElementById('scoreline');
        const pills = document.getElementById('pills');
        const note = document.getElementById('scorenote');
        line.innerHTML = '<strong>' + (d.passed ?? 0) + ' / ' + (d.total ?? 0) + '</strong> change tests passed';
        pills.innerHTML = '';
        for (const t of (d.change_tests || [])) {{
          const s = document.createElement('span');
          s.className = 'pill ' + (t.pass ? 'ok' : 'bad');
          s.textContent = t.test_id + (t.pass ? ' PASS' : ' FAIL');
          pills.appendChild(s);
        }}
        if (d.note) note.textContent = d.note;
      }} catch (e) {{
        document.getElementById('scoreline').textContent = 'Eval unavailable — run python -m src.eval_harness';
      }}
    }})();
  </script>
</body>
</html>"""
