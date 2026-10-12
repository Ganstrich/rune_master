from processing.valuation.stat_calculator import STAT_WEIGHTS
from processing.valuation.density import RUNE_DENSITY


def test_rune_density_matches_the_existing_published_reference() -> None:
    """Reference is the Dofus 3 rune weight table used by the prior calculator."""
    assert RUNE_DENSITY == STAT_WEIGHTS
    assert RUNE_DENSITY["% Résistance terre"] == 6
    assert RUNE_DENSITY["Résistance Terre"] == 2
    assert RUNE_DENSITY["Vitalité"] == 0.2