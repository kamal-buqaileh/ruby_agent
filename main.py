"""CLI entry point for Ruby agent."""

import argparse
import json
import os
import signal
import sys
from pathlib import Path

from ruby_agent.api.handlers import APIHandlers
from ruby_agent.api.server import RubyAgentServer
from ruby_agent.core.analyzer import RubyAnalyzer
from ruby_agent.core.config import AgentConfig, ConfigManager


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Parse Ruby source files with Tree-sitter and output aggregated node JSON."
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run interactive setup to configure the agent.",
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Start the HTTP server instead of running analysis.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host to bind the server to (default: localhost).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000).",
    )
    parser.add_argument(
        "root",
        type=Path,
        nargs="?",
        help="Root directory to scan for Ruby files (required if not using --server).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("nodes.json"),
        help="Path to write the aggregated JSON output (default: nodes.json).",
    )
    return parser.parse_args()


def run_setup() -> None:
    """Run interactive setup to configure the agent."""
    config_manager = ConfigManager()

    print("=" * 60)
    print("Ruby Agent Setup")
    print("=" * 60)
    print()

    # Check if config already exists
    if config_manager.exists():
        existing_config = config_manager.get_config()
        if existing_config:
            print(f"Existing configuration found:")
            print(f"  Name: {existing_config.user_name}")
            print(f"  Email: {existing_config.user_email}")
            print(f"  Root Path: {existing_config.root_path}")
            print(f"  Agent ID: {existing_config.agent_id}")
            print()
            response = input("Do you want to overwrite this configuration? (y/N): ").strip().lower()
            if response != "y":
                print("Setup cancelled.")
                return

    # Get user name
    while True:
        user_name = input("Enter your name: ").strip()
        if user_name:
            break
        print("Name cannot be empty. Please try again.")

    # Get user email
    while True:
        user_email = input("Enter your work email: ").strip()
        if user_email and "@" in user_email:
            break
        print("Please enter a valid email address.")

    # Get root path
    # Check if running in Docker
    is_docker = Path("/.dockerenv").exists() or os.environ.get("DOCKER_CONTAINER") == "true"
    
    if is_docker:
        print("\n⚠️  Running in Docker container")
        print("   Use container paths (e.g., /workspace/project)")
        print("   Make sure to mount your project directory when running docker:")
        print("   docker run -v /host/path:/workspace/project ...")
        print()
    
    while True:
        root_path = input("Enter the root path for your project: ").strip()
        if root_path:
            # Expand ~ to home directory
            path = Path(root_path).expanduser()
            
            # In Docker, check if it's an absolute path that exists in container
            if is_docker and not path.is_absolute():
                print("⚠️  In Docker, please use absolute container paths (e.g., /workspace/project)")
                continue
            
            if path.exists() and path.is_dir():
                root_path = str(path.resolve())
                break
            
            if is_docker:
                print(f"Path '{root_path}' does not exist in the container.")
                print("   Make sure to mount your project directory with: -v /host/path:/workspace/project")
            else:
                print(f"Path '{root_path}' does not exist or is not a directory. Please try again.")
        else:
            print("Root path cannot be empty. Please try again.")

    # Language (default to ruby)
    language = input("Enter the programming language (default: ruby): ").strip() or "ruby"

    # Generate agent ID
    agent_id = config_manager.generate_agent_id(user_email)

    # Create and save config
    config = config_manager.setup(
        user_name=user_name,
        user_email=user_email,
        root_path=root_path,
        language=language,
        agent_id=agent_id,
    )

    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print(f"Name: {config.user_name}")
    print(f"Email: {config.user_email}")
    print(f"Root Path: {config.root_path}")
    print(f"Language: {config.language}")
    print(f"Agent ID: {config.agent_id}")
    print()
    print(f"Configuration saved to: {config_manager.config_file}")


def run_server(host: str, port: int) -> None:
    """Run the HTTP server."""
    analyzer = RubyAnalyzer()
    handlers = APIHandlers(analyzer)

    server = RubyAgentServer(host=host, port=port)
    server.register_handler("/health", handlers.health_handler)
    server.register_handler("/analyze", handlers.analyze_directory_handler)

    def signal_handler(sig, frame):
        """Handle shutdown signals."""
        print("\nShutting down server...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server.start(daemon=False)
    try:
        # Keep the main thread alive
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


def main() -> None:
    """Main entry point."""
    args = parse_args()

    if args.setup:
        run_setup()
        return

    if args.server:
        run_server(args.host, args.port)
        return

    if args.root is None:
        raise SystemExit("Root directory is required when not using --server mode")

    if not args.root.exists():
        raise SystemExit(f"Path not found: {args.root}")

    if not args.root.is_dir():
        raise SystemExit(f"Root path must be a directory: {args.root}")

    # Set output directory to ruby_agent directory
    ruby_agent_dir = Path(__file__).resolve().parent
    output_dir = ruby_agent_dir / args.output.parent if args.output.parent != Path(".") else ruby_agent_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    analyzer = RubyAnalyzer()
    nodes = analyzer.analyze_directory(args.root)
    formatted_nodes = analyzer.format_nodes(nodes)
    classes_dict = analyzer.build_classes_dictionary()

    # Write nodes.json
    nodes_output = output_dir / args.output.name
    nodes_output.write_text(json.dumps(formatted_nodes, indent=2), encoding="utf-8")
    print(f"Wrote {len(formatted_nodes)} nodes to {nodes_output}")

    # Write classes_dictionary.json
    classes_output = output_dir / "classes_dictionary.json"
    classes_output.write_text(json.dumps(classes_dict, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote classes dictionary with {len(classes_dict)} files to {classes_output}")


if __name__ == "__main__":
    main()
