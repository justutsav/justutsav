# hero scene

`assets/walk.webp` is rendered from these two scripts. Rerun when the project list changes.

```bash
python3 scripts/scene/cards.py                 # billboard screens -> scripts/scene/cards/*.png (needs Chrome)
blender -b --factory-startup -P scripts/scene/walk.py -- anim $PWD/scripts/scene   # 720 frames, ~50 min on an RTX 4060
ffmpeg -framerate 20 -i scripts/scene/frames/f_%04d.png -c:v libwebp_anim -loop 0 -quality 85 -preset picture assets/walk.webp
```

`walk.py -- still <dir> 100,275,450` renders single frames for checking. Frames and card
PNGs are build products; only `assets/walk.webp` is committed.
