# Random Treasure

> From the Curse of Strahd game wiki (it covers the whole game, spoilers included): https://curseofstrahd.app/wiki/items/random-treasure.html. Unofficial Fan Content permitted under the Fan Content Policy, not approved or endorsed by Wizards of the Coast.

Random magic item placement (story/treasure.gd, ADR 0012). The party's level in each region (from the region design docs) decides the rarities, following the 2024 DMG's treasure guidance: tier 1 (levels 1-4) mostly common and uncommon items, tier 2 (levels 5-10) mostly uncommon and rare with the odd very rare one. A location can name its own level with "treasure_level". No common items (owner, 2026-10-08: early commons become uncommon, later ones rarer): the DMG's common share goes to uncommon.

## Party level by region

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

## Rarity By Level

```json
[
 {
  "max_level": 2,
  "weights": {
   "uncommon": 100
  }
 },
 {
  "max_level": 4,
  "weights": {
   "uncommon": 95,
   "rare": 5
  }
 },
 {
  "max_level": 7,
  "weights": {
   "uncommon": 75,
   "rare": 25
  }
 },
 {
  "max_level": 10,
  "weights": {
   "uncommon": 55,
   "rare": 38,
   "very_rare": 7
  }
 },
 {
  "max_level": 20,
  "weights": {
   "uncommon": 25,
   "rare": 45,
   "very_rare": 25,
   "legendary": 5
  }
 }
]
```

## Items Per Location

```json
{
 "none": 20,
 "one": 50,
 "two": 30,
 "extra_if_containers": 4,
 "extra_chance": 30
}
```

## Group Weights

```json
{
 "spell_scroll": 4,
 "potion": 3
}
```
