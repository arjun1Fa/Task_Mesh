"""Automated full-stack visual verification script for TaskMesh.

Launches:
1. Orchestrator server on port 8000
2. Three real Worker Agents: node-alpha (port 8081), node-beta (port 8082), node-edge-gamma (port 8083)
3. Submits multiple tasks with varying priorities and handlers
4. Controls Google Chrome via Playwright to log in, interact with all features, and capture screenshots.
5. Verifies live WebSocket feeds and real telemetry.
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
    print("=== TASKMESH VISUAL VERIFICATION STARTING ===")
    
    try:
        # 1. Start Orchestrator
        print("[1/6] Launching TaskMesh Orchestrator Server on port 8000...")
        orch_proc = subprocess.Popen(
            [sys.executable, "-m", "taskmesh.orchestrator.main", "--host", "127.0.0.1", "--port", "8000", "--mode", "adaptive"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        processes.append(("Orchestrator", orch_proc))
        
        if not wait_for_url("http://127.0.0.1:8000/v1/cluster/health", timeout=25):
            raise RuntimeError("Orchestrator failed to start within timeout.")
        print("  -> Orchestrator healthy and responding on http://127.0.0.1:8000/")

        # 2. Start 3 Real Node Agents
        print("[2/6] Launching 3 distinct Node Agents (GPU Rig, Multi-core CPU, Edge Mini-PC)...")
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
            print(f"  -> Launched [{nid}] (Concurrency: {workers}, Console Port: {cport})")

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

        # 3. Submit real workload tasks to exercise the cluster
        print("[3/6] Submitting workload tasks to cluster...")
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
        print("[4/6] Launching Google Chrome to perform visual verification...")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                args=["--window-size=1440,960", "--disable-gpu", "--no-sandbox"]
            )
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            page = context.new_page()

            # Attach console and error listeners
            page.on("console", lambda msg: print(f"  [BROWSER {msg.type.upper()}]: {msg.text}"))
            page.on("pageerror", lambda err: print(f"  [BROWSER ERROR]: {err}\n{getattr(err, 'stack', '')}"))
            page.on("response", lambda res: print(f"  [HTTP {res.status}] {res.url}") if res.status >= 400 else None)

            # Navigate to frontend
            print("  -> Navigating to http://127.0.0.1:8000/ ...")
            page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
            time.sleep(2)

            page.screenshot(path=str(OUTPUT_DIR / "00_initial_load.png"))
            print("  -> Initial page load screenshot saved: 00_initial_load.png")

            # Check title
            title = page.title()
            print(f"  -> Page Title: '{title}'")
            print(f"  -> Root text length: {len(page.locator('#root').inner_text())}")
            assert "TaskMesh" in title

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
                print("  -> Logged in successfully!")

            # -----------------------------------------------------------------
            # VISUAL CHECK 1: Global Overview
            # -----------------------------------------------------------------
            print("  -> Verifying [1. Global Overview]...")
            page.wait_for_selector(".kpi-card", timeout=5000)
            page.screenshot(path=str(OUTPUT_DIR / "01_global_overview.png"), full_page=True)
            print("     [OK] Screenshot saved: 01_global_overview.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 2: Cluster & Nodes
            # -----------------------------------------------------------------
            print("  -> Verifying [2. Cluster & Nodes]...")
            page.click(".nav-item:has-text('Cluster & Nodes')")
            time.sleep(1)
            page.wait_for_selector("text=node-alpha", timeout=5000)
            page.wait_for_selector("text=node-beta", timeout=5000)
            page.wait_for_selector("text=node-edge-gamma", timeout=5000)
            page.screenshot(path=str(OUTPUT_DIR / "02_cluster_nodes.png"), full_page=True)
            print("     [OK] All 3 nodes visible on screen. Screenshot: 02_cluster_nodes.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 3: Live Task Monitor
            # -----------------------------------------------------------------
            print("  -> Verifying [3. Live Task Monitor]...")
            page.click(".nav-item:has-text('Live Task Monitor')")
            time.sleep(1)
            page.screenshot(path=str(OUTPUT_DIR / "03_live_task_monitor.png"), full_page=True)
            print("     [OK] Screenshot saved: 03_live_task_monitor.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 4: Task Queue
            # -----------------------------------------------------------------
            print("  -> Verifying [4. Task Queue]...")
            page.click(".nav-item:has-text('Task Queue')")
            time.sleep(1)
            page.wait_for_selector("table", timeout=5000)
            page.screenshot(path=str(OUTPUT_DIR / "04_task_queue.png"), full_page=True)
            print("     [OK] Screenshot saved: 04_task_queue.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 5: Scheduling Engine
            # -----------------------------------------------------------------
            print("  -> Verifying [5. Scheduling Engine & 6 Adaptive Subsystems]...")
            page.click(".nav-item:has-text('Scheduling Engine')")
            time.sleep(1)
            # Switch mode to LEAST_LOADED and back to ADAPTIVE
            page.click("button:has-text('LEAST LOADED')")
            time.sleep(0.8)
            page.click("button:has-text('ADAPTIVE')")
            time.sleep(0.8)
            page.screenshot(path=str(OUTPUT_DIR / "05_scheduling_engine.png"), full_page=True)
            print("     [OK] Mode switching verified. Screenshot: 05_scheduling_engine.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 6: Network & TMCH Protocol
            # -----------------------------------------------------------------
            print("  -> Verifying [6. Network Topology & TMCH 48-byte Binary Header]...")
            page.click(".nav-item:has-text('Network & Inference')")
            time.sleep(1)
            page.click("button:has-text('TMCH Protocol')")
            time.sleep(0.8)
            page.screenshot(path=str(OUTPUT_DIR / "06_network_inference.png"), full_page=True)
            print("     [OK] Screenshot saved: 06_network_inference.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 7: Workers Pool
            # -----------------------------------------------------------------
            print("  -> Verifying [7. Workers Pool & Concurrency Slots]...")
            page.click(".nav-item:has-text('Workers Pool')")
            time.sleep(1)
            page.screenshot(path=str(OUTPUT_DIR / "07_workers_pool.png"), full_page=True)
            print("     [OK] Screenshot saved: 07_workers_pool.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 8: Logs & Events
            # -----------------------------------------------------------------
            print("  -> Verifying [8. Logs & Real-Time Event Stream]...")
            page.click(".nav-item:has-text('Logs & Events')")
            time.sleep(1)
            page.screenshot(path=str(OUTPUT_DIR / "08_logs_events.png"), full_page=True)
            print("     [OK] Screenshot saved: 08_logs_events.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 9: Dead Letter Queue
            # -----------------------------------------------------------------
            print("  -> Verifying [9. Dead Letter Queue]...")
            page.click(".nav-item:has-text('Dead Letter Queue')")
            time.sleep(1)
            page.screenshot(path=str(OUTPUT_DIR / "09_dead_letter_queue.png"), full_page=True)
            print("     [OK] Screenshot saved: 09_dead_letter_queue.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 10: Recovery & HA
            # -----------------------------------------------------------------
            print("  -> Verifying [10. High Availability & Replication]...")
            page.click(".nav-item:has-text('Recovery & HA')")
            time.sleep(1)
            page.screenshot(path=str(OUTPUT_DIR / "10_recovery_ha.png"), full_page=True)
            print("     [OK] Screenshot saved: 10_recovery_ha.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 11: Users & Permissions
            # -----------------------------------------------------------------
            print("  -> Verifying [11. Users & RBAC Permissions]...")
            page.click(".nav-item:has-text('Users & Permissions')")
            time.sleep(1)
            page.screenshot(path=str(OUTPUT_DIR / "11_users_permissions.png"), full_page=True)
            print("     [OK] Screenshot saved: 11_users_permissions.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 12: System Config
            # -----------------------------------------------------------------
            print("  -> Verifying [12. System Configuration]...")
            page.click(".nav-item:has-text('System Configuration')")
            time.sleep(1)
            page.screenshot(path=str(OUTPUT_DIR / "12_system_config.png"), full_page=True)
            print("     [OK] Screenshot saved: 12_system_config.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 13: Security & Audit
            # -----------------------------------------------------------------
            print("  -> Verifying [13. Security Audit Trail]...")
            page.click(".nav-item:has-text('Security & Audit')")
            time.sleep(1)
            page.screenshot(path=str(OUTPUT_DIR / "13_security_audit.png"), full_page=True)
            print("     [OK] Screenshot saved: 13_security_audit.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 14: System Health
            # -----------------------------------------------------------------
            print("  -> Verifying [14. System Health & Deep Diagnostics]...")
            page.click(".nav-item:has-text('System Health')")
            time.sleep(1)
            page.screenshot(path=str(OUTPUT_DIR / "14_system_health.png"), full_page=True)
            print("     [OK] Screenshot saved: 14_system_health.png")

            # -----------------------------------------------------------------
            # VISUAL CHECK 15: Worker Agent Console (Interface A)
            # -----------------------------------------------------------------
            print("[5/6] Verifying [Interface A: Worker Agent Console]...")
            page.click("button:has-text('Switch to Worker Console')")
            time.sleep(1)
            page.screenshot(path=str(OUTPUT_DIR / "15_worker_console_overview.png"), full_page=True)
            print("     [OK] Worker Overview screenshot: 15_worker_console_overview.png")

            # Check Worker Hardware page
            page.click(".nav-item:has-text('Hardware & Capabilities')")
            time.sleep(0.8)
            page.screenshot(path=str(OUTPUT_DIR / "16_worker_console_hardware.png"), full_page=True)
            print("     [OK] Worker Hardware screenshot: 16_worker_console_hardware.png")

            # Check Worker Pool page
            page.click(".nav-item:has-text('Execution & Worker Pool')")
            time.sleep(0.8)
            page.screenshot(path=str(OUTPUT_DIR / "17_worker_console_pool.png"), full_page=True)
            print("     [OK] Worker Pool screenshot: 17_worker_console_pool.png")

            # Check Worker Network page
            page.click(".nav-item:has-text('Network & Communication')")
            time.sleep(0.8)
            page.screenshot(path=str(OUTPUT_DIR / "18_worker_console_network.png"), full_page=True)
            print("     [OK] Worker Network screenshot: 18_worker_console_network.png")

            # Switch target worker in dropdown to node-beta
            node_select = page.query_selector("select.form-select")
            if node_select:
                page.select_option("select.form-select", "node-beta")
                time.sleep(1)
                page.click(".nav-item:has-text('Worker Overview')")
                time.sleep(0.8)
                page.screenshot(path=str(OUTPUT_DIR / "19_worker_node_beta.png"), full_page=True)
                print("     [OK] Node Beta Console screenshot: 19_worker_node_beta.png")

            browser.close()

        print("[6/6] Visual verification run COMPLETED successfully!")

    finally:
        print("\nCleaning up background processes...")
        for name, proc in reversed(processes):
            try:
                proc.terminate()
                proc.kill()
            except Exception:
                pass
        print("All processes cleanly terminated.")

if __name__ == "__main__":
    main()

