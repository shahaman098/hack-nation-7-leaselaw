/**
 * Shared helpers for the cursor-driven submission videos.
 *
 * - Draws a visible arrow cursor + click ripple (headless Chromium has none).
 *   The overlay follows real CDP mouse events, so hover states and clicks are genuine.
 * - Eased, slightly curved pointer moves and smooth scrolling.
 * - A "director" that waits for words in the ElevenLabs narration, using the
 *   character timings from generate_voiceover.py --timestamps.
 */
import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const REPO = path.resolve(__dirname, "../../../..");
export const APP = path.join(REPO, "apps/leaselaw");
export const VIDEOS = path.join(REPO, "docs/hn7-submission-pack/videos");
export const AUDIO = path.join(VIDEOS, "out/audio");
export const SCREEN = path.join(VIDEOS, "out/screen");
export const LIVE = (process.env.LIVE_URL || "https://leaselaw-navigator.onrender.com").replace(/\/$/, "");

// 1280x720 CSS px keeps text readable. Playwright records at viewport size (it pads rather
// than scales a larger recordVideo size), so capture 1280x720; assemble.sh upscales to 1080p.
const VIEWPORT = { width: 1280, height: 720 };
const VIDEO_SIZE = VIEWPORT;

export const sleep = (ms) => new Promise((r) => setTimeout(r, Math.max(0, ms)));

/** Runs in the page. Idempotent; survives body.innerHTML swaps (mounted on <html>). */
const CURSOR_SRC = `(() => {
  const install = () => {
    if (document.getElementById("__cur")) return;
    const st = document.createElement("style");
    st.textContent = \`
      html{scroll-behavior:auto !important}
      #__cur{position:fixed;left:0;top:0;width:30px;height:30px;z-index:2147483647;pointer-events:none;
        transform:translate(-200px,-200px);will-change:transform}
      #__cur svg{display:block;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35));transform-origin:5px 3px;transition:transform .09s}
      #__cur.down svg{transform:scale(.82)}
      .__rip{position:fixed;z-index:2147483646;pointer-events:none;width:46px;height:46px;margin:-23px 0 0 -23px;
        border-radius:50%;background:rgba(37,99,235,.22);border:2px solid rgba(37,99,235,.75);
        animation:__rip .6s ease-out forwards}
      @keyframes __rip{from{transform:scale(.25);opacity:1}to{transform:scale(1.5);opacity:0}}\`;
    document.documentElement.appendChild(st);
    const c = document.createElement("div");
    c.id = "__cur";
    c.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M4 2.5 L4 19.5 L8.6 15.3 L11.6 22 L14.6 20.7 L11.7 14.1 L18 14.1 Z" fill="#111" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>';
    document.documentElement.appendChild(c);
    // Arrow tip sits at (4,2.5) in a 24-unit box drawn at 30px → (5,3.1) px.
    const place = (x, y) => { c.style.transform = "translate(" + (x - 5) + "px," + (y - 3) + "px)"; };
    addEventListener("mousemove", (e) => place(e.clientX, e.clientY), true);
    addEventListener("mousedown", (e) => {
      c.classList.add("down");
      const r = document.createElement("div");
      r.className = "__rip";
      r.style.left = e.clientX + "px";
      r.style.top = e.clientY + "px";
      document.documentElement.appendChild(r);
      setTimeout(() => r.remove(), 700);
    }, true);
    addEventListener("mouseup", () => c.classList.remove("down"), true);
  };
  if (document.documentElement) install();
  else document.addEventListener("DOMContentLoaded", install);
})();`;

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

/** Loads narration timings and waits for spoken words. */
export function makeDirector(track) {
  const a = JSON.parse(fs.readFileSync(path.join(AUDIO, `${track}.alignment.json`), "utf8"));
  const text = a.characters.join("");
  const starts = a.character_start_times_seconds;
  const audioEnd = a.character_end_times_seconds.at(-1);
  let cursorIdx = 0;
  let t0 = null;

  /** Time (s) a phrase starts being spoken; searches forward so repeated words resolve in order. */
  const timeOf = (phrase) => {
    const i = text.indexOf(phrase, cursorIdx);
    if (i < 0) throw new Error(`[${track}] phrase not in narration (after idx ${cursorIdx}): "${phrase}"`);
    cursorIdx = i;
    return starts[i];
  };

  return {
    audioEnd,
    start() {
      t0 = Date.now();
    },
    now() {
      return (Date.now() - t0) / 1000;
    },
    /** Wait until `phrase` starts (+offset seconds). Negative offset = act slightly before the word. */
    async cue(phrase, offset = 0) {
      const target = timeOf(phrase) + offset;
      if (process.env.FAST) return;
      const lag = this.now() - target;
      if (lag > 0.4) console.warn(`  [${track}] late by ${lag.toFixed(2)}s at "${phrase}"`);
      await sleep((target - this.now()) * 1000);
    },
    async at(seconds) {
      await sleep((seconds - this.now()) * 1000);
    },
  };
}

export class Stage {
  constructor(track) {
    this.track = track;
    this.pos = { x: VIEWPORT.width * 0.62, y: VIEWPORT.height * 0.55 };
    Stage.last = this;
  }

  async open(url, readySelector) {
    // Wake Render before the camera rolls.
    for (let i = 0; i < 6; i++) {
      try {
        const r = await fetch(`${LIVE}/health`);
        if (r.ok) break;
      } catch {}
      await sleep(10000);
    }
    fs.mkdirSync(SCREEN, { recursive: true });
    // --lang drives the native date-input format (mm/dd/yyyy for US judges).
    this.browser = await chromium.launch({ headless: true, args: ["--lang=en-US"], env: { ...process.env, LANG: "en_US.UTF-8" } });
    this.context = await this.browser.newContext({
      viewport: VIEWPORT,
      deviceScaleFactor: 1.5,
      locale: "en-US",
      timezoneId: "America/New_York",
      colorScheme: "light",
      recordVideo: { dir: SCREEN, size: VIDEO_SIZE },
    });
    await this.context.addInitScript(CURSOR_SRC);
    this.recStart = Date.now();
    this.page = await this.context.newPage();
    this.page.setDefaultTimeout(60000);
    await this.goto(url, readySelector);
    return this.page;
  }

  /** Navigate, wait for content, and restore the cursor at its last position. */
  async goto(url, readySelector, waitUntil = "networkidle") {
    await this.page.goto(url, { waitUntil });
    if (readySelector) await this.page.waitForSelector(readySelector);
    await this.ensureCursor();
  }

  async ensureCursor() {
    await this.page.evaluate(CURSOR_SRC);
    await this.page.mouse.move(this.pos.x, this.pos.y);
  }

  /**
   * Preload a slow page (e.g. GitHub) in a second tab before narration starts.
   * Each tab records its own WebM; switchToSide() marks where assemble.sh splices them.
   */
  async openSide(url, readySelector) {
    this.sideRecStart = Date.now();
    this.side = await this.context.newPage();
    this.side.setDefaultTimeout(60000);
    await this.side.goto(url, { waitUntil: "domcontentloaded" });
    if (readySelector) await this.side.waitForSelector(readySelector);
    await this.side.evaluate(CURSOR_SRC);
    // Park the pointer away from hover menus; a background tab's last frame is what shows at the cut.
    await this.side.mouse.move(this.pos.x, this.pos.y);
    await this.side.mouse.move(VIEWPORT.width - 100, VIEWPORT.height - 60);
    await sleep(800);
    await this.page.bringToFront();
  }

  async switchToSide() {
    this.switchAt = Date.now();
    this.main = this.page;
    this.page = this.side;
    await this.page.bringToFront();
    await this.page.mouse.move(this.pos.x, this.pos.y);
  }

  /** Offset (s) from video start to the moment narration begins; assemble.sh trims to it. */
  markStart(director) {
    director.start();
    this.markAt = Date.now();
    this.offset = (this.markAt - this.recStart) / 1000;
  }

  async moveTo(x, y, ms = 700, { straight = false } = {}) {
    const from = { ...this.pos };
    const dx = x - from.x;
    const dy = y - from.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 1) return;
    // Small perpendicular bow so paths look hand-driven, not robotic. `straight` avoids
    // sweeping across hover menus (e.g. GitHub's top nav).
    const bow = straight ? 0 : Math.min(60, dist * 0.12) * (dx > 0 ? 1 : -1);
    const nx = -dy / dist;
    const ny = dx / dist;
    const t0 = Date.now();
    const frames = Math.max(10, Math.round(ms / 16));
    for (let i = 1; i <= frames; i++) {
      const t = ease(i / frames);
      const arc = Math.sin(Math.PI * t) * bow;
      const px = from.x + dx * t + nx * arc;
      const py = from.y + dy * t + ny * arc;
      await this.page.mouse.move(px, py);
      await sleep(t0 + (ms * i) / frames - Date.now());
    }
    this.pos = { x, y };
  }

  /** Smoothly scroll so the element sits at `frac` of the viewport height. */
  async scrollToEl(selector, { frac = 0.3, ms = 800 } = {}) {
    await this.page.locator(selector).first().evaluate(
      async (el, { frac, ms }) => {
        const start = scrollY;
        const target = Math.max(0, start + el.getBoundingClientRect().top - innerHeight * frac);
        const t0 = performance.now();
        const e = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
        await new Promise((done) => {
          const step = (now) => {
            const t = Math.min(1, (now - t0) / ms);
            scrollTo(0, start + (target - start) * e(t));
            t < 1 ? requestAnimationFrame(step) : done();
          };
          requestAnimationFrame(step);
        });
      },
      { frac, ms }
    );
  }

  async scrollBy(dy, ms = 800) {
    await this.page.evaluate(
      async ({ dy, ms }) => {
        const start = scrollY;
        const t0 = performance.now();
        const e = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
        await new Promise((done) => {
          const step = (now) => {
            const t = Math.min(1, (now - t0) / ms);
            scrollTo(0, start + dy * e(t));
            t < 1 ? requestAnimationFrame(step) : done();
          };
          requestAnimationFrame(step);
        });
      },
      { dy, ms }
    );
  }

  async scrollTop(ms = 800) {
    const y = await this.page.evaluate(() => scrollY);
    if (y > 0) await this.scrollBy(-y, ms);
  }

  /** Point inside an element: fx/fy are fractions of its box (default centre). */
  async pointOf(selector, { fx = 0.5, fy = 0.5, scroll = true } = {}) {
    const loc = this.page.locator(selector).first();
    await loc.waitFor({ state: "visible", timeout: 10000 });
    let box = await loc.boundingBox();
    const vh = VIEWPORT.height;
    if (scroll && (box.y < 60 || box.y + box.height > vh - 40)) {
      await this.scrollToEl(selector, { frac: 0.35 });
      box = await loc.boundingBox();
    }
    return { x: box.x + box.width * fx, y: box.y + box.height * fy };
  }

  async hover(selector, opts = {}) {
    const p = await this.pointOf(selector, opts);
    await this.moveTo(p.x, p.y, opts.ms ?? 650, { straight: opts.straight });
  }

  async click(selector, opts = {}) {
    await this.hover(selector, opts);
    // A lookup in flight disables the button; a click then would be silently dropped.
    const handle = await this.page.locator(selector).first().elementHandle();
    await this.page.waitForFunction((el) => !el.disabled, handle, { timeout: 15000 });
    if (process.env.DEBUG) {
      const hit = await this.page.evaluate(({ x, y }) => {
        const el = document.elementFromPoint(x, y);
        return el ? `${el.tagName}.${el.className}#${el.id} "${(el.textContent || "").trim().slice(0, 30)}"` : "none";
      }, this.pos);
      console.log(`  click ${selector} @ (${this.pos.x | 0},${this.pos.y | 0}) → ${hit}`);
    }
    await sleep(opts.pause ?? 140);
    await this.page.mouse.down();
    await sleep(90);
    await this.page.mouse.up();
  }

  /** Click a text field, select its contents, and type like a person. */
  async typeInto(selector, text, { delay = 85, ...opts } = {}) {
    await this.hover(selector, { fx: 0.35, ...opts });
    await this.page.mouse.click(this.pos.x, this.pos.y, { clickCount: 3 });
    await sleep(150);
    await this.page.keyboard.type(text, { delay });
  }

  /** Open a live JSON endpoint and show it pretty-printed, one line per row, with the URL on top. */
  async prettyJson(url) {
    await this.goto(url, "body", "domcontentloaded");
    const data = await this.page.evaluate(async (url) => (await fetch(url, { cache: "no-store" })).json(), url);
    await this.page.evaluate(({ url, data }) => {
      const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
      const hl = (l) =>
        esc(l)
          .replace(/^(\s*)("[^"]+")(:)/, '$1<span class="k">$2</span>$3')
          .replace(/: (true|false|\d+)(,?)$/, ': <span class="v">$1</span>$2')
          .replace(/: ("[^"]*")(,?)$/, ': <span class="s">$1</span>$2');
      const lines = JSON.stringify(data, null, 2).split("\n");
      document.head.insertAdjacentHTML(
        "beforeend",
        `<style>
          body{margin:0;background:#f6f7fb;font-family:system-ui,-apple-system,sans-serif;color:#111827}
          .hdr{position:sticky;top:0;z-index:5;display:flex;gap:12px;align-items:center;padding:14px 28px;
            background:#fff;border-bottom:1px solid #e5e7eb;font-size:15px}
          .m{font-weight:700;color:#fff;background:#2563eb;border-radius:6px;padding:2px 8px;font-size:13px}
          .u{font-family:"SF Mono",Menlo,monospace}
          .live{margin-left:auto;color:#059669;font-weight:600;font-size:13px}
          .code{padding:14px 0 40px}
          .ln{font:15px/1.6 "SF Mono",Menlo,monospace;padding:0 28px;white-space:pre;transition:background .3s}
          .k{color:#7c3aed}.v{color:#b45309;font-weight:600}.s{color:#047857}
          .hit{background:#fff1b8}
        </style>`
      );
      document.body.innerHTML =
        `<div class="hdr"><span class="m">GET</span><span class="u">${esc(url)}</span><span class="live">● live response</span></div>` +
        `<div class="code">${lines.map((l) => `<div class="ln">${hl(l)}</div>`).join("")}</div>`;
    }, { url, data });
    await this.ensureCursor();
  }

  /** Soft yellow highlight on an element (e.g. a JSON line being talked about). */
  async mark(selector) {
    await this.page.locator(selector).first().evaluate((el) => el.classList.add("hit"));
  }

  async finish(director, tail = 1.6) {
    if (!process.env.FAST) await director.at(director.audioEnd + tail);
    const mainPage = this.main || this.page;
    const video = mainPage.video();
    const sideVideo = this.switchAt ? this.side.video() : null;
    // Every tab's WebM ends when the context closes, but a tab's video only starts at its
    // first paint. So cut points are stored as seconds *before the end* of each file.
    const closeAt = Date.now();
    const before = (t) => +((closeAt - t) / 1000).toFixed(3);
    await this.context.close();
    await this.browser.close();
    const dest = path.join(SCREEN, `${this.track}.webm`);
    fs.renameSync(await video.path(), dest);
    const meta = { offset_sec: +this.offset.toFixed(3), audio_end_sec: director.audioEnd, live: LIVE };
    meta.segments = [{ file: path.basename(dest), from_end: before(this.markAt) }];
    if (sideVideo) {
      const sideDest = path.join(SCREEN, `${this.track}-side.webm`);
      fs.renameSync(await sideVideo.path(), sideDest);
      meta.segments[0].until_from_end = before(this.switchAt);
      meta.segments.push({ file: path.basename(sideDest), from_end: before(this.switchAt) });
    } else if (this.side) {
      await this.side.video()?.delete().catch(() => {});
    }
    fs.writeFileSync(path.join(SCREEN, `${this.track}.json`), JSON.stringify(meta, null, 2));
    console.log(`Saved ${dest}  (narration starts at ${meta.offset_sec}s into raw capture)`);
  }
}
