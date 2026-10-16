"""Node agent CLI executable entrypoint."""

import argparse
import asyncio
import logging
import os
import signal
import sys

from taskmesh.core.config import NodeConfig
from taskmesh.node.agent import NodeAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="TaskMesh Compute Node Agent")
    parser.add_argument("--node-id", type=str, default=None, help="Unique node identifier")
    parser.add_argument("--url", "--orchestrator", dest="url", type=str, default=None, help="Orchestrator WebSocket URL (ws://...)")
    parser.add_argument("--token", type=str, default=None, help="Cluster join token")
    parser.add_argument("--workers", type=int, default=None, help="Local worker concurrency")
    parser.add_argument("--tags", type=str, default=None, help="Comma-separated capability tags")
    parser.add_argument("--standby-url", type=str, default=None, help="Standby Orchestrator WebSocket URL for failover")
    parser.add_argument("--secure", action="store_true", help="Enable secure HMAC signing")
    parser.add_argument("--local", action="store_true", help="Mark node as local compute worker")
    parser.add_argument("--lan-ip", type=str, default=None, help="Specific LAN IP to advertise")
    parser.add_argument("--no-discovery", action="store_true", help="Disable UDP broadcast discovery")
    parser.add_argument("--heartbeat-interval", type=float, default=None, help="Heartbeat interval in seconds")
    parser.add_argument("--telemetry-interval", type=float, default=None, help="Telemetry interval in seconds")
    args = parser.parse_args()

    cfg = NodeConfig()
    if args.node_id:
        cfg.node_id = args.node_id
    if args.url:
        norm_url = args.url.strip()
        if norm_url.startswith("http://"):
            norm_url = "ws://" + norm_url[7:]
        elif norm_url.startswith("https://"):
            norm_url = "wss://" + norm_url[8:]
        if not norm_url.rstrip("/").endswith("/v1/ws/nodes"):
            norm_url = norm_url.rstrip("/") + "/v1/ws/nodes"
        cfg.orchestrator_url = norm_url
    if args.standby_url:
        norm_standby = args.standby_url.strip()
        if norm_standby.startswith("http://"):
            norm_standby = "ws://" + norm_standby[7:]
        elif norm_standby.startswith("https://"):
            norm_standby = "wss://" + norm_standby[8:]
        if not norm_standby.rstrip("/").endswith("/v1/ws/nodes"):
            norm_standby = norm_standby.rstrip("/") + "/v1/ws/nodes"
        cfg.standby_url = norm_standby
    if args.token:
        cfg.join_token = args.token
    if args.secure:
        cfg.secure_mode = True
    if args.local:
        cfg.is_local = True
    if args.lan_ip:
        cfg.lan_ip = args.lan_ip
    if args.no_discovery:
        cfg.enable_discovery = False
    if args.workers:
        cfg.worker_concurrency = args.workers
    if args.tags:
        cfg.tags = args.tags
    if args.heartbeat_interval is not None:
        cfg.heartbeat_interval_seconds = args.heartbeat_interval
    if args.telemetry_interval is not None:
        cfg.telemetry_interval_seconds = args.telemetry_interval


    agent = NodeAgent(config=cfg)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def handle_signal(*_: object) -> None:
        loop.create_task(agent.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handle_signal)
        except Exception:
            pass

    try:
        loop.run_until_complete(agent.start())
    except KeyboardInterrupt:
        loop.run_until_complete(agent.stop())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
