"""Entry point for the agent daemon service."""

from __future__ import annotations

import os

from agent_daemon.logging_utils import configure_logging
from agent_daemon.server import create_server


def main() -> None:
    """Start the daemon gRPC server."""

    logger = configure_logging()

    host = os.environ.get("AGENT_DAEMON_HOST", "0.0.0.0")
    port = int(os.environ.get("AGENT_DAEMON_PORT", "50051"))
    bind_address = f"{host}:{port}"

    server = create_server()
    server.add_insecure_port(bind_address)
    server.start()

    logger.info("agent-daemon gRPC server started", extra={"grpc_method": "startup"})
    logger.info(f"listening on {bind_address}", extra={"grpc_method": "startup"})

    server.wait_for_termination()


if __name__ == "__main__":
    main()
