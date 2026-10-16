"""CLI management tool for TaskMesh."""

import argparse
import json
import sys
from typing import Any, Dict
import httpx


def get_client(base_url: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=10.0)


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2))


def handle_task_cmd(args: argparse.Namespace, base_url: str) -> None:
    with get_client(base_url) as client:
        if args.task_action == "submit":
            payload = {}
            if args.payload:
                try:
                    payload = json.loads(args.payload)
                except Exception:
                    try:
                        import ast
                        payload = ast.literal_eval(args.payload)
                    except Exception as e:
                        print(f"Error parsing JSON payload: {e}", file=sys.stderr)
                        sys.exit(1)

            req = {
                "task_type": args.type,
                "payload": payload,
                "priority": args.priority,
                "requires_gpu": args.gpu,
                "offload_policy": getattr(args, "policy", "wireless_allowed"),
            }
            resp = client.post("/v1/tasks", json=req)
            if resp.status_code == 201:
                print("Task submitted successfully:")
                print_json(resp.json())
            else:
                print(f"Error ({resp.status_code}): {resp.text}", file=sys.stderr)

        elif args.task_action == "submit-image":
            import os
            image_path = args.image
            if not os.path.exists(image_path):
                print(f"Error: Image file not found: {image_path}", file=sys.stderr)
                sys.exit(1)
            with open(image_path, "rb") as f:
                img_bytes = f.read()

            policy = "local_only" if args.local_only else (args.policy or "wireless_allowed")
            params = {
                "task_type": "image_inference",
                "model": args.model,
                "priority": args.priority,
                "offload_policy": policy,
                "requires_gpu": args.gpu,
            }
            resp = client.post("/v1/tasks/binary", params=params, content=img_bytes, headers={"Content-Type": "image/jpeg"})
            if resp.status_code == 201:
                print("Image inference task submitted successfully:")
                print_json(resp.json())
            else:
                print(f"Error ({resp.status_code}): {resp.text}", file=sys.stderr)

        elif args.task_action == "get":
            resp = client.get(f"/v1/tasks/{args.task_id}")
            if resp.status_code == 200:
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)

        elif args.task_action == "list":
            resp = client.get("/v1/tasks")
            if resp.status_code == 200:
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)

        elif args.task_action == "cancel":
            resp = client.post(f"/v1/tasks/{args.task_id}/cancel")
            if resp.status_code == 200:
                print("Task cancelled:")
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)

        elif args.task_action == "retry":
            resp = client.post(f"/v1/tasks/{args.task_id}/retry")
            if resp.status_code == 200:
                print("Task re-queued for execution:")
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)


def handle_node_cmd(args: argparse.Namespace, base_url: str) -> None:
    if getattr(args, "node_action", None) == "discover":
        from taskmesh.discovery.broadcast import DiscoveryClient
        timeout = getattr(args, "timeout", 2.0)
        print(f"Scanning local Wi-Fi / LAN for TaskMesh nodes ({timeout}s)...")
        nodes = DiscoveryClient.discover_sync(timeout_seconds=timeout)
        if not nodes:
            print("No TaskMesh nodes discovered via UDP broadcast.")
        else:
            print(f"Discovered {len(nodes)} TaskMesh node(s):")
            print_json([n.model_dump(mode="json") for n in nodes])
        return

    if getattr(args, "node_action", None) == "connect":
        target = args.target
        print(f"To register node with orchestrator at {target}, execute:")
        print(f"  taskmesh node --orchestrator {target}")
        return

    with get_client(base_url) as client:
        if args.node_action == "list":
            resp = client.get("/v1/nodes")
            if resp.status_code == 200:
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)

        elif args.node_action == "inspect":
            resp = client.get(f"/v1/nodes/{args.node_id}")
            if resp.status_code == 200:
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)

        elif args.node_action == "drain":
            resp = client.post(f"/v1/nodes/{args.node_id}/drain")
            if resp.status_code == 200:
                print(f"Node {args.node_id} is draining:")
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)



def handle_cluster_cmd(args: argparse.Namespace, base_url: str) -> None:
    with get_client(base_url) as client:
        if args.cluster_action == "health":
            resp = client.get("/v1/cluster/health")
            if resp.status_code == 200:
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)


def handle_scheduler_cmd(args: argparse.Namespace, base_url: str) -> None:
    with get_client(base_url) as client:
        if args.sched_action == "status":
            resp = client.get("/v1/scheduler/status")
            if resp.status_code == 200:
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)

        elif args.sched_action == "decisions":
            resp = client.get("/v1/scheduler/decisions")
            if resp.status_code == 200:
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)


def handle_dlq_cmd(args: argparse.Namespace, base_url: str) -> None:
    with get_client(base_url) as client:
        if args.dlq_action == "list":
            resp = client.get("/v1/dlq")
            if resp.status_code == 200:
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)

        elif args.dlq_action == "recover":
            resp = client.post(f"/v1/dlq/{args.task_id}/recover")
            if resp.status_code == 200:
                print("Task recovered from DLQ:")
                print_json(resp.json())
            else:
                print(f"Error: {resp.text}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(prog="taskmeshctl", description="TaskMesh Cluster CLI")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="TaskMesh Orchestrator HTTP URL")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Task commands
    task_p = subparsers.add_parser("task", help="Manage cluster tasks")
    task_sub = task_p.add_subparsers(dest="task_action", required=True)

    t_submit = task_sub.add_parser("submit", help="Submit a task")
    t_submit.add_argument("--type", required=True, help="Task type (e.g. log, cpu_test, image_inference)")
    t_submit.add_argument("--payload", default="{}", help="JSON payload")
    t_submit.add_argument("--priority", type=int, default=0, help="Task priority")
    t_submit.add_argument("--policy", default="wireless_allowed", choices=["local_only", "wireless_allowed", "remote_allowed"], help="Offload policy")
    t_submit.add_argument("--gpu", action="store_true", help="Requires GPU")

    t_img = task_sub.add_parser("submit-image", help="Submit an image file for wireless AI inference")
    t_img.add_argument("--image", required=True, help="Path to local image file")
    t_img.add_argument("--model", default="yolov8n", help="Model identifier (default: yolov8n)")
    t_img.add_argument("--priority", type=int, default=5, help="Task priority")
    t_img.add_argument("--local-only", action="store_true", help="Force execution on local node only")
    t_img.add_argument("--policy", default="wireless_allowed", choices=["local_only", "wireless_allowed", "remote_allowed"], help="Offload policy")
    t_img.add_argument("--gpu", action="store_true", help="Requires GPU")

    t_get = task_sub.add_parser("get", help="Get task by ID")
    t_get.add_argument("task_id", help="Task ID")

    t_list = task_sub.add_parser("list", help="List tasks")

    t_cancel = task_sub.add_parser("cancel", help="Cancel task")
    t_cancel.add_argument("task_id", help="Task ID")

    t_retry = task_sub.add_parser("retry", help="Retry task")
    t_retry.add_argument("task_id", help="Task ID")

    # Node commands
    node_p = subparsers.add_parser("node", help="Manage cluster compute nodes")
    node_sub = node_p.add_subparsers(dest="node_action", required=True)
    node_sub.add_parser("list", help="List nodes")
    n_insp = node_sub.add_parser("inspect", help="Inspect node")
    n_insp.add_argument("node_id", help="Node ID")
    n_drain = node_sub.add_parser("drain", help="Drain node")
    n_drain.add_argument("node_id", help="Node ID")

    n_disc = node_sub.add_parser("discover", help="Discover TaskMesh nodes on local Wi-Fi / LAN")
    n_disc.add_argument("--timeout", type=float, default=2.0, help="Discovery timeout in seconds")

    n_conn = node_sub.add_parser("connect", help="Node connection instructions")
    n_conn.add_argument("target", help="Target orchestrator URL or LAN IP")

    # Shortcut: taskmeshctl discover
    disc_p = subparsers.add_parser("discover", help="Discover TaskMesh nodes on local Wi-Fi / LAN")
    disc_p.add_argument("--timeout", type=float, default=2.0, help="Discovery timeout in seconds")


    # Cluster commands
    cluster_p = subparsers.add_parser("cluster", help="Cluster operations")
    cluster_sub = cluster_p.add_subparsers(dest="cluster_action", required=True)
    cluster_sub.add_parser("health", help="Check cluster health")

    # Scheduler commands
    sched_p = subparsers.add_parser("scheduler", help="Scheduler status and decisions")
    sched_sub = sched_p.add_subparsers(dest="sched_action", required=True)
    sched_sub.add_parser("status", help="View scheduler status, weights and Q-table")
    sched_sub.add_parser("decisions", help="View explainable scheduler decisions")

    # DLQ commands
    dlq_p = subparsers.add_parser("dlq", help="Dead Letter Queue management")
    dlq_sub = dlq_p.add_subparsers(dest="dlq_action", required=True)
    dlq_sub.add_parser("list", help="List DLQ items")
    d_rec = dlq_sub.add_parser("recover", help="Recover task from DLQ")
    d_rec.add_argument("task_id", help="Task ID")

    args = parser.parse_args()

    try:
        if args.command == "task":
            handle_task_cmd(args, args.url)
        elif args.command == "node":
            handle_node_cmd(args, args.url)
        elif args.command == "discover":
            handle_node_cmd(argparse.Namespace(node_action="discover", timeout=getattr(args, "timeout", 2.0)), args.url)
        elif args.command == "cluster":
            handle_cluster_cmd(args, args.url)

        elif args.command == "scheduler":
            handle_scheduler_cmd(args, args.url)
        elif args.command == "dlq":
            handle_dlq_cmd(args, args.url)
    except httpx.ConnectError:
        print(f"Error: Unable to connect to TaskMesh Orchestrator at {args.url}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
