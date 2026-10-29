extends Node3D
## Trailer v5's world shots (~/Documents/CurseOfStrahdSite; not part of the game): the party of Godrick, Ratatouille,
## Kip and Liriel walking through each place close enough to see their walks, no HUD, the Modern look on the High
## preset. Stills (a test frame of each shot, early and late in its walk) are PNGs; clips (SITE_MODE=clips, run with
## --fixed-fps 30 and --motion) are numbered JPEGs, one per frame.
##   python3 tools/capture.py --lane <lane> --scene trailer_world --mode stills|clips [--only road,village]
## Environment: SITE_MODE=stills|clips, SITE_ONLY=road,village (default: every shot).
## Settings and saves use files of this run's own (removed at the end), never the player's.

## The trailer's party in every shot (owner, 2026-10-28), Godrick leading.
const PARTY: Array[String] = ["godrick_pendlebrook", "ratatoille", "kip_smudgewick", "liriel_dawnsong"]
const BESIDE: Array[Vector2i] = [Vector2i.ZERO, Vector2i(1, 0), Vector2i(0, 1), Vector2i(1, 1)]

## Each shot: the place ("loc"), the hour, the weather, where the party starts ("at", else the place's spawn), the
## camera's distance ("zoom", "zoom_to"), quarter turns ("turns"), "pitch"/"pitch_to" (degrees flatter than the play
## view), "tilt"/"tilt_to" (toward the horizon), "drift" (squares the camera slides along its right and forward over
## the shot), "face": "castle", and where the party walks: "walk" (a square) or "walk_by" ([right, forward] squares
## from the leader, as the camera sees it: [0, -6] is toward the camera). The camera follows the leader unless "look"
## holds it over a square ([x, z] or "middle"). "strikes": seconds at which lightning strikes. "seconds": the clip's
## length.
var SHOTS := {
	"road": {"loc": "into_the_mists_road", "hour": 22, "weather": "fog", "at": [13, 14], "zoom": 9.0, "zoom_to": 8.0,
		"pitch": 4.0, "walk": [3, 15], "seconds": 5.0},
	"village": {"loc": "village_of_barovia", "hour": 21, "weather": "rain", "zoom": 9.5, "zoom_to": 8.5,
		"pitch": 8.0, "walk_by": [6, 0], "seconds": 4.0},
	"vallaki": {"loc": "vallaki", "hour": 20, "weather": "rain", "zoom": 9.5, "zoom_to": 8.5, "pitch": 8.0,
		"walk_by": [-6, -1], "seconds": 4.0, "strikes": [1.2]},
	"krezk": {"loc": "krezk", "hour": 15, "weather": "snow", "at": [22, 13], "zoom": 10.0, "zoom_to": 9.0,
		"pitch": 8.0, "walk": [13, 13], "seconds": 4.0},
	"inn": {"loc": "vallaki_blue_water_inn", "hour": 20, "at": [3, 3], "zoom": 9.0, "zoom_to": 8.0, "pitch": 6.0,
		"walk": [10, 3], "seconds": 4.0},
	"tser": {"loc": "tser_pool", "hour": 19, "weather": "overcast", "at": [24, 19], "zoom": 11.0, "zoom_to": 10.0,
		"pitch": 6.0, "walk": [19, 15], "seconds": 4.5},
	"vista": {"loc": "village_of_barovia", "hour": 18, "weather": "storm", "zoom": 12.0, "zoom_to": 24.0,
		"tilt_to": 1.0, "face": "castle", "seconds": 5.0, "strikes": [3.0]},
	"gates": {"loc": "castle_ravenloft_gates", "hour": 23, "weather": "storm", "at": [19, 31], "turns": 2,
		"zoom": 11.0, "zoom_to": 9.5, "pitch": 8.0, "walk": [19, 11], "seconds": 5.0, "strikes": [0.8, 3.6]},
	"argyn": {"loc": "argynvostholt", "hour": 17, "weather": "fog", "zoom": 10.0, "zoom_to": 9.0, "pitch": 8.0,
		"walk_by": [5, -2], "seconds": 4.0},
	"winery": {"loc": "wizard_of_wines", "hour": 17, "weather": "rain", "zoom": 10.0, "zoom_to": 9.0, "pitch": 8.0,
		"walk_by": [5, -2], "seconds": 4.0},
	"abbey": {"loc": "abbey_of_st_markovia", "hour": 18, "weather": "snow", "zoom": 10.0, "zoom_to": 9.0, "pitch": 8.0,
		"walk_by": [-5, -2], "seconds": 4.0},
	"lake": {"loc": "lake_zarovich", "hour": 17, "weather": "overcast", "zoom": 10.0, "zoom_to": 9.0, "pitch": 8.0,
		"walk_by": [5, -2], "seconds": 4.0},
	"berez": {"loc": "berez", "hour": 11, "weather": "fog", "zoom": 10.0, "zoom_to": 9.0, "pitch": 8.0,
		"walk_by": [5, -2], "seconds": 4.0},
	# The walking montage (owner, 2026-10-28): the party walks across the frame in the same place on screen, through
	# place after place, never stopping until the last. "lane": the party starts where `steps` squares to the camera's
	# right are clear (nearest "near", else the middle) and walks them; the camera holds on the party's middle.
	"m_road": {"loc": "into_the_mists_road", "hour": 21, "weather": "fog", "lane": true, "steps": 12, "seconds": 3.0},
	"m_village": {"loc": "village_of_barovia", "hour": 21, "weather": "rain", "lane": true, "steps": 16, "seconds": 3.0},
	"m_vallaki": {"loc": "vallaki", "hour": 20, "weather": "rain", "lane": true, "steps": 16, "seconds": 3.0,
		"strikes": [1.0]},
	"m_abbey": {"loc": "abbey_of_st_markovia", "hour": 18, "weather": "snow", "lane": true, "steps": 16, "seconds": 3.0},
	"m_krezk": {"loc": "krezk", "hour": 15, "weather": "snow", "lane": true, "steps": 16, "seconds": 3.0},
	"m_inn": {"loc": "vallaki_blue_water_inn", "hour": 20, "lane": true, "steps": 12, "seconds": 3.0},
	"m_winery": {"loc": "wizard_of_wines", "hour": 17, "weather": "rain", "lane": true, "steps": 16, "seconds": 3.0},
	"m_tser": {"loc": "tser_pool", "hour": 19, "weather": "overcast", "lane": true, "steps": 6, "seconds": 4.0},
	"m_argyn": {"loc": "argynvostholt", "hour": 17, "weather": "fog", "lane": true, "steps": 16, "seconds": 3.0},
	"m_berez": {"loc": "berez", "hour": 11, "weather": "fog", "lane": true, "steps": 16, "seconds": 3.0},
	"m_lake": {"loc": "lake_zarovich", "hour": 17, "weather": "overcast", "lane": true, "steps": 16, "seconds": 3.0},
	"m_yester": {"loc": "yester_hill", "hour": 18, "weather": "overcast", "lane": true, "steps": 16, "seconds": 3.0},
	"m_bonegrinder": {"loc": "old_bonegrinder_hill", "hour": 12, "weather": "overcast", "lane": true, "steps": 16,
		"seconds": 3.0},
	"m_amber": {"loc": "amber_temple", "hour": 14, "weather": "snow", "lane": true, "steps": 16, "seconds": 3.0},
	# The valley's looks (owner, 2026-10-28: each place its own aesthetic): the party standing, the camera easing in.
	"d_village": {"loc": "village_of_barovia", "hour": 21, "weather": "rain", "at": [16, 12], "zoom": 11.0,
		"zoom_to": 9.5, "pitch": 6.0, "pitch_to": 10.0, "drift": [1.2, 0.0], "seconds": 3.0, "strikes": [0.9]},
	"d_vallaki": {"loc": "vallaki", "hour": 20, "weather": "rain", "at": [24, 19], "zoom": 11.0, "zoom_to": 9.5,
		"pitch": 6.0, "pitch_to": 10.0, "drift": [-1.2, 0.0], "seconds": 3.0, "strikes": [0.5]},
	"d_inn": {"loc": "vallaki_blue_water_inn", "hour": 20, "at": [3, 3], "zoom": 9.0, "zoom_to": 7.5, "pitch": 6.0,
		"pitch_to": 12.0, "seconds": 3.0},
	"d_abbey": {"loc": "abbey_of_st_markovia", "hour": 18, "weather": "snow", "at": [14, 16], "zoom": 10.0,
		"zoom_to": 8.5, "pitch": 6.0, "pitch_to": 10.0, "drift": [1.0, 0.0], "seconds": 3.0},
	"d_church": {"loc": "vallaki_st_andrals", "hour": 20, "look": "middle", "zoom": 11.0, "zoom_to": 9.0, "pitch": 6.0,
		"pitch_to": 12.0, "seconds": 3.0},
	"d_deathhouse": {"loc": "death_house_ground", "hour": 22, "at": [13, 8], "zoom": 9.0, "zoom_to": 7.5, "pitch": 6.0,
		"pitch_to": 12.0, "seconds": 3.0},
	"d_tser": {"loc": "tser_pool", "hour": 19, "weather": "overcast", "at": [24, 16], "zoom": 9.0, "zoom_to": 7.5,
		"pitch": 8.0, "pitch_to": 12.0, "seconds": 3.5},
	# The castle's crypts, the party sneaking by lantern light.
	"sneak": {"loc": "castle_ravenloft_catacombs", "hour": 23, "lane": true, "steps": 12, "sneak": true, "seconds": 4.0},
	# Inside the castle: the party walking into the dining hall.
	"hall": {"loc": "castle_ravenloft_main_floor", "hour": 22, "lane": true, "steps": 12, "near": [6, 9], "seconds": 4.0},
	# The site's loop of sunbeams on the misty road at dusk, the party walking under them.
	"sunbeams": {"loc": "into_the_mists_road", "hour": 18, "weather": "fog", "at": [14, 14], "zoom": 11.0,
		"zoom_to": 9.5, "pitch": 4.0, "pitch_to": 8.0, "walk": [5, 15], "seconds": 6.0},
	# The title's backdrop: the party on the drawbridge before the gates, the storm over the castle.
	"title_bg": {"loc": "castle_ravenloft_gates", "hour": 23, "weather": "storm", "at": [19, 28], "zoom": 11.0,
		"zoom_to": 9.5, "tilt": 0.6, "tilt_to": 0.9, "seconds": 12.0, "strikes": [1.0, 6.5, 10.5]},
}

## Every montage shot holds the camera the same way, so the party stays in one place on screen across the cuts.
const LANE_ZOOM := 9.0
const LANE_PITCH := 8.0

var view: LocationView = null
var _focus: Node3D = null
var _weather: Dictionary = {}
var _own := ""


func _ready() -> void:
	_own = "user://capture_trailer_%d" % OS.get_process_id()
	GameSettings.path = _own + "_settings.cfg"
	InputActions.ensure()
	Look.set_style("modern", false)
	Graphics.set_preset("high", false)
	_weather = Weather.data().duplicate(true)


func _exit_tree() -> void:
	for f: String in [GameSettings.path]:
		if FileAccess.file_exists(f):
			DirAccess.remove_absolute(f)


func capture_shots(tool: Node, out: String) -> void:
	var clips := OS.get_environment("SITE_MODE") == "clips"
	var only := OS.get_environment("SITE_ONLY").split(",", false)
	var dir := out.get_base_dir()
	for id: String in SHOTS:
		if not only.is_empty() and not id in only:
			continue
		print("site_world: ", id)
		var shot := SHOTS[id] as Dictionary
		_build(shot)
		if bool(shot.get("lane", false)):
			shot = _lane(shot)
			_build(shot)
		await tool.call("wait_frames", 50 if not clips else 20)
		_bare()
		if clips:
			await _clip(shot, "%s/%s" % [dir, id])
		else:
			# A test frame early in the walk and one later on, to judge the framing and the walk.
			_start_walk(shot)
			await tool.call("wait_frames", 20)
			_bare()
			tool.call("_shot", "%s/%s_a.png" % [dir, id])
			await tool.call("wait_frames", 45)
			_bare()
			tool.call("_shot", "%s/%s_b.png" % [dir, id])
			if shot.has("zoom_to") or shot.has("tilt_to") or shot.has("pitch_to"):
				view.rig.distance = float(shot.get("zoom_to", view.rig.distance))
				view.rig.horizon = float(shot.get("tilt_to", view.rig.horizon))
				view.rig.horizon_shown = view.rig.horizon
				view.rig.shot_pitch = float(shot.get("pitch_to", view.rig.shot_pitch))
				await tool.call("wait_frames", 20)
				tool.call("_shot", "%s/%s_c.png" % [dir, id])


## The place with the party in it, as the game shows it.
func _build(shot: Dictionary) -> void:
	var d := _weather.duplicate(true)
	if shot.has("weather"):
		for c: String in d["climates"]:
			d["climates"][c] = {str(shot["weather"]): 1}
	Weather.use(d)
	if view != null:
		view.queue_free()
		view = null
	GameState.reset()
	for pid: String in PARTY:
		var ch := Pregens.build(pid, 7)
		ch.finish_long_rest()
		GameState.story.party.append(ch)
	var st := GameState.story
	st.minute_of_day = int(shot.get("hour", 12)) * 60
	var loc_id := str(shot["loc"])
	var spawn := "default"
	if shot.has("at"):
		var at := shot["at"] as Array
		st.location = loc_id
		st.visited[loc_id] = true
		for b in BESIDE:
			st.positions.append(Vector2i(int(at[0]), int(at[1])) + b)
		spawn = ""
	view = LocationView.create(loc_id, st, Narrator.new(), Dice.roller, spawn)
	view.input_locked = true
	add_child(view)
	view.update_daylight()
	view.atmosphere.settle()
	var zoom := float(shot.get("zoom", 13.0))
	view.rig.zoom_max = maxf(view.rig.zoom_max, maxf(zoom, float(shot.get("zoom_to", zoom))))
	view.rig.distance = zoom
	view.rig.rotate_step(int(shot.get("turns", 0)))
	view.rig.horizon = float(shot.get("tilt", 0.0))
	view.rig.horizon_shown = view.rig.horizon
	view.rig.shot_pitch = float(shot.get("pitch", 0.0))
	view.rig.snap_to_target()
	if str(shot.get("face", "")) == "castle":
		_face_castle(loc_id)
	if shot.has("look"):
		var mid := Vector3(view.grid.width / 2.0, 0, view.grid.depth / 2.0)
		if shot["look"] is Array:
			var c := shot["look"] as Array
			mid = view.board.cell_center(Vector2i(int(c[0]), int(c[1])))
		view.rig.follow = null
		view.rig.global_position = mid
		view.rig.snap_to_target()


## Sets the party walking, if the shot says so (sneaking with "sneak").
func _start_walk(shot: Dictionary) -> void:
	var lead := view.leader()
	if bool(shot.get("sneak", false)):
		view.set_sneaking(true)
	if shot.has("walk"):
		var to := shot["walk"] as Array
		view.walk_to(Vector2i(int(to[0]), int(to[1])) if bool(shot.get("lane", false)) else
			_open_near(Vector2i(int(to[0]), int(to[1]))))
	elif shot.has("walk_by"):
		var by := shot["walk_by"] as Array
		var g := view.rig.ground_basis()
		var right := Vector2(g[1].x, g[1].z)
		var fwd := Vector2(g[0].x, g[0].z)
		var off := right * float(by[0]) + fwd * float(by[1])
		view.walk_to(_open_near(lead.cell + Vector2i(roundi(off.x), roundi(off.y))))


## Records the clip: the party walks if the shot says so, the camera eases from its start to its end, and every frame
## is kept (with --fixed-fps 30, one frame is a thirtieth of a second however long it takes to draw).
func _clip(shot: Dictionary, dir: String) -> void:
	DirAccess.make_dir_recursive_absolute(dir)
	_start_walk(shot)
	var frames := int(float(shot["seconds"]) * 30.0)
	print("segment %s %d %d %d" % [dir.get_file(), 0, Engine.get_process_frames() + 1, frames])
	var z0 := view.rig.distance
	var z1 := float(shot.get("zoom_to", z0))
	var h0 := view.rig.horizon
	var h1 := float(shot.get("tilt_to", h0))
	var p0 := float(shot.get("pitch", 0.0))
	var p1 := float(shot.get("pitch_to", p0))
	var strikes: Array[int] = []
	for at: Variant in shot.get("strikes", []):
		strikes.append(int(float(at) * 30.0))
	var from := view.rig.global_position
	var slide := Vector3.ZERO
	if shot.has("drift"):
		var by := shot["drift"] as Array
		var g := view.rig.ground_basis()
		slide = g[1] * float(by[0]) + g[0] * float(by[1])
		view.rig.follow = null
	var lane := bool(shot.get("lane", false))
	if lane:
		_focus = Node3D.new()
		add_child(_focus)
		_focus.global_position = _party_middle()
		view.rig.follow = _focus
		view.rig.snap_to_target()
	for i in frames:
		if lane:
			_focus.global_position = _party_middle()
			view.rig.snap_to_target()
		if i in strikes:
			view.atmosphere.strike(true)
		var k := smoothstep(0.0, 1.0, float(i) / float(maxi(frames - 1, 1)))
		view.rig.distance = lerpf(z0, z1, k)
		view.rig.horizon = lerpf(h0, h1, k)
		view.rig.horizon_shown = view.rig.horizon
		view.rig.shot_pitch = lerpf(p0, p1, k)
		if shot.has("drift"):
			view.rig.global_position = from + slide * k
		_bare()
		await get_tree().process_frame
		get_viewport().get_texture().get_image().save_jpg("%s/f%04d.jpg" % [dir, i], 0.93)
	print("capture: %s (%d frames)" % [dir, frames])


## No rings, bars or names under anyone: the walks show as they are.
func _bare() -> void:
	for tok: Node in view.find_children("*", "", true, false):
		if not tok is CombatToken:
			continue
		for part: String in ["_ring", "_active_ring", "_bar_back", "_bar_fill", "_label"]:
			var n: Variant = tok.get(part)
			if n is Node3D:
				(n as Node3D).scale = Vector3.ZERO
		# Godrick's Aura of Protection draws its ring round the party even while they walk.
		for c: Node in tok.get_children():
			if c is Label3D or c.name == "Aura":
				(c as Node3D).scale = Vector3.ZERO


## The nearest square to `cell` the party can stand on.
func _open_near(cell: Vector2i) -> Vector2i:
	for r in 6:
		for dx in range(-r, r + 1):
			for dy in range(-r, r + 1):
				var c := cell + Vector2i(dx, dy)
				if view.grid.in_bounds(c) and not view.grid.is_solid(c):
					return c
	return cell


## Turns the camera the quarter turns that best face Castle Ravenloft from this place (as land_capture does).
func _face_castle(loc_id: String) -> void:
	var here: Variant = Vista.place_at(loc_id)
	var castle := (Vista.config().get("castle", {}) as Dictionary).get("at", [0.5, 0.5]) as Array
	if here == null:
		return
	var want := (Vector2(float(castle[0]), float(castle[1])) - (here as Vector2)).normalized()
	var best := 0
	var best_dot := -2.0
	for k in 4:
		var fwd := view.rig.ground_basis()[0]
		var d := Vector2(fwd.x, fwd.z).dot(want)
		if d > best_dot:
			best_dot = d
			best = k
		view.rig.rotate_step(1)
		view.rig.snap_to_target()
	view.rig.rotate_step(best)
	view.rig.snap_to_target()


## The middle of the party's figures, a little up: what a montage shot's camera holds on.
func _party_middle() -> Vector3:
	var mid := Vector3.ZERO
	var n := 0
	for tok: Node in view.find_children("*", "", true, false):
		if tok is CombatToken and (tok as CombatToken).combatant in view.members:
			mid += (tok as Node3D).global_position
			n += 1
	return mid / maxf(n, 1) + Vector3(0, 0.3, 0)


## A montage shot's start and end: the clear lane of `steps` squares to the camera's right (with a square clear on
## each side, and room behind for the party's formation) nearest "near" or the place's middle.
func _lane(shot: Dictionary) -> Dictionary:
	# Along the grid's east (toward the camera's right and front, so their faces show), the same way in every place, so
	# the party walks the same way on screen; long straight runs that way are what roads and streets give.
	var dir := Vector2i(int((shot.get("dir", [1, 0]) as Array)[0]), int((shot.get("dir", [1, 0]) as Array)[1]))
	var steps := int(shot.get("steps", 12))
	var near := Vector2i(view.grid.width / 2, view.grid.depth / 2)
	if shot.has("near"):
		near = Vector2i(int((shot["near"] as Array)[0]), int((shot["near"] as Array)[1]))
	var best := Vector2i(-1, -1)
	var best_d := INF
	for x in view.grid.width:
		for y in view.grid.depth:
			var start := Vector2i(x, y)
			var ok := true
			for k in range(-3, steps + 1):
				var c := start + dir * k
				if not view.grid.in_bounds(c) or view.grid.is_solid(c) or (k > -3 and view.grid.is_cliff(c - dir, c)):
					ok = false
					break
			if ok:
				var d := Vector2(start + dir * (steps / 2) - near).length()
				if d < best_d:
					best_d = d
					best = start
	var out := shot.duplicate()
	if best.x < 0:
		print("site_world: no clear lane of %d squares at %s" % [steps, shot["loc"]])
		return out
	out["at"] = [best.x, best.y]
	var end := best + dir * steps
	out["walk"] = [end.x, end.y]
	out["zoom"] = LANE_ZOOM
	out["pitch"] = LANE_PITCH
	out.erase("zoom_to")
	out.erase("pitch_to")
	print("site_world: lane at %s from %s to %s" % [shot["loc"], best, end])
	return out
