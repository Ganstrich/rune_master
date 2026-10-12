"""Game rune-density constants and stat-name normalization."""

from typing import Mapping


# Reference: Dofus 3 rune weight table used by the project's existing stat model.
RUNE_DENSITY: dict[str, float] = {
    "PA": 100, "PM": 90, "Portée": 51, "Invocation": 30,
    "Dommage": 5, "Dommages": 5, "Dommage Terre": 5, "Dommages Terre": 5,
    "Dommage Feu": 5, "Dommages Feu": 5, "Dommage Eau": 5, "Dommages Eau": 5,
    "Dommage Air": 5, "Dommages Air": 5, "Dommage Neutre": 5, "Dommages Neutre": 5,
    "Dommage Critiques": 5, "Dommages Critiques": 5, "Dommage poussée": 5,
    "Dommage poussée": 5, "Dommage Pièges": 5, "Dommages Pièges": 5,
    "Dommage Critique": 5, "Dommages Critique": 5,
    "Dommage Poussée": 5, "Dommages Poussée": 5,
    "% Résistance terre": 6, "% Résistances terre": 6, "% Résistance feu": 6,
    "% Résistances feu": 6, "% Résistance eau": 6, "% Résistances eau": 6,
    "% Résistance air": 6, "% Résistances air": 6, "% Résistance neutre": 6,
    "% Résistances neutre": 6,
    "% Résistance Air": 6, "% Résistances Air": 6,
    "% Résistance Feu": 6, "% Résistances Feu": 6,
    "% Résistance Eau": 6, "% Résistances Eau": 6,
    "% Résistance Terre": 6, "% Résistances Terre": 6,
    "% Résistance Neutre": 6, "% Résistances Neutre": 6,
    "% Résistance mêlée": 6, "% Résistance distance": 6,
    "Retrait PA": 7, "Retraits PA": 7,
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
    "soins Neutre": 10, "soins Feu": 10,
    "vol Eau": 1, "vol Feu": 1, "vol Air": 1, "vol Neutre": 1, "vol Terre": 1,
    "Vole PM": 1,
    "Puissance Pièges": 2,
    "Dommages Renvoyés": 10,
    "% Dommages d'armes": 5, "% Dommages distance": 5,
    "% Dommages mêlée": 5, "% Dommages aux sorts": 5,
    "dommages du meilleur élément": 5,
    "vol du meilleur élément": 1,
    ": + Dommages": 5,
}

# Non-rune stats: spell effects, crafting constraints, formatting artifacts.
# These are silently skipped (no warning, no weight contribution).
NON_RUNE_STATS: frozenset[str] = frozenset({
    "Arme de chasse", "Attire de case", "Repousse de case",
    "-special spell-", "Fabrication coopérative impossible",
    "Quelqu'un vous suit !", "Titre :", "Lié au personnage",
    "Taille : %", "Avance de case",
    ": + Portée maximale", ": - PA", ": ligne de vue désactivée",
    ": Portée modifiable", ": - de relance", ": + lancer par tour",
    ": +% Critique", ": lancer en ligne désactivé",
    ": + lancer par cible", ": + dégâts de base",
    ": - Portée minimale", ": case occupée nécessaire désactivée",
})


class UnknownStatError(KeyError):
    """Raised for stat names that are not in the density table."""
    pass


def resolve_stat_name(
    raw_name: str,
    stat_weights: Mapping[str, float] | None = None,
    *,
    skip_non_rune: bool = True,
) -> str:
    """Resolve API singular/plural and case variants to a density key.

    Non-rune stats (spell effects, crafting constraints, formatting
    artifacts) are silently skipped when ``skip_non_rune`` is True.
    """
    if raw_name in NON_RUNE_STATS:
        if skip_non_rune:
            raise _NonRuneStat(raw_name)
        raise UnknownStatError(raw_name)
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
    raise UnknownStatError(raw_name)


class _NonRuneStat(KeyError):
    """Internal sentinel for non-rune stats that should be silently skipped."""
    pass