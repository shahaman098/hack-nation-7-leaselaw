"""Visible (headed) interactive browser demo for the user.

Runs Playwright with headless=False and slow_mo so the user can watch the browser
navigate, interact with the UI, test presets, and toggle languages live on screen.
"""

import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_PATH = ROOT / "out" / "visible_demo_screenshot.png"


async def run_visible_demo():
    from playwright.async_api import async_playwright

    print("🖥️ Launching visible browser window on your desktop...")
    async with async_playwright() as p:
        # Launch Chromium headed (visible window) with slow_mo so human can watch
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=1000,  # 1 second pause between actions
            args=["--start-maximized", "--window-size=1280,900"]
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        print("🌐 Navigating to http://127.0.0.1:8012...")
        await page.goto("http://127.0.0.1:8012", wait_until="networkidle")
        await asyncio.sleep(2)

        # Highlight Scorecard
        print("📊 Showing Judge Scorecard & Badges...")
        await page.wait_for_selector("#eval-pills .pill")
        await asyncio.sleep(2)

        # Step 1: Click T1 Before
        print("🔍 Clicking T1 Before (2025-12-31)...")
        await page.click('button[data-test="T1"]')
        await asyncio.sleep(2.5)

        # Step 2: Click T1 After
        print("🔍 Clicking T1 After (2026-01-02)...")
        await page.click('button[data-test="T1b"]')
        await asyncio.sleep(2.5)

        # Step 3: Select San Francisco
        print("🏙️ Selecting San Francisco (Local Supersession)...")
        await page.click('.city-btn[data-city="San Francisco"]')
        await asyncio.sleep(2.5)

        # Step 4: Click Berkeley §9 Open Question
        print("⚖️ Opening §9 Berkeley Conflict Preset...")
        await page.click('button[data-q="Q1"]')
        await asyncio.sleep(2.5)

        # Step 5: Toggle Spanish Language
        print("🌐 Switching Language to Spanish (ES)...")
        await page.click('#lang-toggle')
        await asyncio.sleep(3)

        # Take screenshot
        SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
        print(f"📸 Saved demo screenshot to {SCREENSHOT_PATH}")

        # Keep browser open for a few seconds so user can see the final state
        print("👀 Keeping browser visible for 5 seconds...")
        await asyncio.sleep(5)

        await browser.close()
        print("✅ Visible demo completed!")


if __name__ == "__main__":
    asyncio.run(run_visible_demo())
