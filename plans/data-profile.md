# Data Profile: Full Snapshot

**Snapshot version:** 3.7.7.6  
**Created:** 2026-10-09T19:56:21.637624+00:00  
**Equipment:** 2858  
**Resources:** 1642  
**Set mappings:** 3646  
**Level range:** 1 - 200  

**Density filter formula:** `stat_weight >= level * 3.0` (matches `ProcessingConfig.equipment_density_level_ratio = 3.0`)

**Related:** project wiki in-repo at `wiki/` (see `wiki/concepts/cost-popularity-taux-hypothesis.md`).

---

## RECIPES

### 1. Distinct resources per recipe; units per recipe

| Metric | min | median | p90 | max | n |
|--------|-----|--------|-----|-----|---|
| Distinct resources | 0 | 6 | 8 | 8 | 2858 |
| Total units | 0 | 27 | 184 | 8046 | 2858 |

**Items with empty recipes (0 resources):** 2 (0.1%)

### 2. Resource frequency: top 30 most shared resources

| Rank | Resource ID | Name | Items | % of recipes |
|------|-------------|------|-------|--------------|
| 1 | 26870 | Fragment d'anomalie | 211 | 7.4% |
| 2 | 14921 | Étoffe Mystérieuse | 178 | 6.2% |
| 3 | 16460 | Substrat de Sylve | 176 | 6.2% |
| 4 | 15219 | Trame Dimensionnelle | 162 | 5.7% |
| 5 | 12740 | Galet brasillant | 154 | 5.4% |
| 6 | 12728 | Ardonite | 149 | 5.2% |
| 7 | 14635 | Pépite | 148 | 5.2% |
| 8 | 15271 | Tourmaline | 124 | 4.3% |
| 9 | 2540 | Substrat de Futaie | 121 | 4.2% |
| 10 | 12745 | Substrat de Bocage | 121 | 4.2% |
| 11 | 746 | Ébonite | 117 | 4.1% |
| 12 | 33515 | Neurone de dragodinde | 111 | 3.9% |
| 13 | 19975 | Corne de volkorne | 110 | 3.8% |
| 14 | 17864 | Ambre de muldo | 102 | 3.6% |
| 15 | 749 | Bakélélite | 90 | 3.1% |
| 16 | 748 | Magnésite | 86 | 3.0% |
| 17 | 16212 | Substrat de Fourré | 78 | 2.7% |
| 18 | 12737 | Galet cramoisi | 75 | 2.6% |
| 19 | 2543 | Substrat de Fascine | 71 | 2.5% |
| 20 | 12744 | Substrat de Bosquet | 69 | 2.4% |
| 21 | 12733 | Substrat de Forêt | 68 | 2.4% |
| 22 | 16459 | Substrat de Forêt vierge | 67 | 2.3% |
| 23 | 24144 | Substrat Astral | 66 | 2.3% |
| 24 | 12738 | Galet rutilant | 63 | 2.2% |
| 25 | 6457 | Kriptonite | 60 | 2.1% |
| 26 | 750 | Kouartz | 57 | 2.0% |
| 27 | 13367 | Galet Solaire | 55 | 1.9% |
| 28 | 13366 | Galet Lunaire | 54 | 1.9% |
| 29 | 8916 | Ambre du Tynril | 53 | 1.9% |
| 30 | 29444 | Galet rayonnant | 53 | 1.9% |

**Resources appearing in > 20% of recipes** (threshold = 572 items):

_None._

### 3. Are 15263 and 14635 actually the ubiquitous ones?

| Resource ID | Name | Items | % of recipes | In excluded set? |
|-------------|------|-------|--------------|------------------|
| 14635 | Pépite | 148 | 5.2% | yes |
| 15263 | not in snapshot | 0 | 0.0% | yes |

_No other resources exceed the 20% threshold; 15263 and 14635 are the only ubiquitous ones._

### 4. Resources used by exactly one item (dead-ends for sharing)

**Count:** 173

| Resource ID | Name |
|-------------|------|
| 290 | Champignon |
| 311 | Eau Potable |
| 381 | Fraise |
| 391 | Noix de Cajou |
| 397 | Huile de Koode |
| 399 | Huile de Sésame |
| 410 | Livre du Bwork Mage |
| 424 | Fibre criminelle |
| 430 | Os Invisible du Chafer Invisible |
| 442 | Bronze |
| 465 | Cristal |
| 467 | Rubis |
| 538 | Pommes de Terre épluchées |
| 543 | Pierre de Diamant |
| 545 | Pierre de Cristal |
| 546 | Pierre de Saphir |
| 547 | Pierre de Rubis |
| 600 | Kralamoure |
| 654 | Étoffe du Wabbit |
| 1002 | Tronc de Kokoko |
| 1557 | Rune Ga Pa |
| 1683 | Sac à Patates Clair |
| 1687 | Teinture Magique Verdâtre |
| 1750 | Poisson Pané |
| 1973 | Huile à frire |
| 1978 | Mesure de Poivre |
| 2060 | Patte de Corbac |
| 2266 | Lait de Cochon de Lait |
| 2297 | Flèche du Chafer Archer |
| 2549 | Boîte de Vétauran |
| 2584 | Main de Boo |
| 2617 | Tranche de Nodkoko |
| 2632 | Glouto Rhum |
| 2653 | Arakne Majeure Morte |
| 2656 | Os rongé de Gobichon |
| 2805 | Testicules Magiques de Muloubard |
| 6904 | Protection usagée du Bworker |
| 7013 | Bois de Bambou |
| 7033 | Dolomite |
| 7274 | Katana de Kwamouraï |
| 7276 | Baguette de Tétonuki |
| 7438 | Rune Po |
| 7442 | Rune Invo |
| 8055 | Os de Mama Koalak |
| 8065 | Poils de barbe de dragodinde |
| 8066 | Poils de Barbe du Warko Violet |
| 8076 | Boomerang du Maître Koalak |
| 8345 | Corne de Dragoss Protéiforme |
| 8348 | Coquille de Dragoss Charbon |
| 8353 | Écaille de Dragoss Ardoise |
| 8729 | Corail usé |
| 8733 | Corail Malibout |
| 8734 | Corail Passaoh |
| 8762 | Fragment de cerveau poli |
| 8804 | Braguette du Maître Zoth |
| 8805 | Mouchoir de la Gamine Zoth |
| 9940 | Nacre brute |
| 10221 | Eau transmutée |
| 10831 | Bananagrume |
| 10835 | Cachet du bizut |
| 11102 | Perce-Neige |
| 11107 | Bois de Tremble |
| 11110 | Obsidienne |
| 11247 | Oreille percée du Fricochère |
| 11251 | Sternum de Chachachovage |
| 11252 | Patte de Rat Bougri |
| 11253 | Étoffe de Rat Bougri |
| 11254 | Pince de Crabe Hijacob |
| 11255 | Œil de Crabe Hijacob |
| 11559 | Pierre de Feu |
| 11560 | Pierre de Terre |
| 11561 | Pierre d'Eau |
| 11562 | Pierre d'Air |
| 11795 | Racine de synthèse |
| 12970 | Paquet Cadeau du Minotoboule de Nowel |
| 13172 | Casque Mâchouillé |
| 13193 | Fiole de gaz draconique |
| 13196 | Cuir synthétique |
| 13365 | Galet Saisonnier |
| 13593 | Peau de Larve Saphir |
| 13697 | Poils de Guerrier Koalak |
| 13700 | Couche usagée de Warko Violet |
| 13702 | Dédicace de Skeunk pour Émeraude |
| 13706 | Journal Intime d'Émeraude |
| 13708 | Pense-bête de Rubise |
| 13716 | Bec de Vilain Petit Tofu |
| 13722 | Plume de Tofubine |
| 13723 | Œuf de Tofubine |
| 13724 | Patte de Tofu Dodu |
| 13725 | Aile Atrophiée de Tofu Dodu |
| 14507 | Pelote d'Ecaflip |
| 14868 | Vieille Tête de Marteau |
| 14936 | Insigne des Justiciers |
| 14977 | Bitte d'amarrage |
| 15046 | Canine de Félygiène |
| 15452 | Patte de Scoliopode |
| 15453 | Aile de Puceronde |
| 15454 | Pince de Lucrane |
| 15455 | Venin d'Éperfide |
| 15661 | Ossements sacrés de Givrefoux |
| 16149 | Œil d'Abrakne |
| 16162 | Œil de Branche Invocatrice |
| 16207 | Sceau Sylvestre |
| 16208 | Fragment de Rubis Fertile |
| 16497 | Planche à Pain |
| 16526 | Tête de Marteau en Jade |
| 18209 | Gratrooll |
| 18318 | Soie chatoyante |
| 18441 | Cocktail cacterre |
| 19636 | Minerai enchanté |
| 19638 | Support métallique |
| 19640 | Fil enchanté |
| 20648 | Légende de Brumaire |
| 20649 | Légende de Brâm Barbe-Monde |
| 20650 | Légende de Crocobur |
| 20651 | Légende du Trompe-la-Mort |
| 20652 | Légende de Dame Jhessica |
| 20653 | Légende de Mille Lieues |
| 20654 | Légende de Dodge |
| 20655 | Légende de Fallanster |
| 20656 | Légende du Cul Botté |
| 20657 | Légende du Destin |
| 20658 | Légende de Rykke Errel |
| 20659 | Légende de Buhorado |
| 20660 | Légende de Jahash Jurgen |
| 20661 | Légende de Ganymède |
| 20816 | Œil Bionique |
| 20818 | Emballage Suspect |
| 20940 | Oreille de Kakoalak |
| 20942 | Estomac de Mansocolat |
| 20944 | Enrobage de Chocoskargo |
| 20945 | Bec de Kwakao |
| 22048 | Langue de Krèvladal |
| 22049 | Côtes de Désosseur |
| 22050 | Capuche de Skentu |
| 22051 | Œil de Dawaj |
| 22208 | Peau pourrie de Dolid |
| 22210 | Patte de Nheur'Gueule |
| 22211 | Tentacule de Tentaclaque |
| 22212 | Pétale de Gangredogue |
| 22216 | Bois de pagaie usée |
| 22218 | Baguette Rythmique |
| 22223 | Boulet lesté |
| 22224 | Manche de Fouet |
| 22415 | Légende de Misère |
| 22416 | Légende de Guerre |
| 22417 | Légende de Servitude |
| 22418 | Légende de Corruption |
| 23523 | Branche de bambou spirituel |
| 29117 | Morceau du Ménologium |
| 29379 | Métronome du Début-Temps |
| 31674 | Corne de Lapilope |
| 31675 | Défense de Brutapir |
| 32129 | Légende d'Oto Mustam |
| 32130 | Légende du Miroir |
| 32131 | Légende de Mériana |
| 32132 | Légende de Menalt |
| 32133 | Légende de Thanatena |
| 32134 | Légende d'Helséphine |
| 32135 | Légende d'Henual |
| 32162 | Légende d'Amayiro |
| 33520 | Moustache de muldo orchidée |
| 33521 | Moustache de muldo indigo |
| 33522 | Moustache de muldo pourpre |
| 33523 | Moustache de muldo ébène |
| 33524 | Moustache de muldo doré |
| 33529 | Aile de volkorne indigo |
| 34324 | Pièce d'armure des Gardiens du Sanctuaire |
| 34325 | Pommeau brisé de la Reine Écarlate |
| 34326 | Bouquet de lianes de la Princesse Maudite |
| 34337 | Venin de Mureine |
| 34338 | Carapace d'Exécrabe |
| 34339 | Aileron de Willorque |

#### 4b. Dead-end deep dive: are they really single-use?

- **Still single-use when ALL recipe subtypes are counted (quest equipment + consumables included):** 173 of 173. So the resource-only filter is not creating false dead-ends.

**Dead-end resources by resource type:**

| Resource type | Dead-end resources |
|---------------|--------------------|
| Ressource diverse | 33 |
| Ressource des Songes | 26 |
| Os | 14 |
| Pierre précieuse | 9 |
| Pierre brute | 8 |
| Poil | 8 |
| Liquide | 7 |
| Patte | 6 |
| Minerai | 5 |
| Œil | 5 |
| Huile | 4 |
| Étoffe | 4 |
| Bois | 4 |
| Vêtement | 4 |
| Peau | 4 |
| Rune de forgemagie | 3 |
| Fleur | 3 |
| Aile | 3 |
| Fruit | 2 |
| Poisson | 2 |
| Ressource de combat | 2 |
| Oreille | 2 |
| Champignon | 1 |
| Graine | 1 |
| Légume | 1 |
| Teinture | 1 |
| Poudre | 1 |
| Coquille | 1 |
| Racine | 1 |
| Nowel | 1 |
| Matériel d'alchimie | 1 |
| Cuir | 1 |
| Galet | 1 |
| Plume | 1 |
| Œuf | 1 |
| Planche | 1 |
| Carapace | 1 |

**One example per level band** (the single equipment that consumes each dead-end resource; a few shown per band):

| Band | Resource ID | Resource | Resource type | Equipment ID | Eq Lvl | Slot | Equipment |
|------|-------------|----------|---------------|--------------|--------|------|-----------|
| 0 | 19636 | Minerai enchanté | Minerai | 19637 | 1 | hammer | Fléau d'armes |
| 0 | 19638 | Support métallique | Minerai | 19639 | 1 | shield | Écu Rikulome |
| 0 | 19640 | Fil enchanté | Ressource diverse | 19641 | 1 | cloak | Tabard Nak |
| 0 | 311 | Eau Potable | Liquide | 949 | 3 | hat | Bandeau de Vitalité |
| 0 | 399 | Huile de Sésame | Huile | 673 | 8 | axe | Mangeuse de Châtaignier |
| 0 | 16526 | Tête de Marteau en Jade | Ressource diverse | 16527 | 8 | hammer | Marteau de Hargnok |
| 1 | 10831 | Bananagrume | Fruit | 10830 | 28 | cloak | Banana Cape |
| 1 | 8733 | Corail Malibout | Pierre brute | 8873 | 39 | belt | Krustoture |
| 2 | 2653 | Arakne Majeure Morte | Ressource diverse | 11042 | 40 | belt | Cordon Père au gnon |
| 2 | 2656 | Os rongé de Gobichon | Os | 26337 | 42 | boots | Bottes du Directeur Grunob |
| 2 | 2266 | Lait de Cochon de Lait | Liquide | 10643 | 43 | ring | Anneau de Grizou |
| 2 | 2297 | Flèche du Chafer Archer | Ressource diverse | 13092 | 43 | hammer | Marteau du Chafer Draugr |
| 2 | 430 | Os Invisible du Chafer Invisible | Os | 2809 | 49 | belt | Ceinture Chafeuse |
| 2 | 442 | Bronze | Minerai | 1354 | 49 | bow | L'Arc à Hick |
| 3 | 13593 | Peau de Larve Saphir | Peau | 17214 | 60 | belt | Culotte des 1001 Griffes |
| 3 | 33529 | Aile de volkorne indigo | Aile | 34255 | 60 | boots | Botovolko |
| 3 | 381 | Fraise | Fruit | 11375 | 61 | belt | Slipapier |
| 3 | 20818 | Emballage Suspect | Ressource diverse | 20848 | 61 | staff | Sceptre Zor |
| 3 | 9940 | Nacre brute | Pierre brute | 7229 | 64 | hat | Chapeau Aerdala |
| 3 | 10835 | Cachet du bizut | Pierre précieuse | 10836 | 64 | amulet | Boufbamu |
| 4 | 538 | Pommes de Terre épluchées | Légume | 30688 | 80 | shield | Doritoclier |
| 4 | 1973 | Huile à frire | Huile | 30688 | 80 | shield | Doritoclier |
| 4 | 1978 | Mesure de Poivre | Poudre | 30688 | 80 | shield | Doritoclier |
| 4 | 2549 | Boîte de Vétauran | Ressource diverse | 13262 | 80 | cloak | Sac Rebleux |
| 4 | 11254 | Pince de Crabe Hijacob | Os | 16141 | 80 | cloak | Cape Ortail |
| 4 | 546 | Pierre de Saphir | Pierre brute | 2608 | 84 | axe | Francisque Basquaise |
| 5 | 8353 | Écaille de Dragoss Ardoise | Peau | 8728 | 100 | boots | Bottes Deuradi |
| 5 | 2632 | Glouto Rhum | Liquide | 6743 | 104 | ring | Fourballiance |
| 5 | 2805 | Testicules Magiques de Muloubard | Ressource diverse | 180 | 105 | wand | La Baguette des Limbes |
| 5 | 2060 | Patte de Corbac | Patte | 2546 | 106 | hat | Corbacoiffe |
| 5 | 8055 | Os de Mama Koalak | Os | 15014 | 107 | bow | Arc de Flèche Mauve |
| 5 | 11253 | Étoffe de Rat Bougri | Étoffe | 7144 | 108 | hat | Blémiche |
| 6 | 8076 | Boomerang du Maître Koalak | Ressource de combat | 6523 | 120 | staff | La Racine Hagogue |
| 6 | 13702 | Dédicace de Skeunk pour Émeraude | Ressource diverse | 14004 | 120 | boots | Bottes de Mandrin |
| 6 | 13708 | Pense-bête de Rubise | Ressource diverse | 14002 | 120 | boots | Bottes d'Inferno |
| 6 | 13724 | Patte de Tofu Dodu | Patte | 6535 | 121 | shovel | Pelle Hikule |
| 6 | 20944 | Enrobage de Chocoskargo | Peau | 20982 | 126 | boots | Bottes Croquantes |
| 6 | 8345 | Corne de Dragoss Protéiforme | Os | 7171 | 127 | wand | Baguette Ourderie |
| 7 | 16208 | Fragment de Rubis Fertile | Pierre précieuse | 16169 | 140 | staff | Vieille Branche du Chêne Mou |
| 7 | 11247 | Oreille percée du Fricochère | Oreille | 12092 | 142 | boots | Bottes de Frigostine |
| 7 | 13723 | Œuf de Tofubine | Œuf | 14519 | 151 | hammer | Marteau du Juge Lou |
| 7 | 8804 | Braguette du Maître Zoth | Vêtement | 8848 | 156 | hat | Coiffe du Maître Zoth |
| 8 | 7033 | Dolomite | Minerai | 23590 | 160 | sword | Musamune |
| 8 | 13172 | Casque Mâchouillé | Vêtement | 13135 | 160 | hat | Casque de Metag Robill |
| 8 | 15046 | Canine de Félygiène | Os | 15062 | 160 | hat | Coiffe de l'Orfélin |
| 8 | 6904 | Protection usagée du Bworker | Ressource diverse | 8695 | 177 | sword | L'Épée Nice |
| 8 | 15455 | Venin d'Éperfide | Liquide | 15500 | 177 | boots | Bottes Nécrotiques |
| 8 | 14977 | Bitte d'amarrage | Ressource diverse | 11850 | 178 | belt | Slip Iholo |
| 9 | 397 | Huile de Koode | Huile | 29110 | 180 | shield | Ménologium |
| 9 | 29117 | Morceau du Ménologium | Ressource diverse | 29110 | 180 | shield | Ménologium |
| 9 | 29379 | Métronome du Début-Temps | Ressource diverse | 29110 | 180 | shield | Ménologium |
| 9 | 15452 | Patte de Scoliopode | Patte | 15501 | 182 | cloak | Cape Nécrotique |
| 9 | 15454 | Pince de Lucrane | Os | 15501 | 182 | cloak | Cape Nécrotique |
| 9 | 11795 | Racine de synthèse | Racine | 11794 | 186 | amulet | Racine Hueuse |
| 10 | 11102 | Perce-Neige | Fleur | 15660 | 200 | dagger | Couteaux sacrés |
| 10 | 11107 | Bois de Tremble | Bois | 15660 | 200 | dagger | Couteaux sacrés |
| 10 | 11110 | Obsidienne | Minerai | 15660 | 200 | dagger | Couteaux sacrés |
| 10 | 14936 | Insigne des Justiciers | Ressource diverse | 14937 | 200 | cloak | Cape des Justiciers |
| 10 | 15661 | Ossements sacrés de Givrefoux | Os | 15660 | 200 | dagger | Couteaux sacrés |
| 10 | 18318 | Soie chatoyante | Étoffe | 958 | 200 | cloak | Dofusteuse |

#### 4c. Do the items that consume dead-end resources still share?

A dead-end resource has one consumer, but that consumer's **other** resources can still overlap with other items. These are the 154 items that consume at least one dead-end resource.

- **Items consuming >= 1 dead-end resource:** 154
- **Items with zero shared resources overall (isolated):** 3 (of which boss items: 1)
- **Boss items that still share >= 1 resource:** 153 of 154 (99.4%)
- **Boss-item pairs sharing resources with each other:** 1390

**Resources that most often drive boss-item overlap:**

| Resource ID | Name | Boss-item pairs |
|-------------|------|-----------------|
| 32079 | Reflet onirique | 325 |
| 24144 | Substrat Astral | 276 |
| 12740 | Galet brasillant | 253 |
| 14921 | Étoffe Mystérieuse | 136 |
| 12728 | Ardonite | 105 |
| 19975 | Corne de volkorne | 91 |
| 33515 | Neurone de dragodinde | 78 |
| 26870 | Fragment d'anomalie | 55 |
| 14635 | Pépite | 55 |
| 16212 | Substrat de Fourré | 45 |

#### 4d. Constraint-resource hypothesis (user, 2026-10-09) - NOT testable from this snapshot

> **User hypothesis (recorded in the project wiki as `cost-popularity-taux-hypothesis`):** resources like the ones above are **high-constraint** - scarce / high-demand / expensive. Items built from them are more expensive than other items at the same level, so more players choose and break them, so their **taux** (break rate) is weak.

This snapshot contains **no price and no taux data**, so the hypothesis cannot be confirmed or refuted here. What the snapshot *does* show is the necessary precondition - these resources are shared across many recipes:

| Resource ID | Name | % of recipes | Boss-item pairs |
|-------------|------|--------------|-----------------|
| 32079 | Reflet onirique | 0.9% | 325 |
| 24144 | Substrat Astral | 2.3% | 276 |
| 12740 | Galet brasillant | 5.4% | 253 |
| 14921 | Étoffe Mystérieuse | 6.2% | 136 |
| 12728 | Ardonite | 5.2% | 105 |
| 19975 | Corne de volkorne | 3.8% | 91 |
| 33515 | Neurone de dragodinde | 3.9% | 78 |
| 26870 | Fragment d'anomalie | 7.4% | 55 |
| 14635 | Pépite | 5.2% | 55 |
| 16212 | Substrat de Fourré | 2.7% | 45 |

**Cross-check plan (resolution path):** join empirical break outcomes (`break_log`, via the capture pipeline) with recipe cost (`c_i`, via the price feed), grouped by item level and stat density. Prediction: items dominated by high-cost / high-demand resources show lower empirical taux than same-level, same-density items built from cheap/common resources.

---

## STRUCTURE

### 5. Items per type and per level band

**Items per type:**

| Type (FR) | Slot (EN) | Items |
|-----------|-----------|-------|
| Anneau | ring | 367 |
| Bottes | boots | 362 |
| Chapeau | hat | 362 |
| Ceinture | belt | 354 |
| Amulette | amulet | 324 |
| Cape | cloak | 298 |
| Bouclier | shield | 111 |
| Épée | sword | 100 |
| Marteau | hammer | 95 |
| Bâton | staff | 89 |
| Baguette | wand | 77 |
| Dague | dagger | 76 |
| Arc | bow | 75 |
| Hache | axe | 75 |
| Pelle | shovel | 59 |
| Lance | lance | 20 |
| Faux | scythe | 14 |

**Items per 20-level band:**

| Band | Level range | Items |
|------|-------------|-------|
| 0 | 0-19 | 264 |
| 1 | 20-39 | 295 |
| 2 | 40-59 | 510 |
| 3 | 60-79 | 186 |
| 4 | 80-99 | 211 |
| 5 | 100-119 | 191 |
| 6 | 120-139 | 206 |
| 7 | 140-159 | 162 |
| 8 | 160-179 | 125 |
| 9 | 180-199 | 278 |
| 10 | 200-219 | 430 |

### 6. Panoplie sizes

- **Items with set_id = None:** 1068 (37.4%)
- **Distinct sets:** 516
- **Items in a set:** 1790

| Set size | min | median | p90 | max | n |
|----------|-----|--------|-----|-----|---|
| Items per set | 1 | 3 | 5 | 8 | 516 |

### 7. Type x level-band cells with too few items to group (< 2 items)

| Type (FR) | Slot (EN) | Band | Level range | Items |
|-----------|-----------|------|-------------|-------|
| Faux | scythe | 0 | 0-19 | 1 |
| Faux | scythe | 1 | 20-39 | 1 |
| Faux | scythe | 2 | 40-59 | 1 |
| Faux | scythe | 3 | 60-79 | 0 |
| Faux | scythe | 4 | 80-99 | 0 |
| Faux | scythe | 5 | 100-119 | 0 |
| Faux | scythe | 6 | 120-139 | 1 |
| Faux | scythe | 7 | 140-159 | 1 |
| Faux | scythe | 8 | 160-179 | 0 |
| Lance | lance | 0 | 0-19 | 0 |
| Lance | lance | 1 | 20-39 | 1 |
| Lance | lance | 6 | 120-139 | 0 |
| Lance | lance | 8 | 160-179 | 0 |
| Lance | lance | 9 | 180-199 | 1 |

---

## SIMILARITY

### 8. Pairwise Jaccard similarity distribution

- **Total possible pairs:** 4082653
- **Candidate pairs (share >= 1 resource):** 246081
- **Pairs with Jaccard = 0 (no shared resources):** 3836572

_Total pairs (4082653) < 5M, so no sampling was needed; all candidate pairs were evaluated._

| Jaccard | min | median | p90 | max | n |
|---------|-----|--------|-----|-----|---|
| All candidate pairs | 0.07 | 0.07 | 0.18 | 1 | 246081 |

| Threshold | Pairs exceeding | % of all pairs | % of candidate pairs |
|-----------|-----------------|----------------|----------------------|
| 0.1 | 88673 | 2.17% | 36.03% |
| 0.2 | 24386 | 0.60% | 9.91% |
| 0.3 | 9650 | 0.24% | 3.92% |

**graph_min_shared_ratio = 0.3** keeps 9650 edges (0.24% of all pairs, 3.92% of candidate pairs).

### 9. Connected components at several thresholds

| Threshold | Components | Largest | Nodes in comps | Size min | Size median | Size p90 | Size max |
|-----------|------------|---------|----------------|----------|-------------|----------|----------|
| 0.1 | 5 | 2835 | 2854 | 3 | 5 | 7 | 2835 |
| 0.2 | 18 | 2730 | 2796 | 2 | 4 | 7 | 2730 |
| 0.3 | 193 | 869 | 2450 | 2 | 3 | 12 | 869 |
| 0.4 | 312 | 147 | 1462 | 2 | 2 | 9 | 147 |
| 0.5 | 253 | 100 | 967 | 2 | 2 | 5 | 100 |

### 10. Cross-type sharing

**By pair count:**

- **Same-type pairs:** 25381 (10.3%)
- **Cross-type pairs:** 220700 (89.7%)

**By shared-resource instances (sum of |A intersect B|):**

- **Same-type shared instances:** 33900 (11.4%)
- **Cross-type shared instances:** 263992 (88.6%)

### 11. Cross-level sharing

- **Same 20-level band pairs:** 116973 (47.5%)
- **Cross-band pairs:** 129108 (52.5%)
- **Pairs with level diff <= 20:** 190932 (77.6%)

| Level diff | min | median | p90 | max | n |
|------------|-----|--------|-----|-----|---|
| |level_a - level_b| | 0 | 6 | 56 | 180 | 246081 |

---

## FILTERS

### 12. Density filter (ratio = 3.0) removal

- **Total items removed:** 1689 (59.1%)
- **Items retained:** 1169 (40.9%)

**Removed by type:**

| Type (FR) | Slot (EN) | Removed | Retained |
|-----------|-----------|---------|----------|
| Anneau | ring | 352 | 15 |
| Bottes | boots | 250 | 112 |
| Chapeau | hat | 216 | 146 |
| Ceinture | belt | 245 | 109 |
| Amulette | amulet | 220 | 104 |
| Cape | cloak | 190 | 108 |
| Bouclier | shield | 99 | 12 |
| Épée | sword | 9 | 91 |
| Marteau | hammer | 11 | 84 |
| Bâton | staff | 22 | 67 |
| Baguette | wand | 18 | 59 |
| Dague | dagger | 28 | 48 |
| Arc | bow | 15 | 60 |
| Hache | axe | 4 | 71 |
| Pelle | shovel | 8 | 51 |
| Lance | lance | 0 | 20 |
| Faux | scythe | 2 | 12 |

**Removed by 20-level band:**

| Band | Level range | Removed |
|------|-------------|---------|
| 0 | 0-19 | 168 |
| 1 | 20-39 | 207 |
| 2 | 40-59 | 415 |
| 3 | 60-79 | 121 |
| 4 | 80-99 | 139 |
| 5 | 100-119 | 123 |
| 6 | 120-139 | 122 |
| 7 | 140-159 | 83 |
| 8 | 160-179 | 64 |
| 9 | 180-199 | 136 |
| 10 | 200-219 | 111 |

---

## SCOPE COMPARISON: resources-only vs all recipe entries

The loader (`EquipmentLoader._parse_recipe`) keeps only recipe entries with `item_subtype == 'resources'`. Some recipes also list quest **equipment** and **consumables**. This section compares the two treatments. All other sections use the resources-only view (the pipeline's actual behaviour).

**Raw recipe entry counts by subtype:**

| item_subtype | Entries |
|--------------|---------|
| resources | 16368 |
| consumables | 43 |
| equipment | 27 |

**Items whose recipe contains a non-resource entry:** 44 of 2858 (1.5%)

| Metric | resources-only | all entries |
|--------|----------------|-------------|
| Distinct recipe entries (median) | 6 | 6 |
| Distinct recipe entries (p90) | 8 | 8 |
| Distinct recipe entries (max) | 8 | 8 |
| Candidate pairs (share >= 1) | 246081 | 246081 |
| Jaccard median (candidates) | 0.07 | 0.07 |
| Jaccard p90 (candidates) | 0.18 | 0.18 |
| Pairs >= 0.1 | 88673 | 88466 |
| Pairs >= 0.2 | 24386 | 24400 |
| Pairs >= 0.3 | 9650 | 9666 |
| Components @ 0.3 | 193 | 192 |
| Largest component @ 0.3 | 869 | 869 |

---

## INFERENCE (interpretation, not raw data)

> The following are interpretations of the numbers above. They are not themselves computed statistics.

1. **No resource is ubiquitous in this snapshot.** The top resource appears in only 7.4% of recipes. Neither 15263 nor 14635 comes close to the 20% threshold: 15263 appears in 0 recipes (absent from the snapshot entirely), and 14635 appears in 148 (5.2%). The `excluded_resource_ids = {15263, 14635}` default does not match the current data.
2. **Resource sharing is sparse.** Only 6.0% of all pairs share even one resource. The median Jaccard among candidate pairs is 0.07, and the p90 is 0.18.
3. **graph_min_shared_ratio = 0.3 is an aggressive threshold.** It keeps only 9650 edges (3.9% of candidate pairs). At 0.3 the graph fragments into 193 components, the largest containing 869 of 2858 items (30.4%).
4. **Sharing is predominantly cross-type.** 89.7% of candidate pairs are cross-type, and 88.6% of shared-resource instances are cross-type. This is expected: different slots use different base materials.
5. **Sharing is not confined to a narrow level range.** 52.5% of pairs span different 20-level bands, and the median level difference is 6. However, 77.6% of pairs are within 20 levels of each other.
6. **The density filter (ratio 3.0) removes 59.1% of items.** It removes the majority of accessories (Anneau, Bottes, Ceinture, Amulette, Chapeau, Cape) but only a small fraction of weapons. This is because accessories have low stat_weight relative to their level.
7. **173 resources (10.5% of distinct resources) are dead-ends** used by exactly one item. But this does NOT make their consuming items worthless: 153 of 154 such items still share other resources with the rest of the pool, and they form 1390 boss-item pairs. Excluding these items would remove real recipe overlap.
8. **Including non-resource recipe entries barely changes the similarity structure.** 44 of 2858 items (1.5%) list quest equipment or consumables. Adding them changes the edge counts by at most a few hundred (9650 -> 9666 at threshold 0.3) and the component count by 1 (193 -> 192); the largest component is unchanged (869). The resource-only filter is therefore not materially distorting the graph.
9. **The high-constraint-resource / taux link is a user hypothesis, not shown here.** The snapshot has no price or taux data. It confirms only that the candidate resources are shared widely (necessary, not sufficient). Testing it needs `break_log` outcomes joined to recipe cost - see `wiki/concepts/cost-popularity-taux-hypothesis.md`.

