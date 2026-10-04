#!/usr/bin/env node
/** Team video: logo + title slides (voice in post). */
import { chromium } from "playwright";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "../../../..");
const OUT = path.join(REPO, "docs/hn7-submission-pack/videos/out/screen");
const LIVE = process.env.LIVE_URL || "https://leaselaw-navigator.onrender.com";

async function sleep(ms) {
  await new Promise((r) => setTimeout(r, ms));
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: { dir: OUT, size: { width: 1920, height: 1080 } },
  });
  const page = await context.newPage();

  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/>
  <style>
    body{margin:0;font-family:system-ui,sans-serif;background:#f8f9fc;color:#0f1419;
      display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;padding:2rem}
    h1{font-size:3rem;margin:0.5rem 0} p{font-size:1.35rem;color:#5c6570;max-width:40rem;margin:0 auto 1rem}
    img{width:96px;height:96px;border-radius:16px}
  </style></head><body>
  <div id="s1"><img src="${LIVE}/static/logo-mark.svg" alt=""/><h1>LeaseLaw Navigator</h1>
  <p>Hack Nation 7 · Track 02 RealPage</p></div>
  </body></html>`;

  await page.setContent(html);
  await sleep(12000);
  await page.evaluate(() => {
    document.body.innerHTML = `<div><h1>One address. One date.</h1>
    <p>Which rental housing rules apply?</p><p style="margin-top:2rem;font-size:1rem">Not legal advice</p></div>`;
  });
  await sleep(8000);
  await page.goto(LIVE, { waitUntil: "networkidle" });
  await sleep(12000);

  const video = page.video();
  await context.close();
  await browser.close();
  if (video) {
    const saved = await video.path();
    const dest = path.join(OUT, "team.webm");
    const fs = await import("fs/promises");
    await fs.rename(saved, dest);
    console.log("Saved", dest);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
