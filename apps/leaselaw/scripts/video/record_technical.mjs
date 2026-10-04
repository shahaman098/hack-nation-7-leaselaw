#!/usr/bin/env node
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

  await page.goto(`${LIVE}/pipeline`, { waitUntil: "networkidle" });
  await sleep(12000);

  await page.goto(`${LIVE}/`, { waitUntil: "networkidle" });
  await sleep(5000);
  await page.click('.city-btn[data-city="San Francisco"]');
  await sleep(8000);

  await page.goto(`${LIVE}/health`, { waitUntil: "networkidle" });
  await sleep(8000);

  await page.evaluate(async (base) => {
    const r = await fetch(`${base}/api/eval`);
    const d = await r.json();
    document.body.innerHTML = `<pre style="font:14px/1.4 monospace;padding:2rem">${JSON.stringify(d, null, 2)}</pre>`;
  }, LIVE);
  await sleep(15000);

  const video = page.video();
  await context.close();
  await browser.close();
  if (video) {
    const saved = await video.path();
    const dest = path.join(OUT, "technical.webm");
    const fs = await import("fs/promises");
    await fs.rename(saved, dest);
    console.log("Saved", dest);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
