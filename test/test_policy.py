from models import Equipment
from processing.config_dataclass import ProcessingConfig
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