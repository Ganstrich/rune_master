"""Run one grouping method in a subprocess for evaluation."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one grouping method")
    parser.add_argument("--method", choices=["greedy"], default="greedy")
    parser.add_argument("--snapshot", default="data/snapshots/3.7.7.6")
    parser.add_argument("--no-set-filter", action="store_true")
    args = parser.parse_args()

    # Delegate to main.py with the right arguments
    cmd = [
        sys.executable,
        "main.py",
        "--no-serve",
        "--grouping-method",
        args.method,
    ]
    if args.no_set_filter:
        cmd.append("--set-exclusion-min-size")
        cmd.append("99")

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    elapsed = time.time() - start

    output = {
        "method": args.method,
        "elapsed_seconds": round(elapsed, 2),
        "exit_code": result.returncode,
        "stdout_tail": result.stdout[-2000:] if result.stdout else "",
        "stderr_tail": result.stderr[-500:] if result.stderr else "",
        "status": "completed" if result.returncode == 0 else "failed",
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
