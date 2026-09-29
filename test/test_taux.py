from datetime import datetime, timezone

from processing.valuation.taux import PosteriorTauxModel


def test_taux_prior_bonus_and_volume_decay() -> None:
    model = PosteriorTauxModel(
        [], {}, prior=1.2, now=datetime.now(timezone.utc)
    )

    assert model.expected(10, 0) == 1.2
    assert model.expected(10, 10) < model.expected(10, 0)
    assert model.confidence(10) == 0.0
    assert model.exploration_bonus(10) > 0.0


def test_fresher_observation_is_weighted_more_heavily() -> None:
    now = datetime(2026, 1, 8, tzinfo=timezone.utc)
    model = PosteriorTauxModel(
        [
            {"item_id": 1, "observed_density": 4.0, "observed_at": "2026-01-08T00:00:00+00:00"},
            {"item_id": 1, "observed_density": 1.0, "observed_at": "2025-12-25T00:00:00+00:00"},
        ],
        {1: 1.0},
        prior=0.0,
        half_life_days=7.0,
        now=now,
    )

    assert model.expected(1, 0) > 2.0
    assert model.confidence(1) > 0.0