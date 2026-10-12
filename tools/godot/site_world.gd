extends Node3D
## The showcase site's world shots (~/Documents/CurseOfStrahdSite; not part of the game): places from the game's own
## camera with the party standing or walking in them, no HUD, the Modern look on the High preset. Stills are PNGs;
## clips (SITE_MODE=clips, run with --fixed-fps 30 --motion) are numbered JPEGs, one per frame, for the trailer.
##   tools/godot --path . [--fixed-fps 30] res://tools/capture/capture.tscn -- --scene=res://tools/capture/site_world.tscn
##     --out=<dir>/w --frames=10 --size=1920x1080 [--motion]
## Environment: SITE_MODE=stills|clips, SITE_ONLY=village_night,castle_vista (default: every shot of the mode).
## Settings, saves and What's new use files of this run's own (removed at the end), never the player's.

const PARTY: Array[String] = ["godrick_pendlebrook", "liriel_dawnsong", "thistle", "ratatoille"]
const BESIDE: Array[Vector2i] = [Vector2i.ZERO, Vector2i(1, 0), Vector2i(0, 1), Vector2i(1, 1)]

## Each still: the place, the hour, the weather, where the party stands (else the place's spawn), the camera's
## distance, quarter turns and tilt toward the horizon, "face": "castle" to turn toward Castle Ravenloft, and "look"
## ([x, z] or "middle") to hold the camera over a square instead of the party.
## The 1.0.7 look (owner, 2026-10-12: "highlight the new aesthetics", "a lot of the different regions"): each region's
## own hue, weather, ground, trees and landmarks, seen wide like a diorama, and each indoor place's own light.
const W := {"look": "middle", "zoom": 26.0, "tilt": 0.4}
const IN := {"look": "middle", "zoom": 22.0, "hour": 20}
var STILLS := {
	# Outdoors, one or two a region.
	"village_day": W.merged({"loc": "village_of_barovia", "hour": 11, "weather": "overcast"}),
	"village_night": W.merged({"loc": "village_of_barovia", "hour": 21, "weather": "fog", "zoom": 22.0}),
	"road_dusk": {"loc": "into_the_mists_road", "hour": 17, "weather": "fog", "at": [12, 15], "zoom": 17.0},
	"castle_vista": {"loc": "village_of_barovia", "hour": 11, "weather": "overcast", "zoom": 30.0, "tilt": 1.0,
		"face": "castle"},
	"tser_pool_camp": W.merged({"loc": "tser_pool", "hour": 17, "weather": "overcast"}),
	"tser_pool_night": {"loc": "tser_pool", "hour": 21, "weather": "overcast", "at": [24, 16], "zoom": 19.0},
	"vallaki_noon": W.merged({"loc": "vallaki", "hour": 11, "weather": "overcast"}),
	"vallaki_rain": W.merged({"loc": "vallaki", "hour": 19, "weather": "rain", "zoom": 24.0}),
	"wizard_of_wines": W.merged({"loc": "wizard_of_wines", "hour": 17, "weather": "rain"}),
	"krezk_snow": W.merged({"loc": "krezk", "hour": 12, "weather": "snow"}),
	"abbey_snow": W.merged({"loc": "abbey_of_st_markovia", "hour": 18, "weather": "snow"}),
	"argynvostholt": W.merged({"loc": "argynvostholt", "hour": 11, "weather": "overcast"}),
	"bonegrinder_heath": W.merged({"loc": "old_bonegrinder_hill", "hour": 11, "weather": "overcast"}),
	"lake_rain": W.merged({"loc": "lake_zarovich", "hour": 11, "weather": "rain"}),
	"berez_marsh": W.merged({"loc": "berez", "hour": 11, "weather": "fog", "zoom": 22.0}),
	"yester_hill": W.merged({"loc": "yester_hill", "hour": 17, "weather": "overcast"}),
	"castle_gates": W.merged({"loc": "castle_ravenloft_gates", "hour": 12, "weather": "storm"}),
	# Indoors, each with its own light.
	"death_house": {"loc": "death_house_ground", "at": [13, 8], "zoom": 12.0},
	"death_house_hall": IN.merged({"loc": "death_house_ground"}),
	"st_andrals": IN.merged({"loc": "vallaki_st_andrals"}),
	"blue_water_inn": IN.merged({"loc": "vallaki_blue_water_inn"}),
	"argynvostholt_hall": IN.merged({"loc": "argynvostholt_hall"}),
	"marsh_hut": IN.merged({"loc": "berez_baba_lysagas_hut", "zoom": 18.0}),
	"guard_tower": IN.merged({"loc": "tsolenka_pass_guard_tower"}),
	"toy_shop": IN.merged({"loc": "vallaki_blinsky_toys", "zoom": 18.0}),
	"village_church": IN.merged({"loc": "village_church"}),
}

## Each clip: a still's set-up, how many seconds it runs, where the party walks ("walk", a square), and the camera's
## move over the clip: "zoom_to", "tilt_to" (toward the horizon), "pitch" and "pitch_to" (degrees flatter than the play
## view), and "drift" (squares the camera slides along its right and forward). "strikes": seconds at which lightning
## strikes.
var CLIPS := {
	# The trailer's places (1.0.7: every region in its own look, owner 2026-10-12), most seen wide with the camera
	# drifting over them, and two rooms indoors.
	"road": {"loc": "into_the_mists_road", "hour": 17, "weather": "fog", "at": [8, 15], "zoom": 15.0, "seconds": 6.0,
		"walk": [16, 15], "zoom_to": 17.0},
	"village": W.merged({"loc": "village_of_barovia", "hour": 11, "weather": "overcast", "zoom": 28.0, "seconds": 5.0,
		"zoom_to": 23.0, "drift": [2.0, 0.0]}),
	"tser": W.merged({"loc": "tser_pool", "hour": 17, "weather": "overcast", "zoom": 28.0, "seconds": 5.0,
		"zoom_to": 23.0, "drift": [1.5, 0.0]}),
	"krezk": W.merged({"loc": "krezk", "hour": 12, "weather": "snow", "zoom": 28.0, "seconds": 5.0, "zoom_to": 23.0,
		"drift": [-1.5, 0.0]}),
	"vallaki": W.merged({"loc": "vallaki", "hour": 19, "weather": "rain", "zoom": 26.0, "seconds": 5.0, "zoom_to": 21.0,
		"drift": [1.5, 0.0], "strikes": [2.2]}),
	"winery": W.merged({"loc": "wizard_of_wines", "hour": 17, "weather": "rain", "zoom": 28.0, "seconds": 5.0,
		"zoom_to": 23.0, "drift": [1.5, 0.0]}),
	"berez": W.merged({"loc": "berez", "hour": 11, "weather": "fog", "zoom": 25.0, "seconds": 5.0, "zoom_to": 20.0,
		"drift": [-1.5, 0.0]}),
	"argynvostholt": W.merged({"loc": "argynvostholt", "hour": 11, "weather": "overcast", "zoom": 28.0, "seconds": 5.0,
		"zoom_to": 23.0, "drift": [1.5, 0.0]}),
	"bonegrinder": W.merged({"loc": "old_bonegrinder_hill", "hour": 11, "weather": "overcast", "zoom": 28.0,
		"seconds": 5.0, "zoom_to": 23.0, "drift": [1.5, 0.0]}),
	"abbey": W.merged({"loc": "abbey_of_st_markovia", "hour": 18, "weather": "snow", "zoom": 28.0, "seconds": 5.0,
		"zoom_to": 23.0, "drift": [-1.5, 0.0]}),
	"castle": {"loc": "village_of_barovia", "hour": 15, "weather": "overcast", "zoom": 14.0, "seconds": 8.0,
		"face": "castle", "zoom_to": 30.0, "tilt_to": 1.0},
	"gates": {"loc": "castle_ravenloft_gates", "hour": 23, "weather": "storm", "at": [19, 31], "zoom": 16.0,
		"seconds": 5.0, "walk_by": [0, -4], "zoom_to": 13.0},
	"gates_day": W.merged({"loc": "castle_ravenloft_gates", "hour": 12, "weather": "storm", "zoom": 28.0,
		"seconds": 5.0, "zoom_to": 22.0, "strikes": [1.5]}),
	# Interiors, each in its own light (owner's ask: the rooms' mood and lighting).
	"interior_death_house": IN.merged({"loc": "death_house_ground", "seconds": 5.0, "zoom_to": 16.0, "pitch_to": 6.0}),
	"interior_inn": IN.merged({"loc": "vallaki_blue_water_inn", "seconds": 5.0, "zoom_to": 16.0, "pitch_to": 6.0}),
	"interior_church": IN.merged({"loc": "vallaki_st_andrals", "seconds": 5.0, "zoom_to": 16.0, "pitch_to": 6.0}),
	"interior_hall": IN.merged({"loc": "argynvostholt_hall", "seconds": 5.0, "zoom_to": 16.0, "pitch_to": 6.0}),
	# Short loops for GIFs (owner, 2026-10-09): firelight and heat shimmer, a lightning strike in the rain, footsteps
	# kicking up snow and splashes.
	"gif_fire": {"loc": "tser_pool", "hour": 21, "weather": "overcast", "at": [24, 16], "zoom": 9.0, "seconds": 4.0},
	"gif_lightning": {"loc": "vallaki", "hour": 20, "weather": "rain", "zoom": 14.0, "seconds": 4.0, "strike_at": 1.0},
	"gif_snow_steps": {"loc": "krezk", "hour": 12, "weather": "snow", "at": [14, 7], "zoom": 8.0, "seconds": 4.0,
		"walk_by": [-4, 3]},
	"gif_splash_steps": {"loc": "vallaki", "hour": 19, "weather": "rain", "zoom": 8.0, "seconds": 4.0, "walk_by": [4, -2]},
	# Cinematic loops (owner, 2026-10-09: "more cinematic", each showing off one of the game's visuals): the party stands
	# and the camera moves slowly.
	"loop_castle": {"loc": "village_of_barovia", "hour": 18, "weather": "storm", "zoom": 14.0, "seconds": 7.0,
		"face": "castle", "zoom_to": 30.0, "tilt_to": 1.0, "strikes": [5.3]},
	"loop_storm": {"loc": "vallaki", "hour": 21, "weather": "rain", "zoom": 12.5, "zoom_to": 10.0, "pitch_to": 8.0,
		"drift": [1.5, 0.0], "seconds": 5.0, "strikes": [1.3]},
	"loop_sunbeams": {"loc": "into_the_mists_road", "hour": 18, "weather": "fog", "at": [12, 15], "zoom": 13.0,
		"zoom_to": 11.0, "pitch_to": 6.0, "drift": [-2.5, 0.5], "seconds": 6.0},
	"loop_inn": {"loc": "vallaki_blue_water_inn", "hour": 20, "zoom": 12.0, "zoom_to": 9.5, "pitch_to": 8.0,
		"seconds": 5.0},
}

var view: LocationView = null
var _weather: Dictionary = {}
var _own := ""


func _ready() -> void:
	_own = "user://capture_site_%d" % OS.get_process_id()
	GameSettings.path = _own + "_settings.cfg"
	WhatsNew.seen_path = _own + "_whats_new.cfg"
	InputActions.ensure()
	Look.set_style("modern", false)
	Graphics.set_preset("high", false)
	_weather = Weather.data().duplicate(true)


func _exit_tree() -> void:
	for f: String in [GameSettings.path, WhatsNew.seen_path]:
		if FileAccess.file_exists(f):
			DirAccess.remove_absolute(f)


func capture_shots(tool: Node, out: String) -> void:
	var clips := OS.get_environment("SITE_MODE") == "clips"
	var only := OS.get_environment("SITE_ONLY").split(",", false)
	var list: Dictionary = CLIPS if clips else STILLS
	# A survey (SITE_SURVEY=vallaki,krezk SITE_HOURS=11,18 [SITE_ZOOM=15] [SITE_WEATHER=rain]): each place at its own
	# spawn at each hour, to pick shots from (survey_<place>_<hour>.png).
	var survey := OS.get_environment("SITE_SURVEY").split(",", false)
	if not survey.is_empty():
		list = {}
		var hours := OS.get_environment("SITE_HOURS").split(",", false)
		if hours.is_empty():
			hours = PackedStringArray(["11"])
		for loc: String in survey:
			for h: String in hours:
				var s := {"loc": loc, "hour": int(h), "zoom": float(OS.get_environment("SITE_ZOOM")) if OS.get_environment("SITE_ZOOM") != "" else 15.0}
				if OS.get_environment("SITE_WEATHER") != "":
					s["weather"] = OS.get_environment("SITE_WEATHER")
				if OS.get_environment("SITE_LOOK") != "":
					s["look"] = OS.get_environment("SITE_LOOK")
				if OS.get_environment("SITE_TILT") != "":
					s["tilt"] = float(OS.get_environment("SITE_TILT"))
				list["survey_%s_%02d" % [loc, int(h)]] = s
		only = PackedStringArray()
	for id: String in list:
		if not only.is_empty() and not id in only:
			continue
		var shot := list[id] as Dictionary
		_build(shot)
		await tool.call("wait_frames", 50 if not clips else 20)
		if clips:
			await _clip(shot, "%s/%s" % [out.get_base_dir(), id])
		else:
			await tool.call("wait_frames", 10)
			tool.call("_shot", "%s/%s.png" % [out.get_base_dir(), id])


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
		var ch := Pregens.build(pid, 5)
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
	view.rig.snap_to_target()
	if str(shot.get("face", "")) == "castle":
		_face_castle(loc_id)
	# "look": [x, z] holds the camera over that square instead of the party ("look": "middle" for the map's middle),
	# for a wider view of a town or a camp with the party somewhere in it.
	if shot.has("look"):
		var mid := Vector3(view.grid.width / 2.0, 0, view.grid.depth / 2.0)
		if shot["look"] is Array:
			var c := shot["look"] as Array
			mid = view.board.cell_center(Vector2i(int(c[0]), int(c[1])))
		view.rig.follow = null
		view.rig.global_position = mid
		view.rig.snap_to_target()


## Records the clip: the party walks if the shot says so, the camera eases from its start to its end, and every frame
## is kept (with --fixed-fps 30, one frame is a thirtieth of a second however long it takes to draw).
func _clip(shot: Dictionary, dir: String) -> void:
	DirAccess.make_dir_recursive_absolute(dir)
	var lead := view.leader()
	if shot.has("walk"):
		var to := shot["walk"] as Array
		view.walk_to(Vector2i(int(to[0]), int(to[1])))
	elif shot.has("walk_by"):
		var by := shot["walk_by"] as Array
		view.walk_to(_open_near(lead.cell + Vector2i(int(by[0]), int(by[1]))))
	var frames := int(float(shot["seconds"]) * 30.0)
	print("segment %s %d %d %d" % [dir.get_file(), 0, Engine.get_process_frames() + 1, frames])
	var z0 := view.rig.distance
	var z1 := float(shot.get("zoom_to", z0))
	var h0 := view.rig.horizon
	var h1 := float(shot.get("tilt_to", h0))
	var p0 := float(shot.get("pitch", 0.0))
	var p1 := float(shot.get("pitch_to", p0))
	var strikes: Array[int] = []
	for at: Variant in shot.get("strikes", [shot.get("strike_at", -1.0)]):
		strikes.append(int(float(at) * 30.0))
	var from := view.rig.global_position
	var slide := Vector3.ZERO
	if shot.has("drift"):
		var by := shot["drift"] as Array
		var g := view.rig.ground_basis()
		slide = g[1] * float(by[0]) + g[0] * float(by[1])
		view.rig.follow = null
	for i in frames:
		if i in strikes:
			view.atmosphere.strike(true)
		var k := smoothstep(0.0, 1.0, float(i) / float(maxi(frames - 1, 1)))
		view.rig.distance = lerpf(z0, z1, k)
		view.rig.horizon = lerpf(h0, h1, k)
		view.rig.horizon_shown = view.rig.horizon
		view.rig.shot_pitch = lerpf(p0, p1, k)
		if shot.has("drift"):
			view.rig.global_position = from + slide * k
		await get_tree().process_frame
		get_viewport().get_texture().get_image().save_jpg("%s/f%04d.jpg" % [dir, i], 0.93)
	print("capture: %s (%d frames)" % [dir, frames])


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
