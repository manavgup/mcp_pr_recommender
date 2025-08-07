#!/usr/bin/env python3
"""CLI module for mcp_pr_recommender."""
import argparse
import os
import sys

from mcp_shared_lib.server.runner import run_server
from mcp_shared_lib.transports.config import TransportConfig
from mcp_shared_lib.utils import logging_service

from mcp_pr_recommender.main import create_server, register_tools

logger = logging_service.get_logger(__name__)


def check_environment() -> None:
    """Check if required environment variables are set."""
    required_env = {"OPENAI_API_KEY": "OpenAI API key for LLM operations"}

    missing = []
    for var, description in required_env.items():
        if not os.getenv(var):
            missing.append(f"  {var}: {description}")

    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(var)
        print("\nPlease set these variables and try again.")
        print("Example:")
        print("  export OPENAI_API_KEY=your_api_key_here")
        print("  pr-recommender")
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP PR Recommender Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--transport", type=str, help="Transport type (stdio, http, websocket, sse)"
    )
    parser.add_argument("--config", type=str, help="Path to transport config YAML")
    parser.add_argument(
        "--port",
        type=int,
        help="Port to run the HTTP/WebSocket server on (overrides config/env)",
    )
    parser.add_argument(
        "--host", type=str, help="Host to bind the server to (overrides config/env)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )
    parser.add_argument(
        "--skip-env-check",
        action="store_true",
        help="Skip environment variable validation (use with caution)",
    )

    return parser.parse_args()


def main() -> None:
    """Run the main CLI entry point."""
    args = parse_args()

    # Check environment unless skipped
    if not args.skip_env_check:
        check_environment()

    logger.info("Starting MCP PR Recommender Server")

    # Load config
    if args.config:
        config = TransportConfig.from_file(args.config)
    else:
        config = TransportConfig.from_env()
        if args.transport:
            config.type = args.transport
        if args.port and config.type in ("http", "websocket"):
            if config.type == "http":
                if not config.http:
                    from mcp_shared_lib.transports.config import HTTPConfig

                    config.http = HTTPConfig()
                config.http.port = args.port
            elif config.type == "websocket":
                if not config.websocket:
                    from mcp_shared_lib.transports.config import WebSocketConfig

                    config.websocket = WebSocketConfig()
                config.websocket.port = args.port
        if args.host and config.type in ("http", "websocket"):
            if config.type == "http":
                if not config.http:
                    from mcp_shared_lib.transports.config import HTTPConfig

                    config.http = HTTPConfig()
                config.http.host = args.host
            elif config.type == "websocket":
                if not config.websocket:
                    from mcp_shared_lib.transports.config import WebSocketConfig

                    config.websocket = WebSocketConfig()
                config.websocket.host = args.host

    # Create and register server
    mcp, services = create_server()
    mcp.pr_generator = services["pr_generator"]
    mcp.feasibility_analyzer = services["feasibility_analyzer"]
    mcp.strategy_manager = services["strategy_manager"]
    mcp.validator = services["validator"]
    register_tools(mcp)

    try:
        run_server(mcp, config, server_name="PR Recommender")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
