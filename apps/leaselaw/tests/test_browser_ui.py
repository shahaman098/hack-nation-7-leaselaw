"""End-to-end browser test for LeaseLaw Navigator on port 8012."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_PATH = ROOT / "out" / "browser_test_screenshot.png"


async def run_browser_test():
    from playwright.async_api import async_playwright

    print("Launching browser test...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        response = await page.goto("http://127.0.0.1:8012", wait_until="networkidle")
        assert response and response.status == 200
        assert "LeaseLaw" in await page.title()

        disclaimer = await page.locator(".disclaimer-banner").first.text_content()
        assert "Not legal advice" in disclaimer

        await page.wait_for_selector(".rule-card")
        assert await page.locator("#score-big").count() == 0

        await page.click('button[data-test="T1"]')
        await page.wait_for_timeout(400)
        alg = page.locator('.rule-card[data-rule-id="CA-ALG-01"]')
        assert await alg.count() == 1
        assert "Not in effect yet" in await alg.first.text_content()

        await page.click('button[data-test="T1b"]')
        await page.wait_for_timeout(400)
        alg2 = page.locator('.rule-card[data-rule-id="CA-ALG-01"]')
        assert "Applies" in await alg2.first.text_content()

        await page.click('.city-btn[data-city="San Francisco"]')
        await page.wait_for_timeout(400)
        sf = page.locator('.rule-card[data-rule-id="SF-RENT-01"]')
        ca = page.locator('.rule-card[data-rule-id="CA-RENT-01"]')
        assert "Applies" in await sf.first.text_content()
        assert "Replaced by a local rule" in await ca.first.text_content()

        await page.click('.city-btn[data-city="Berkeley"]')
        await page.wait_for_timeout(400)
        berk = page.locator('.rule-card[data-rule-id="BERK-ALG-01"]')
        assert await berk.count() >= 1
        assert "Unclear or conflicting" in await berk.first.text_content()

        await page.click("#lang-toggle")
        await page.wait_for_timeout(300)
        es = await page.locator(".disclaimer-banner").first.text_content()
        assert "No es asesoramiento legal" in es

        SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
        await browser.close()
        print("Browser UI tests passed.")


if __name__ == "__main__":
    asyncio.run(run_browser_test())
