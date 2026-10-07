"""Main entrypoint for TaskMesh Orchestrator server."""

import argparse
import logging
import os
import uvicorn

from taskmesh.core.config import OrchestratorConfig
from taskmesh.core.enums import SchedulerMode
from taskmesh.orchestrator.server import create_app
from taskmesh.persistence.repositories import SQLiteTaskRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="TaskMesh Distributed Orchestrator")
    parser.add_argument("--host", type=str, default=None, help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Port to listen (default: 8000)")
    parser.add_argument("--mode", type=str, default=None, choices=["adaptive", "round_robin", "least_loaded", "highest_bid"], help="Scheduler policy mode")
    parser.add_argument("--token", type=str, default=None, help="Cluster join token")
    parser.add_argument("--db", type=str, default=None, help="SQLite database path")
    parser.add_argument("--standby", action="store_true", help="Run in Standby replica mode")
    parser.add_argument("--primary-url", type=str, default=None, help="Primary orchestrator HTTP URL for replication")
    parser.add_argument("--snapshot-interval", type=float, default=None, help="Standby snapshot polling interval in seconds")
    parser.add_argument("--secure", action="store_true", help="Enable secure HMAC authentication and replay protection")
    parser.add_argument("--heartbeat-interval", type=float, default=None, help="Heartbeat interval in seconds")
    parser.add_argument("--node-timeout", type=float, default=None, help="Node timeout threshold in seconds")
    parser.add_argument("--lease-seconds", type=float, default=None, help="Task lease duration in seconds")
    args = parser.parse_args()

    cfg = OrchestratorConfig()
    if args.host:
        cfg.host = args.host
    if args.port:
        cfg.port = args.port
    if args.mode:
        cfg.scheduler_mode = SchedulerMode(args.mode)
    if args.token:
        cfg.join_token = args.token
    if args.db:
        cfg.db_url = f"sqlite:///{args.db}"
    if args.standby:
        cfg.standby_mode = True
    if args.primary_url:
        cfg.primary_url = args.primary_url
    if args.snapshot_interval is not None:
        cfg.snapshot_interval_seconds = args.snapshot_interval
    if args.secure:
        cfg.secure_mode = True
    if args.heartbeat_interval is not None:
        cfg.heartbeat_interval_seconds = args.heartbeat_interval
    if args.node_timeout is not None:
        cfg.node_timeout_seconds = args.node_timeout
    if args.lease_seconds is not None:
        cfg.task_lease_seconds = args.lease_seconds

    app = create_app(config=cfg)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
