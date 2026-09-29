import pytest

from models import Equipment, EquipmentStat, ResourceRequirement
from processing.valuation.economic import FlatTauxModel, ProfitObjective
from processing.valuation.objective import GroupCandidate
from processing.valuation.overlap import OverlapObjective
from processing.valuation.prices import NullPriceSource


class Prices:
    def resource_price(self, resource_id: int) -> float | None:
        return 20.0 if resource_id == 10 else None

    def rune_price(self, stat: str) -> float | None:
        return 100.0 if stat == "Force" else None

    def depth(self, item_id: int) -> None:
        return None


def item() -> Equipment:
    return Equipment(
        1,
        {"id": 1},
        50,
        "Test",
        effects=[EquipmentStat({"id": 1, "name": "Force"}, 10, 10)],
        recipe=[ResourceRequirement(10, 1)],
    )


def test_null_prices_fall_back_to_overlap() -> None:
    candidate = GroupCandidate([item()])
    objective = ProfitObjective(NullPriceSource())

    assert objective.score(candidate) == pytest.approx(OverlapObjective().score(candidate))
    assert objective.score_details(candidate)["fallback"] is True


def test_profit_is_kamas_and_records_focus() -> None:
    details = ProfitObjective(Prices(), FlatTauxModel(0.5)).score_details(
        GroupCandidate([item()])
    )

    assert details["score"] == pytest.approx(480.0)
    assert details["unit"] == "kamas"
    assert details["focus_by_item"] == {1: "Force"}