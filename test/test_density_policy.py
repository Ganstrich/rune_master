from models import Equipment
from processing.config import ProcessingConfig
from data.loaders import EquipmentLoader


def test_zero_density_equipment_is_excluded_from_loaded_pool() -> None:
    loader = EquipmentLoader()
    raw_items = [
        {"ankama_id": 1, "type": {"id": 1}, "name": "Zero", "level": 10},
        {
            "ankama_id": 2,
            "type": {"id": 1},
            "name": "Valued",
            "level": 10,
            "effects": [
                {
                    "type": {"id": 118, "name": "Vitalité"},
                    "int_minimum": 10,
                    "int_maximum": 10,
                }
            ],
        },
    ]

    retained = loader.from_raw_batch(raw_items)

    assert [item.ankama_id for item in retained] == [2]


def test_density_percentile_is_computed_within_level_bands() -> None:
    items = [
        Equipment(index, {"id": 1}, level, str(index), stat_weight=weight)
        for index, (level, weight) in enumerate(
            [(10, 1.0), (10, 2.0), (10, 3.0), (50, 1.0), (50, 2.0), (50, 3.0)],
            start=1,
        )
    ]

    retained = EquipmentLoader._filter_by_density_percentile(items, 0.5, 20)

    assert {item.ankama_id for item in retained} == {2, 3, 5, 6}