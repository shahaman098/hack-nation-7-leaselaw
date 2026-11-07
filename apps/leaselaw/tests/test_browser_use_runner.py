"""E2E Browser Test executed via browser-use library."""

import asyncio
import json
from pathlib import Path
from browser_use import Browser

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_PATH = ROOT / "out" / "browser_use_screenshot.png"


async def js_eval(page, expr: str):
    raw = await page.evaluate(expr)
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return raw
    return raw


async def run_browser_use_test():
    print("🚀 [browser-use] Initializing browser session...")
    browser = Browser(headless=True)
    await browser.start()

    try:
        # Step 1: Navigate to local running instance
        print("🌐 [browser-use] Navigating to http://127.0.0.1:8012...")
        await browser.navigate_to("http://127.0.0.1:8012")
        page = await browser.get_current_page()

        # Step 2: Verify Title and Disclaimer
        title = await js_eval(page, "() => document.title")
        print(f"   ✓ [browser-use] Page Title: '{title}'")
        assert "LeaseLaw" in title, f"Unexpected title: {title}"

        disclaimer = await js_eval(
            page, "() => document.querySelector('.disclaimer-banner')?.textContent || ''"
        )
        print(f"   ✓ [browser-use] Disclaimer: '{disclaimer.strip()}'")
        assert "Not legal advice" in disclaimer, "Disclaimer banner missing 'Not legal advice'"

        # Step 3: Verify Judge Scorecard and Verification Badges
        # Wait up to 5s for async /api/eval to load
        score_text = ""
        for _ in range(10):
            score_text = await js_eval(
                page, "() => document.getElementById('score-big')?.textContent || ''"
            )
            if "5/5" in str(score_text):
                break
            await asyncio.sleep(0.5)

        pills = await js_eval(
            page,
            "() => Array.from(document.querySelectorAll('#eval-pills .pill')).map(el => el.textContent.trim())"
        )
        print(f"   ✓ [browser-use] Scorecard: {score_text}")
        print(f"   ✓ [browser-use] Eval badges: {pills}")
        assert "5/5" in str(score_text), f"Scorecard expected 5/5, got: {score_text}"
        assert any("T1 PASS" in p for p in pills), f"Missing T1 PASS badge in {pills}"
        assert any("SCHEMA VALID" in p for p in pills), f"Missing SCHEMA VALID badge in {pills}"
        assert any("§9 SURFACED" in p for p in pills), f"Missing §9 SURFACED badge in {pills}"

        # Step 4: Test T1 Before Preset (AB325 before 2026-01-01)
        print("🔍 [browser-use] Clicking T1 Before button...")
        await page.evaluate("() => document.querySelector('button[data-test=\"T1\"]').click()")
        await asyncio.sleep(1.0)

        rules_summary = await js_eval(page, """() => {
            const cards = Array.from(document.querySelectorAll('.rule-card'));
            return cards.map(c => ({
                id: c.querySelector('.rule-id')?.textContent.trim() || '',
                status: c.querySelector('.result-badge')?.textContent.trim() || ''
            }));
        }""")
        ab325_before = next((r for r in rules_summary if "CA-ALG-01" in r["id"]), None)
        assert ab325_before, f"CA-ALG-01 rule card not found in {rules_summary}"
        print(f"   ✓ [browser-use] CA-ALG-01 status on 2025-12-31: {ab325_before['status']}")
        assert ab325_before["status"] == "not_yet_effective", (
            f"Expected not_yet_effective, got: {ab325_before['status']}"
        )

        # Step 5: Test T1 After Preset (AB325 after 2026-01-01)
        print("🔍 [browser-use] Clicking T1 After button...")
        await page.evaluate("() => document.querySelector('button[data-test=\"T1b\"]').click()")
        await asyncio.sleep(1.0)

        rules_after = await js_eval(page, """() => {
            const cards = Array.from(document.querySelectorAll('.rule-card'));
            return cards.map(c => ({
                id: c.querySelector('.rule-id')?.textContent.trim() || '',
                status: c.querySelector('.result-badge')?.textContent.trim() || ''
            }));
        }""")
        ab325_after = next((r for r in rules_after if "CA-ALG-01" in r["id"]), None)
        assert ab325_after, f"CA-ALG-01 rule card not found in {rules_after}"
        print(f"   ✓ [browser-use] CA-ALG-01 status on 2026-01-02: {ab325_after['status']}")
        assert ab325_after["status"] == "applies", f"Expected applies, got: {ab325_after['status']}"

        # Step 6: Test Local Supersession (San Francisco A0016)
        print("🔍 [browser-use] Selecting San Francisco...")
        await page.evaluate("() => document.querySelector('.city-btn[data-city=\"San Francisco\"]').click()")
        await asyncio.sleep(1.0)

        sf_rules = await js_eval(page, """() => {
            const cards = Array.from(document.querySelectorAll('.rule-card'));
            return cards.map(c => ({
                id: c.querySelector('.rule-id')?.textContent.trim() || '',
                status: c.querySelector('.result-badge')?.textContent.trim() || ''
            }));
        }""")
        sf_rent = next((r for r in sf_rules if "SF-RENT-01" in r["id"]), None)
        ca_rent = next((r for r in sf_rules if "CA-RENT-01" in r["id"]), None)
        assert sf_rent and sf_rent["status"] == "applies", f"SF-RENT-01 should apply: {sf_rent}"
        assert ca_rent and ca_rent["status"] == "superseded", f"CA-RENT-01 should be superseded: {ca_rent}"
        print(f"   ✓ [browser-use] Local supersession verified: SF-RENT-01 applies, CA-RENT-01 superseded")

        # Step 7: Test Section 9 Berkeley Conflict Preset
        print("🔍 [browser-use] Testing §9 Open Questions preset (Q1 Berkeley Dual Dates)...")
        await page.evaluate("() => document.querySelector('button[data-q=\"Q1\"]').click()")
        await asyncio.sleep(1.0)

        has_conflict = await js_eval(page, """() => {
            const cards = Array.from(document.querySelectorAll('.rule-card'));
            const card = cards.find(c => c.textContent.includes('BERK-ALG-01'));
            return card ? (card.innerHTML.includes('conflict') || card.innerHTML.includes('Conflict')) : false;
        }""")
        print(f"   ✓ [browser-use] Berkeley BERK-ALG-01 conflict badge displayed: {has_conflict}")
        assert has_conflict, "BERK-ALG-01 did not display conflict badge"

        # Step 8: Test Bilingual Spanish Toggle
        print("🌐 [browser-use] Toggling Spanish language...")
        await page.evaluate("() => document.getElementById('lang-toggle').click()")
        await asyncio.sleep(0.5)

        es_disclaimer = await js_eval(
            page, "() => document.querySelector('.disclaimer-banner')?.textContent || ''"
        )
        print(f"   ✓ [browser-use] Spanish disclaimer: '{es_disclaimer.strip()}'")
        assert "No es asesoramiento legal" in str(es_disclaimer), "Spanish disclaimer did not translate"

        # Step 9: Capture Screenshot
        import base64
        SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        img_data = await page.screenshot()
        if isinstance(img_data, str):
            if "," in img_data:
                img_data = img_data.split(",", 1)[1]
            img_bytes = base64.b64decode(img_data)
        else:
            img_bytes = img_data
        SCREENSHOT_PATH.write_bytes(img_bytes)
        print(f"📸 [browser-use] Screenshot captured to {SCREENSHOT_PATH} ({len(img_bytes)} bytes)")

        print("🎉 [browser-use] ALL E2E BROWSER TESTS PASSED (10/10)!")

    finally:
        print("🛑 [browser-use] Stopping browser session...")
        await browser.stop()


if __name__ == "__main__":
    asyncio.run(run_browser_use_test())
