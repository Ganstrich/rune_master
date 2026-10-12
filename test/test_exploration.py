from datetime import datetime, timezone, timedelta

from models import Equipment, EquipmentStat, ResourceRequirement
from processing.valuation.exploration import rank_exploration


def item(item_id: int) -> Equipment:
    return Equipment(
        item_id,
        {"id": 1},
        50,
        f"Item {item_id}",
        effects=[EquipmentStat({"id": 1, "name": "Force"}, 10, 10)],
        recipe=[ResourceRequirement(10, 1)],
    )


def test_empty_log_produces_a_density_ranked_shortlist() -> None:
    candidates = rank_exploration([item(1), item(2)], [], now=datetime.now(timezone.utc))

    assert candidates
    assert all(candidate.observation_count == 0 for candidate in candidates)
    assert "break_log.py" in candidates[0].record_command


def test_poor_observation_drops_until_it_becomes_stale() -> None:
    now = datetime(2026, 1, 8, tzinfo=timezone.utc)
    recent = [{
        "item_id": 1,
        "observed_density": 0.1,
        "observed_at": "2026-01-08T00:00:00+00:00",
    }]
    stale = [{
        **recent[0],
        "observed_at": (now - timedelta(days=14)).isoformat(),
    }]

    recent_score = rank_exploration([item(1)], recent, now=now)[0].exploration_score
    stale_score = rank_exploration([item(1)], stale, now=now)[0].exploration_score

    assert stale_score > recent_score