# Building OMD Map Builder

Everything runs on Windows with the game installed from Steam.

## 1. Folder layout

`build_exe.py` and the app expect this layout in your Documents folder:

```
Documents\Claud OMD\
  tools\
    exe_src\      <- app\ from this repo
    mapbuild\     <- builder\ from this repo, plus navbuild.exe, navtool.exe, repak.exe
    base\         <- files taken from your own game install (step 3)
    retoc.exe
  notes\          (logs)
```

## 2. Tools

| Tool | Where from | Goes in |
|---|---|---|
| Python 3.9+ with PyInstaller | `pip install pyinstaller` | |
| `retoc.exe` | [github.com/trumank/retoc](https://github.com/trumank/retoc) releases | `tools\` |
| `repak.exe` | [github.com/trumank/repak](https://github.com/trumank/repak) releases | `tools\mapbuild\` |
| `navbuild.exe` | Build `navmesh/navbuild.cpp` against [Recast](https://github.com/recastnavigation/recastnavigation) | `tools\mapbuild\` |
| `navtool.exe` | Build `navmesh/navtool.cpp` against NavWeakness from [NavKit](https://github.com/glacier-modding/NavKit). In NavWeakness, `isKnt()` has to accept graph version `0x2E` as well as `0x30` | `tools\mapbuild\` |
| UE4SS | [github.com/UE4SS-RE/RE-UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) | the game's `OMDD\Binaries\Win64\` (needed to play, not to build) |

## 3. Base files from the game

The builder edits copies of a few of the game's own levels. These files are not in this repo. Extract them from
your own install with retoc (`retoc to-legacy` on `OMDD\Content\Paks`) and put them in `tools\base\`:

- `/Game/Levels/BaseGame/Castle/CastlePlaza/`: `Level_Castle_CastlePlaza` (.umap/.uexp),
  `Level_Castle_CastlePlaza_Lighting` (.umap/.uexp), `Level_Castle_CastlePlaza_MapData` (.uasset/.uexp),
  `MD_Castle_CastlePlaza` (.uasset/.uexp)
- `Level_Castle_Colosseum` and `Level_Castle_Colosseum_MapData`
- `Level_Gardens_Arboretum`, `Level_Gardens_Arboretum_MapData` and `BP_Onslaught_Gardens_Arboretum`
- `AssetRegistry.bin` (the game's asset registry)
- `geo_template` (.umap/.uexp) and `tile_template` (.uasset/.uexp): the empty geometry level and tile asset the
  builder fills in

The full list is in `app/build_exe.py`.

## 4. Build the exe

```
python tools\exe_src\build_exe.py
```

The result is `Documents\Claud OMD\OMD Map Builder.exe`. Its log is `notes\build_exe.txt`.

## 5. Making changes

- **Map Maker:** edit `app/mapmaker.html`. It's one self-contained page, so you can also open it straight in a browser.
- **How maps are built:** `app/builder.py` drives it; `builder/mapv2.py` turns a map into a build plan
  (floors, walls, routes, spawns).
- **Mods:** each mod is a UE4SS Lua script under `mods/`. The Python scripts next to them made the mods' game files.

`docs/AI guide - how it all works.md` explains the whole pipeline.
