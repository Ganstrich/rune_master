"""Orchestrate the full evaluation across grouping methods."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

METHODS = ("greedy",)


def run_in_subprocess(name: str, mode: str, timeout: int) -> dict:
    """Run challenge_worker.py in a subprocess."""
    cmd = [
        sys.executable,
        "scripts/challenge_worker.py",
        "--method",
        name,
    ]
    if mode == "expert":
        cmd.extend(["--expert", name])

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "method": name,
            "mode": mode,
            "status": "completed" if result.returncode == 0 else "failed",
            "elapsed": round(time.time() - start, 2),
            "output": result.stdout[-1000:] if result.stdout else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "method": name,
            "mode": mode,
            "status": "timed_out",
            "elapsed": timeout,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate all grouping methods")
    parser.add_argument("--snapshot", default="data/snapshots/3.7.7.6")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--out", default="data/plans/challenge-results.json")
    args = parser.parse_args()

    results = []
    for method in METHODS:
        print(f"Running {method}...")
        result = run_in_subprocess(method, "method", args.timeout)
        results.append(result)
        print(f"  {result['status']} ({result['elapsed']}s)")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults saved to {args.out}")


if __name__ == "__main__":
    main()
