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
## distance, quarter turns and tilt toward the horizon, and "face": "castle" to turn toward Castle Ravenloft.
const STILLS := {
	"village_night": {"loc": "village_of_barovia", "hour": 22, "weather": "fog", "zoom": 13.0},
	"vallaki_rain": {"loc": "vallaki", "hour": 18, "weather": "rain", "zoom": 14.0},
	"road_dusk": {"loc": "into_the_mists_road", "hour": 18, "weather": "fog", "at": [12, 15], "zoom": 12.0},
	"castle_vista": {"loc": "village_of_barovia", "hour": 18, "weather": "overcast", "zoom": 30.0, "tilt": 1.0,
		"face": "castle"},
	"krezk_snow": {"loc": "krezk", "hour": 12, "weather": "snow", "at": [14, 7], "zoom": 13.0},
	"death_house": {"loc": "death_house_ground", "at": [13, 8], "zoom": 12.0},
	"tser_pool_night": {"loc": "tser_pool", "hour": 21, "weather": "overcast", "at": [24, 16], "zoom": 14.0},
	"castle_gates": {"loc": "castle_ravenloft_gates", "hour": 23, "weather": "storm", "at": [19, 29], "zoom": 15.0},
	"road_castle": {"loc": "into_the_mists_road", "hour": 17, "weather": "overcast", "at": [12, 15], "zoom": 30.0,
		"tilt": 1.0, "face": "castle"},
}

## Each clip: a still's set-up, how many seconds it runs, where the party walks ("walk", a square), and the camera's
## move over the clip: "zoom_to", "tilt_to" (toward the horizon), and "drift" (squares the camera slides, x and z).
const CLIPS := {
	"road": {"loc": "into_the_mists_road", "hour": 18, "weather": "fog", "at": [8, 15], "zoom": 11.0, "seconds": 6.0,
		"walk": [16, 15], "zoom_to": 13.0},
	"village": {"loc": "village_of_barovia", "hour": 22, "weather": "fog", "zoom": 14.0, "seconds": 6.0,
		"walk_by": [-5, 3], "zoom_to": 12.0},
	"vallaki": {"loc": "vallaki", "hour": 18, "weather": "rain", "zoom": 13.0, "seconds": 5.0, "walk_by": [5, -2],
		"zoom_to": 12.0},
	"krezk": {"loc": "krezk", "hour": 12, "weather": "snow", "at": [14, 7], "zoom": 10.0, "seconds": 5.0,
		"walk_by": [-4, 4], "zoom_to": 12.0},
	"castle": {"loc": "village_of_barovia", "hour": 18, "weather": "overcast", "zoom": 14.0, "seconds": 8.0,
		"face": "castle", "zoom_to": 30.0, "tilt_to": 1.0},
	"tser": {"loc": "tser_pool", "hour": 21, "weather": "overcast", "at": [22, 18], "zoom": 13.0, "seconds": 5.0,
		"walk_by": [3, -3], "zoom_to": 15.0},
	"gates": {"loc": "castle_ravenloft_gates", "hour": 23, "weather": "storm", "at": [19, 31], "zoom": 16.0,
		"seconds": 5.0, "walk_by": [0, -4], "zoom_to": 13.0},
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
	var z0 := view.rig.distance
	var z1 := float(shot.get("zoom_to", z0))
	var h0 := view.rig.horizon
	var h1 := float(shot.get("tilt_to", h0))
	for i in frames:
		var k := smoothstep(0.0, 1.0, float(i) / float(maxi(frames - 1, 1)))
		view.rig.distance = lerpf(z0, z1, k)
		view.rig.horizon = lerpf(h0, h1, k)
		view.rig.horizon_shown = view.rig.horizon
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
