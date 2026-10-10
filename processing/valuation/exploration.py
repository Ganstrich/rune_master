"""Rank items worth testing for break-rate information."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from models import Equipment
from processing.blocks.recipes import iter_recipe
from processing.valuation.focus import break_density
from processing.valuation.taux import PosteriorTauxModel


@dataclass(frozen=True)
class ExplorationCandidate:
    item_id: int
    item_name: str
    theoretical_break_density: float
    observation_count: int
    latest_age_days: float | None
    last_observed_taux: float | None
    exploration_score: float
    record_command: str


def rank_exploration(
    items: Iterable[Equipment],
    observations: list[dict[str, object]],
    half_life_days: float = 7.0,
    now: datetime | None = None,
) -> list[ExplorationCandidate]:
    """Return a density-per-recipe-unit exploration shortlist."""
    current = now or datetime.now(timezone.utc)
    densities = {item.ankama_id: break_density(item) for item in items}
    model = PosteriorTauxModel(
        observations, densities, half_life_days=half_life_days, now=current
    )
    by_item: dict[int, list[dict[str, object]]] = {}
    for observation in observations:
        by_item.setdefault(int(observation["item_id"]), []).append(observation)
    candidates: list[ExplorationCandidate] = []
    for item in items:
        item_observations = by_item.get(item.ankama_id, [])
        latest = max(
            (datetime.fromisoformat(str(row["observed_at"])) for row in item_observations),
            default=None,
        )
        if latest and latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        age_days = (
            max((current - latest).total_seconds() / 86400, 0.0) if latest else None
        )
        last_taux = None
        if item_observations and densities[item.ankama_id] > 0:
            last_taux = float(
                max(item_observations, key=lambda row: str(row["observed_at"]))[
                    "observed_density"
                ]
            ) / densities[item.ankama_id]
        recipe_units = sum(quantity for _resource_id, quantity in iter_recipe(item))
        density_per_unit = densities[item.ankama_id] / max(recipe_units, 1)
        score = density_per_unit * (
            model.expected(item.ankama_id, 0)
            + model.exploration_bonus(item.ankama_id)
        )
        candidates.append(
            ExplorationCandidate(
                item.ankama_id,
                item.name,
                densities[item.ankama_id],
                len(item_observations),
                age_days,
                last_taux,
                score,
                f"python break_log.py --item-id {item.ankama_id} --item-level {item.level}",
            )
        )
    return sorted(candidates, key=lambda candidate: candidate.exploration_score, reverse=True)