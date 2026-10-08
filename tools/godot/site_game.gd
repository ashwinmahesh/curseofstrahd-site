extends Node
## The showcase site's interface shots (~/Documents/CurseOfStrahdSite; not part of the game): the title, the party
## roster, a conversation's skill check and its d20, a fight's odds, an area spell's template, staged spells and blows
## for the trailer, a boss's entrance, sneaking, the sheet, the inventory and the travel map. The six companions are
## the party, the Modern look on the High preset. Stills are PNGs; clips (SITE_MODE=clips, run with --fixed-fps 30
## and --motion) are numbered JPEGs, one per frame.
##   tools/godot --path . [--fixed-fps 30] res://tools/capture/capture.tscn -- --scene=res://tools/capture/site_game.tscn
##     --out=<dir>/g --frames=10 --size=1920x1080 [--motion]
## Environment: SITE_MODE=stills|clips, SITE_ONLY=combat_odds,dialogue_check (default: every shot of the mode).
## What the fights and conversations change is shown only; settings, saves, achievements and What's new use files of
## this run's own (removed at the end), never the player's.

const GAME := "res://scenes/game.tscn"
const MENU := "res://scenes/main_menu.tscn"
const FIGHTERS: Array[String] = ["godrick_pendlebrook", "liriel_dawnsong", "ratatoille", "kip_smudgewick"]
const TALKERS: Array[String] = ["wren_featherfoot", "godrick_pendlebrook", "thistle", "liriel_dawnsong"]
const STILLS: Array[String] = ["title", "party_roster", "dialogue_check", "dialogue_d20", "combat_odds", "combat_area",
	"combat_fireball", "combat_battlefield", "combat_boss", "stealth_sight", "character_sheet", "inventory",
	"travel_map"]
const CLIPS: Array[String] = ["title", "dialogue", "fight", "boss"]
## The village fight: who stands where, as offsets from the party's leader along the camera's right and away from it.
const FOES := [["strahd_zombie", 4, 1], ["zombie", 5, -1], ["zombie", 6, 1], ["ghoul", 4, -2], ["strahd_zombie", 7, 0]]

var tool: Node
var dir := ""
var clips := false
var root: Node = null
var menu: Node = null
var cv: CombatView = null
var _own := ""
var _weather: Dictionary = {}


func _ready() -> void:
	_own = "user://capture_site_%d" % OS.get_process_id()
	GameSettings.path = _own + "_settings.cfg"
	WhatsNew.seen_path = _own + "_whats_new.cfg"
	# Nothing is new to this run's title screen.
	var cfg := ConfigFile.new()
	cfg.set_value("whats_new", "seen_at", int(WhatsNew.build().get("committed_at", 0)) + 3600)
	cfg.save(WhatsNew.seen_path)
	InputActions.ensure()
	Look.set_style("modern", false)
	Graphics.set_preset("high", false)
	_weather = Weather.data().duplicate(true)
	Dice.reseed(11)


func _exit_tree() -> void:
	for f: String in [GameSettings.path, WhatsNew.seen_path]:
		if FileAccess.file_exists(f):
			DirAccess.remove_absolute(f)


func capture_shots(t: Node, out: String) -> void:
	tool = t
	dir = out.get_base_dir()
	clips = OS.get_environment("SITE_MODE") == "clips"
	var only := OS.get_environment("SITE_ONLY").split(",", false)
	for id: String in (CLIPS if clips else STILLS):
		if not only.is_empty() and not id in only:
			continue
		print("site_game: ", id)
		await call(("_clip_" if clips else "_still_") + id)
	_clear()


# --- Set-up ---------------------------------------------------------------------------------------------------------

func _wait(n: int) -> void:
	await tool.call("wait_frames", n)


func _shot(name: String) -> void:
	tool.call("_shot", "%s/%s.png" % [dir, name])


## Keeps every frame for `seconds` (with --fixed-fps 30, each frame is a thirtieth of a second), numbered on from
## `first` in the clip's folder. Returns the next frame's number.
func _record(clip: String, seconds: float, first: int = 0) -> int:
	var to := "%s/%s" % [dir, clip]
	DirAccess.make_dir_recursive_absolute(to)
	var n := int(seconds * 30.0)
	for i in n:
		await get_tree().process_frame
		get_viewport().get_texture().get_image().save_jpg("%s/f%04d.jpg" % [to, first + i], 0.93)
	print("capture: %s (%d frames)" % [to, first + n])
	return first + n


func _clear() -> void:
	get_tree().paused = false
	for n: Node in [root, menu]:
		if n != null:
			n.queue_free()
	root = null
	menu = null
	cv = null
	await _wait(3)


## The story game at `loc` at `hour`, the party (levelled to `level`) at its spawn or at `at`, in this weather.
func _game(loc: String, hour: int, party: Array[String], level: int, weather: String = "", at: Array = []) -> void:
	await _clear()
	var d := _weather.duplicate(true)
	if weather != "":
		for c: String in d["climates"]:
			d["climates"][c] = {weather: 1}
	Weather.use(d)
	GameState.reset()
	var st := GameState.story
	for pid: String in party:
		var ch := Pregens.build(pid, level)
		ch.finish_long_rest()
		st.party.append(ch)
	st.gold = 240.0
	st.minute_of_day = hour * 60
	st.location = loc
	st.visited[loc] = true
	if not at.is_empty():
		for b: Vector2i in [Vector2i.ZERO, Vector2i(1, 0), Vector2i(0, 1), Vector2i(1, 1)]:
			st.positions.append(Vector2i(int(at[0]), int(at[1])) + b)
	root = (load(GAME) as PackedScene).instantiate()
	add_child(root)
	await _wait(40)
	# A place's first-visit cutscene (the village by night) would sit over everything with the game paused.
	if root.get("screen") is CutscenePlayer:
		root.call("close_screen")
	get_tree().paused = false
	_hud().close_narration()
	_view().input_locked = true
	# Clips play the interface's motion, so a new region's loading card holds for its 2.4 s and fades: wait it out.
	await _wait(110 if clips else 10)


func _view() -> LocationView:
	return root.get("view") as LocationView


func _hud() -> ExploreHud:
	return root.get("hud") as ExploreHud


## The title screen, its What's new and its development entries (the Phase 2 arena) left out.
func _title() -> void:
	await _clear()
	menu = (load(MENU) as PackedScene).instantiate()
	add_child(menu)
	await _wait(5)
	for b in menu.find_children("*", "Button", true, false):
		var text := (b as Button).text
		if text.contains("arena") or text.contains("What's new"):
			b.queue_free()
	await _wait(5)


# --- Fights ---------------------------------------------------------------------------------------------------------

## A fight in the village square at night with the party at level 7: the foes stand off to the camera's right of the
## party (FOES, or `foes`). Waits for the party's first turn. Returns false if it couldn't start.
func _fight(foes: Array = FOES, hour: int = 23) -> bool:
	await _game("village_of_barovia", hour, FIGHTERS, 7, "fog")
	var view := _view()
	if OS.get_environment("SITE_DEBUG") != "":
		_shot("debug_1_before_fight")
	var basis := _ground_axes(view.rig)
	var lead := view.leader().cell
	var monsters: Array = []
	var taken := {}
	for f: Variant in foes:
		var spec := f as Array
		var want := lead + basis[0] * int(spec[1]) + basis[1] * int(spec[2])
		var cell := _free_near(view, want, taken)
		taken[cell] = true
		monsters.append({"monster": str(spec[0]), "cell": [cell.x, cell.y]})
	Dice.reseed(11)
	var ok := view.start_custom_encounter({"id": "site_fight", "text": "", "monsters": monsters, "surprise": "enemies"})
	if not ok:
		push_warning("site_game: the fight didn't start")
		return false
	cv = view.combat_view
	cv.input_locked = true
	if OS.get_environment("SITE_DEBUG") != "":
		await _wait(30)
		_shot("debug_2_fight_started")
		print("site_game: mode %d, current %s, screen %s, paused %s" % [cv.mode, cv.e.current().name() if cv.e.current() != null else "-", root.get("screen"), get_tree().paused])
	for i in 3000:
		await get_tree().process_frame
		if cv.mode == CombatView.Mode.PROMPT:
			cv.call("_answer", false, "ask")
		if cv.mode == CombatView.Mode.IDLE and cv.e.current().side == &"party":
			break
	await _wait(30)
	return true


## The camera's right and its forward, on the grid (whole squares).
func _ground_axes(rig: CameraRig) -> Array[Vector2i]:
	var g := rig.ground_basis()
	var right := Vector2i(roundi(g[1].x), roundi(g[1].z))
	var fwd := Vector2i(roundi(g[0].x), roundi(g[0].z))
	if right == Vector2i.ZERO:
		right = Vector2i(1, 0)
	if fwd == Vector2i.ZERO or absi(fwd.x) == absi(right.x):
		fwd = Vector2i(-right.y, right.x)
	return [right, fwd]


## The nearest open, level, unoccupied square to `cell` (not in `taken`).
func _free_near(view: LocationView, cell: Vector2i, taken: Dictionary) -> Vector2i:
	for r in 8:
		for dx in range(-r, r + 1):
			for dy in range(-r, r + 1):
				var c := cell + Vector2i(dx, dy)
				if not view.grid.in_bounds(c) or view.grid.is_solid(c) or taken.has(c):
					continue
				var held := false
				for m in view.members:
					held = held or m.cell == c
				if not held:
					return c
	return cell


func _hero(name_part: String) -> Combatant:
	for c in cv.e.combatants:
		if c.side == &"party" and c.name().contains(name_part):
			return c
	return null


func _foes() -> Array[Combatant]:
	var out: Array[Combatant] = []
	for c in cv.e.combatants:
		if c.side == &"enemy" and c.is_alive():
			out.append(c)
	return out


## Makes `c` the one whose turn it is (shown only): the hotbar, the ring under them and the camera follow.
func _make_current(c: Combatant) -> void:
	var i := cv.e.turn_index
	var at := cv.e.order.find(c)
	if at < 0 or i < 0 or at == i:
		return
	var was := cv.e.order[i]
	cv.e.order[i] = c
	cv.e.order[at] = was
	cv.call("_refresh_all")
	cv.rig.follow = cv.tokens[c.id] as Node3D


## Moves `c` (and its token) to the open square nearest `cell`.
func _put(c: Combatant, cell: Vector2i) -> void:
	var taken := {}
	for o in cv.e.combatants:
		if o != c and o.is_alive():
			taken[o.cell] = true
	var spot := _free_near(_view(), cell, taken)
	c.cell = spot
	var tok := cv.tokens[c.id] as CombatToken
	tok.position = cv.board.cell_center(spot, c.size_cells)


## Points the camera at the middle of `who`, `dist` away.
func _frame(who: Array, dist: float) -> void:
	var mid := Vector3.ZERO
	for c: Variant in who:
		mid += (cv.tokens[(c as Combatant).id] as Node3D).global_position
	mid /= float(maxi(who.size(), 1))
	cv.rig.follow = null
	cv.rig.global_position = mid + Vector3(0, 0.3, 0)
	cv.rig.distance = dist


## The tooltip the game shows while the mouse rests on `foe` with `c`'s turn up: the hit chance, the damage, and
## Advantage with its reasons.
func _hover_attack(c: Combatant, foe: Combatant) -> void:
	cv.hover_token = cv.tokens[foe.id] as CombatToken
	cv.hover_cell = foe.cell
	cv.hover_world = cv.board.cell_center(foe.cell)
	cv.using_pad = true
	cv.call("_update_hover")


## An area spell aimed at `at`, the way the game shows it before the click: its squares, each creature caught with its
## chance to fail the save, and the warning for an ally inside.
func _aim_area(c: Combatant, spell: String, at: Vector2i, slot: int) -> void:
	var a := cv.catalog.find(c, "spell:" + spell)
	if a.is_empty():
		push_warning("site_game: %s can't cast %s" % [c.name(), spell])
		return
	var point := Vector2(at.x + 0.5, at.y + 0.5)
	var dir2 := (point - cv.e.center_of(c)).normalized()
	var pv := cv.catalog.spell_preview(c, a, point, dir2, slot)
	cv.overlay.show_cells("area", pv["cells"] as Array)
	var lines: Array = []
	for w: Dictionary in pv["creatures"]:
		lines.append(str(w["line"]))
	var screen := cv.rig.camera.unproject_position(cv.board.cell_center(at) + Vector3(0, 0.5, 0))
	cv.hud.show_tooltip("%s · slot level %d" % [a["label"], int(pv["slot"])], lines, pv["warnings"] as Array, screen)


## Plays `events` (ids already filled in) as the game plays a turn's results.
func _play(events: Array) -> void:
	cv.e.events.append_array(events)
	cv.call("_play_events")


## The squares of a Fireball centred on `mid` (20 ft radius), on the board.
func _ball(mid: Vector2i) -> Array:
	var cells: Array = []
	for dx in range(-4, 5):
		for dy in range(-4, 5):
			var cell := mid + Vector2i(dx, dy)
			if Vector2(dx, dy).length() <= 4.2 and cv.e.grid.in_bounds(cell):
				cells.append(cell)
	return cells


# --- Stills ---------------------------------------------------------------------------------------------------------

func _still_title() -> void:
	await _title()
	await _wait(60)
	_shot("title")


func _still_party_roster() -> void:
	await _title()
	menu.call("_new_game")
	await _wait(20)
	_shot("party_roster")


## Blinsky's toy shop in Vallaki: his welcome, then the choices, the Performance check among them with who rolls it
## and their chance.
func _talk() -> DialogueUI:
	await _game("vallaki_blinsky_toys", 14, TALKERS, 5)
	root.call("start_dialogue", "vallaki/blinsky:start", "blinsky")
	var d := root.get("dialogue") as DialogueUI
	for i in 12:
		if d == null or not d.options_shown.is_empty():
			break
		d.call("_advance")
		await _wait(4)
	await _wait(20)
	return d


## Picks the Performance check with the dice seeded to `roll_seed`. True if the roll succeeded.
func _laugh(d: DialogueUI, roll_seed: int) -> bool:
	Dice.reseed(roll_seed)
	for i in d.options_shown.size():
		if str((d.options_shown[i] as Dictionary).get("text", "")).contains("laugh"):
			d.call("_choose", i)
			break
	return d.d20 != null and bool(d.d20.beat.get("success", false))


## A seed whose Performance roll succeeds (a laugh out of Blinsky reads better than a groan), tried a few at a time.
var _good_seed := -1


func _seed_that_lands() -> int:
	if _good_seed >= 0:
		return _good_seed
	for roll_seed: int in [7, 3, 5, 9, 13, 21, 34, 55]:
		var d := await _talk()
		if d != null and _laugh(d, roll_seed):
			_good_seed = roll_seed
			return roll_seed
	_good_seed = 7
	return _good_seed


func _still_dialogue_check() -> void:
	await _talk()
	_shot("dialogue_check")


func _still_dialogue_d20() -> void:
	var roll_seed := await _seed_that_lands()
	var d := await _talk()
	if d == null:
		return
	_laugh(d, roll_seed)
	await _wait(30)
	_shot("dialogue_d20")


func _still_combat_odds() -> void:
	if not await _fight():
		return
	var godrick := _hero("Godrick")
	var foe := _foes()[0]
	_make_current(godrick)
	_put(godrick, foe.cell - _ground_axes(cv.rig)[0])
	foe.creature.add_condition(&"prone", "Capture")
	cv.call("_refresh_all")
	_frame([godrick, foe], 9.0)
	await _wait(30)
	_hover_attack(godrick, foe)
	await _wait(10)
	_shot("combat_odds")


func _still_combat_area() -> void:
	if not await _fight():
		return
	var wiz := _hero("Ratatoille")
	_make_current(wiz)
	var foes := _foes()
	var godrick := _hero("Godrick")
	# Godrick has waded in among them: the template warns before the spell catches him.
	_put(godrick, foes[1].cell + Vector2i(1, 0))
	cv.call("_refresh_all")
	_frame([wiz, foes[0], foes[1], foes[2]], 13.0)
	await _wait(30)
	_aim_area(wiz, "fireball", foes[1].cell, 3)
	await _wait(10)
	_shot("combat_area")


func _still_combat_fireball() -> void:
	if not await _fight():
		return
	var wiz := _hero("Ratatoille")
	_make_current(wiz)
	var foes := _foes()
	_frame([wiz, foes[0], foes[1], foes[2]], 13.0)
	await _wait(30)
	var events: Array = [{"type": "spell", "caster": wiz.id, "spell": "fireball", "cells": _ball(foes[1].cell), "targets": []}]
	for f in foes:
		events.append({"type": "damage", "id": f.id, "amount": 28})
	_play(events)
	# Several moments of the blast, to pick from.
	for k: int in [12, 20, 28, 40]:
		await _wait(8)
		_shot("combat_fireball_%d" % k)


func _still_combat_battlefield() -> void:
	if not await _fight():
		return
	# Liriel's Spirit Guardians wheel round her among the dead, and Kip's Hunger of Hadar swallows the far rank.
	var cleric := _hero("Liriel")
	var warlock := _hero("Kip")
	var foes := _foes()
	_make_current(cleric)
	_put(cleric, foes[0].cell - _ground_axes(cv.rig)[0])
	cv.call("_refresh_all")
	var far := foes[foes.size() - 1]
	_frame([cleric, far], 14.0)
	await _wait(20)
	_zone(cleric, "spirit_guardians", cleric.cell)
	_zone(warlock, "hunger_of_hadar", far.cell)
	await _wait(60)
	_shot("combat_battlefield")


## A spell's lingering area on the board, as the rules leave it (shown only).
func _zone(caster: Combatant, spell: String, at: Vector2i) -> void:
	var sd := Compendium.shared().spell_data(spell)
	var lvl := maxi(1, int(sd.get("level", 1)))
	var cells := cv.e.spells.area_for(caster, sd, Vector2(at.x + 0.5, at.y + 0.5), Vector2.ZERO, lvl)
	var zone := FieldObject.new(FieldObject.Kind.ZONE, spell, str(sd.get("name", "")))
	zone.caster_id = caster.id
	zone.cells.assign(cells)
	zone.rules = (sd.get("zone", {}) as Dictionary).duplicate(true)
	zone.rounds_left = 1000
	zone.follows_caster = str((sd.get("area", {}) as Dictionary).get("shape", "")) == "emanation"
	cv.e.spells.zones.objects.append(zone)
	_play([{"type": "spell", "spell": spell, "caster": caster.id, "targets": [], "cells": cells},
		{"type": "object", "id": zone.id, "kind": "zone", "cell": Vector2i.ZERO}])


func _still_combat_boss() -> void:
	BossBar.entrances = false
	var ok := await _fight([["strahd_von_zarovich", 5, 0], ["dire_wolf", 4, -2], ["dire_wolf", 4, 2]])
	BossBar.entrances = true
	if not ok:
		return
	var strahd: Combatant = null
	for f in _foes():
		if f.name().contains("Strahd"):
			strahd = f
	if strahd == null:
		return
	var godrick := _hero("Godrick")
	_make_current(godrick)
	_put(godrick, strahd.cell - _ground_axes(cv.rig)[0])
	strahd.creature.hp = int(strahd.creature.max_hp() * 0.6)
	cv.call("_refresh_all")
	_frame([godrick, strahd], 9.5)
	await _wait(40)
	_shot("combat_boss")


func _still_stealth_sight() -> void:
	await _game("vallaki_blue_water_inn", 20, FIGHTERS, 5)
	var view := _view()
	view.set_sneaking(true)
	for m: Combatant in view.members:
		view.sneak_totals[m.creature] = 6
	root.call("_refresh")
	view.rig.distance = 17.0
	await _wait(40)
	_shot("stealth_sight")
	view.set_sneaking(false)


func _still_character_sheet() -> void:
	await _game("vallaki", 13, FIGHTERS, 7, "overcast")
	root.call("open_screen", "sheet", 2)
	var sheet := root.get("screen") as CharacterSheetScreen
	if sheet != null:
		sheet.show_tab("Spells")
	await _wait(20)
	_shot("character_sheet")
	root.call("close_screen")


func _still_inventory() -> void:
	await _game("vallaki", 13, FIGHTERS, 7, "overcast")
	root.call("open_screen", "inventory", 0)
	await _wait(20)
	_shot("inventory")
	root.call("close_screen")


func _still_travel_map() -> void:
	await _game("vallaki", 16, FIGHTERS, 5, "overcast")
	var st := GameState.story
	for loc: String in ["into_the_mists_road", "village_of_barovia", "svalich_crossroads", "tser_pool", "vallaki",
			"lake_zarovich", "wizard_of_wines", "krezk"]:
		st.visited[loc] = true
	root.call("open_travel", true)
	var map := root.get("screen") as TravelScreen
	if map != null:
		var known := Travel.known(st)
		for k: Variant in known:
			if str((k as Dictionary)["id"]).contains("krezk"):
				map.select(str((k as Dictionary)["id"]))
	await _wait(20)
	_shot("travel_map")


# --- Clips ----------------------------------------------------------------------------------------------------------

## The title's key art with its bats, crows, mist and lightning, the menu hidden.
func _clip_title() -> void:
	await _title()
	for c in menu.get_children():
		if c is VBoxContainer:
			(c as Control).visible = false
	await _wait(30)
	await _record("title", 6.0)


## Blinsky's shop: the options with their odds, and the d20 rolling for the Performance.
func _clip_dialogue() -> void:
	var roll_seed := await _seed_that_lands()
	var d := await _talk()
	if d == null:
		return
	var n := await _record("dialogue", 2.5)
	_laugh(d, roll_seed)
	n = await _record("dialogue", 3.0, n)
	d.call("_advance")
	await _record("dialogue", 2.0, n)


## The fight's big moments, each a clip of its own: the odds on hover, a smite that crits, a Fireball, an Eldritch
## Blast, Spirit Guardians, and the last foe falling in slow motion.
func _clip_fight() -> void:
	if not await _fight():
		return
	var godrick := _hero("Godrick")
	var wiz := _hero("Ratatoille")
	var warlock := _hero("Kip")
	var cleric := _hero("Liriel")
	var axes := _ground_axes(cv.rig)
	var foes := _foes()
	# The odds before the swing.
	_make_current(godrick)
	_put(godrick, foes[0].cell - axes[0])
	cv.call("_refresh_all")
	_frame([godrick, foes[0]], 9.0)
	await _wait(20)
	_hover_attack(godrick, foes[0])
	await _record("fight_odds", 3.5)
	cv.hud.hide_tooltip()
	cv.overlay.clear_all()
	# The smite: a critical hit, the camera pushing in.
	var t := foes[0]
	t.creature.hp = t.creature.max_hp()
	var amount := t.creature.max_hp() + 5
	t.creature.hp = 0
	t.creature.dead = true
	_play([{"type": "attack", "attacker": godrick.id, "target": t.id, "hit": true, "critical": true},
		{"type": "smite", "caster": godrick.id, "spell": "divine_smite", "target": t.id},
		{"type": "damage", "id": t.id, "amount": amount, "critical": true}, {"type": "death", "id": t.id}])
	await _record("fight_smite", 4.0)
	# The Fireball into the rest.
	foes = _foes()
	_make_current(wiz)
	_frame([wiz] + foes, 13.0)
	await _wait(25)
	var events: Array = [{"type": "spell", "caster": wiz.id, "spell": "fireball", "cells": _ball(foes[0].cell), "targets": []}]
	for f in foes:
		f.creature.hp = 1
		events.append({"type": "damage", "id": f.id, "amount": 26})
	_play(events)
	await _record("fight_fireball", 5.0)
	# Eldritch Blast, two beams.
	foes = _foes()
	if not foes.is_empty():
		_make_current(warlock)
		_frame([warlock, foes[0]], 10.0)
		await _wait(25)
		_play([{"type": "spell", "spell": "eldritch_blast", "caster": warlock.id, "targets": [foes[0].id, foes[0].id]},
			{"type": "attack", "attacker": warlock.id, "target": foes[0].id, "hit": true}, {"type": "damage", "id": foes[0].id, "amount": 9},
			{"type": "attack", "attacker": warlock.id, "target": foes[0].id, "hit": true}, {"type": "damage", "id": foes[0].id, "amount": 7}])
		await _record("fight_blast", 4.0)
	# Spirit Guardians around Liriel.
	_make_current(cleric)
	_frame([cleric], 10.0)
	await _wait(25)
	_zone(cleric, "spirit_guardians", cleric.cell)
	await _record("fight_guardians", 4.0)
	# The last foe, in slow motion.
	foes = _foes()
	if foes.is_empty():
		return
	var last := foes[0]
	for f in foes:
		if f != last:
			f.creature.hp = 0
			f.creature.dead = true
			cv.e.events.append({"type": "death", "id": f.id})
	cv.call("_play_events")
	await _wait(30)
	_make_current(godrick)
	_put(godrick, last.cell - axes[0])
	cv.call("_refresh_all")
	_frame([godrick, last], 9.0)
	await _wait(25)
	cv.e.state = Encounter.State.OVER
	cv.e.outcome = "victory"
	last.creature.hp = 0
	last.creature.dead = true
	_play([{"type": "attack", "attacker": godrick.id, "target": last.id, "hit": true},
		{"type": "damage", "id": last.id, "amount": 30}, {"type": "death", "id": last.id}])
	await _record("fight_last", 5.0)


## Strahd's entrance: the letterbox, the camera low on him, his name and the bell.
func _clip_boss() -> void:
	await _game("village_of_barovia", 23, FIGHTERS, 7, "storm")
	var view := _view()
	var axes := _ground_axes(view.rig)
	var lead := view.leader().cell
	var taken := {}
	var monsters: Array = []
	for f: Array in [["strahd_von_zarovich", 5, 0], ["dire_wolf", 4, -2], ["dire_wolf", 4, 2]]:
		var cell := _free_near(view, lead + axes[0] * int(f[1]) + axes[1] * int(f[2]), taken)
		taken[cell] = true
		monsters.append({"monster": str(f[0]), "cell": [cell.x, cell.y]})
	view.start_custom_encounter({"id": "site_boss", "text": "", "monsters": monsters, "surprise": ""})
	cv = view.combat_view
	cv.input_locked = true
	await _record("boss", 7.0)
