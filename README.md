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
| `media/trailer.mp4`, `media/trailer-poster.jpg` | The trailer and its poster frame. |
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

```bash
python3 tools/capture.py --lane /Volumes/StrahdLanes/CurseOfStrahdGame-site --scene site_game --mode clips
```

```bash
python3 tools/build.py --raw build/raw/stills
```

```bash
python3 tools/make_trailer.py
```

`--only a,b` on a capture runs only those shots. Raw captures and trailer frames go to `build/`, which git ignores.

## Putting it online

Any static host works: GitHub Pages, Netlify, Cloudflare Pages, or an itch.io page for the game. The trailer is the
only large file (about 65 MB). Before it goes public, read the note on the download in the vault's *Showcase Plan*.
