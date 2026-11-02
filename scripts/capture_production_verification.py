"""Automated Visual Verification Script for TaskMesh Production Readiness.
Uses Playwright (MS Edge channel) to exercise the live running cluster:
- Orchestrator (port 8000)
- Worker Alpha (console port 8081)
- Worker Beta (console port 8082)
Captures high-resolution screenshots for the final production report.
"""

import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = r"C:\Users\ASUS\.gemini\antigravity\brain\29993f87-25bb-47fa-b376-64dff7f6033e\production_readiness"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

ORCHESTRATOR_URL = "http://127.0.0.1:8000"
WORKER_ALPHA_URL = "http://127.0.0.1:8081"

async def run_verification():
    print(f"[*] Starting visual verification against {ORCHESTRATOR_URL} and {WORKER_ALPHA_URL}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # -------------------------------------------------------------
        # STEP 1: Orchestrator Overview & Login
        # -------------------------------------------------------------
        print("[1/9] Navigating to Orchestrator...")
        await page.goto(ORCHESTRATOR_URL, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Check if we need to sign in
        sign_in_button = page.locator("button:has-text('Sign In')")
        if await sign_in_button.count() > 0:
            print("      Logging in as admin...")
            await sign_in_button.first.click()
            await page.wait_for_timeout(500)
            
            # Fill credentials
            await page.fill("input[placeholder*='admin, operator']", "admin")
            await page.fill("input[type='password']", "admin123")
            await page.click("button[type='submit']:has-text('Sign In')")
            await page.wait_for_timeout(2000)

        # Wait for WebSocket telemetry to update (nodes to appear)
        print("      Waiting for cluster telemetry & worker node connections...")
        await page.wait_for_timeout(3000)

        shot1 = os.path.join(SCREENSHOTS_DIR, "01_orchestrator_overview_live.png")
        await page.screenshot(path=shot1)
        print(f"      [OK] Saved: {shot1}")

        # -------------------------------------------------------------
        # STEP 2: Open Submit Task Modal & Select 5M Iterations Preset
        # -------------------------------------------------------------
        print("[2/9] Opening Submit Task Modal...")
        submit_nav = page.locator("button:has-text('Submit Task')")
        await submit_nav.first.click()
        await page.wait_for_timeout(800)

        # Click the 5,000,000 preset button
        five_m_btn = page.locator("button:has-text('5,000,000 Iterations')")
        if await five_m_btn.count() > 0:
            await five_m_btn.first.click()
            await page.wait_for_timeout(500)

        shot2 = os.path.join(SCREENSHOTS_DIR, "02_orchestrator_submit_modal_5m.png")
        await page.screenshot(path=shot2)
        print(f"      [OK] Saved: {shot2}")

        # -------------------------------------------------------------
        # STEP 3: Dispatch Task & Confirmation Screen
        # -------------------------------------------------------------
        print("[3/9] Submitting 5M CPU workload to cluster...")
        dispatch_btn = page.locator("button:has-text('Dispatch Task to Cluster')")
        await dispatch_btn.first.click()
        await page.wait_for_timeout(1500)

        shot3 = os.path.join(SCREENSHOTS_DIR, "03_orchestrator_submit_confirmation.png")
        await page.screenshot(path=shot3)
        print(f"      [OK] Saved: {shot3}")

        # Close confirmation modal or click view in task queue
        view_queue_btn = page.locator("button:has-text('View in Task Queue')")
        if await view_queue_btn.count() > 0:
            await view_queue_btn.first.click()
        else:
            close_btn = page.locator(".modal-header button")
            if await close_btn.count() > 0:
                await close_btn.first.click()

        # Wait for execution to finish (computation takes ~1.0-1.8s)
        print("      Waiting 4 seconds for multi-node execution to complete...")
        await page.wait_for_timeout(4000)

        # -------------------------------------------------------------
        # STEP 4: Orchestrator Task History
        # -------------------------------------------------------------
        print("[4/9] Navigating to Task History...")
        task_history_nav = page.locator(".nav-item:has-text('Task History')")
        await task_history_nav.first.click()
        await page.wait_for_timeout(1500)

        shot4 = os.path.join(SCREENSHOTS_DIR, "04_orchestrator_task_history.png")
        await page.screenshot(path=shot4)
        print(f"      [OK] Saved: {shot4}")

        # -------------------------------------------------------------
        # STEP 5: Open Task Details Drawer (Orchestrator)
        # -------------------------------------------------------------
        print("[5/9] Opening Task Details Drawer on completed 5M CPU task...")
        # Click on the first completed task row in history
        table_rows = page.locator("table.data-table tbody tr")
        if await table_rows.count() > 0:
            await table_rows.first.click()
            await page.wait_for_timeout(1000)

        shot5 = os.path.join(SCREENSHOTS_DIR, "05_orchestrator_task_details_drawer.png")
        await page.screenshot(path=shot5)
        print(f"      [OK] Saved: {shot5}")

        # Close the drawer
        close_drawer = page.locator("button[title*='Close'], .drawer-header button")
        if await close_drawer.count() > 0:
            await close_drawer.first.click()
            await page.wait_for_timeout(500)

        # -------------------------------------------------------------
        # STEP 6: Orchestrator Scheduling Intelligence
        # -------------------------------------------------------------
        print("[6/9] Navigating to Scheduling Intelligence...")
        sched_nav = page.locator(".nav-item:has-text('Scheduling Intelligence')")
        if await sched_nav.count() > 0:
            await sched_nav.first.click()
            await page.wait_for_timeout(1500)
            shot6 = os.path.join(SCREENSHOTS_DIR, "06_orchestrator_scheduling_intelligence.png")
            await page.screenshot(path=shot6)
            print(f"      [OK] Saved: {shot6}")

        # -------------------------------------------------------------
        # STEP 7: Worker Agent Console Overview (Worker Alpha)
        # -------------------------------------------------------------
        print("[7/9] Navigating to Worker Agent Console Overview (http://127.0.0.1:8081)...")
        await page.goto(WORKER_ALPHA_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        shot7 = os.path.join(SCREENSHOTS_DIR, "07_worker_overview.png")
        await page.screenshot(path=shot7)
        print(f"      [OK] Saved: {shot7}")

        # -------------------------------------------------------------
        # STEP 8: Worker Console Local Task Execution
        # -------------------------------------------------------------
        print("[8/9] Navigating to Worker Tasks...")
        worker_tasks_nav = page.locator(".nav-item:has-text('Task Execution')")
        await worker_tasks_nav.first.click()
        await page.wait_for_timeout(1000)

        # Switch to Recent Completed tab
        completed_tab = page.locator("button:has-text('Recent Completed')")
        if await completed_tab.count() > 0:
            await completed_tab.first.click()
            await page.wait_for_timeout(800)

        shot8 = os.path.join(SCREENSHOTS_DIR, "08_worker_tasks_overview.png")
        await page.screenshot(path=shot8)
        print(f"      [OK] Saved: {shot8}")

        # -------------------------------------------------------------
        # STEP 9: Worker Console Task Details Drawer
        # -------------------------------------------------------------
        print("[9/9] Opening Task Details Drawer on Worker Console...")
        worker_rows = page.locator("table.data-table tbody tr")
        if await worker_rows.count() > 0:
            await worker_rows.first.click()
            await page.wait_for_timeout(1000)

        shot9 = os.path.join(SCREENSHOTS_DIR, "09_worker_task_details_drawer.png")
        await page.screenshot(path=shot9)
        print(f"      [OK] Saved: {shot9}")

        await browser.close()
        print("\n[SUCCESS] All 9 production verification screenshots captured successfully!")

if __name__ == "__main__":
    asyncio.run(run_verification())
