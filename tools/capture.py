#!/usr/bin/env python3
"""Runs the site's capture scenes in a game worktree, off screen, and stops them if they hang.

  python3 tools/capture.py --lane /Volumes/StrahdLanes/CurseOfStrahdGame-site --scene site_world --mode stills
      [--only village_night,castle_vista] [--out build/raw] [--timeout 900]

Copies tools/godot/<scene>.gd/.tscn into the lane's tools/capture/ first (they stay untracked there), then runs the
game's own capture tool through the lane's tools/godot, so the window never takes focus and stays off screen. Stills
run at the normal frame cap; clips run with --fixed-fps 30 and --motion, so every frame is a thirtieth of a second
however long it takes to draw. The run is stopped by its own process id if it prints nothing for --quiet seconds, runs
past --timeout, or prints a SCRIPT ERROR and then stalls (a script error before quit leaves Godot idling).
"""
import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent


def main() -> int:
	ap = argparse.ArgumentParser()
	ap.add_argument("--lane", type=Path, required=True)
	ap.add_argument("--scene", required=True, help="site_world, site_game, or any tools/capture scene name")
	ap.add_argument("--mode", choices=["stills", "clips"], default="stills")
	ap.add_argument("--only", default="")
	ap.add_argument("--out", type=Path, default=SITE / "build/raw")
	ap.add_argument("--size", default="1920x1080")
	ap.add_argument("--timeout", type=int, default=1200)
	ap.add_argument("--quiet", type=int, default=240)
	ap.add_argument("--env", action="append", default=[], help="KEY=VALUE for the scene")
	ap.add_argument("--movie", action="store_true",
		help="clips only: also record the game's sound with Godot's Movie Maker (<out>/clips/<scene>.avi); the scene "
		"prints each clip's first and last frame so tools/make_trailer.py can cut the sound to match")
	args = ap.parse_args()

	src = SITE / "tools/godot"
	for ext in (".gd", ".tscn"):
		f = src / (args.scene + ext)
		if f.exists():
			shutil.copy(f, args.lane / "tools/capture" / f.name)
	out = (args.out / args.mode).resolve()
	out.mkdir(parents=True, exist_ok=True)
	godot_args = ["tools/godot", "--path", ".", "--resolution", "1x1", "--position", "100000,100000",
		"--audio-driver", "Dummy"]
	godot_args += ["--fixed-fps", "30"] if args.mode == "clips" else ["--max-fps", "60"]
	godot_args += ["res://tools/capture/capture.tscn", "--", "--scene=res://tools/capture/%s.tscn" % args.scene,
		"--out=%s/%s" % (out, args.scene), "--frames=10", "--size=%s" % args.size]
	if args.mode == "clips":
		godot_args.append("--motion")
	if args.movie:
		# Godot's own option goes before the "--" that starts the scene's arguments. The movie takes the window's size
		# at start, so the (still off-screen) window opens at the capture size.
		cut = godot_args.index("--")
		godot_args[cut:cut] = ["--write-movie", str(out / ("%s.avi" % args.scene))]
		godot_args[godot_args.index("1x1")] = args.size
	env = dict(os.environ, SITE_MODE=args.mode, SITE_ONLY=args.only,
		GODOT=os.environ.get("GODOT", "/Applications/Godot.app/Contents/MacOS/Godot"))
	for kv in args.env:
		k, _, v = kv.partition("=")
		env[k] = v
	log_path = out / ("%s.log" % args.scene)
	log = open(log_path, "w")
	proc = subprocess.Popen(godot_args, cwd=args.lane, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
		stdin=subprocess.DEVNULL, text=True, bufsize=1)
	print("capture: Godot PID %d, log %s" % (proc.pid, log_path), flush=True)
	last = [time.time()]
	errored = [0.0]

	def pump() -> None:
		for line in proc.stdout:
			log.write(line)
			log.flush()
			last[0] = time.time()
			if "SCRIPT ERROR" in line and errored[0] == 0.0:
				errored[0] = time.time()
			if line.startswith("capture:") or line.startswith("site_") or "ERROR" in line:
				print(line.rstrip(), flush=True)

	reader = threading.Thread(target=pump, daemon=True)
	reader.start()
	start = time.time()
	why = ""
	while proc.poll() is None:
		time.sleep(2)
		now = time.time()
		if now - start > args.timeout:
			why = "ran past %d s" % args.timeout
		elif now - last[0] > args.quiet:
			why = "printed nothing for %d s" % args.quiet
		elif errored[0] and now - last[0] > 30:
			why = "stalled after a SCRIPT ERROR"
		if why:
			print("capture: stopping PID %d (%s)" % (proc.pid, why), flush=True)
			proc.send_signal(signal.SIGTERM)
			try:
				proc.wait(10)
			except subprocess.TimeoutExpired:
				proc.kill()
			break
	reader.join(5)
	log.close()
	code = proc.returncode
	print("capture: done in %d s, exit %s%s" % (time.time() - start, code, " (%s)" % why if why else ""), flush=True)
	return 1 if why or errored[0] else 0


if __name__ == "__main__":
	sys.exit(main())
