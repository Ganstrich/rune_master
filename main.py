#!/usr/bin/env python3
"""Main entry point for RuneMaster equipment group discovery and visualization."""

import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from pipeline import run_pipeline
from processing import ProcessingConfig
from web_server import start_dev_server


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RuneMaster: Equipment Group Discovery"
    )
    parser.add_argument(
        "--grouping-method",
        choices=["deterministic", "random", "hybrid", "committee", "genetic"],
    )
    parser.add_argument(
        "--random-groups", type=int, help="Number of random groups to generate"
    )
    parser.add_argument(
        "--density-ratio", type=float, help="Density/level ratio filter"
    )
    parser.add_argument(
        "--tune", action="store_true", help="Search for best grouping parameters"
    )
    parser.add_argument(
        "--no-serve",
        action="store_true",
        help="Generate reports without starting server",
    )
    args = parser.parse_args()

    print("\n 🔥 RUNEMASTER - GROUP DISCOVERY 🔥 \n")

    # Build ProcessingConfig from CLI args + defaults
    processing_config = ProcessingConfig.from_args(args, Config)

    try:
        index_path = run_pipeline(
            processing_config, tune=args.tune, output_dir="visualizations"
        )

        if args.no_serve:
            print(f"\n✅ Report ready at: {os.path.abspath(index_path)}")
            print("🚀 Dashboard update complete. Refresh your browser.")
            return

        visualizations_path = os.path.join(PROJECT_ROOT, "visualizations")
        server = start_dev_server(port=8000, directory=visualizations_path)
        if server:
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()

            browser_url = f"http://127.0.0.1:8000/index.html"
            print(f"\n📖 Opening in browser: {browser_url}")
            time.sleep(1)
            webbrowser.open(browser_url)

            print("\n✅ Press Ctrl+C to stop the server\n")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                server.shutdown()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
