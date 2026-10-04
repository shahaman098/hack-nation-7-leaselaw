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

function ruleSummary(r) {
  if (lang === "es" && r.plain_language_es) return r.plain_language_es;
  return r.plain_language || r.explanation || r.title || "";
}

function renderRuleCard(r) {
  const conf = Math.round((r.confidence ?? 0.75) * 100);
  const badge = resultLabel(lang, r.result);
  const cat = categoryLabel(lang, r.category);
  const title = r.title || r.citation || cat;
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
      ${r.conflict_flag ? `<span class="conflict">⚠ ${esc(t(lang, "conflict"))}${r.conflict_note ? ": " + esc(r.conflict_note) : ""}</span>` : ""}
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
      const br = b?.result || "—";
      const ar = a?.result || "—";
      if (br !== ar) {
        const name = a?.title || b?.title || a?.citation || b?.citation || categoryLabel(lang, a?.category || b?.category);
        changes.push({ name, br, ar, a: a || b });
      }
    }
    let html = `<h2 class="section-title">${esc(t(lang, "compareTitle"))}</h2>`;
    html += `<p class="meta-row">${esc(t(lang, "compareBefore"))}: Dec 31, 2025 · ${esc(t(lang, "compareAfter"))}: Jan 2, 2026</p>`;
    if (!changes.length) {
      html += `<p class="empty">No rule status changes between these dates for this address.</p>`;
    } else {
      for (const c of changes) {
        html += `<article class="rule-card">
          <div class="rule-title">${esc(c.name)}</div>
          <p class="plain">${esc(resultLabel(lang, c.br))} → ${esc(resultLabel(lang, c.ar))}</p>
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

export async function initApp() {
  applyTheme();
  applyI18n();
  await loadAddresses();
  bindEvents();
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
