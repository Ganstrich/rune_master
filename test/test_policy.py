from models import Equipment
from processing.config import ProcessingConfig
from processing.policy import GroupAcceptancePolicy


def test_policy_reports_first_rejection_reason_and_accepts_valid_group() -> None:
    policy = GroupAcceptancePolicy(
        ProcessingConfig(
            group_min_size=2,
            group_max_size=4,
            group_min_shared_resources=2,
            group_efficiency_threshold=0.5,
            group_quality_threshold=0.4,
        )
    )
    group = {
        "equipments": [Equipment(1, None, 1, "one")],
        "shared_resources_count": 2,
        "sharing_efficiency": 0.8,
        "quality_score": 0.9,
    }

    assert policy.rejection_reason(group) == "group_size"
    group["equipments"].append(Equipment(2, None, 1, "two"))
    group["group_size"] = 2
    assert policy.accepts(group)


def test_policy_rejects_groups_dominated_by_one_panoplie() -> None:
    """No group may be majority-built from a single set."""
    policy = GroupAcceptancePolicy(
        ProcessingConfig(
            group_min_size=2,
            group_min_shared_resources=0,
            group_efficiency_threshold=0.0,
            group_max_set_share=0.5,
        )
    )
    group = {
        "group_size": 4,
        "shared_resources_count": 2,
        "sharing_efficiency": 0.8,
        "quality_score": 0.9,
        "largest_set_share": 0.5,
    }

    assert policy.accepts(group)

    group["largest_set_share"] = 0.75
    assert policy.rejection_reason(group) == "largest_set_share"