#!/usr/bin/env node
/**
 * Cursor-driven screen capture for the three HN7 videos, cued to the ElevenLabs narration.
 *
 *   node record_cursor.mjs demo|team|technical|all
 *
 * Needs out/audio/<track>.alignment.json (generate_voiceover.py --timestamps).
 * Writes out/screen/<track>.webm + <track>.json (cut points for assemble.sh).
 * HackOS + the Google Form cap each video at 60 seconds; keep narrations under ~55s.
 */
import { execSync } from "child_process";
import path from "path";
import { fileURLToPath, pathToFileURL } from "url";
import { APP, LIVE, Stage, makeDirector, sleep } from "./cursor_kit.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RESULTS = "#results .results-header";
const ALG = '.rule-card[data-rule-id="CA-ALG-01"]';

async function waitResults(page, needle) {
  await page.waitForFunction(
    (n) => {
      const h = document.querySelector("#results .results-header");
      return h && h.textContent.includes(n);
    },
    needle,
    { timeout: 30000 }
  );
}

async function waitAudit(page) {
  await page.waitForFunction(
    () => document.querySelectorAll("#results article.rule-card").length > 0 && !document.querySelector("#results .results-header")
  );
}

/** Live /api/eval with the change-test and gold totals highlighted as they are spoken. */
async function showScores(s, d, { changePhrase, goldPhrase }) {
  await s.prettyJson(`${LIVE}/api/eval`);
  await d.cue(changePhrase, -0.1);
  await s.mark('.ln:has-text("\\"passed\\": 5")');
  await s.mark('.ln:has-text("\\"total\\": 5")');
  await s.hover('.ln:has-text("\\"passed\\": 5")', { fx: 0.12, ms: 500 });
  await d.cue(goldPhrase, -0.2);
  await s.scrollToEl('.ln:has-text("gold_passed")', { frac: 0.5, ms: 700 });
  await s.mark('.ln:has-text("gold_passed")');
  await s.mark('.ln:has-text("gold_total")');
  await s.hover('.ln:has-text("gold_passed")', { fx: 0.14, ms: 500 });
}

// ───────────────────────────── DEMO ─────────────────────────────
async function demo() {
  const d = makeDirector("demo");
  const s = new Stage("demo");
  const page = await s.open(LIVE, RESULTS);
  s.markStart(d);

  await d.cue("The banner says", -0.3);
  await s.hover(".disclaimer-banner", { ms: 700 });

  await d.cue("I search for an address", -0.1);
  await s.typeInto("#search-input", "Los Angeles", { delay: 50, ms: 550 });

  await d.cue("Under Try an example", -0.3);
  await s.click(".hero .sub", { fx: 0.85, ms: 400 }); // click away: closes the suggestion list
  await s.hover('button[data-test="T1"]', { ms: 550 });
  await d.cue("I pick California before", 0.2);
  await s.click('button[data-test="T1"]', { ms: 200 });
  await waitResults(page, "2025-12-31");
  await d.cue("and click Check my address", 0.1);
  await s.click("#lookup-btn", { ms: 500 });
  await waitResults(page, "2025-12-31");

  await d.cue("The statewide algorithm pricing rule", -0.4);
  await s.scrollToEl(ALG, { frac: 0.28, ms: 600 });
  await s.hover(`${ALG} .result-badge`, { ms: 550 });

  await d.cue("I expand Read the original text", 0.1);
  await s.click(`${ALG} details.source summary`, { fx: 0.08, ms: 500 });
  await sleep(250);
  await s.hover(`${ALG} .quote`, { fx: 0.35, ms: 450 });

  await d.cue("Now California after", -0.4);
  await s.scrollToEl('button[data-test="T1b"]', { frac: 0.4, ms: 600 });
  await s.click('button[data-test="T1b"]', { ms: 450 });
  await waitResults(page, "2026-01-02");

  await d.cue("The same rule now shows Applies", -0.5);
  await s.scrollToEl(ALG, { frac: 0.28, ms: 600 });
  await s.hover(`${ALG} .result-badge`, { ms: 450 });

  await d.cue("Next, Hoboken", -0.5);
  await s.click('button[data-test="T2"]', { ms: 450 });
  await waitResults(page, "Hoboken");

  await d.cue("Then Boston", -0.3);
  await s.click('button[data-test="T4"]', { ms: 400 });
  await page.waitForSelector("#results .result-badge.pending");
  await d.cue("bills still pending");
  await s.scrollToEl("#results .result-badge.pending", { frac: 0.32, ms: 600 });
  await s.hover("#results .result-badge.pending", { ms: 450 });

  await d.cue("The ES button", -0.5);
  await s.scrollTop(500);
  await s.click("#lang-toggle", { ms: 500 });
  await s.hover(".hero h1", { fx: 0.3, fy: 0.4, ms: 600 });

  await d.cue("How we decided shows", -0.9);
  await s.click("#lang-toggle", { ms: 400 }); // back to English
  await s.click("#how-btn", { ms: 450 });
  await waitAudit(page);
  await d.cue("plain notes");
  await s.scrollToEl("#results", { frac: 0.15, ms: 700 });
  await s.hover("#results article.rule-card .plain", { fx: 0.3, ms: 450 });
  await d.cue("not a black box");
  await s.scrollBy(200, 700);

  await d.cue("Finally, the live score report", -0.5);
  await showScores(s, d, { changePhrase: "five out of five", goldPhrase: "ten of ten gold checks" });
  await d.cue("It is not a substitute");
  await s.scrollTop(600);
  await s.hover(".hdr .u", { fx: 0.6, ms: 600 });

  await s.finish(d);
}

// ───────────────────────────── TEAM ─────────────────────────────
async function team() {
  const d = makeDirector("team");
  const s = new Stage("team");
  const page = await s.open(LIVE, RESULTS);

  // Title card over the live page, faded away when the problem statement starts.
  await page.evaluate((logo) => {
    const t = document.createElement("div");
    t.id = "__title";
    t.style.cssText =
      "position:fixed;inset:0;z-index:2147483600;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;" +
      "background:radial-gradient(ellipse at 50% 35%,#ffffff 0%,#eef2fb 70%);font-family:system-ui,-apple-system,sans-serif;color:#0f1419;transition:opacity .9s";
    t.innerHTML = `<img src="${logo}" width="88" height="88" style="border-radius:20px;box-shadow:0 12px 30px rgba(37,99,235,.25)"/>
      <div style="font-size:52px;font-weight:700;letter-spacing:-.02em">LeaseLaw Navigator</div>
      <div style="font-size:21px;color:#5c6570">Hack-Nation 7 · Track 02 RealPage · solo build</div>
      <div style="margin-top:18px;font-size:14px;color:#b45309;font-weight:600">Not legal advice</div>`;
    document.documentElement.appendChild(t);
  }, `${LIVE}/static/logo-mark.svg`);
  await sleep(400);
  s.markStart(d);

  await d.cue("If you manage rentals", -0.2);
  await page.evaluate(() => {
    const t = document.getElementById("__title");
    t.style.opacity = "0";
    setTimeout(() => t.remove(), 1000);
  });

  await d.cue("It is knowing which city");
  await s.scrollToEl(RESULTS, { frac: 0.25, ms: 900 });
  await d.cue("city,", -0.1);
  await s.hover("#results .stack-chip:nth-child(3)");
  await d.cue("county,", -0.1);
  await s.hover("#results .stack-chip:nth-child(2)", { ms: 450 });
  await d.cue("and state", -0.1);
  await s.hover("#results .stack-chip:nth-child(1)", { ms: 450 });
  await d.cue("to one address", -0.1);
  await s.hover("#results .results-header .rule-title", { fx: 0.4 });
  await d.cue("on one date", -0.1);
  await s.hover("#results .results-header .meta-row", { fx: 0.4 });

  // "You enter an address and a date" is short, so start typing while the app is introduced.
  // Hoboken on the default date already shows applies / not yet in effect / need more information.
  await d.cue("I built LeaseLaw Navigator", -0.3);
  await s.scrollTop(500);
  await s.typeInto("#search-input", "Hobo", { delay: 55, ms: 550 });
  await page.waitForSelector("#suggestions.open button");
  await s.click("#suggestions button:nth-child(2)", { fx: 0.3, ms: 400 });
  await waitResults(page, "Hoboken");
  await d.cue("and a date", -0.2);
  await s.hover("#asof", { fx: 0.3, ms: 400 });
  await sleep(250);
  await s.click("#lookup-btn", { ms: 400 });
  await waitResults(page, "Hoboken");
  await s.scrollToEl("#results .result-badge.applies", { frac: 0.2, ms: 500 });

  await d.cue("what applies", -0.2);
  await s.hover("#results .result-badge.applies");
  await d.cue("what does not apply yet", -0.1);
  await s.hover("#results .result-badge.not_yet_effective");
  await d.cue("what we cannot decide", -0.1);
  await s.hover("#results .result-badge.unknown");

  await d.cue("Every answer links back", -0.2);
  await s.click("#results .rule-card details.source summary", { fx: 0.08 });
  await sleep(300);
  await s.hover("#results .rule-card details[open] .quote", { fx: 0.35 });

  await d.cue("It is not legal advice", -0.3);
  await s.scrollTop(700);
  await s.hover(".disclaimer-banner");

  await d.cue("On five hundred sample addresses", -0.2);
  await showScores(s, d, { changePhrase: "five of five change tests", goldPhrase: "ten of ten gold checks" });

  await s.finish(d);
}

// ─────────────────────────── TECHNICAL ──────────────────────────
function run(cmd) {
  try {
    return execSync(cmd, { cwd: APP, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  } catch (e) {
    return (e.stdout || "") + (e.stderr || "");
  }
}

async function technical() {
  // Capture genuine terminal output before recording starts.
  const changesCmd =
    "python3 -c \"import json; [print(k, len(v['affected_address_ids']), 'addresses') for k,v in json.load(open('out/changes.json')).items()]\"";
  const changesOut = run(changesCmd);
  let harnessOut;
  try {
    harnessOut = execSync("python3 -m src.eval_harness", { cwd: APP, encoding: "utf8" });
  } catch (e) {
    throw new Error("eval_harness failed; refusing to record a passing terminal");
  }

  const d = makeDirector("technical");
  const s = new Stage("technical");
  const page = await s.open(`${LIVE}/pipeline`, "#pipeline-steps > *");
  s.markStart(d);

  const step = (n) => `#pipeline-steps > :nth-child(${n})`;
  await s.hover(".hero h1", { fx: 0.4, ms: 900 });
  await d.cue("Module A extracts rules", -0.2);
  await s.hover(step(1), { fx: 0.15, ms: 600 });

  await d.cue("The challenge was trust", -0.2);
  await s.click(".nav a.btn-icon", { ms: 600 });
  await page.waitForSelector(RESULTS);
  await s.ensureCursor();

  const firstCard = "#results .rule-card";
  await d.cue("So we keep a rule only if", -0.3);
  await s.scrollToEl(firstCard, { frac: 0.3, ms: 600 });
  await s.click(`${firstCard} details.source summary`, { fx: 0.08, ms: 500 });
  await sleep(250);
  await s.hover(`${firstCard} details[open] .quote`, { fx: 0.35, ms: 450 });

  await d.cue("and How we decided", -0.5);
  await s.scrollTop(500);
  await s.click("#how-btn", { ms: 450 });
  await waitAudit(page);
  await d.cue("audit trail", -0.1);
  await s.scrollToEl("#results", { frac: 0.12, ms: 600 });
  await s.hover("#results article.rule-card .plain", { fx: 0.35, ms: 450 });

  await d.cue("Module B matches addresses", -0.3);
  await s.scrollTop(500);
  await d.cue("Postal cities map", -0.1);
  await s.typeInto("#search-input", "Dorchester", { delay: 45, ms: 500 });
  await page.waitForSelector("#suggestions.open button");
  await s.hover("#suggestions button:nth-child(1)", { fx: 0.55, ms: 400 });
  await d.cue("San Ysidro", -0.4);
  await s.typeInto("#search-input", "San Ysidro", { delay: 40, ms: 400 });
  await page.waitForSelector("#suggestions.open button");
  await d.cue("to San Diego", -0.1);
  await s.click("#suggestions button:nth-child(1)", { fx: 0.55, ms: 400 });
  await waitResults(page, "CYPRESS");
  await s.hover("#results .stack-chip:nth-child(3)", { ms: 450 });

  await d.cue("Missing building facts", -0.2);
  await s.scrollToEl("#results .result-badge.unknown", { frac: 0.35, ms: 700 });
  await s.hover("#results .result-badge.unknown", { ms: 450 });
  await d.cue("Instead of guessing");
  await s.hover('#results .rule-card:has(.result-badge.unknown) .plain', { fx: 0.4, ms: 500 });

  await d.cue("Module C tracks changes", -0.4);
  await s.goto(pathToFileURL(path.join(__dirname, "terminal.html")).href, "#out");
  await s.moveTo(1180, 660, 400);
  await page.evaluate(
    async ({ cmd, out }) => {
      term.prompt();
      await term.type(cmd, 1100);
      await term.print(out, 400);
      term.prompt();
    },
    { cmd: changesCmd, out: changesOut }
  );

  await d.cue("The eval harness exits zero", -0.6);
  await page.evaluate(async (out) => {
    await term.type("python3 -m src.eval_harness", 900);
    await term.print(out, 1500);
    term.prompt();
    await term.type('echo "exit code $?"', 450);
    await term.print("exit code 0");
    term.prompt();
  }, harnessOut);

  await d.cue("Limitations", -0.4);
  await s.prettyJson(`${LIVE}/api/eval`);
  await s.scrollToEl('.ln:has-text("quoted_span_gaps")', { frac: 0.4, ms: 600 });
  await s.mark('.ln:has-text("quoted_span_literal")');
  await s.mark('.ln:has-text("quoted_span_gaps")');
  await d.cue("one Hoboken rule", -0.1);
  await s.hover('.ln:has-text("quoted_span_gaps")', { fx: 0.16, ms: 600 });

  await s.finish(d);
}

const SCENES = { demo, team, technical };
const which = process.argv[2] || "all";
const list = which === "all" ? ["team", "demo", "technical"] : [which];
for (const name of list) {
  if (!SCENES[name]) throw new Error(`unknown track ${name}`);
  console.log(`▶ recording ${name}`);
  try {
    await SCENES[name]();
  } catch (e) {
    const shot = process.env.FAIL_SHOT;
    if (shot && Stage.last?.page) await Stage.last.page.screenshot({ path: shot }).catch(() => {});
    if (process.env.DEBUG && Stage.last?.page) {
      const st = await Stage.last.page
        .evaluate(() => ({ asof: document.querySelector("#asof")?.value, results: document.querySelector("#results")?.innerText.slice(0, 300) }))
        .catch((x) => String(x));
      console.log("DEBUG state:", st);
    }
    throw e;
  }
}
