#!/usr/bin/env python3
"""Run one grouping method or expert and print its groups as JSON.

Invoked by scripts/challenge_evaluate.py in a subprocess so a slow or hung
method cannot take down the whole evaluation. Prints a single @@RESULT@@ line.

Usage:
    uv run python scripts/challenge_worker.py --snapshot <dir> \
        --method greedy
    uv run python scripts/challenge_worker.py --snapshot <dir> \
        --expert baseline
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.snapshot import load_snapshot
from processing.config_dataclass import ProcessingConfig
from processing.orchestrator import RuneMaster

METHOD_DISPATCH = {
    "deterministic": "run_deterministic",
    "random": "run_random_grouping",
    "hybrid": "run_hybrid_grouping",
    "greedy": "run_greedy",
    "survey": "run_survey",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, help="Snapshot directory")
    parser.add_argument("--method", default=None)
    parser.add_argument("--expert", default=None)
    parser.add_argument("--no-set-filter", action="store_true",
                        help="Disable the panoplie exclusion (plan §3.3 C5)")
    args = parser.parse_args()

    if bool(args.method) == bool(args.expert):
        parser.error("exactly one of --method / --expert is required")

    equipments, _, _ = load_snapshot(Path(args.snapshot))
    config = ProcessingConfig(grouping_method=args.method or "hybrid")
    if args.no_set_filter:
        config.set_exclusion_min_size = 99

    master = RuneMaster(equipments, config=config)

    if args.expert:
        expert = master.experts.get(args.expert)
        if expert is None:
            print(f"@@ERROR@@ unknown expert {args.expert!r}", flush=True)
            return 1
        groups = expert.discover_groups(master.equipments, config)
    else:
        dispatch = METHOD_DISPATCH.get(args.method)
        if dispatch is None:
            print(f"@@ERROR@@ unknown method {args.method!r}", flush=True)
            return 1
        groups = getattr(master, dispatch)()

    payload = [
        {"equipments": [int(e.ankama_id) for e in g.get("equipments", [])]}
        for g in groups
    ]
    print("@@RESULT@@" + json.dumps(payload), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
