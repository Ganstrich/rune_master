"""Print an exploration shortlist from a JSON equipment and log export."""

import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the break exploration shortlist")
    parser.add_argument("--input", required=True, help="JSON with items and observations")
    args = parser.parse_args()
    payload = json.loads(open(args.input, encoding="utf-8").read())
    from processing.exploration import rank_exploration
    from data.loaders import EquipmentLoader

    items = [EquipmentLoader().from_raw_api(raw) for raw in payload["items"]]
    for candidate in rank_exploration(items, payload.get("observations", [])):
        print(
            f"{candidate.item_id}\t{candidate.item_name}\t"
            f"density={candidate.theoretical_break_density:.2f}\t"
            f"observations={candidate.observation_count}\t"
            f"score={candidate.exploration_score:.2f}\t{candidate.record_command}"
        )


if __name__ == "__main__":
    main()