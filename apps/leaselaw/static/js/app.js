import { t } from "./i18n.js";

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
  $("#lang-toggle")?.textContent = t(lang, "lang");
  $("#search-input")?.setAttribute("placeholder", t(lang, "searchPlaceholder"));
}

async function loadAddresses() {
  const r = await fetch("/api/addresses?limit=500");
  addresses = await r.json();
}

function formatAddr(a) {
  const street = a.street || a.street_address || "";
  const city = a.legal_city || a.postal_city || "";
  return `${street}, ${city} ${a.state} (${a.address_id})`;
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
      const hay = `${a.address_id} ${a.street_address || a.street} ${a.postal_city} ${a.legal_city || ""} ${a.state}`.toLowerCase();
      return hay.includes(ql);
    })
    .slice(0, 12);
  box.innerHTML = hits
    .map(
      (a, i) =>
        `<button type="button" data-id="${a.address_id}" aria-selected="${i === 0}">${formatAddr(a)}</button>`
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

function renderResults(data) {
  currentData = data;
  const root = $("#results");
  if (!root) return;
  if (!data || !data.address_id) {
    root.innerHTML = `<p class="empty">${esc(t(lang, "selectAddress"))}</p>`;
    return;
  }

  const stack = (data.jurisdiction_stack || []).map((s) => `<span class="stack-chip">${esc(s)}</span>`).join("");
  const grouped = groupRules(data.rules);
  let html = `
    <div class="results-header">
      <div>
        <div class="rule-title">${esc(data.street)}, ${esc(data.postal_city)} ${esc(data.state)}</div>
        <div class="meta-row">${esc(data.address_id)} · as-of ${esc(data.as_of)}</div>
      </div>
      <div class="stack-chips">${stack}</div>
    </div>`;

  for (const [resultKey, labelKey] of GROUP_ORDER) {
    const items = grouped.get(resultKey);
    if (!items?.length) continue;
    html += `<h3 class="section-title">${esc(t(lang, labelKey))}</h3>`;
    for (const r of items) {
      const conf = Math.round((r.confidence ?? 0.75) * 100);
      const plain = lang === "es" && r.plain_language_es ? r.plain_language_es : r.plain_language || r.explanation;
      html += `
        <article class="rule-card">
          <div class="rule-top">
            <div>
              <div class="rule-id">${esc(r.team_rule_id)} · ${esc(r.category || "")}</div>
              <div class="rule-title">${esc(r.citation || r.team_rule_id)}</div>
            </div>
            <span class="result-badge ${esc(r.result)}">${esc(r.result)}</span>
          </div>
          <p class="plain">${esc(plain)}</p>
          ${r.conflict_flag ? `<span class="conflict">⚠ ${esc(t(lang, "conflict"))}${r.conflict_note ? ": " + esc(r.conflict_note) : ""}</span>` : ""}
          <div class="conf-bar" title="${esc(t(lang, "confidence"))}"><span style="width:${conf}%"></span></div>
          <div class="meta-row">
            <span>${esc(r.source_doc_id || "")}</span>
            <span>${esc(t(lang, "retrieved"))}: ${esc(r.source_retrieved_at || "—")}</span>
          </div>
          <details class="source">
            <summary>${esc(t(lang, "source"))}</summary>
            <div class="quote">${esc(r.quoted_span || "")}</div>
            ${r.source_url ? `<p><a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(r.source_url)}</a></p>` : ""}
          </details>
        </article>`;
    }
  }

  const failed = data.failed_or_not_applied || [];
  if (failed.length) {
    html += `<h3 class="section-title">${esc(t(lang, "failed"))}</h3>`;
    for (const r of failed) {
      html += `<article class="rule-card"><div class="rule-id">${esc(r.team_rule_id)}</div><p class="plain">${esc(r.explanation)}</p></article>`;
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
    $("#results").innerHTML = `<p class="empty">${esc(t(lang, "error"))}: ${esc(e.message)}</p>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function runCompare() {
  if (!selectedId) return;
  const btn = $("#lookup-btn");
  if (btn) btn.disabled = true;
  try {
    const r = await fetch(
      `/api/compare?address_id=${encodeURIComponent(selectedId)}&before=2025-12-31&after=2026-01-02`
    );
    const d = await r.json();
    $("#results").innerHTML = `<pre class="json-dump">${esc(JSON.stringify(d, null, 2))}</pre>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function runAudit() {
  if (!selectedId) return;
  const asof = $("#asof")?.value || "2026-10-01";
  const r = await fetch(`/api/audit/${encodeURIComponent(selectedId)}?as_of=${encodeURIComponent(asof)}`);
  const d = await r.json();
  $("#results").innerHTML = `<pre class="json-dump">${esc(JSON.stringify(d, null, 2))}</pre>`;
}

async function loadEval() {
  try {
    const d = await fetch("/api/eval").then((r) => r.json());
    const q = d.quality_scorecard || {};
    $("#score-big").textContent = `${d.passed ?? 0}/${d.total ?? 0}`;
    $("#score-sub").textContent = `gold ${d.gold_passed ?? 0}/${d.gold_total ?? 0} · ${q.rules_count ?? "—"} rules · ${q.quoted_span_literal ?? "—"} literal spans`;
    const pills = $("#eval-pills");
    if (pills) {
      pills.innerHTML = (d.change_tests || [])
        .map(
          (x) =>
            `<span class="pill ${x.pass ? "ok" : "bad"}">${esc(x.test_id)} ${x.pass ? "PASS" : "FAIL"}</span>`
        )
        .join("");
    }
  } catch {
    $("#score-big").textContent = "—";
  }
}

const TEST_PRESETS = {
  T1: { id: "A0001", asof: "2025-12-31" },
  T1b: { id: "A0001", asof: "2026-01-02" },
  T2: { id: "A0002", asof: "2026-10-01" },
  T3: { id: "A0002", asof: "2027-07-02" },
  T4: { id: "A0006", asof: "2026-10-01" },
  T5: { id: "A0006", asof: "2026-10-01" },
};

function bindEvents() {
  $("#search-input")?.addEventListener("input", (e) => showSuggestions(e.target.value));
  $("#search-input")?.addEventListener("focus", (e) => showSuggestions(e.target.value));
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-panel")) $("#suggestions")?.classList.remove("open");
  });
  $("#lookup-btn")?.addEventListener("click", runLookup);
  $("#ab325-btn")?.addEventListener("click", runCompare);
  $("#audit-btn")?.addEventListener("click", runAudit);
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
}

export async function initApp() {
  applyTheme();
  applyI18n();
  await loadAddresses();
  bindEvents();
  await loadEval();
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
