"""Local multi-process development cluster launcher for TaskMesh."""

import argparse
import os
import signal
import subprocess
import sys
import time


def main() -> None:
    parser = argparse.ArgumentParser(description="TaskMesh Local Development Cluster Launcher")
    parser.add_argument("--nodes", type=int, default=3, help="Number of compute nodes to spawn (default: 3)")
    parser.add_argument("--port", type=int, default=8000, help="Orchestrator HTTP port (default: 8000)")
    args = parser.parse_args()

    python_bin = sys.executable
    processes = []

    print("=" * 60)
    print("Starting TaskMesh Multi-Process Local Development Cluster")
    print(f"Orchestrator: http://127.0.0.1:{args.port} (WebSocket: ws://127.0.0.1:{args.port}/v1/ws/nodes)")
    print(f"Spawning {args.nodes} independent Node Agent processes...")
    print("=" * 60)

    try:
        # 1. Start Orchestrator process
        orch_cmd = [python_bin, "-m", "taskmesh.orchestrator.main", "--port", str(args.port)]
        p_orch = subprocess.Popen(orch_cmd)
        processes.append(("Orchestrator", p_orch))

        # Allow orchestrator 2 seconds to bind port
        time.sleep(2.0)

        # 2. Start independent Node Agent processes
        ws_url = f"ws://127.0.0.1:{args.port}/v1/ws/nodes"
        node_names = ["node-alpha", "node-beta", "node-gamma", "node-delta", "node-epsilon"]

        for i in range(args.nodes):
            name = node_names[i] if i < len(node_names) else f"node-{i+1}"
            tags = "gpu,cuda" if i == 0 else "cpu,general"
            node_cmd = [
                python_bin, "-m", "taskmesh.node.main",
                "--node-id", name,
                "--url", ws_url,
                "--workers", "4",
                "--tags", tags,
            ]
            p_node = subprocess.Popen(node_cmd)
            processes.append((name, p_node))
            time.sleep(0.5)

        print("\nAll cluster processes active!")
        print("To submit tasks: taskmeshctl task submit --type log --payload '{\"message\":\"hello\"}'")
        print("To view cluster health: taskmeshctl cluster health")
        print("Press Ctrl+C to terminate cluster cleanly.\n")

        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nShutting down local cluster processes...")
    finally:
        for name, p in reversed(processes):
            try:
                p.terminate()
                p.wait(timeout=2.0)
            except Exception:
                p.kill()
        print("All cluster processes terminated.")


if __name__ == "__main__":
    main()
