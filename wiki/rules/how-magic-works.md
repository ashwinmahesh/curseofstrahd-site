# How Magic Works

> From the Curse of Strahd game wiki (it covers the whole game, spoilers included): https://curseofstrahd.app/wiki/rules/how-magic-works.html. Unofficial Fan Content permitted under the Fan Content Policy, not approved or endorsed by Wizards of the Coast.

Spells follow the 2024 Player's Handbook. Every spell's full text is on its level's page ([Spells by Class](https://curseofstrahd.app/wiki/spells/spells-by-class.md) lists who can learn what). This page covers how casting works in this game, and where it plays differently from the book ([House Rules](https://curseofstrahd.app/wiki/rules/house-rules.md) has the full list).

#### Spell slots, preparing and resting

- Spell slots come back on a Long Rest (a Warlock's Pact Magic slots on a Short Rest too). Rest with **R**.
- Prepared spells can be changed after a Long Rest, on the character sheet's Spells tab (**C**), or from the camp panel when you make camp in the wild ([Resting and Saving](https://curseofstrahd.app/wiki/rules/resting-and-saving.md)). Clerics, Druids and Wizards can swap as many as they like; Paladins and Rangers swap one; a Wizard can also swap one cantrip.
- Wizards prepare from their spellbook: six level 1 spells to start and two more each level. A spellbook or scroll you find can be copied into it from the inventory: 2 hours and 50 gp per spell level, for a level you can prepare.
- Spells that last 8 hours (Mage Armor, Aid, Darkvision, Death Ward, Alarm, Leomund's Tiny Hut and the rest) last until the next Long Rest instead of eight hours on the clock.
- Mage Armor can be set to cast itself as each Long Rest ends, so nobody has to remember it in the morning.

#### Casting in a fight

- Spells sit on the hotbar: number keys **1** to **0**, **Z** and **X** to change tab. Pick a spell, then click a target or a square; **T** cycles targets and **Enter** confirms.
- To cast with a higher slot (upcasting), raise or lower the slot level with **[** and **]** before you cast.
- Aiming an area spell draws its shape on the ground and lists every creature it would catch ([below](https://curseofstrahd.app/wiki/rules/how-magic-works.md#aiming-areas-and-lines)).
- **Hex and Hunter's Mark** move when their target drops: a Move action appears on the hotbar once the marked creature is down, and Hex's ability curse moves with it. Hunter's Mark needs a new quarry you can see.
- **Teleporting** (Misty Step and the like) frees you from webs, nets, entangling plants and grapples.
- **Sculpt Spells:** an Evoker picks which creatures a sculpted spell spares, and can spare themselves too (a house rule).
- Concentration works as in the book: one spell at a time, and taking damage calls for a Constitution save (DC 10 or half the damage, whichever is higher, up to 30).
- Reactions and choices made mid-roll (Shield, Counterspell, Heroic Inspiration, a Bardic Inspiration die and the like) follow each hero's rule on the class tab of the character sheet: Ask, Automatic or Never ([below](https://curseofstrahd.app/wiki/rules/how-magic-works.md#reactions)).
- **Divine Smite** uses the older rule the game's owner prefers: it isn't a spell and costs no Bonus Action, so a Paladin can smite every melee hit while slots last. By default the game asks after each hit. Arm it on the Spells tab to smite every hit that turn, or set it to Automatic or Off on the class tab.

#### Aiming areas and lines

Aiming an area spell draws its edge on the ground as a pale gold line, and paints no squares: a circle for a radius ([Fireball](https://curseofstrahd.app/wiki/spells/level-3-spells.md#fireball)), a triangle for a cone ([Burning Hands](https://curseofstrahd.app/wiki/spells/level-1-spells.md#burning-hands)) and a square for a cube ([Thunderwave](https://curseofstrahd.app/wiki/spells/level-1-spells.md#thunderwave), [Hypnotic Pattern](https://curseofstrahd.app/wiki/spells/level-3-spells.md#hypnotic-pattern)). The same line flashes when the spell goes off. A panel beside it lists every creature the spell would catch, with each one's chance to save. Walls still outline their squares.

![area preview fireball](https://curseofstrahd.app/wiki/img/combat/area-preview-fireball.webp)

![area preview cone cube](https://curseofstrahd.app/wiki/img/combat/area-preview-cone-cube.webp)

Emanations and auras are round too. [Spirit Guardians](https://curseofstrahd.app/wiki/spells/level-3-spells.md#spirit-guardians), a [Paladin's](https://curseofstrahd.app/wiki/characters/classes/paladin.md) Aura of Protection and a monster's aura reach everything within their size measured straight from their source, so the circle on the floor shows exactly who's inside. A 5-ft aura covers the same squares as before; from 10 ft up, the far diagonal corners fall outside. In a fight a Paladin's aura shows as a patch on the floor around them, with no glow round the Paladin.

**Line spells** ([Lightning Bolt](https://curseofstrahd.app/wiki/spells/level-3-spells.md#lightning-bolt), Gust of Wind, Sunbeam, a Dragonborn's breath line) aim at any angle. Point the mouse, or the left stick on a controller, and the line runs straight out from the middle of the caster's space. A square is caught when at least half of it lies inside the line, the DMG's grid rule. Within 2° of a row, column or diagonal the line snaps to lie exactly along it. Cones and cubes still point along the nearest of the eight grid directions. Monsters' lines work the same way ([House Rules](https://curseofstrahd.app/wiki/rules/house-rules.md#lines-on-the-grid)).

![line aim lightning bolt](https://curseofstrahd.app/wiki/img/combat/line-aim-lightning-bolt.webp)

#### Reactions

A hero set to Ask who has more than one Reaction that fits the moment gets one prompt listing them all. Pick one and choose **Use Reaction**, or **Skip** to keep the Reaction for later. During an attack the prompt also lists what could come later in it, such as **Sentinel, if the attack hits**: picking that keeps the Reaction for the Opportunity Attack after a hit, and if the attack misses the hero still has it. So a Paladin with the Protection fighting style and the Sentinel feat ([Feats](https://curseofstrahd.app/wiki/characters/feats.md)) is asked once, not once for each. On a controller, **A** on an option picks it.

![reaction prompt](https://curseofstrahd.app/wiki/img/combat/reaction-prompt.webp)

#### Casting while exploring

- Healing and other helpful spells can be cast outside a fight from the character sheet, on your heroes and on guests travelling with you. Slots, free castings, Concentration and lasting effects behave exactly as they do in a fight. That includes bringing back the dead: Revivify, Raise Dead, Reincarnate, Resurrection and True Resurrection, plus Gentle Repose to keep a body fresh.
- Spells that harm, push or summon wait for a fight, except the companions that stay with their caster: Find Familiar and Find Steed. Light, Dancing Lights, Continual Flame and Daylight are worth casting while exploring too, since their light lasts.
- Many utility spells do something real while exploring:
  - **Scouting:** Augury, Divination, Commune, Clairvoyance and Arcane Eye tell you about the place you're in; Legend Lore and Scrying fill in the journal's bestiary; Find the Path lets you skip encounters on the road.
  - **Getting through:** Stone Shape and Passwall open doors, and Unseen Servant springs traps for you.
  - **Carrying and brewing:** Tenser's Floating Disk adds carrying capacity, Secret Chest opens your stash from anywhere, and Tasha's Bubbling Cauldron brews potions.
  - **Helping a check:** seven cantrips and twelve spells give Advantage on the skills they suit, and Zone of Amicability makes 10 the lowest roll on influence checks.
  - **Raising help:** Animate Dead and Create Undead (at night only) can be cast while exploring, and the dead join the day's fights. Prayer of Healing, Regenerate and Foresight work outside fights too.
  - **Warding a rest:** Hallow, Forbiddance, Private Sanctum and Nondetection make a rest safe, and Tiny Hut and Guards and Wards let you Long Rest in a building that still has enemies in it ([Resting and Saving](https://curseofstrahd.app/wiki/rules/resting-and-saving.md)).
- Some conversations offer a spell as an option when a hero knows it. **Speak with Animals** is cast there as a Ritual (ten more minutes, no slot) and lets a beast tell you what it saw. **Speak with Dead** costs a slot of 3rd level or higher and works once on each corpse. **Speak with Plants** gets a garden or a row of vines to tell you what passed it in the last day ([Talking Creatures](https://curseofstrahd.app/wiki/world/talking-creatures.md)).
- Before a skill check on something in the world, a hero proficient in the skill Helps (Advantage), and anyone who knows Guidance casts it on whoever tries.

#### Components, focuses and scrolls

- A material component with no listed cost, and a spellcasting focus, are assumed to be carried. A hand is always free for them and for gestures, whatever the caster is holding.
- A component with a gold cost has to be in the inventory, and it's used up if the spell says so (a diamond for Revivify, for example). Father Lucian in Vallaki sells diamonds and diamond dust ([Merchants and Services](https://curseofstrahd.app/wiki/items/merchants.md)).
- **Spell scrolls** are cast from the inventory (right-click, Cast) if the spell is on the reader's class list. A spell above the reader's own level needs a spellcasting check (DC 10 + the spell's level), and the scroll is used up either way.
- Some magic items pass for something else until someone casts **Identify** on them from the item card.
