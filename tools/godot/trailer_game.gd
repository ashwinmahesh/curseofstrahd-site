extends Node
## Trailer v5's gameplay shots (~/Documents/CurseOfStrahdSite; not part of the game): the fights, Madam Eva's card,
## the dinner with Strahd and the bosses, always with the party of Godrick, Ratatouille, Kip and Liriel (owner,
## 2026-10-28), on the Modern look and the High preset. Clips (SITE_MODE=clips, run with --fixed-fps 30 and --motion)
## are numbered JPEGs, one per frame; stills (the default) keep three test frames of each clip instead.
##   python3 tools/capture.py --lane <lane> --scene trailer_game --mode stills|clips [--only fight,dinner] [--movie]
## Environment: SITE_MODE=stills|clips, SITE_ONLY=fight,dinner (default: every shot).
## What the fights and conversations change is shown only; settings and saves use files of this run's own.

const GAME := "res://scenes/game.tscn"
const MENU := "res://scenes/main_menu.tscn"
## The trailer's party (owner, 2026-10-28), Godrick at the front.
const FIGHTERS: Array[String] = ["godrick_pendlebrook", "ratatoille", "kip_smudgewick", "liriel_dawnsong"]
const FRONT := "Godrick"
## Kip speaks for the party in conversations (owner, 2026-10-08).
const TALKERS: Array[String] = ["kip_smudgewick", "godrick_pendlebrook", "ratatoille", "liriel_dawnsong"]
const SHOTS: Array[String] = ["strahd_road", "fight", "eva", "dinner", "boss_strahd", "boss_lysaga", "boss_dragon",
	"castle", "camp", "talk", "fight_open",
	"boss_entrance", "big_spells"]
## The shots whose voices the trailer keeps (the dinner's Strahd line); the rest keep their sound effects only.
const VOICED: Array[String] = ["dinner"]

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
## While set, every recorded frame first hides the interface again (the combat view re-shows names and rings).
var _bare_frames := false
## What the camera holds on when a shot frames several creatures.
var _focus: Node3D = null


func _ready() -> void:
	_own = "user://capture_site_%d" % OS.get_process_id()
	GameSettings.path = _own + "_settings.cfg"
	InputActions.ensure()
	Look.set_style("modern", false)
	Graphics.set_preset("high", false)
	_weather = Weather.data().duplicate(true)
	Dice.reseed(11)
	# Movie Maker runs on the Dummy sound driver, which the game treats as "no sound device" (tests): with
	# STRAHD_MOVIE_SOUND set, music and effects play into the movie anyway (VoiceOver checks it too, in a capture-only
	# local change).
	if OS.get_environment("STRAHD_MOVIE_SOUND") != "":
		Audio.set("_silent", false)
		# The trailer has its own music: only the game's effects and voices go into the movie.
		var music := AudioServer.get_bus_index("Music")
		if music >= 0:
			AudioServer.set_bus_mute(music, true)


func _exit_tree() -> void:
	for f: String in [GameSettings.path]:
		if FileAccess.file_exists(f):
			DirAccess.remove_absolute(f)


func capture_shots(t: Node, out: String) -> void:
	tool = t
	dir = out.get_base_dir()
	clips = OS.get_environment("SITE_MODE") == "clips"
	var only := OS.get_environment("SITE_ONLY").split(",", false)
	for id: String in SHOTS:
		if not only.is_empty() and not id in only:
			continue
		print("site_game: ", id)
		_quiet_voices(clips and not id in VOICED)
		await call("_shot_" + id)
	_clear()


# --- Set-up ---------------------------------------------------------------------------------------------------------

func _quiet_voices(on: bool) -> void:
	var bus := AudioServer.get_bus_index(VoiceOver.BUS)
	if bus < 0:
		AudioServer.add_bus()
		bus = AudioServer.bus_count - 1
		AudioServer.set_bus_name(bus, VoiceOver.BUS)
	AudioServer.set_bus_mute(bus, on)
	if on:
		VoiceOver.stop()

func _wait(n: int) -> void:
	await tool.call("wait_frames", n)


func _shot(name: String) -> void:
	tool.call("_shot", "%s/%s.png" % [dir, name])


## Keeps every frame for `seconds` (with --fixed-fps 30, each frame is a thirtieth of a second), numbered on from
## `first` in the clip's folder. Returns the next frame's number. In stills mode the same time passes and three test
## frames are kept (<clip>_<first + frame>.png at its start, middle and end).
func _record(clip: String, seconds: float, first: int = 0) -> int:
	var n := int(seconds * 30.0)
	# SITE_FIGHT_ONLY=fight_blast,...: a pass that keeps only these clips (the others play out unrecorded), so each
	# fight moment can come from a place of its own (owner, 2026-10-28).
	# A place's own conversation (a figure who approaches as the party arrives) can open over a staged fight: closed.
	if clip.begins_with("fight_") and root != null and root.get("dialogue") != null:
		root.call("_leave_dialogue_for_fight")
		# Leaving it brings the exploring party panel back over the fight's own: hidden again.
		_hud().visible = false
	var keep := OS.get_environment("SITE_FIGHT_ONLY").split(",", false)
	if not keep.is_empty() and clip.begins_with("fight_") and not clip in keep:
		for i in n:
			await get_tree().process_frame
		return first + n
	if not clips:
		for i in n:
			if _bare_frames:
				_no_interface()
			await get_tree().process_frame
			if i == 2 or i == n / 2 or i == n - 1:
				_shot("%s_%04d" % [clip, first + i])
		return first + n
	var to := "%s/%s" % [dir, clip]
	DirAccess.make_dir_recursive_absolute(to)
	# With Movie Maker on, the sound for these frames is in the movie: its frame numbers are the engine's process frames.
	print("segment %s %d %d %d" % [clip, first, Engine.get_process_frames() + 1, n])
	for i in n:
		if _bare_frames:
			_no_interface()
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
	# A cold start (the first game of a run) can take longer to build the place.
	for i in 600:
		if root.get("view") != null:
			break
		await _wait(1)
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
## `opening` records the fight's first seconds as that clip (the turn order coming in) before waiting for the turn.
func _fight(foes: Array = FOES, hour: int = 23, loc: String = "village_of_barovia", weather: String = "fog",
		at: Array = [], opening: String = "") -> bool:
	await _game(loc, hour, FIGHTERS, 7, weather, at)
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
		push_warning("trailer_game: the fight didn't start")
		return false
	cv = view.combat_view
	cv.input_locked = true
	if opening != "":
		await _record(opening, 3.0)
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
	if _focus == null or not is_instance_valid(_focus):
		_focus = Node3D.new()
		add_child(_focus)
	_focus.global_position = mid + Vector3(0, 0.3, 0)
	cv.rig.follow = _focus
	cv.rig.distance = dist
	cv.rig.snap_to_target()


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
		push_warning("trailer_game: %s can't cast %s" % [c.name(), spell])
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



## Where to put a second spell five squares from `at`, and the camera's quarter turn, so that both sit on open ground
## with no house between them and the camera: each turn and each way out from `at` is scored by the walls and roofs
## (solid squares, or off the map) in a band toward the camera from the pair's middle and under the spell itself. Turns
## the camera to the best and returns the spell's square.
func _open_view(at: Vector2i) -> Vector2i:
	var grid := _view().grid
	var best := at
	var best_turn := 0
	var best_score := 1 << 30
	for k in 4:
		var ax := _ground_axes(cv.rig)
		var right: Vector2i = ax[0]
		var fwd: Vector2i = ax[1]
		for dir: Vector2i in [right, -right, fwd, right + fwd, -right + fwd]:
			var spot := at + Vector2i(roundi(dir.x * 5.0 / Vector2(dir).length()), roundi(dir.y * 5.0 / Vector2(dir).length()))
			var mid := (at + spot) / 2
			var score := 0
			for d in range(1, 8):
				for side in range(-4, 5):
					var c := mid - fwd * d + right * side
					if not grid.in_bounds(c) or grid.is_solid(c):
						score += 2
			for dx in range(-3, 4):
				for dy in range(-3, 4):
					var c := spot + Vector2i(dx, dy)
					if not grid.in_bounds(c) or grid.is_solid(c):
						score += 1
			if score < best_score:
				best_score = score
				best = spot
				best_turn = k
		cv.rig.rotate_step(1)
		cv.rig.snap_to_target()
	cv.rig.rotate_step(best_turn)
	cv.rig.snap_to_target()
	print("trailer_game: open view turn %d, spell at %s, score %d" % [best_turn, best, best_score])
	return best


## Sets the scene for Spirit Guardians round `cleric` and Hunger of Hadar at `dark`: the foes stand in the darkness
## and round her, and the rest of the party stands back behind her, out of both.
func _stage_spells(cleric: Combatant, dark: Vector2i) -> void:
	var away := Vector2(cleric.cell - dark).normalized()
	var back := cleric.cell + Vector2i(roundi(away.x * 5.0), roundi(away.y * 5.0))
	var foes := _foes()
	var spots: Array[Vector2i] = [dark, dark + Vector2i(1, 1), dark + Vector2i(-1, 1), dark + Vector2i(1, -1),
		cleric.cell + Vector2i(roundi(-away.x * 2.0), roundi(-away.y * 2.0))]
	for i in foes.size():
		_put(foes[i], spots[i % spots.size()])
	var i := 0
	for c in cv.e.combatants:
		if c.side == &"party" and c != cleric:
			_put(c, back + Vector2i(i % 2, i / 2))
			i += 1
	cv.call("_refresh_all")


## Points the camera at the middle of two squares, `dist` away.
func _aim_between(a: Vector2i, b: Vector2i, dist: float) -> void:
	cv.rig.follow = null
	cv.rig.global_position = (cv.board.cell_center(a) + cv.board.cell_center(b)) * 0.5 + Vector3(0, 0.3, 0)
	cv.rig.distance = dist


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



# --- The trailer's shots ----------------------------------------------------------------------------------------------

## The heroes by their trailer names.
func _party() -> Dictionary:
	return {"godrick": _hero("Godrick"), "wiz": _hero("Ratatouille"), "kip": _hero("Kip"), "liriel": _hero("Liriel")}


## A foe of `kind` (by name) among the living, or null.
func _foe_named(part: String) -> Combatant:
	for f in _foes():
		if f.name().contains(part):
			return f
	return null


## A custom fight at `loc` with no boss entrance and the interface hidden: the foes stand where `foes` puts them
## ([monster, right, forward] from the leader, as the camera sees it). Returns the encounter's combat view or null.
## `sunsword`: Godrick goes in with the Sunsword in hand (attuned), so its light is lit as the fight starts.
## `opening`: the fight's first `opening_s` seconds are recorded as that clip (the foes' first turn, the camera on it).
## `tough`: the heroes go in with three times their Hit Points, so a big blow shows without anyone falling.
func _staged(loc: String, hour: int, weather: String, at: Array, foes: Array, hud: bool = false,
		sunsword: bool = false, opening: String = "", opening_s: float = 0.0, tough: bool = false) -> CombatView:
	await _game(loc, hour, FIGHTERS, 9 if sunsword else 7, weather, at)
	if sunsword:
		for ch: Character in GameState.story.party:
			if ch.name.contains("Godrick"):
				ch.add_item("sunsword")
				ch.attune("sunsword")
				ch.equip("sunsword", "main_hand")
	var view := _view()
	var axes := _ground_axes(view.rig)
	var lead := view.leader().cell
	var taken := {}
	var monsters: Array = []
	for f: Variant in foes:
		var spec := f as Array
		var cell := _free_near(view, lead + axes[0] * int(spec[1]) + axes[1] * int(spec[2]), taken)
		taken[cell] = true
		monsters.append({"monster": str(spec[0]), "cell": [cell.x, cell.y]})
	if tough:
		for ch: Character in GameState.story.party:
			ch.hp = ch.max_hp() * 3
	BossBar.entrances = false
	Dice.reseed(11)
	var ok := view.start_custom_encounter({"id": "trailer_fight", "text": "", "monsters": monsters, "surprise": "enemies"})
	BossBar.entrances = true
	if not ok:
		push_warning("trailer_game: the fight at %s didn't start" % loc)
		return null
	cv = view.combat_view
	cv.input_locked = true
	cv.hud.visible = hud
	if opening != "":
		await _record(opening, opening_s)
	for i in 3000:
		await get_tree().process_frame
		if cv.mode == CombatView.Mode.PROMPT:
			cv.call("_answer", false, "ask")
		if cv.mode == CombatView.Mode.IDLE and cv.e.current().side == &"party":
			break
	cv.hud.visible = hud
	await _wait(20)
	return cv


## Cold open: on the misty road at night, a swarm of bats sweeps in front of the party and becomes Strahd.
func _shot_strahd_road() -> void:
	if await _staged("village_of_barovia", 23, "fog", [], [["strahd_von_zarovich", 3, 0]]) == null:
		return
	var strahd := _foe_named("Strahd")
	var p := _party()
	cv.overlay.clear_all()
	_bare_frames = true
	_no_interface()
	var tok := cv.tokens[strahd.id] as Node3D
	print("trailer_game: Strahd at %s, form %s, token visible %s at %s" % [strahd.cell, cv.e.legendary.base_form(strahd),
		tok.visible if tok != null else "-", tok.global_position if tok != null else "-"])
	cv.e.legendary._set_form(strahd, "bat")
	cv.call("_play_events")
	await _wait(60)
	if OS.get_environment("SITE_DEBUG") != "":
		_frame([p["godrick"], strahd], 16.0)
		await _wait(20)
		_shot("debug_road_wide_bat")
		var t1 := cv.tokens[strahd.id] as Node3D
		print("trailer_game: bat token visible %s, follow %s" % [t1.visible, cv.rig.follow])
	_frame([p["godrick"], p["liriel"], strahd], 7.0)
	cv.rig.shot_pitch = 10.0
	await _wait(20)
	var n := await _record("strahd_road", 0.8)
	cv.e.legendary._set_form(strahd, cv.e.legendary.base_form(strahd))
	cv.call("_play_events")
	_no_interface()
	await _record("strahd_road", 3.7, n)
	_bare_frames = false
	if OS.get_environment("SITE_DEBUG") != "":
		_frame([p["godrick"], strahd], 16.0)
		await _wait(20)
		_shot("debug_road_wide_after")
		var t2 := cv.tokens[strahd.id] as Node3D
		print("trailer_game: after: token visible %s at %s, children %s" % [t2.visible, t2.global_position,
			t2.get_children().map(func(c: Node) -> String: return "%s:%s" % [c.name, (c as Node3D).visible if c is Node3D else ""])])


## Nothing over the picture: every interface layer hidden, and no names, rings or bars under anyone.
func _no_interface() -> void:
	for layer: Node in root.find_children("*", "CanvasLayer", true, false):
		(layer as CanvasLayer).visible = false
	for tok: Node in root.find_children("*", "", true, false):
		if not tok is CombatToken:
			continue
		# Shrunk rather than hidden: the combat view turns rings and names back on as it updates.
		for part: String in ["_ring", "_active_ring", "_bar_back", "_bar_fill", "_label"]:
			var n: Variant = tok.get(part)
			if n is Node3D:
				(n as Node3D).scale = Vector3.ZERO
		for c: Node in tok.get_children():
			if c is Label3D or c.name == "Aura":
				(c as Node3D).scale = Vector3.ZERO


## The village fight: the turn order coming in, Godrick's smite on a critical hit, Ratatouille aiming a Fireball (who
## it catches, their odds, the friendly-fire warning) and casting it, Kip's Eldritch Blast, Liriel's Spirit Guardians,
## and the last foe falling in slow motion. Each is a clip of its own.
func _shot_fight() -> void:
	await _fight_clips("village_of_barovia", 23, "rain", [], true)


## The same fight after the smite on open ground (owner, 2026-10-28: in the village some foes were cut off by the
## houses): SITE_FIGHT_LOC, SITE_FIGHT_HOUR, SITE_FIGHT_WEATHER and SITE_FIGHT_AT ("x,y") pick the place.
func _shot_fight_open() -> void:
	var at: Array = []
	var a := OS.get_environment("SITE_FIGHT_AT").split(",", false)
	if a.size() == 2:
		at = [int(a[0]), int(a[1])]
	var loc := OS.get_environment("SITE_FIGHT_LOC")
	await _fight_clips(loc if loc != "" else "old_bonegrinder_hill", int(OS.get_environment("SITE_FIGHT_HOUR")) if
		OS.get_environment("SITE_FIGHT_HOUR") != "" else 21, OS.get_environment("SITE_FIGHT_WEATHER"), at, false)


## The fight's clips: the turn order coming in and Godrick's smite (with `smite`), then the Fireball's aim and burst,
## Kip's Eldritch Blast, Liriel's Spirit Guardians, Hunger of Hadar and the last foe in slow motion.
func _fight_clips(loc: String, hour: int, weather: String, at: Array, smite: bool) -> void:
	if not await _fight(FOES, hour, loc, weather, at, "fight_start" if smite else ""):
		return
	var p := _party()
	var godrick: Combatant = p["godrick"]
	var wiz: Combatant = p["wiz"]
	var warlock: Combatant = p["kip"]
	var cleric: Combatant = p["liriel"]
	var axes := _ground_axes(cv.rig)
	var foes := _foes()
	# The smite: Godrick beside the first foe, a critical hit, the camera pushing in.
	if not smite:
		foes[0].creature.hp = 0
		foes[0].creature.dead = true
		cv.e.events.append({"type": "death", "id": foes[0].id})
		cv.call("_play_events")
		await _wait(20)
	_make_current(godrick)
	_put(godrick, foes[0].cell - axes[0])
	cv.call("_refresh_all")
	_frame([godrick, foes[0]], 7.5)
	await _wait(25)
	var t := foes[0]
	var amount := t.creature.max_hp() + 5
	t.creature.hp = 0
	t.creature.dead = true
	if smite:
		_play([{"type": "attack", "attacker": godrick.id, "target": t.id, "hit": true, "critical": true},
			{"type": "smite", "caster": godrick.id, "spell": "divine_smite", "target": t.id},
			{"type": "damage", "id": t.id, "amount": amount, "critical": true}, {"type": "death", "id": t.id}])
		await _record("fight_smite", 3.5)
	# The Fireball's aim: Godrick has waded in among them, so the template warns before it catches him.
	foes = _foes()
	_make_current(wiz)
	_put(godrick, foes[1].cell + axes[0])
	cv.call("_refresh_all")
	_frame([wiz] + foes, 11.0)
	await _wait(30)
	_aim_area(wiz, "fireball", foes[1].cell, 3)
	await _record("fight_aim", 3.0)
	cv.hud.hide_tooltip()
	cv.overlay.clear_all()
	_put(godrick, foes[0].cell - axes[0] * 4)
	cv.call("_refresh_all")
	# The Fireball: Ratatouille's cast, the burst.
	_frame([wiz] + foes, 10.0)
	await _wait(20)
	var events: Array = [{"type": "spell", "caster": wiz.id, "spell": "fireball", "cells": _ball(foes[1].cell), "targets": []}]
	for f in foes:
		f.creature.hp = 1
		events.append({"type": "damage", "id": f.id, "amount": 26})
	_play(events)
	await _record("fight_fireball", 4.0)
	# Kip's Eldritch Blast, two beams.
	foes = _foes()
	if not foes.is_empty():
		_make_current(warlock)
		_frame([warlock, foes[0]], 8.5)
		await _wait(25)
		_play([{"type": "spell", "spell": "eldritch_blast", "caster": warlock.id, "targets": [foes[0].id, foes[0].id]},
			{"type": "attack", "attacker": warlock.id, "target": foes[0].id, "hit": true}, {"type": "damage", "id": foes[0].id, "amount": 9},
			{"type": "attack", "attacker": warlock.id, "target": foes[0].id, "hit": true}, {"type": "damage", "id": foes[0].id, "amount": 7}])
		await _record("fight_blast", 3.5)
	# Liriel's Spirit Guardians.
	_make_current(cleric)
	_frame([cleric], 8.0)
	await _wait(25)
	_zone(cleric, "spirit_guardians", cleric.cell)
	await _record("fight_guardians", 3.5)
	# Kip's Hunger of Hadar swallowing the foes beside Liriel's guardians, the camera easing in lower.
	foes = _foes()
	if foes.size() >= 2:
		_put(cleric, foes[0].cell - axes[0])
		cv.call("_refresh_all")
		var dark := _open_view(cleric.cell)
		_stage_spells(cleric, dark)
		_aim_between(cleric.cell, dark, 12.0)
		await _wait(30)
		var to := 0
		_zone(warlock, "hunger_of_hadar", dark)
		for k in 6:
			cv.rig.distance = lerpf(12.0, 10.0, (k + 1) / 6.0)
			cv.rig.shot_pitch = lerpf(0.0, 6.0, (k + 1) / 6.0)
			to = await _record("fight_hadar", 0.7, to)
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
	_frame([godrick, last], 7.5)
	await _wait(25)
	cv.e.state = Encounter.State.OVER
	cv.e.outcome = "victory"
	last.creature.hp = 0
	last.creature.dead = true
	_play([{"type": "attack", "attacker": godrick.id, "target": last.id, "hit": true},
		{"type": "damage", "id": last.id, "amount": 30}, {"type": "death", "id": last.id}])
	await _record("fight_last", 4.5)


## Madam Eva's reading: the first card turns face up above the conversation, over the reading's storybook picture
## (owner, 2026-10-28: the cutscene, not the tent; one beat, one picture).
func _shot_eva() -> void:
	await _game("tser_pool_eva_tent", 21, TALKERS, 5)
	root.call("start_dialogue", "svalich_road/madam_eva:reading", "madam_eva")
	var d := root.get("dialogue") as DialogueUI
	if d == null:
		push_warning("trailer_game: Eva's reading didn't start")
		return
	# Her lines up to the first card's.
	for i in 12:
		var said: Array = d.get("_history")
		if not said.is_empty() and str(said[-1]).contains("The first card"):
			break
		d.call("_advance")
		await _wait(6)
	VoiceOver.stop()
	var n := await _record("eva", 0.8)
	d.call("_advance")
	VoiceOver.stop()
	await _record("eva", 4.6, n)


## Dinner with Strahd in Castle Ravenloft's dining hall: the party at his table, Kip watching him (Insight DC 17, the
## d20 rolling against it), the roll failing, and Strahd's answer in his own voice. Record with --movie for the voice.
func _shot_dinner() -> void:
	await _clear()
	var seeds: Array[int] = [3, 5, 7, 9, 13, 21, 34, 55, 2, 4]
	for roll_seed in seeds:
		var d := await _dinner_table()
		if d == null:
			return
		if await _watch_him(d, roll_seed, roll_seed == seeds[-1]):
			return


func _dinner_table() -> DialogueUI:
	await _game("castle_ravenloft_main_floor", 20, TALKERS, 9, "", [6, 9])
	GameState.story.set_flag("strahd_invitation", "accepted")
	GameState.story.set_flag("crg_dinner_excused", true)
	root.call("start_dialogue", "castle_ravenloft/gates_dinner:start", "strahd")
	var d := root.get("dialogue") as DialogueUI
	for i in 12:
		if d == null or not d.options_shown.is_empty():
			break
		d.call("_advance")
		await _wait(4)
	await _wait(20)
	_no_picture(d)
	return d


## The conversation over the board, not over a storybook picture: the party and the room stay in view.
func _no_picture(d: DialogueUI) -> void:
	if d != null and d.cutscene != null:
		d.cutscene.queue_free()
		d.cutscene = null


## Picks the Insight option with the dice seeded to `roll_seed`; when it fails (or `anyway`), records the roll and
## Strahd's answer and returns true.
func _watch_him(d: DialogueUI, roll_seed: int, anyway: bool) -> bool:
	var pick := -1
	for i in d.options_shown.size():
		if str((d.options_shown[i] as Dictionary).get("text", "")).contains("What does he actually want"):
			pick = i
	if pick < 0:
		push_warning("trailer_game: no Insight option at the dinner")
		return true
	if not clips:
		_shot("dinner_options")
	Dice.reseed(roll_seed)
	var n := 0
	if clips:
		n = await _record("dinner", 1.5)
	d.call("_choose", pick)
	# The Guidance offer goes unanswered in the trailer: roll as it stands.
	for i in 90:
		if d.guidance != null:
			d.guidance.decline_button.pressed.emit()
		if d.d20 != null:
			break
		await get_tree().process_frame
	var failed := d.d20 != null and not bool(d.d20.result.get("success", true))
	print("trailer_game: dinner seed %d, roll %s" % [roll_seed, "failed" if failed else "passed"])
	if not failed and not anyway:
		return false
	_no_picture(d)
	n = await _record("dinner", 3.0, n)
	# Heroic Inspiration's offer to reroll: let it stand.
	for p: Node in root.find_children("*", "CheckAidPrompt", true, false):
		(p as CheckAidPrompt).stand_button.pressed.emit()
	await _wait(2)
	# The narrator's line, then Strahd's.
	d.call("_advance")
	VoiceOver.stop()
	await _wait(2)
	d.call("_advance")
	_no_picture(d)
	await _record("dinner", 4.6, n)
	return true


## Strahd in the dining hall, the fight on: his boss plate and bar, and his change to mist and back.
func _shot_boss_strahd() -> void:
	if await _staged("castle_ravenloft_main_floor", 21, "", [6, 10], [["strahd_von_zarovich", 0, 4],
			["strahds_animated_armor", 3, 3]], true) == null:
		return
	var strahd := _foe_named("Strahd")
	var p := _party()
	_frame([p["godrick"], strahd], 8.5)
	await _wait(20)
	var n := await _record("boss_strahd", 0.6)
	cv.e.legendary._set_form(strahd, "mist")
	cv.call("_play_events")
	n = await _record("boss_strahd", 1.6, n)
	cv.e.legendary._set_form(strahd, cv.e.legendary.base_form(strahd))
	cv.call("_play_events")
	await _record("boss_strahd", 1.6, n)


## Baba Lysaga's creeping hut at Berez stamping in on the party.
func _shot_boss_lysaga() -> void:
	if await _staged("berez", 17, "fog", [], [["baba_lysagas_creeping_hut", 0, 4], ["baba_lysaga", 2, 3]], true) == null:
		return
	var hut := _foe_named("Hut")
	if hut == null:
		hut = _foes()[0]
	var p := _party()
	_frame([p["godrick"], hut], 9.0)
	await _wait(20)
	_play([{"type": "attack", "attacker": hut.id, "target": (p["godrick"] as Combatant).id, "hit": true},
		{"type": "damage", "id": (p["godrick"] as Combatant).id, "amount": 14}])
	await _record("boss_lysaga", 3.0)


## Castle Ravenloft's climax in the dining hall: Strahd strikes Godrick and Kip (their hurt), then Godrick, with the
## Sunsword drawn, strikes back and its light floods the hall.
func _shot_castle() -> void:
	await _clear()
	if await _staged("castle_ravenloft_main_floor", 22, "", [6, 10], [["strahd_von_zarovich", 0, 3]], true,
			true) == null:
		return
	var strahd := _foe_named("Strahd")
	var p := _party()
	var godrick: Combatant = p["godrick"]
	_frame([godrick, strahd], 8.0)
	await _wait(30)
	_play([{"type": "attack", "attacker": strahd.id, "target": godrick.id, "hit": true},
		{"type": "damage", "id": godrick.id, "amount": 17},
		{"type": "attack", "attacker": strahd.id, "target": (p["kip"] as Combatant).id, "hit": true},
		{"type": "damage", "id": (p["kip"] as Combatant).id, "amount": 12}])
	var n := await _record("castle_strike", 2.5)
	_make_current(godrick)
	_put(godrick, strahd.cell - _ground_axes(cv.rig)[1])
	cv.call("_refresh_all")
	_frame([godrick, strahd], 7.0)
	await _wait(10)
	_play([{"type": "attack", "attacker": godrick.id, "target": strahd.id, "hit": true, "critical": true},
		{"type": "damage", "id": strahd.id, "amount": 34, "critical": true}])
	var k := 0
	for i in 8:
		cv.rig.distance = lerpf(7.0, 5.5, (i + 1) / 8.0)
		k = await _record("sunsword", 0.7, k)


## The button: the party's camp in the forest at night, by the fire, nothing over the picture.
func _shot_camp() -> void:
	await _game("lake_zarovich", 22, FIGHTERS, 7, "overcast")
	var view := _view()
	var camp := LocationCamp.pitch(view, root, "safe")
	if camp == null:
		push_warning("trailer_game: no room for a camp")
		return
	await _wait(40)
	_hud().close_narration()
	_no_interface()
	view.rig.distance = 7.5
	view.rig.shot_pitch = 10.0
	view.rig.snap_to_target()
	await _wait(20)
	_no_interface()
	await _record("camp", 4.0)


## Sarkhaza, the ancient red, breathing fire across the party in her lair (the engine's own Fire Breath, aimed at the
## middle of the party; the party is levelled up so the heroes take it on their feet).
func _shot_boss_dragon() -> void:
	if await _staged("ghakis_lair", 22, "", [], [["sarkhaza", 0, 8]], true, false, "boss_dragon", 6.0, true) == null:
		return
	var p := _party()
	for c: Combatant in [p["godrick"], p["wiz"], p["kip"], p["liriel"]]:
		print("trailer_game: %s at %d HP after the dragon's turn" % [c.name(), c.creature.hp])


## The Vine Mother at Yester Hill with a legendary action on the party.
func _shot_boss_vine() -> void:
	if await _staged("yester_hill", 17, "overcast", [], [["vine_mother", 0, 5]], true) == null:
		return
	var vine := _foe_named("Vine")
	var p := _party()
	_frame([p["godrick"], vine], 11.0)
	await _wait(20)
	_play([{"type": "attack", "attacker": vine.id, "target": (p["godrick"] as Combatant).id, "hit": true},
		{"type": "damage", "id": (p["godrick"] as Combatant).id, "amount": 18}])
	await _record("boss_vine", 3.0)


## The site's conversation loop: at the Blue Water Inn's bar, Urwin's conversation opens, the camera eases in on Kip
## and him, and the busts come in.
func _shot_talk() -> void:
	await _game("vallaki_blue_water_inn", 20, TALKERS, 5)
	var n := await _record("talk", 0.8)
	root.call("start_dialogue", "vallaki/martikovs:urwin", "urwin_martikov")
	n = await _record("talk", 0.3, n)
	var d := root.get("dialogue") as DialogueUI
	if d != null:
		d.call("_advance")
	await _record("talk", 3.6, n)


## Strahd's boss entrance in the castle (the game's own: letterbox bars, the camera low on him, his name and title, a
## sting), from the moment the fight starts.
func _shot_boss_entrance() -> void:
	await _game("castle_ravenloft_main_floor", 22, FIGHTERS, 9, "", [6, 10])
	var view := _view()
	var axes := _ground_axes(view.rig)
	var lead := view.leader().cell
	var taken := {}
	var monsters: Array = []
	for f: Array in [["strahd_von_zarovich", 0, 4], ["vampire_spawn", -3, 3], ["vampire_spawn", 3, 3]]:
		var cell := _free_near(view, lead + axes[0] * int(f[1]) + axes[1] * int(f[2]), taken)
		taken[cell] = true
		monsters.append({"monster": str(f[0]), "cell": [cell.x, cell.y]})
	BossBar.entrances = true
	Dice.reseed(11)
	if not view.start_custom_encounter({"id": "trailer_entrance", "text": "", "monsters": monsters, "surprise": "enemies"}):
		push_warning("trailer_game: Strahd's entrance didn't start")
		return
	cv = view.combat_view
	cv.input_locked = true
	await _record("boss_entrance", 5.0)


## The party's big spells on Strahd and his spawn in the castle, each a clip: Liriel's Flame Strike and Ratatouille's
## Lightning Bolt.
func _shot_big_spells() -> void:
	if await _staged("castle_ravenloft_main_floor", 22, "", [6, 10], [["strahd_von_zarovich", 1, 5],
			["vampire_spawn", 3, 4], ["vampire_spawn", -1, 6]], true) == null:
		return
	var p := _party()
	var strahd := _foe_named("Strahd")
	for f in _foes():
		f.creature.hp = f.creature.max_hp() * 3
	# All of them inside the lit dining hall (squares 1-12 by 4-14): Strahd by the organ, his spawn either side.
	_put(strahd, Vector2i(6, 6))
	var spawns := _foes().filter(func(f: Combatant) -> bool: return f != strahd)
	if spawns.size() >= 2:
		_put(spawns[0], Vector2i(4, 7))
		_put(spawns[1], Vector2i(8, 7))
	_put(p["liriel"], Vector2i(6, 11))
	_put(p["wiz"], Vector2i(4, 12))
	_put(p["godrick"], Vector2i(7, 10))
	_put(p["kip"], Vector2i(9, 12))
	cv.call("_refresh_all")
	# Flame Strike: a column of fire on Strahd.
	_make_current(p["liriel"])
	_frame([p["liriel"], strahd], 9.0)
	await _wait(20)
	var sd := Compendium.shared().spell_data("flame_strike")
	var cells := cv.e.spells.area_for(p["liriel"], sd, Vector2(strahd.cell.x + 0.5, strahd.cell.y + 0.5), Vector2.ZERO, 5)
	var events: Array = [{"type": "spell", "spell": "flame_strike", "caster": (p["liriel"] as Combatant).id, "targets": [],
		"cells": cells}]
	for f in _foes():
		if f.cell in cells:
			events.append({"type": "damage", "id": f.id, "amount": 31})
	_play(events)
	await _record("spell_flame", 3.0)
	# Lightning Bolt: a line from Ratatouille through Strahd and his spawn.
	_make_current(p["wiz"])
	var wiz: Combatant = p["wiz"]
	_frame([wiz, strahd], 10.0)
	await _wait(20)
	var sd2 := Compendium.shared().spell_data("lightning_bolt")
	var aim := Vector2(strahd.cell.x + 0.5, strahd.cell.y + 0.5)
	var dir2 := (aim - cv.e.center_of(wiz)).normalized()
	var cells2 := cv.e.spells.area_for(wiz, sd2, aim, dir2, 3)
	var events2: Array = [{"type": "spell", "spell": "lightning_bolt", "caster": wiz.id, "targets": [], "cells": cells2}]
	for f in _foes():
		if f.cell in cells2:
			events2.append({"type": "damage", "id": f.id, "amount": 28})
	_play(events2)
	await _record("spell_bolt", 3.0)
