"""Capture remaining visual verification screenshots (steps 6-9)."""

import asyncio
import os
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = r"C:\Users\ASUS\.gemini\antigravity\brain\29993f87-25bb-47fa-b376-64dff7f6033e\production_readiness"
ORCHESTRATOR_URL = "http://127.0.0.1:8000"
WORKER_ALPHA_URL = "http://127.0.0.1:8081"

async def run_remaining():
    print("[*] Capturing remaining screenshots (6-9)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Step 6: Orchestrator Scheduling Intelligence
        print("[6/9] Navigating to Orchestrator Scheduling Intelligence...")
        await page.goto(ORCHESTRATOR_URL, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Check if login needed
        sign_in_btn = page.locator("button:has-text('Sign In')")
        if await sign_in_btn.count() > 0:
            await sign_in_btn.first.click()
            await page.wait_for_timeout(500)
            await page.fill("input[placeholder*='admin, operator']", "admin")
            await page.fill("input[type='password']", "admin123")
            await page.click("button[type='submit']:has-text('Sign In')")
            await page.wait_for_timeout(2000)

        # Navigate to Scheduling Intelligence
        sched_nav = page.locator(".nav-item:has-text('Scheduling Intelligence')")
        await sched_nav.first.click()
        await page.wait_for_timeout(2000)

        shot6 = os.path.join(SCREENSHOTS_DIR, "06_orchestrator_scheduling_intelligence.png")
        await page.screenshot(path=shot6)
        print(f"      [OK] Saved: {shot6}")

        # Step 7: Worker Agent Console Overview
        print("[7/9] Navigating to Worker Console Overview...")
        await page.goto(WORKER_ALPHA_URL, wait_until="networkidle")
        await page.wait_for_timeout(2500)

        shot7 = os.path.join(SCREENSHOTS_DIR, "07_worker_overview.png")
        await page.screenshot(path=shot7)
        print(f"      [OK] Saved: {shot7}")

        # Step 8: Worker Console Local Task Execution
        print("[8/9] Navigating to Worker Tasks...")
        tasks_nav = page.locator(".nav-item:has-text('Task Execution')")
        await tasks_nav.first.click()
        await page.wait_for_timeout(1000)

        # Switch to Recent Completed tab
        comp_tab = page.locator("button:has-text('Recent Completed')")
        if await comp_tab.count() > 0:
            await comp_tab.first.click()
            await page.wait_for_timeout(1000)

        shot8 = os.path.join(SCREENSHOTS_DIR, "08_worker_tasks_overview.png")
        await page.screenshot(path=shot8)
        print(f"      [OK] Saved: {shot8}")

        # Step 9: Worker Console Task Details Drawer
        print("[9/9] Opening Task Details Drawer on Worker Console...")
        worker_rows = page.locator("table.data-table tbody tr")
        if await worker_rows.count() > 0:
            await worker_rows.first.click()
            await page.wait_for_timeout(1200)

        shot9 = os.path.join(SCREENSHOTS_DIR, "09_worker_task_details_drawer.png")
        await page.screenshot(path=shot9)
        print(f"      [OK] Saved: {shot9}")

        await browser.close()
        print("\n[SUCCESS] All screenshots 6-9 captured successfully!")

if __name__ == "__main__":
    asyncio.run(run_remaining())

