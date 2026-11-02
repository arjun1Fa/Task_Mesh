"""Capture multi-worker verification screenshots:
1. Worker Alpha Task Execution Console (task_eb10ba09fd36 / AI Inference)
2. Worker Beta Task Execution Console (task_de9b7d8fdde0 / AI Inference)
3. Orchestrator Task Details for Alpha AI Task
4. Orchestrator Task Details for Beta AI Task
"""

import asyncio
import os
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = r"C:\Users\ASUS\.gemini\antigravity\brain\29993f87-25bb-47fa-b376-64dff7f6033e"
ORCHESTRATOR_URL = "http://127.0.0.1:8000"
WORKER_ALPHA_URL = "http://127.0.0.1:8081"
WORKER_BETA_URL = "http://127.0.0.1:8082"

ALPHA_TASK_ID = "task_eb10ba09fd36"
BETA_TASK_ID = "task_de9b7d8fdde0"

async def capture_all():
    print("[*] Starting multi-worker screenshot capture with msedge...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # 1. Worker Alpha Console - Tasks page
        print("[1/4] Worker Alpha Tasks...")
        await page.goto(f"{WORKER_ALPHA_URL}", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        task_nav = page.locator(".nav-item:has-text('Task Execution')")
        if await task_nav.count() > 0:
            await task_nav.first.click()
            await page.wait_for_timeout(1500)
        shot1 = os.path.join(SCREENSHOTS_DIR, "alpha_worker_completed_task.png")
        await page.screenshot(path=shot1)
        print(f"      [OK] Saved: {shot1}")

        # 2. Worker Beta Console - Tasks page
        print("[2/4] Worker Beta Tasks...")
        await page.goto(f"{WORKER_BETA_URL}", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        task_nav_b = page.locator(".nav-item:has-text('Task Execution')")
        if await task_nav_b.count() > 0:
            await task_nav_b.first.click()
            await page.wait_for_timeout(1500)
        shot2 = os.path.join(SCREENSHOTS_DIR, "beta_worker_completed_task.png")
        await page.screenshot(path=shot2)
        print(f"      [OK] Saved: {shot2}")

        # 3. Orchestrator Control Center
        print("[3/4] Orchestrator Task History & Alpha Task Details...")
        await page.goto(ORCHESTRATOR_URL, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Login
        sign_in_btn = page.locator("button:has-text('Sign In')")
        if await sign_in_btn.count() > 0:
            await sign_in_btn.first.click()
            await page.wait_for_timeout(500)
            await page.fill("input[placeholder*='admin, operator']", "admin")
            await page.fill("input[type='password']", "admin123")
            await page.click("button[type='submit']:has-text('Sign In')")
            await page.wait_for_timeout(2000)

        # Task History
        th_nav = page.locator(".nav-item:has-text('Task History')")
        if await th_nav.count() > 0:
            await th_nav.first.click()
            await page.wait_for_timeout(1500)

        # Look for Alpha task or view drawer
        alpha_row = page.locator(f"text={ALPHA_TASK_ID[:8]}")
        if await alpha_row.count() > 0:
            await alpha_row.first.click()
            await page.wait_for_timeout(1500)
        shot3 = os.path.join(SCREENSHOTS_DIR, "orchestrator_alpha_task_details.png")
        await page.screenshot(path=shot3)
        print(f"      [OK] Saved: {shot3}")

        # 4. Orchestrator Beta Task Details
        print("[4/4] Orchestrator Beta Task Details...")
        beta_row = page.locator(f"text={BETA_TASK_ID[:8]}")
        if await beta_row.count() > 0:
            await beta_row.first.click()
            await page.wait_for_timeout(1500)
        shot4 = os.path.join(SCREENSHOTS_DIR, "orchestrator_beta_task_details.png")
        await page.screenshot(path=shot4)
        print(f"      [OK] Saved: {shot4}")

        await browser.close()
        print("[*] All screenshots captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture_all())

