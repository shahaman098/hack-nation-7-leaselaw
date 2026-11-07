#!/usr/bin/env node
import { chromium } from "playwright";
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";
import { runBeatAction, sleep } from "./beat_actions.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "../../../..");
const OUT_SCREEN = path.join(REPO, "docs/hn7-submission-pack/videos/out/screen");
const OUT_AUDIO = path.join(REPO, "docs/hn7-submission-pack/videos/out/audio");
const LIVE = process.env.LIVE_URL || "https://leaselaw-navigator.onrender.com";

async function loadManifest(track) {
  const p = path.join(OUT_AUDIO, track, "manifest.json");
  return JSON.parse(await fs.readFile(p, "utf8"));
}

async function recordTrack(track) {
  const manifest = await loadManifest(track);
  const segDir = path.join(OUT_SCREEN, track);
  await fs.mkdir(segDir, { recursive: true });

  for (const seg of manifest.segments) {
    const holdMs = Math.max(800, Math.ceil(seg.duration_sec * 1000) + 500);
    console.log(`[${track}] ${seg.id} audio=${seg.duration_sec}s hold=${holdMs}ms`);

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      recordVideo: { dir: segDir, size: { width: 1920, height: 1080 } },
    });
    const page = await context.newPage();
    page.setDefaultTimeout(90000);

    await runBeatAction(page, LIVE, seg.action);
    await sleep(holdMs);

    const video = page.video();
    await context.close();
    await browser.close();

    if (video) {
      const saved = await video.path();
      const dest = path.join(segDir, `${seg.id}.webm`);
      await fs.rename(saved, dest);
      console.log("  ->", dest);
    }
  }
}

const track = process.argv[2];
if (!track) {
  console.error("Usage: node record_beats.mjs team|demo|technical");
  process.exit(1);
}

recordTrack(track).catch((e) => {
  console.error(e);
  process.exit(1);
});
