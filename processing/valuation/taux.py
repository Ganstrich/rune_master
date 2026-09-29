"""Observed taux models with explicit decay and uncertainty."""

import math
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Protocol


class TauxModel(Protocol):
    def expected(self, item_id: int, planned_volume: int) -> float: ...

    def confidence(self, item_id: int) -> float: ...

    def exploration_bonus(self, item_id: int) -> float: ...


class PosteriorTauxModel:
    """Estimate taux from age-weighted observed density ratios."""

    def __init__(
        self,
        observations: Iterable[dict[str, object]],
        theoretical_density: dict[int, float],
        prior: float = 1.0,
        half_life_days: float = 7.0,
        volume_decay: float = 0.01,
        bonus_scale: float = 0.5,
        now: datetime | None = None,
    ) -> None:
        self.prior = prior
        self.half_life_days = half_life_days
        self.volume_decay = volume_decay
        self.bonus_scale = bonus_scale
        self.now = now or datetime.now(timezone.utc)
        self._weighted: dict[int, tuple[float, float]] = {}
        for row in observations:
            item_id = int(row["item_id"])
            denominator = theoretical_density.get(item_id, 0.0)
            if denominator <= 0:
                continue
            observed_at = datetime.fromisoformat(str(row["observed_at"]))
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=timezone.utc)
            age_days = max((self.now - observed_at).total_seconds() / 86400, 0.0)
            weight = math.exp(-math.log(2) * age_days / half_life_days)
            ratio = float(row["observed_density"]) / denominator
            total, weights = self._weighted.get(item_id, (0.0, 0.0))
            self._weighted[item_id] = (total + ratio * weight, weights + weight)

    def confidence(self, item_id: int) -> float:
        """Return confidence in [0, 1] based on effective observations."""
        _total, weight = self._weighted.get(item_id, (0.0, 0.0))
        return weight / (weight + 1.0)

    def expected(self, item_id: int, planned_volume: int) -> float:
        """Return a non-increasing volume-adjusted taux estimate."""
        total, weight = self._weighted.get(item_id, (0.0, 0.0))
        posterior = total / weight if weight else self.prior
        return posterior * math.exp(-self.volume_decay * max(planned_volume, 0))

    def exploration_bonus(self, item_id: int) -> float:
        """Return a positive bonus that shrinks with effective history."""
        _total, weight = self._weighted.get(item_id, (0.0, 0.0))
        return self.bonus_scale / math.sqrt(weight + 1.0)