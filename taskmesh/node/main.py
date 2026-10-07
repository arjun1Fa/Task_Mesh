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
    parser.add_argument("--url", type=str, default=None, help="Orchestrator WebSocket URL (ws://...)")
    parser.add_argument("--token", type=str, default=None, help="Cluster join token")
    parser.add_argument("--workers", type=int, default=None, help="Local worker concurrency")
    parser.add_argument("--tags", type=str, default=None, help="Comma-separated capability tags")
    args = parser.parse_args()

    cfg = NodeConfig()
    if args.node_id:
        cfg.node_id = args.node_id
    if args.url:
        cfg.orchestrator_url = args.url
    if args.token:
        cfg.join_token = args.token
    if args.workers:
        cfg.worker_concurrency = args.workers
    if args.tags:
        cfg.tags = args.tags

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
