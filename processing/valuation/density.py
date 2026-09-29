"""Game rune-density constants and stat-name normalization."""

from typing import Mapping


# Reference: Dofus 3 rune weight table used by the project's existing stat model.
RUNE_DENSITY: dict[str, float] = {
    "PA": 100, "PM": 90, "Portée": 51, "Invocation": 30,
    "Dommage": 5, "Dommages": 5, "Dommage Terre": 5, "Dommages Terre": 5,
    "Dommage Feu": 5, "Dommages Feu": 5, "Dommage Eau": 5, "Dommages Eau": 5,
    "Dommage Air": 5, "Dommages Air": 5, "Dommage Neutre": 5, "Dommages Neutre": 5,
    "Dommage Critiques": 5, "Dommages Critiques": 5, "Dommages poussée": 5,
    "Dommage poussée": 5, "Dommage Pièges": 5, "Dommages Pièges": 5,
    "% Résistance terre": 6, "% Résistances terre": 6, "% Résistance feu": 6,
    "% Résistances feu": 6, "% Résistance eau": 6, "% Résistances eau": 6,
    "% Résistance air": 6, "% Résistances air": 6, "% Résistance neutre": 6,
    "% Résistances neutre": 6, "Retrait PA": 7, "Retraits PA": 7,
    "Retrait PM": 7, "Retraits PM": 7, "Esquive PA": 7, "Esquives PA": 7,
    "Esquive PM": 7, "Esquives PM": 7, "% Critique": 10, "% Critiques": 10,
    "Soin": 10, "Soins": 10, "Renvoi dommages": 10, "Renvois dommages": 10,
    "Tacle": 4, "Tacles": 4, "Fuite": 4, "Fuites": 4, "Sagesse": 3,
    "Prospection": 3, "Puissance": 2, "Résistance Terre": 2,
    "Résistances Terre": 2, "Résistance Feu": 2, "Résistances Feu": 2,
    "Résistance Eau": 2, "Résistances Eau": 2, "Résistance Air": 2,
    "Résistances Air": 2, "Résistance Neutre": 2, "Résistances Neutre": 2,
    "Résistance Critiques": 2, "Résistances Critiques": 2,
    "Résistance Poussée": 2, "Résistances Poussée": 2, "Force": 1,
    "Intelligence": 1, "Agilité": 1, "Chance": 1, "Vitalité": 0.2,
    "Pod": 0.25, "Initiative": 0.1,
}


def resolve_stat_name(raw_name: str, stat_weights: Mapping[str, float] | None = None) -> str:
    """Resolve API singular/plural and case variants to a density key."""
    weights = stat_weights or RUNE_DENSITY
    if raw_name in weights:
        return raw_name
    for key in weights:
        if key.lower() == raw_name.lower():
            return key

    def variants(name: str) -> set[str]:
        lowered = name.lower()
        result = {lowered}
        if lowered.endswith("s"):
            result.add(lowered[:-1])
        if lowered.endswith("es"):
            result.add(lowered[:-2])
        return result

    raw_variants = variants(raw_name)
    for key in weights:
        if raw_variants & variants(key):
            return key
    similar = [key for key in weights if key.lower().startswith(raw_name.lower()[:3])]
    raise KeyError(
        f"Unknown stat type: '{raw_name}'. "
        f"Did you mean: {similar if similar else 'See available stats below'}? "
        f"Available: {list(weights.keys())}"
    )