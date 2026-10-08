"""Record one manual break observation from the command line."""

import argparse
import json

from config import Config
from data.cache_manager import CacheManager
from processing.break_log import rune_density
from processing.valuation.density import RUNE_DENSITY


def main() -> None:
    parser = argparse.ArgumentParser(description="Append a Rune Master break observation")
    parser.add_argument("--item-id", type=int, required=True)
    parser.add_argument("--item-level", type=int, required=True)
    parser.add_argument("--focus")
    parser.add_argument("--runes", required=True, help='JSON object, e.g. {"Force": 3}')
    parser.add_argument("--source", default="manual")
    parser.add_argument("--cache", default=Config.CACHE_FILE)
    args = parser.parse_args()
    runes = json.loads(args.runes)
    if not isinstance(runes, dict):
        raise SystemExit("--runes must be a JSON object")
    with CacheManager(args.cache) as cache:
        row_id = cache.record_break_observation(
            args.item_id,
            args.item_level,
            args.focus,
            {str(stat): int(quantity) for stat, quantity in runes.items()},
            rune_density(runes, RUNE_DENSITY),
            args.source,
        )
    print(f"Recorded break observation {row_id}")


if __name__ == "__main__":
    main()