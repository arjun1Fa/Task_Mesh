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

    app = create_app()
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
