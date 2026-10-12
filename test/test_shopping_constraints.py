from processing.config import ProcessingConfig
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
    """A large group inside the shopping budget is admissible."""
    policy = GroupAcceptancePolicy(ProcessingConfig())

    # 12 is the group_max_size ceiling: max_line_items=32 admits compact
    # 12-item unions, where the former 12-line cap rejected 95% of them.
    assert policy.accepts(group(12, 9, 180))


def test_group_above_max_size_is_rejected() -> None:
    policy = GroupAcceptancePolicy(ProcessingConfig())

    assert not policy.accepts(group(13, 9, 180))
    assert policy.rejection_reason(group(13, 9, 180)) == "group_size"


def test_large_shopping_list_is_rejected() -> None:
    policy = GroupAcceptancePolicy(ProcessingConfig())

    assert not policy.accepts(group(4, 40, 40))
    assert policy.rejection_reason(group(4, 40, 40)) == "max_line_items"