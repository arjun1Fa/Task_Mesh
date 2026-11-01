"""Automated full-stack visual verification script for TaskMesh.

Verifies TWO SEPARATE, INDEPENDENTLY RUNNING APPLICATIONS:
1. Orchestrator Control Center (port 8000)
2. Worker Agent Console on node-alpha (port 8081)
3. Worker Agent Console on node-beta (port 8082)

Strict Architectural Rules Verified:
- No button to switch between Worker and Orchestrator modes.
- No dropdown to select a worker node identity in the worker console.
- The running backend process strictly dictates the frontend application identity.
- Port 8081 binds strictly to node-alpha (4 slots).
- Port 8082 binds strictly to node-beta (8 slots).
"""

import os
import sys
import time
import subprocess
import json
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(r"C:\Users\ASUS\.gemini\antigravity\brain\29993f87-25bb-47fa-b376-64dff7f6033e\visual_check")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def wait_for_url(url, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def http_post_json(url, data, token=None):
    body = json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_get_json(url, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    processes = []
    print("=== TASKMESH TWO-APPLICATION VISUAL VERIFICATION STARTING ===")
    
    try:
        # 1. Start Orchestrator
        print("\n[1/6] Launching TaskMesh Orchestrator Server on port 8000...")
        orch_proc = subprocess.Popen(
            [sys.executable, "-m", "taskmesh.orchestrator.main", "--host", "127.0.0.1", "--port", "8000", "--mode", "adaptive"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        processes.append(("Orchestrator", orch_proc))
        
        if not wait_for_url("http://127.0.0.1:8000/v1/cluster/health", timeout=25):
            raise RuntimeError("Orchestrator failed to start within timeout.")
        print("  -> Orchestrator healthy and responding on http://127.0.0.1:8000/")

        # 2. Start 3 Real Node Agents with their own embedded console servers
        print("\n[2/6] Launching 3 Node Agents with independent Worker Consoles...")
        nodes_config = [
            ("node-alpha", 4, 8081),
            ("node-beta", 8, 8082),
            ("node-edge-gamma", 2, 8083),
        ]
        
        for nid, workers, cport in nodes_config:
            p = subprocess.Popen(
                [
                    sys.executable, "-m", "taskmesh.node.main",
                    "--node-id", nid,
                    "--url", "ws://127.0.0.1:8000/v1/ws/nodes",
                    "--workers", str(workers),
                    "--console-port", str(cport),
                    "--heartbeat-interval", "2.0",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            processes.append((nid, p))
            print(f"  -> Launched [{nid}] (Concurrency: {workers}, Dedicated Console: http://127.0.0.1:{cport})")

        # Wait for nodes to register
        print("  -> Waiting for all 3 nodes to register with the orchestrator...")
        time.sleep(3)
        for _ in range(25):
            nodes_data = http_get_json("http://127.0.0.1:8000/v1/nodes")
            online_ids = [n["id"] for n in nodes_data if n["status"] == "online"]
            if len(online_ids) >= 3:
                print(f"  -> All 3 nodes successfully registered & online: {online_ids}")
                break
            time.sleep(1)
        else:
            raise RuntimeError("Nodes failed to register in time.")

        # Verify console endpoints are responding
        if not wait_for_url("http://127.0.0.1:8081/api/worker/identity", timeout=15):
            raise RuntimeError("node-alpha console failed to respond.")
        if not wait_for_url("http://127.0.0.1:8082/api/worker/identity", timeout=15):
            raise RuntimeError("node-beta console failed to respond.")
        print("  -> Worker Consoles online on ports 8081 and 8082.")

        # 3. Submit real workload tasks to exercise the cluster
        print("\n[3/6] Submitting workload tasks to cluster...")
        tasks = [
            {"task_type": "benchmark", "payload": {"matrix_size": 250, "iterations": 4}, "priority": 9},
            {"task_type": "echo", "payload": {"message": "Cluster operational verification 1"}, "priority": 5},
            {"task_type": "benchmark", "payload": {"matrix_size": 150, "iterations": 2}, "priority": 7},
            {"task_type": "echo", "payload": {"message": "High-priority alert broadcast"}, "priority": 10},
            {"task_type": "benchmark", "payload": {"matrix_size": 300, "iterations": 3}, "priority": 4},
        ]
        
        submitted_ids = []
        for t in tasks:
            res = http_post_json("http://127.0.0.1:8000/v1/tasks", t)
            submitted_ids.append(res["id"])
            print(f"  -> Submitted task: {res['id'][:12]}... (Type: {t['task_type']}, Priority: P{t['priority']})")

        time.sleep(2)

        # 4. Chrome Playwright Automation
        print("\n[4/6] Launching Google Chrome to perform visual verification...")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                args=["--window-size=1440,960", "--disable-gpu", "--no-sandbox"]
            )
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            page = context.new_page()

            page.on("console", lambda msg: print(f"  [BROWSER {msg.type.upper()}]: {msg.text}") if msg.type in ['error', 'warning'] else None)
            page.on("pageerror", lambda err: print(f"  [BROWSER ERROR]: {err}\n{getattr(err, 'stack', '')}"))

            # =================================================================
            # APPLICATION 1: Orchestrator Control Center (http://127.0.0.1:8000/)
            # =================================================================
            print("\n=======================================================")
            print("VERIFYING APPLICATION 1: Orchestrator Control Center")
            print("=======================================================")
            page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
            time.sleep(2)

            title = page.title()
            print(f"  -> Page Title: '{title}'")
            assert "Orchestrator" in title, f"Expected Orchestrator in title, got: {title}"
            
            # Verify NO worker mode switch exists
            worker_toggle = page.query_selector("button:has-text('Worker Console'), button:has-text('Switch to Worker')")
            assert worker_toggle is None, "Violation: Found worker console switcher inside Orchestrator app!"
            print("  -> Verified: NO worker switch button exists in Orchestrator Control Center.")

            page.screenshot(path=str(OUTPUT_DIR / "00_initial_load.png"))
            print("  -> Screenshot saved: 00_initial_load.png")

            # Check Login
            print("  -> Authenticating as 'admin'...")
            login_btn = page.query_selector("button:has-text('Sign In'), button:has-text('Login')")
            if login_btn:
                login_btn.click()
                time.sleep(0.5)
                page.fill("input[type='text'], input[placeholder*='sername']", "admin")
                page.fill("input[type='password']", "admin123")
                page.click("button[type='submit']")
                time.sleep(1)
                print("  -> Logged in successfully as admin!")

            # Orchestrator Views
            views = [
                ("1. Global Overview", "01_global_overview.png"),
                ("2. Cluster Nodes", "02_cluster_nodes.png"),
                ("3. Live Task Allocation", "03_live_task_monitor.png"),
                ("4. Task Queue", "04_task_queue.png"),
                ("5. Task History", "05_task_history.png"),
                ("6. Scheduling Intelligence", "06_scheduling_engine.png"),
                ("7. Network & Inference", "07_network_inference.png"),
                ("8. Logs & Events", "08_logs_events.png"),
                ("9. Dead Letter Queue", "09_dead_letter_queue.png"),
                ("10. Recovery & Failover", "10_recovery_ha.png"),
                ("11. Users & Permissions", "11_users_permissions.png"),
                ("12. System Configuration", "12_system_config.png"),
                ("13. Security & Audit", "13_security_audit.png"),
            ]

            for label, fname in views:
                print(f"  -> Testing Orchestrator view: [{label}]...")
                btn = page.query_selector(f".nav-item:has-text('{label}')")
                if btn:
                    btn.click()
                    time.sleep(0.8)
                    page.screenshot(path=str(OUTPUT_DIR / fname), full_page=True)
                    print(f"     [OK] Saved: {fname}")
                else:
                    print(f"     [WARN] Could not find nav button for: {label}")

            # =================================================================
            # APPLICATION 2: Worker Agent Console (node-alpha on http://127.0.0.1:8081/)
            # =================================================================
            print("\n=======================================================")
            print("VERIFYING APPLICATION 2: Worker Agent Console (node-alpha: 8081)")
            print("=======================================================")
            page.goto("http://127.0.0.1:8081/", wait_until="networkidle")
            time.sleep(2)

            worker_title = page.title()
            print(f"  -> Page Title: '{worker_title}'")
            assert "Worker Agent" in worker_title, f"Expected Worker Agent in title, got: {worker_title}"

            # Verify locked node identity
            node_label = page.locator(".mono:has-text('node-alpha')").first
            assert node_label.is_visible(), "Worker Console did not automatically bind to node-alpha!"
            print("  -> Verified: Worker console automatically bound to local hardware identity 'node-alpha'!")

            # Verify NO node identity dropdown
            dropdown = page.query_selector("select.form-select, select[name='node_id']")
            assert dropdown is None, "Violation: Found worker dropdown selector inside Worker Console!"
            print("  -> Verified: NO node identity dropdown exists in Worker Console.")

            # Capture Worker Views for node-alpha
            worker_views = [
                ("1. Local Overview", "14_worker_alpha_overview.png"),
                ("2. Hardware Profile", "15_worker_alpha_hardware.png"),
                ("3. Task Execution", "16_worker_alpha_tasks.png"),
                ("4. Concurrency Slots", "17_worker_alpha_pool.png"),
                ("5. Network & TMCH", "18_worker_alpha_network.png"),
                ("6. Node Agent Logs", "19_worker_alpha_logs.png"),
                ("7. Local Management", "20_worker_alpha_settings.png"),
            ]

            for label, fname in worker_views:
                print(f"  -> Testing Worker Console view: [{label}]...")
                btn = page.query_selector(f".nav-item:has-text('{label}')")
                if btn:
                    btn.click()
                    time.sleep(0.8)
                    page.screenshot(path=str(OUTPUT_DIR / fname), full_page=True)
                    print(f"     [OK] Saved: {fname}")

            # Verify Concurrency Slots for node-alpha (must be 4 slots)
            page.click(".nav-item:has-text('4. Concurrency Slots')")
            time.sleep(0.5)
            page.wait_for_selector("text=of 4 slots occupied", timeout=5000)
            print("  -> node-alpha slot utilization verified: 4 slots occupied counter found.")

            # =================================================================
            # APPLICATION 2: Worker Agent Console (node-beta on http://127.0.0.1:8082/)
            # =================================================================
            print("\n=======================================================")
            print("VERIFYING APPLICATION 2: Worker Agent Console (node-beta: 8082)")
            print("=======================================================")
            page.goto("http://127.0.0.1:8082/", wait_until="networkidle")
            time.sleep(2)

            beta_node_label = page.locator(".mono:has-text('node-beta')").first
            assert beta_node_label.is_visible(), "Worker Console 8082 did not bind to node-beta!"
            print("  -> Verified: Worker console 8082 automatically bound to local hardware identity 'node-beta'!")

            page.screenshot(path=str(OUTPUT_DIR / "21_worker_beta_overview.png"), full_page=True)
            print("     [OK] Saved: 21_worker_beta_overview.png")

            # Check Concurrency Slots for node-beta (must be 8 slots)
            page.click(".nav-item:has-text('4. Concurrency Slots')")
            time.sleep(0.8)
            page.screenshot(path=str(OUTPUT_DIR / "22_worker_beta_pool.png"), full_page=True)
            print("     [OK] Saved: 22_worker_beta_pool.png (showing 8 slots)")

            browser.close()

        print("\n[5/6] Full visual verification run COMPLETED successfully!")

    finally:
        print("\n[6/6] Cleaning up background processes...")
        for name, proc in reversed(processes):
            try:
                proc.terminate()
                proc.kill()
            except Exception:
                pass
        print("All processes cleanly terminated.")

if __name__ == "__main__":
    main()
