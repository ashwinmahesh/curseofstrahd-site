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
| `privacy/index.html`, `css/privacy.css` | iPhone/iPad privacy policy at `/privacy/`; standalone, responsive, and readable without JavaScript or external fonts. |
| `css/site.css`, `js/site.js` | The look (the game's crimson, black and gold) and the small interactions. |
| `media/shots/`, `media/thumbs/` | Screenshots at 1920 wide and 640 wide thumbnails (WebP). |
| `media/companions/` | The six companions' dialogue busts from the game. |
| `media/trailer-v5.mp4`, `media/trailer-v5-poster.jpg` | The trailer (90 s, 1080p at 5.5 Mbps) and its poster frame (v4 and v3 kept for rollback). |
| `tools/godot/` | The capture scenes, copied into a game worktree's `tools/capture/` to run. |
| `tools/capture.py` | Runs a capture scene off screen in a game worktree and stops it if it hangs. |
| `tools/make_trailer.py` | Cuts the older trailers (v1 to v4) from the clips and the storybook art on the music, and encodes them. |
| `tools/make_trailer_v5.py`, `tools/godot/trailer_world.gd`, `trailer_game.gd` | Trailer v5 (2026-10-28): the capture scenes for its shots with the party of Godrick, Ratatouille, Kip and Liriel, and the cut, with the music at one level throughout and Strahd's lines on its quiet passages. The plan is the vault note *Trailer v5 Plan - 2026-10-28*. |
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
the domain; `.nojekyll` serves the files as they are). Pushing to `main` publishes. The downloads live on
Cloudflare R2 at https://downloads.curseofstrahd.app, published by the game repo's `release.yml`; the vault note
*Website Handoff* has the release routine (`tools/switch_release.py`, `tools/publish_latest.sh`) and the web wiki's
(`tools/build_wiki.py`, `tools/wiki_check.py`).

## Privacy policy maintenance

The canonical policy URL is `https://curseofstrahd.app/privacy/`. It covers local game data, optional save/report
sharing, Apple and TestFlight diagnostics, website hosting, retention and deletion. The home, trailer, releases
and wiki landing pages link to it; the wiki generator includes it in newly rendered pages. `tools/build.py` keeps
its shared stylesheet URL current. Check the policy against the game's implementation when data practices change,
and update its effective date and sitemap entry. Do not describe TestFlight as collecting no data.

The October 17 policy was checked against the iOS branch's `core/save_system.gd`, `core/error_watch.gd`,
`core/save_transfer.gd`, `ui/common/mobile_native.gd` and `tools/native_ios/strahd_ios.mm` at game commit
`1d88d21f3eb935cd89d15ac54a629d1188f60d71`, plus the site's hosting and font requests. Public contact uses the same
GitHub issue tracker as the app's support listing, with an explicit warning against posting personal data.

After deployment, verify this URL returns the policy before assigning it in App Store Connect. Apple's
[review guidelines, section 5.1.1](https://developer.apple.com/app-store/review/guidelines/#data-collection-and-storage)
also require access to the policy inside the app; publishing this website page alone does not satisfy that step.
