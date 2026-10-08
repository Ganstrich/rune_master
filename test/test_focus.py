import pytest

from models import Equipment, EquipmentStat
from processing.valuation.focus import break_density, break_density_focused


def make_equipment(effects: list[EquipmentStat]) -> Equipment:
    return Equipment(1, {"id": 1, "name": "test"}, 50, "Test", effects=effects)


def test_focus_formulas_cover_single_and_two_stat_items() -> None:
    single = make_equipment([EquipmentStat({"id": 1, "name": "Force"}, 10, 10)])
    two_stats = make_equipment([
        EquipmentStat({"id": 1, "name": "Force"}, 10, 10),
        EquipmentStat({"id": 2, "name": "Vitalité"}, 20, 20),
    ])

    assert break_density(single) == pytest.approx(10.0)
    assert break_density_focused(single, "Force") == pytest.approx(10.0)
    assert break_density(two_stats) == pytest.approx(14.0)
    assert break_density_focused(two_stats, "Force") == pytest.approx(12.0)
    assert break_density_focused(two_stats, "Force") >= break_density(two_stats) / 2


def test_negative_and_empty_stat_lines_do_not_add_density() -> None:
    item = make_equipment([EquipmentStat({"id": 1, "name": "Force"}, -10, -2)])

    assert break_density(item) == 0.0
    assert break_density_focused(item, "Force") == 0.0
    assert break_density(make_equipment([])) == 0.0