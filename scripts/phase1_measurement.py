"""Measure pipeline performance on the frozen snapshot."""

import argparse
import json
import time
from pathlib import Path

from data.snapshot import load_snapshot
from processing.config import ProcessingConfig
from processing.orchestrator import RuneMaster


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure greedy pipeline performance")
    parser.add_argument("--snapshot", default="data/snapshots/3.7.7.6")
    parser.add_argument("--out", default="data/plans/phase1-measurement.json")
    args = parser.parse_args()

    equipments, _, _ = load_snapshot(args.snapshot)
    config = ProcessingConfig()

    master = RuneMaster(equipments, config=config)
    start = time.time()
    groups = master.run_greedy()
    elapsed = time.time() - start

    result = {
        "method": "greedy",
        "pool_size": len(master.equipments),
        "groups": len(groups),
        "elapsed_seconds": round(elapsed, 3),
        "summary": master.get_summary(),
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Measured: {len(groups)} groups in {elapsed:.1f}s")
    print(f"Saved to {args.out}")


if __name__ == "__main__":
    main()
