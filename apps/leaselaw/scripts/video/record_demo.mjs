#!/usr/bin/env node
/**
 * Demo video screen capture (no audio). Pair with demo.mp3 in assemble.sh
 */
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
  page.setDefaultTimeout(60000);

  console.log("Opening", LIVE);
  await page.goto(LIVE, { waitUntil: "networkidle" });
  await sleep(5000);

  await page.click('button[data-test="T1"]');
  await sleep(7000);

  await page.click('button[data-test="T1b"]');
  await sleep(7000);

  await page.click('button[data-test="T2"]');
  await sleep(6000);

  await page.click('button[data-test="T4"]');
  await sleep(6000);

  await page.click("#lang-toggle");
  await sleep(4000);

  await page.click("#how-btn");
  await sleep(7000);

  await page.evaluate(async (base) => {
    const r = await fetch(`${base}/api/eval`);
    const d = await r.json();
    document.body.innerHTML = `<div style="font-family:monospace;padding:2rem;background:#fff;color:#111">
    <h2 style="font-family:system-ui">Score report (change tests)</h2>
    <pre style="font-size:14px;white-space:pre-wrap">${JSON.stringify(d, null, 2)}</pre></div>`;
  }, LIVE);
  await sleep(6000);

  const video = page.video();
  await context.close();
  await browser.close();
  if (video) {
    const saved = await video.path();
    const dest = path.join(OUT, "demo.webm");
    const fs = await import("fs/promises");
    await fs.rename(saved, dest);
    console.log("Saved", dest);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
