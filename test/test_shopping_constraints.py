from processing.config_dataclass import ProcessingConfig
from processing.policy import GroupAcceptancePolicy


def group(size: int, line_items: int, total_units: int) -> dict[str, object]:
    return {
        "group_size": size,
        "shared_resources_count": 3,
        "sharing_efficiency": 0.5,
        "quality_score": 0.5,
        "unique_ingredients_count": line_items,
        "total_items_needed": total_units,
    }


def test_compact_large_group_is_admissible() -> None:
    policy = GroupAcceptancePolicy(ProcessingConfig())

    assert policy.accepts(group(20, 9, 180))


def test_large_shopping_list_is_rejected() -> None:
    policy = GroupAcceptancePolicy(ProcessingConfig())

    assert not policy.accepts(group(4, 40, 40))
    assert policy.rejection_reason(group(4, 40, 40)) == "max_line_items"