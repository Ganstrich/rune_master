"""Break-log helpers for observed taux calculations."""

from typing import Mapping


def observed_taux(observed_density: float, theoretical_density: float) -> float:
    """Return observed/theoretical density, or zero when no density was expected."""
    if theoretical_density <= 0:
        return 0.0
    return observed_density / theoretical_density


def rune_density(runes_received: Mapping[str, int], densities: Mapping[str, float]) -> float:
    """Calculate observed rune density from rune quantities and density constants."""
    return sum(max(int(quantity), 0) * densities.get(stat, 0.0) for stat, quantity in runes_received.items())