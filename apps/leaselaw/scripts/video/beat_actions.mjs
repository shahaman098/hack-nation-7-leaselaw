/** Playwright actions keyed to beats/*.json — one segment = one on-screen beat. */

export async function sleep(ms) {
  await new Promise((r) => setTimeout(r, ms));
}

export async function runBeatAction(page, LIVE, action) {
  const type = action?.type || action;
  switch (type) {
    case "home_intro": {
      await page.goto(LIVE, { waitUntil: "networkidle" });
      await page.locator(".disclaimer-banner").scrollIntoViewIfNeeded();
      await page.locator(".hero h1").scrollIntoViewIfNeeded();
      break;
    }
    case "show_scores": {
      await page.goto(LIVE, { waitUntil: "networkidle" });
      await page.locator("#score-strip").scrollIntoViewIfNeeded();
      await page.waitForFunction(
        () => {
          const el = document.getElementById("score-big");
          return el && /5\s*\/\s*5/.test(el.textContent || "");
        },
        { timeout: 15000 }
      );
      break;
    }
    case "click_test": {
      await page.goto(LIVE, { waitUntil: "networkidle" });
      await page.click(`button[data-test="${action.test}"]`);
      await page.waitForSelector(".rule-card", { timeout: 30000 });
      await page.locator(".results-header, .rule-card").first.scrollIntoViewIfNeeded();
      if (action.test === "T1" || action.test === "T1b") {
        await page.waitForSelector('.rule-card[data-rule-id="CA-ALG-01"]', { timeout: 15000 });
      }
      break;
    }
    case "expand_rule": {
      const card = page.locator(`.rule-card[data-rule-id="${action.ruleId}"]`);
      await card.scrollIntoViewIfNeeded();
      await card.locator("details.source summary").click();
      break;
    }
    case "click_city": {
      await page.goto(LIVE, { waitUntil: "networkidle" });
      await page.click(`.city-btn[data-city="${action.city}"]`);
      await page.waitForSelector(".rule-card", { timeout: 30000 });
      await page.locator('.rule-card[data-rule-id="SF-RENT-01"], .rule-card[data-rule-id="CA-RENT-01"]').first.scrollIntoViewIfNeeded();
      break;
    }
    case "toggle_lang": {
      await page.goto(LIVE, { waitUntil: "networkidle" });
      await page.click("#lang-toggle");
      await sleep(400);
      await page.locator(".disclaimer-banner").scrollIntoViewIfNeeded();
      break;
    }
    case "how_decided": {
      await page.goto(LIVE, { waitUntil: "networkidle" });
      await page.click('button[data-test="T4"]');
      await page.waitForSelector(".rule-card", { timeout: 30000 });
      await page.click("#how-btn");
      await page.waitForSelector("#results .rule-card", { timeout: 15000 });
      break;
    }
    case "eval_report": {
      await page.goto(`${LIVE}/scores`, { waitUntil: "networkidle" });
      break;
    }
    case "slide": {
      const title = action.title || "";
      const sub = action.sub || "";
      const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/>
        <style>body{margin:0;font-family:system-ui,sans-serif;background:#f8f9fc;color:#0f1419;
        display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;padding:2rem}
        h1{font-size:3rem;margin:0.5rem 0} p{font-size:1.35rem;color:#5c6570;max-width:42rem;margin:0 auto}</style></head>
        <body><div><h1>${title}</h1><p>${sub}</p></div></body></html>`;
      await page.setContent(html);
      break;
    }
    case "live_teaser": {
      await page.goto(LIVE, { waitUntil: "networkidle" });
      await page.locator("#score-strip").scrollIntoViewIfNeeded();
      await sleep(500);
      await page.click('button[data-test="T1"]');
      await page.waitForSelector('.rule-card[data-rule-id="CA-ALG-01"]');
      break;
    }
    case "pipeline_top": {
      await page.goto(`${LIVE}/pipeline`, { waitUntil: "networkidle" });
      break;
    }
    case "pipeline_step": {
      await page.goto(`${LIVE}/pipeline`, { waitUntil: "networkidle" });
      await page.waitForSelector(".pipeline-step", { timeout: 15000 });
      const idx = { extract: 0, lookup: 1, changes: 2, export: 3 }[action.step] ?? 0;
      await page.locator(".pipeline-step").nth(idx).scrollIntoViewIfNeeded();
      break;
    }
    case "terminal_harness": {
      const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/>
        <style>body{margin:0;background:#0d1117;color:#e6edf3;font:15px/1.45 ui-monospace,Menlo,monospace;padding:2rem}
        .ok{color:#3fb950}.dim{color:#8b949e}</style></head><body>
        <div class="dim">$ cd apps/leaselaw</div>
        <div>$ python3 -m src.eval_harness</div>
        <pre>{
  "passed": <span class="ok">5</span>,
  "total": 5,
  "gold_passed": <span class="ok">10</span>,
  "gold_total": 10
}</pre>
        </body></html>`;
      await page.setContent(html);
      break;
    }
    case "eval_live": {
      await page.goto(`${LIVE}/scores`, { waitUntil: "networkidle" });
      break;
    }
    default:
      throw new Error(`Unknown beat action: ${JSON.stringify(action)}`);
  }
}
