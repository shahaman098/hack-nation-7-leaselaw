import { t, categoryLabel, resultLabel } from "./i18n.js";

const GROUP_ORDER = [
  ["applies", "applies"],
  ["unknown", "unknown"],
  ["superseded", "superseded"],
  ["not_yet_effective", "notYet"],
  ["pending", "pending"],
  ["failed", "failed"],
];

let lang = "en";
let theme = localStorage.getItem("ll-theme") || "light";
let addresses = [];
let selectedId = null;
let currentData = null;

const $ = (sel) => document.querySelector(sel);

function applyTheme() {
  document.documentElement.setAttribute("data-theme", theme === "dark" ? "dark" : "light");
  localStorage.setItem("ll-theme", theme);
}

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    el.textContent = t(lang, key);
  });
  const langBtn = $("#lang-toggle");
  if (langBtn) langBtn.textContent = t(lang, "lang");
  const searchInput = $("#search-input");
  if (searchInput) searchInput.setAttribute("placeholder", t(lang, "searchPlaceholder"));
}

async function loadAddresses() {
  const r = await fetch("/api/addresses?limit=500");
  addresses = await r.json();
}

function formatAddr(a, includeId = false) {
  const street = a.street || a.street_address || "";
  const city = a.legal_city || a.postal_city || "";
  const line = `${street}, ${city}, ${a.state}`;
  return includeId ? `${line}` : line;
}

function showSuggestions(q) {
  const box = $("#suggestions");
  if (!box) return;
  const ql = (q || "").toLowerCase().trim();
  if (ql.length < 1) {
    box.classList.remove("open");
    box.innerHTML = "";
    return;
  }
  const hits = addresses
    .filter((a) => {
      const hay = `${a.street_address || a.street} ${a.postal_city} ${a.legal_city || ""} ${a.state}`.toLowerCase();
      return hay.includes(ql);
    })
    .slice(0, 12);
  box.innerHTML = hits
    .map(
      (a, i) =>
        `<button type="button" data-id="${a.address_id}" aria-selected="${i === 0}">${esc(formatAddr(a))}</button>`
    )
    .join("");
  box.classList.add("open");
  box.querySelectorAll("button").forEach((btn) => {
    btn.onclick = () => {
      selectedId = btn.dataset.id;
      $("#search-input").value = formatAddr(addresses.find((x) => x.address_id === selectedId));
      box.classList.remove("open");
      runLookup();
    };
  });
}

function groupRules(rules) {
  const m = new Map();
  for (const r of rules || []) {
    const k = r.result || "applies";
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(r);
  }
  return m;
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

function cleanDisplayText(s) {
  if (!s) return "";
  return String(s)
    .replace(/\s[—–]\s/g, ", ")
    .replace(/[—–]/g, ", ")
    .replace(/\s·\s/g, ", ")
    .replace(/…/g, "...");
}

function ruleSummary(r) {
  const raw =
    lang === "es" && r.plain_language_es ? r.plain_language_es : r.plain_language || r.explanation || r.title || "";
  return cleanDisplayText(raw);
}

function renderRuleCard(r) {
  const conf = Math.round((r.confidence ?? 0.75) * 100);
  const badge = resultLabel(lang, r.result);
  const cat = categoryLabel(lang, r.category);
  const title = cleanDisplayText(r.title || r.citation || cat);
  return `
    <article class="rule-card" data-rule-id="${esc(r.team_rule_id || "")}">
      <div class="rule-top">
        <div>
          <div class="rule-cat">${esc(cat)}</div>
          <div class="rule-title">${esc(title)}</div>
        </div>
        <span class="result-badge ${esc(r.result)}">${esc(badge)}</span>
      </div>
      <p class="plain">${esc(ruleSummary(r))}</p>
      ${r.conflict_flag ? `<span class="conflict">Note: ${esc(t(lang, "conflict"))}${r.conflict_note ? ". " + esc(cleanDisplayText(r.conflict_note)) : ""}</span>` : ""}
      <div class="conf-bar" aria-label="${esc(t(lang, "sureness"))}"><span style="width:${conf}%"></span></div>
      <details class="source">
        <summary>${esc(t(lang, "source"))}</summary>
        <div class="quote">${esc(r.quoted_span || "")}</div>
        ${r.source_url ? `<p><a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(t(lang, "moreDetails"))}</a></p>` : ""}
      </details>
    </article>`;
}

function renderResults(data) {
  currentData = data;
  const root = $("#results");
  if (!root) return;
  if (!data || !data.address_id) {
    root.innerHTML = `<p class="empty">${esc(t(lang, "selectAddress"))}</p>`;
    return;
  }

  const stack = (data.jurisdiction_stack || [])
    .map((s) => `<span class="stack-chip">${esc(s)}</span>`)
    .join("");
  const grouped = groupRules(data.rules);
  let html = `
    <div class="results-header">
      <div>
        <div class="rule-title">${esc(data.street)}, ${esc(data.postal_city || data.legal_city)} ${esc(data.state)}</div>
        <div class="meta-row">${esc(t(lang, "asOfLine"))} ${esc(data.as_of)}</div>
      </div>
      <div class="stack-block">
        <span class="meta-row stack-label">${esc(t(lang, "yourArea"))}</span>
        <div class="stack-chips">${stack}</div>
      </div>
    </div>`;

  for (const [resultKey, labelKey] of GROUP_ORDER) {
    const items = grouped.get(resultKey);
    if (!items?.length) continue;
    html += `<h3 class="section-title">${esc(t(lang, labelKey))}</h3>`;
    for (const r of items) html += renderRuleCard(r);
  }

  const failed = data.failed_or_not_applied || [];
  if (failed.length) {
    html += `<h3 class="section-title">${esc(t(lang, "failed"))}</h3>`;
    for (const r of failed) {
      html += `<article class="rule-card"><p class="plain">${esc(r.explanation || ruleSummary(r))}</p></article>`;
    }
  }

  root.innerHTML = html;
}

async function runLookup() {
  if (!selectedId) {
    const q = $("#search-input")?.value || "";
    const hit = addresses.find((a) => formatAddr(a) === q || a.address_id === q);
    if (hit) selectedId = hit.address_id;
  }
  if (!selectedId) return;
  const asof = $("#asof")?.value || "2026-10-01";
  const btn = $("#lookup-btn");
  if (btn) btn.disabled = true;
  $("#results").innerHTML = `<p class="empty">${esc(t(lang, "loading"))}</p>`;
  try {
    const r = await fetch(`/api/lookup?address_id=${encodeURIComponent(selectedId)}&as_of=${encodeURIComponent(asof)}`);
    if (!r.ok) throw new Error("HTTP " + r.status);
    renderResults(await r.json());
  } catch (e) {
    $("#results").innerHTML = `<p class="empty">${esc(t(lang, "error"))}</p>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

function indexRules(lookup) {
  const m = new Map();
  for (const r of lookup?.rules || []) m.set(r.team_rule_id, r);
  return m;
}

async function runCompare() {
  if (!selectedId) return;
  const btn = $("#compare-dates-btn");
  if (btn) btn.disabled = true;
  $("#results").innerHTML = `<p class="empty">${esc(t(lang, "loading"))}</p>`;
  try {
    const r = await fetch(
      `/api/compare?address_id=${encodeURIComponent(selectedId)}&before=2025-12-31&after=2026-01-02`
    );
    const d = await r.json();
    const before = indexRules(d.before);
    const after = indexRules(d.after);
    const ids = new Set([...before.keys(), ...after.keys()]);
    let changes = [];
    for (const id of ids) {
      const b = before.get(id);
      const a = after.get(id);
      if (!b && !a) continue;
      const br = b?.result || "none";
      const ar = a?.result || "none";
      if (br !== ar) {
        const name = a?.title || b?.title || a?.citation || b?.citation || categoryLabel(lang, a?.category || b?.category);
        changes.push({ name, br, ar, a: a || b });
      }
    }
    let html = `<h2 class="section-title">${esc(t(lang, "compareTitle"))}</h2>`;
    html += `<p class="meta-row">${esc(t(lang, "compareBefore"))}: ${esc(t(lang, "compareRange"))}</p>`;
    if (!changes.length) {
      html += `<p class="empty">${esc(t(lang, "compareNone"))}</p>`;
    } else {
      for (const c of changes) {
        html += `<article class="rule-card">
          <div class="rule-title">${esc(c.name)}</div>
          <p class="plain">${esc(resultLabel(lang, c.br))} ${esc(t(lang, "changedTo"))} ${esc(resultLabel(lang, c.ar))}</p>
        </article>`;
      }
    }
    $("#results").innerHTML = html;
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function runHowDecided() {
  if (!selectedId) return;
  const asof = $("#asof")?.value || "2026-10-01";
  $("#results").innerHTML = `<p class="empty">${esc(t(lang, "loading"))}</p>`;
  try {
    const d = await fetch(`/api/audit/${encodeURIComponent(selectedId)}?as_of=${encodeURIComponent(asof)}`).then((r) =>
      r.json()
    );
    let html = `<h2 class="section-title">${esc(t(lang, "auditTitle"))}</h2>`;
    html += `<p class="meta-row">${esc(t(lang, "asOfLine"))} ${esc(asof)}</p>`;
    for (const row of d.traces || []) {
      html += `<article class="rule-card">
        <div class="rule-top">
          <span class="result-badge ${esc(row.result)}">${esc(resultLabel(lang, row.result))}</span>
        </div>
        <p class="plain">${esc(row.explanation || "")}</p>
      </article>`;
    }
    $("#results").innerHTML = html;
  } catch {
    $("#results").innerHTML = `<p class="empty">${esc(t(lang, "error"))}</p>`;
  }
}

const TEST_PRESETS = {
  T1: { id: "A0001", asof: "2025-12-31" },
  T1b: { id: "A0001", asof: "2026-01-02" },
  T2: { id: "A0002", asof: "2026-10-01" },
  T3: { id: "A0002", asof: "2027-07-02" },
  T4: { id: "A0006", asof: "2026-10-01" },
  T5: { id: "A0006", asof: "2026-10-01" },
  Q1: { id: "A0005", asof: "2026-10-01" },
  Q2: { id: "A0002", asof: "2027-07-02" },
  Q3: { id: "A0001", asof: "2026-10-01" },
  Q4: { id: "A0005", asof: "2026-10-01" },
};

async function toggleOpenQPanel() {
  const panel = $("#open-q-panel");
  if (!panel) return;
  if (panel.style.display !== "none") {
    panel.style.display = "none";
    return;
  }
  panel.style.display = "block";
  panel.innerHTML = `<p class="empty">${esc(t(lang, "loading"))}</p>`;
  try {
    const data = await fetch("/api/open-questions").then((r) => r.json());
    const cards = (data.questions || [])
      .map(
        (q) => `
        <div class="open-q-card">
          <h4>${esc(q.topic)}</h4>
          <p>${esc(q.explanation)}</p>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.5rem;flex-wrap:wrap;gap:0.5rem">
            <span class="stack-chip">${esc(q.jurisdiction)}</span>
            <button type="button" class="btn-primary" style="padding:0.25rem 0.65rem;font-size:0.75rem" data-qid="${esc(q.id)}">${esc(t(lang, "seeExample"))}</button>
          </div>
        </div>`
      )
      .join("");
    panel.innerHTML = `
      <div class="open-q-header">
        <div>
          <h3 style="margin:0;font-size:1.05rem;color:var(--warn)">${esc(t(lang, "openQTitle"))}</h3>
          <p class="meta-row" style="margin:0.25rem 0 0">${esc(t(lang, "openQIntro"))}</p>
        </div>
        <button type="button" class="btn-icon" id="close-open-q" aria-label="Close">✕</button>
      </div>
      <div class="open-q-grid">${cards}</div>`;
    $("#close-open-q")?.addEventListener("click", () => {
      panel.style.display = "none";
    });
    panel.querySelectorAll("[data-qid]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const map = {
          "berkeley-dual-dates": "Q1",
          "nj-fair-preemption": "Q2",
          "la-rso-dual-dates": "Q3",
          "ca-screening-fee-cap": "Q4",
        };
        const key = map[btn.getAttribute("data-qid")];
        if (key && TEST_PRESETS[key]) {
          const p = TEST_PRESETS[key];
          selectedId = p.id;
          const a = addresses.find((x) => x.address_id === p.id);
          if (a) $("#search-input").value = formatAddr(a);
          $("#asof").value = p.asof;
          panel.style.display = "none";
          runLookup();
        }
      });
    });
  } catch {
    panel.innerHTML = `<p class="empty">${esc(t(lang, "error"))}</p>`;
  }
}

let sampleOrdinances = null;

async function toggleLiveIngestPanel() {
  const panel = $("#live-ingest-panel");
  if (!panel) return;
  if (panel.style.display !== "none") {
    panel.style.display = "none";
    return;
  }
  panel.style.display = "block";
  panel.innerHTML = `<p class="empty">${esc(t(lang, "loading"))}</p>`;

  if (!sampleOrdinances) {
    try {
      sampleOrdinances = await fetch("/api/sample-ordinances").then((r) => r.json());
    } catch {
      sampleOrdinances = {};
    }
  }

  const cambridge = sampleOrdinances["cambridge_hour16"] || {};

  panel.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem;flex-wrap:wrap;gap:0.5rem">
      <div>
        <h3 style="margin:0;font-size:1.15rem;color:var(--accent)">⚡ Live Ordinance Ingestion & Extension Studio</h3>
        <p class="meta-row" style="margin:0.25rem 0 0">
          Paste any statute or ordinance to run automated extraction, 100% schema validation, and address resolution.
        </p>
      </div>
      <button type="button" class="btn-icon" id="close-live-ingest" aria-label="Close">✕</button>
    </div>

    <div style="display:flex;gap:0.5rem;margin-bottom:1rem;flex-wrap:wrap">
      <span class="meta-row" style="align-self:center;font-weight:600">Quick-Load Presets:</span>
      <button type="button" class="chip" id="load-cambridge-btn">🏛️ Hour-16 Cambridge (T6)</button>
      <button type="button" class="chip" id="load-seattle-btn">🌲 Seattle Algorithmic Ban</button>
      <button type="button" class="chip" id="load-austin-btn">🤠 Austin Tenant Relocation</button>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:0.75rem;margin-bottom:0.75rem">
      <div>
        <label style="font-size:0.8rem;font-weight:600">Document Title</label>
        <input type="text" id="live-title" class="input" style="width:100%;margin-top:0.25rem;box-sizing:border-box" value="${esc(cambridge.title || '')}"/>
      </div>
      <div>
        <label style="font-size:0.8rem;font-weight:600">City</label>
        <input type="text" id="live-city" class="input" style="width:100%;margin-top:0.25rem;box-sizing:border-box" value="${esc(cambridge.city || 'Cambridge')}"/>
      </div>
      <div>
        <label style="font-size:0.8rem;font-weight:600">State</label>
        <input type="text" id="live-state" class="input" style="width:100%;margin-top:0.25rem;box-sizing:border-box" value="${esc(cambridge.state || 'MA')}"/>
      </div>
      <div>
        <label style="font-size:0.8rem;font-weight:600">Citation</label>
        <input type="text" id="live-citation" class="input" style="width:100%;margin-top:0.25rem;box-sizing:border-box" value="${esc(cambridge.citation || '')}"/>
      </div>
    </div>

    <div style="margin-bottom:0.75rem">
      <label style="font-size:0.8rem;font-weight:600">Statutory / Ordinance Text</label>
      <textarea id="live-text" class="input" rows="7" style="width:100%;font-family:monospace;font-size:0.82rem;margin-top:0.25rem;box-sizing:border-box">${esc(cambridge.text || '')}</textarea>
    </div>

    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;margin-bottom:1rem">
      <div style="display:flex;align-items:center;gap:0.5rem">
        <label style="font-size:0.8rem;font-weight:600">Evaluate As-Of:</label>
        <input type="date" id="live-asof" value="2026-10-01" class="input"/>
      </div>
      <button type="button" class="btn-primary" id="run-live-extract-btn" style="padding:0.5rem 1.25rem">⚡ Extract, Validate & Resolve</button>
    </div>

    <div id="live-extract-output"></div>
  `;

  $("#close-live-ingest")?.addEventListener("click", () => {
    panel.style.display = "none";
  });

  const setPreset = (p) => {
    if (!p) return;
    $("#live-title").value = p.title || "";
    $("#live-city").value = p.city || "";
    $("#live-state").value = p.state || "";
    $("#live-citation").value = p.citation || "";
    $("#live-text").value = p.text || "";
    $("#live-extract-output").innerHTML = "";
  };

  $("#load-cambridge-btn")?.addEventListener("click", () => setPreset(sampleOrdinances["cambridge_hour16"]));
  $("#load-seattle-btn")?.addEventListener("click", () => setPreset(sampleOrdinances["seattle_algo"]));
  $("#load-austin-btn")?.addEventListener("click", () => setPreset(sampleOrdinances["austin_relocation"]));

  $("#run-live-extract-btn")?.addEventListener("click", async () => {
    const btn = $("#run-live-extract-btn");
    const out = $("#live-extract-output");
    btn.disabled = true;
    out.innerHTML = `<p class="empty">${esc(t(lang, "loading"))}</p>`;

    try {
      const payload = {
        title: $("#live-title")?.value || "",
        city: $("#live-city")?.value || "",
        state: $("#live-state")?.value || "",
        citation: $("#live-citation")?.value || "",
        text: $("#live-text")?.value || "",
        as_of: $("#live-asof")?.value || "2026-10-01",
      };
      const res = await fetch("/api/extract-live", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then((r) => r.json());

      if (!res.success) throw new Error("Extraction failed");

      const r = res.rule_record;
      const schemaPill = res.schema_valid
        ? `<span class="pill" style="background:#10b981;color:#fff;padding:0.2rem 0.5rem;border-radius:4px;font-size:0.75rem">✓ SCHEMA VALID (Draft 2020-12)</span>`
        : `<span class="pill" style="background:#ef4444;color:#fff;padding:0.2rem 0.5rem;border-radius:4px;font-size:0.75rem">⚠ SCHEMA ERROR</span>`;
      const quotePill = res.quoted_span_verified
        ? `<span class="pill" style="background:#10b981;color:#fff;padding:0.2rem 0.5rem;border-radius:4px;font-size:0.75rem">✓ QUOTED SPAN VERIFIED (Literal Substring)</span>`
        : `<span class="pill" style="background:#f59e0b;color:#fff;padding:0.2rem 0.5rem;border-radius:4px;font-size:0.75rem">UNVERIFIED SPAN</span>`;
      const statusPill = `<span class="result-badge ${esc(res.status_as_of)}">${esc(res.status_as_of)}</span>`;

      const sampleAddrsHtml = (res.sample_affected_addresses || [])
        .map(
          (a) =>
            `<li><strong>${esc(a.street || a.address_id)}</strong> (${esc(a.city)}, ${esc(a.state)}) — ${a.units || "?"} units, built ${a.year_built || "?"}</li>`
        )
        .join("");

      out.innerHTML = `
        <div style="border-top:1px solid var(--border);padding-top:1rem;margin-top:1rem">
          <div style="display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap;margin-bottom:0.75rem">
            ${schemaPill}
            ${quotePill}
            ${statusPill}
            <span class="stack-chip" style="font-weight:600">${res.affected_addresses_count} Buildings Affected</span>
          </div>

          <article class="rule-card" style="margin-bottom:1rem">
            <div class="rule-top">
              <div>
                <div class="rule-id">${esc(r.team_rule_id)} · ${esc(r.category)}</div>
                <div class="rule-title">${esc(r.title)}</div>
              </div>
            </div>
            <p class="plain">${esc(r.requirement)}</p>
            <p class="plain" style="font-style:italic;color:var(--text-muted)">ES: ${esc(r.plain_es)}</p>
            <div class="meta-row">
              <span><strong>Effective:</strong> ${esc(r.effective_date || "N/A")}</span>
              <span><strong>Citation:</strong> ${esc(r.citation)}</span>
            </div>
            <details class="source" open style="margin-top:0.5rem">
              <summary>Verbatim Quoted Span</summary>
              <div class="quote">${esc(r.quoted_span)}</div>
            </details>
          </article>

          ${
            sampleAddrsHtml
              ? `
            <div style="background:var(--card);border:1px solid var(--border);padding:0.75rem;border-radius:6px">
              <strong style="font-size:0.85rem">Affected Buildings in Dataset (${res.affected_addresses_count} total):</strong>
              <ul style="font-size:0.85rem;margin:0.5rem 0 0 1rem;padding:0">
                ${sampleAddrsHtml}
              </ul>
            </div>
          `
              : `<p class="meta-row">No sample addresses in dataset for ${esc(payload.city)}, ${esc(payload.state)} (Live new jurisdiction simulation).</p>`
          }
        </div>
      `;
    } catch (e) {
      out.innerHTML = `<p class="empty" style="color:var(--warn)">Error during extraction: ${esc(e.message)}</p>`;
    } finally {
      btn.disabled = false;
    }
  });
}

function bindEvents() {
  $("#search-input")?.addEventListener("input", (e) => showSuggestions(e.target.value));
  $("#search-input")?.addEventListener("focus", (e) => showSuggestions(e.target.value));
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-panel")) $("#suggestions")?.classList.remove("open");
  });
  $("#lookup-btn")?.addEventListener("click", runLookup);
  $("#compare-dates-btn")?.addEventListener("click", runCompare);
  $("#how-btn")?.addEventListener("click", runHowDecided);
  $("#open-q-btn")?.addEventListener("click", toggleOpenQPanel);
  $("#live-ingest-btn")?.addEventListener("click", toggleLiveIngestPanel);
  $("#theme-toggle")?.addEventListener("click", () => {
    theme = theme === "dark" ? "light" : "dark";
    applyTheme();
  });
  $("#lang-toggle")?.addEventListener("click", () => {
    lang = lang === "en" ? "es" : "en";
    applyI18n();
    if (currentData) renderResults(currentData);
  });
  document.querySelectorAll(".test-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.test;
      const p = TEST_PRESETS[key];
      if (!p) return;
      selectedId = p.id;
      const a = addresses.find((x) => x.address_id === p.id);
      if (a) $("#search-input").value = formatAddr(a);
      $("#asof").value = p.asof;
      runLookup();
    });
  });
  document.querySelectorAll(".city-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const city = btn.dataset.city;
      const a = addresses.find(
        (x) =>
          (x.legal_city || "").toLowerCase() === city.toLowerCase() ||
          (x.postal_city || "").toLowerCase() === city.toLowerCase()
      );
      if (a) {
        selectedId = a.address_id;
        $("#search-input").value = formatAddr(a);
        runLookup();
      }
    });
  });
}

async function loadScorecard() {
  const big = $("#score-big");
  if (!big) return;
  try {
    const d = await fetch("/api/eval").then((r) => r.json());
    const passed = d.passed ?? 0;
    const total = d.total ?? 5;
    const goldP = d.gold_passed ?? 0;
    const goldT = d.gold_total ?? 10;
    big.textContent = `${passed}/${total} change tests pass`;
    const sub = $("#score-gold");
    if (sub) sub.textContent = `${goldP}/${goldT} gold checks · not official score.py`;
    const pills = $("#score-pills");
    if (pills && d.change_tests) {
      pills.innerHTML = d.change_tests
        .map(
          (t) =>
            `<span class="pill ${t.pass ? "pass" : ""}">${esc(t.test_id)} ${t.pass ? "PASS" : "FAIL"}</span>`
        )
        .join("");
    }
  } catch {
    big.textContent = "Run eval harness locally";
  }
}

export async function initApp() {
  applyTheme();
  applyI18n();
  await loadAddresses();
  bindEvents();
  loadScorecard();
  const demo = addresses.find((a) => a.address_id === "A0016") || addresses[0];
  if (demo) {
    selectedId = demo.address_id;
    $("#search-input").value = formatAddr(demo);
    await runLookup();
  }
}

if (document.body.dataset.page === "home") {
  initApp();
}
