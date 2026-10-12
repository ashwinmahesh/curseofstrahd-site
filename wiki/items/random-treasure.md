# Random Treasure

> From the Curse of Strahd game wiki (it covers the whole game, spoilers included): https://curseofstrahd.app/wiki/items/random-treasure.html. Unofficial Fan Content permitted under the Fan Content Policy, not approved or endorsed by Wizards of the Coast.

What you find besides the fixed treasure the story puts in place: random magic items and potions in containers, and the spoils of fights. Each place rolls its share the first time you come, from your playthrough's seed, and keeps it.

## In a place's containers

- **Magic items:** none 10% of the time, one 40%, two 50%; a place with 3 or more containers gets one more 50% of the time.
- **Potions:** none 25% of the time, one 50%, two 25%. Each is a healing potion for your tier 60% of the time, else any potion of the place's rarity.

## Fights

Story fights you win leave coins by each foe's Challenge Rating and one find (a healing potion, a gem or a spell scroll). Beasts, plants, oozes and mindless creatures carry no coins. Strahd's visits, road fights and arrests leave only their own spoils.

## Rarity by party level

| Party level | Uncommon | Rare | Very rare | Legendary |
|---|---|---|---|---|
| 1–2 | 100% |  |  |  |
| 3–4 | 95% | 5% |  |  |
| 5–7 | 75% | 25% |  |  |
| 8–10 | 55% | 38% | 7% |  |
| 11–20 | 25% | 45% | 25% | 5% |

## Party level by region

Each region's containers roll for this party level (a place can set its own).

| Region | Level |
|---|---|
| [Into the Mists](https://curseofstrahd.app/wiki/regions/into-the-mists.md) | 1 |
| [Death House](https://curseofstrahd.app/wiki/regions/death-house.md) | 2 |
| [The Village of Barovia](https://curseofstrahd.app/wiki/regions/the-village-of-barovia.md) | 3 |
| [The Old Svalich Road](https://curseofstrahd.app/wiki/regions/the-old-svalich-road.md) | 4 |
| [Vallaki](https://curseofstrahd.app/wiki/regions/vallaki.md) | 5 |
| [Old Bonegrinder](https://curseofstrahd.app/wiki/regions/old-bonegrinder.md) | 6 |
| [The Wizard of Wines](https://curseofstrahd.app/wiki/regions/the-wizard-of-wines.md) | 6 |
| [Yester Hill](https://curseofstrahd.app/wiki/regions/yester-hill.md) | 7 |
| [Krezk](https://curseofstrahd.app/wiki/regions/krezk.md) | 7 |
| [The Abbey of St. Markovia](https://curseofstrahd.app/wiki/regions/the-abbey-of-st-markovia.md) | 7 |
| [Argynvostholt](https://curseofstrahd.app/wiki/regions/argynvostholt.md) | 8 |
| [Van Richten's Tower](https://curseofstrahd.app/wiki/regions/van-richtens-tower.md) | 8 |
| [The Werewolf Den](https://curseofstrahd.app/wiki/regions/the-werewolf-den.md) | 8 |
| [Lake Zarovich](https://curseofstrahd.app/wiki/regions/lake-zarovich.md) | 8 |
| [Berez](https://curseofstrahd.app/wiki/regions/berez.md) | 9 |
| [Mount Baratok](https://curseofstrahd.app/wiki/regions/mount-baratok.md) | 9 |
| [The Tsolenka Pass](https://curseofstrahd.app/wiki/regions/the-tsolenka-pass.md) | 9 |
| [Mount Ghakis](https://curseofstrahd.app/wiki/regions/mount-ghakis.md) | 10 |
| [The Amber Temple](https://curseofstrahd.app/wiki/regions/the-amber-temple.md) | 10 |
| [Castle Ravenloft](https://curseofstrahd.app/wiki/regions/castle-ravenloft.md) | 10 |

> [!abstract]- How the rolls work
> Random magic item placement (story/treasure.gd, ADR 0012). The party's level in each region (from the region design docs) decides the rarities, following the 2024 DMG's treasure guidance: tier 1 (levels 1-4) mostly common and uncommon items, tier 2 (levels 5-10) mostly uncommon and rare with the odd very rare one. A location can name its own level with "treasure_level". No common items (owner, 2026-10-08: early commons become uncommon, later ones rarer): the DMG's common share goes to uncommon.

> A roll picks a rarity, then a theme (arcana, armaments, implements, relics) evenly, then an item in it by weight. A theme whose pool at that rarity weighs less than theme_full_weight gets a share in proportion, so a theme with one or two items doesn't hand them out in a quarter of all rolls (owner, 2026-10-12).
