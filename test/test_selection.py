from models import Equipment
from processing.selection import PortfolioSelector


def equipment(equipment_id: int) -> Equipment:
    return Equipment(equipment_id, None, 1, f"Equipment {equipment_id}")


def test_selector_keeps_score_order_and_deduplicates_overlapping_groups() -> None:
    proposals = [
        {"fitness_score": 0.7, "equipments": [equipment(1), equipment(2)]},
        {"fitness_score": 0.9, "equipments": [equipment(1), equipment(2)]},
        {"fitness_score": 0.8, "equipments": [equipment(3), equipment(4)]},
        {"fitness_score": 1.0, "equipments": [equipment(5)]},
    ]

    selected = PortfolioSelector.select(proposals, overlap_threshold=0.7)

    assert [group["fitness_score"] for group in selected] == [0.9, 0.8]