from models import Equipment
from processing.config_dataclass import ProcessingConfig
from data.loaders import EquipmentLoader


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