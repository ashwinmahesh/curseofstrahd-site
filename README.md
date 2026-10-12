# Curse of Strahd showcase site

The game's public page: what it is, the features, screenshots, the trailer, the FAQ, the download (coming soon) and
the credits. Plain HTML, CSS and a little JavaScript with no build step, so any static host can serve the folder.

## Open it locally

```bash
python3 -m http.server 8765 --directory ~/Documents/CurseOfStrahdSite
```

Then open http://localhost:8765. (Opening `index.html` straight from Finder works too, apart from the video on some
browsers.)

## What's where

| Path | What it is |
|---|---|
| `index.html` | The page. The gallery and the credits are filled in by `tools/build.py`. |
| `css/site.css`, `js/site.js` | The look (the game's crimson, black and gold) and the small interactions. |
| `media/shots/`, `media/thumbs/` | Screenshots at 1920 wide and 640 wide thumbnails (WebP). |
| `media/companions/` | The six companions' dialogue busts from the game. |
| `media/trailer-v4.mp4`, `media/trailer-v4-poster.jpg` | The trailer and its poster frame (v3 kept for rollback). |
| `tools/godot/` | The capture scenes, copied into a game worktree's `tools/capture/` to run. |
| `tools/capture.py` | Runs a capture scene off screen in a game worktree and stops it if it hangs. |
| `tools/make_trailer.py` | Cuts the trailer from the clips and the storybook art on the music, and encodes it. |
| `tools/encode.swift`, `tools/envelope.swift` | The Mac's own video encoder, and the music's loudness curve for placing cuts. |
| `tools/build.py` | Screenshots from the raw captures, the gallery, the credits from the game's `art/credits.json`. |

## Rebuilding the media

From a game worktree (never the main checkout), with nothing else of yours running in Godot:

```bash
python3 tools/capture.py --lane /Volumes/StrahdLanes/CurseOfStrahdGame-site --scene site_world --mode stills
```

```bash
python3 tools/capture.py --lane /Volumes/StrahdLanes/CurseOfStrahdGame-site --scene site_game --mode stills
```

```bash
python3 tools/capture.py --lane /Volumes/StrahdLanes/CurseOfStrahdGame-site --scene site_world --mode clips
```

The game's clips are recorded with Godot's Movie Maker for their sound (the fights, the voiced conversation and the
Tarokka cutscene's narrator). The lane needs a one-line local change, never committed: in `core/voice_over.gd`'s
`_ensure_player`, skip the `"Dummy"` driver check when `STRAHD_MOVIE_SOUND` is set.

```bash
python3 tools/capture.py --lane /Volumes/StrahdLanes/CurseOfStrahdGame-site --scene site_game --mode clips --movie --env STRAHD_MOVIE_SOUND=1
```

```bash
python3 tools/avi_audio.py build/raw/clips/site_game.avi build/audio/game_movie.wav
```

```bash
/usr/bin/python3 tools/build.py --raw build/raw/stills
```

```bash
/usr/bin/python3 tools/make_trailer.py --status "Available now"
```

`--only a,b` on a capture runs only those shots. Raw captures and trailer frames go to `build/`, which git ignores.
The trailer script needs the Mac's own Python (`/usr/bin/python3`, which still has `audioop` and PIL). To pick new
shots, a survey shoots any places at any hours: `--env SITE_SURVEY=vallaki,krezk --env SITE_HOURS=11,19`, with
`SITE_LOOK=middle`, `SITE_ZOOM` and `SITE_TILT` for a wide view. `tools/godot/site_eva.dialogue` is the trailer's
Tarokka cutscene (Madam Eva's reading's three pictures and lines, without the cards); capture.py copies it into the
lane.

## Online

The site is served by GitHub Pages from this repo's `main` branch at https://curseofstrahd.app (the `CNAME` file holds
the domain; `.nojekyll` serves the files as they are). Pushing to `main` publishes. The download section stays
"coming soon" until the download question in the vault's *Showcase Plan* is settled.
