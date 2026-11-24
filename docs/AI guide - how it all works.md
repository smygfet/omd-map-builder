# AI guide: how OMD Map Builder and the mods work

For an AI helping someone **develop** this further: fix the app, extend the Map Maker, change how maps are built, or
add mods (traps, game modes). Read "AI guide - making maps.md" first for the map format; this file is the
architecture, where the code is, how to build and test, and the lessons learned.

The game is **Orcs Must Die! Deathtrap** (Unreal Engine 5.3, IoStore paks, Steam). Nothing here uses Unreal Editor:
the app writes cooked game files directly, and runtime behaviour comes from **UE4SS Lua mods**.

---

## 1. The parts

| part | what | source (in this pack: `For your AI\source\`) |
|---|---|---|
| **Map Maker** | single-file HTML/JS grid editor, 2D + 3D view (three.js r128) | `tools\exe_src\mapmaker.html` |
| **OMD Map Builder** | Windows desktop app (Python, tkinter), one-file exe made with PyInstaller | `tools\exe_src\app.py` (UI) + `builder.py` (build/install/mods) |
| **Map builder** | turns a map file into game files | `tools\mapbuild\*.py` (`mapv2.py` is the heart) |
| **Native helpers** | navmesh building, IoStore packing | `tools\mapbuild\navbuild.exe`, `navtool.exe`, `retoc.exe`, `repak.exe` |
| **Base game files** | cooked levels and the asset index the builder patches | `tools\base\` (extracted from the game) |
| **Lua mods** (UE4SS) | VS referee, barricade walls, traps, endless | in the game: `OMDD\Binaries\Win64\Mods\JW*\Scripts\main.lua`; sources also under `tools\mapbuild\*.lua` and `source\mods\` |
| **Trap/mod paks** | new trap assets (trap book items, definitions, icons) | the built paks in the game's `Paks\Mods\zz_JW*`; the scripts that made them in `source\mods\` |
| **Map generators** | Python scripts that write maps | `source\mapgen\` |

## 2. Where things live on a PC

- **Game:** `...\steamapps\common\Orcs Must Die Deathtrap\` (any Steam library; found via `libraryfolders.vdf`).
  - `OMDD\Content\Paks\Mods\`: our paks, all named `zz_JW*`:
    - `zz_JWMaps_P` (.pak/.utoc/.ucas): the custom levels.
    - `zz_JWRegistry_P.pak`: the game's asset index with our missions and trap-book entries added.
    - `zz_JWArcherTrap_P`, `zz_JWTrapBarricade_P` (+ Tags), `zz_JWGiantFlip_P` (+ Tags), `zz_JWEndless_P`: mods.
  - `OMDD\JW_disabled_mods\`: paks of mods switched off in the app (parked here).
  - `OMDD\Binaries\Win64\`: UE4SS (`UE4SS.dll`, `dwmapi.dll`, `UE4SS-settings.ini`) and `Mods\<name>\Scripts\main.lua`
    + `enabled.txt` (on) or `enabled.off` (off). Mod logs: `Binaries\Win64\JW_*.txt`.
- **App data:** `%LOCALAPPDATA%\OMD Map Builder\`:
  - `maps\` (map files; `removed\` = ignored),
  - `settings.json`, `logs\`,
  - `registry_maps.json` (the last build's maps, used to rebuild the index when a mod is switched),
  - `endless_waves.txt`.
- **App:** `%LOCALAPPDATA%\Programs\OMD Map Builder\OMD Map Builder.exe` (installed by the pack).
- **Developer folder** (only where the app is developed): `Documents\Claud OMD\`, with `tools\exe_src`,
  `tools\mapbuild`, `tools\base`, `tools\endless\originals` and `jobs\`. The app looks for this; if it exists, it
  rebuilds itself when the sources change (section 5).

## 3. How Build & install works (`builder.py: build_all` → `build_one` per map)

1. `mapv2.Map(d)` loads the map. For VS maps it **mirrors side A** into side B and widens the middle (`vsMid`).
2. `mapv2.plan(M)` makes a plan dict:
   - `pieces`: kit meshes with position, rotation and scale. Floors are tiles per style; walls are stone column
     stacks; plus ramps, stairs, decks, ceilings, battlements, props, water, banks and spans.
   - `nav_boxes`: walkable boxes for the navmesh.
   - `surfaces`: trap areas.
   - `rift(s)`, `spawns`, `starts`.
   - `routes`: each spawn's path (`Map.routes`: BFS from the rift; equal lengths prefer climbing early).
   - `barricades`, `gates`, `pits`, `killz`, `env_pieces`.
3. Geometry: `geowriter.write_geo` writes a cooked `_Geo` sublevel full of static mesh actors, using a template
   level (`base\geo_template`). `tilepng` draws the mission picture.
4. Navmesh: `boxes2tris.py` → `navbuild.exe` (Recast) → `prune.py` (keeps what connects to the rifts) →
   `navtool.exe` → `deathtrapify.py` (the game's NavPower format).
5. Gameplay level: a **patched copy of a base level** (`bases.py`):
   - Castle Plaza: crystal rift.
   - Castle Colosseum: normal rift.
   - Order Arboretum: normal-rift VS; it already has two rifts.
   - `dupactors.py` copies actors inside the cooked level (a second rift, extra spawners, extra trap grids).
   - `patch_plaza2.py` moves the rift, spawners, starts and path points onto our map, and puts in the navmesh.
   - `hideactors.py` drops the base's scenery.
   - `ue53rename.py` renames the packages to `/Game/Levels/Custom/JW_<id>/...`.
6. Mission definition + asset index: a copy of the base's mission data is renamed (`MD_JW_<id>`). Then `arpatch.py`
   adds every new package to the game's `AssetRegistry.bin` (a copy of `tools\base\AssetRegistry.bin`), which
   `repak.exe` packs into `zz_JWRegistry_P.pak`. **Mods that add trap-book entries** (`registry=True` in `MODS`) get
   their entries added here too, only while they're on (`write_registry`, `add_trapbarricade`, `add_giantflip`).
7. `retoc.exe to-zen --version UE5_3` packs all new packages into `zz_JWMaps_P` (IoStore). Everything is copied into
   `Paks\Mods`.
8. Lua side:
   - `install_referee`: `JWVersus` for VS maps, with `rules.txt` from each map's `rules`.
   - `install_barricades`: `JWBarricades`, from a `barricades.txt` that lists barricade/gate cells, pits and the
     kill height per level.

## 4. The app (`app.py`)

- tkinter window with sidebar pages Maps, Mods, Share and Game. Long work runs in a thread; UI updates go through a
  queue (`self.q`).
- A local HTTP server (`127.0.0.1:<random port>/omd/`) serves the Map Maker page:
  - `GET /omd/map?f=` loads a map,
  - `POST /omd/save` saves into the maps folder,
  - `/omd/build` and `/omd/pack` start a build or a share pack.
  - The Map Maker detects it's running "local" and shows Save-to-app instead of download.
- **Mods page** (`builder.MODS`): `dict(id, name, desc, paks, ue4ss, registry)`.
  - `set_mod` moves paks between `Paks\Mods` and `JW_disabled_mods` and flips `enabled.txt` ↔ `enabled.off`.
  - Registry mods rebuild the installed `zz_JWRegistry_P.pak` right away (`refresh_registry`).
  - Settings panels write `Mods\<mod>\settings.txt` (`key = number` lines) that the Lua mod reads (Endless at
    mission start; Giant Flip every 10 s).
- **Share:** a `.omdshare.json` for friends who have the app, or a ready-to-play zip (`friendpack.py`) for friends
  without it.

## 5. Building the app yourself

- Needs Python 3.11+ with `pip install pyinstaller`.
- The build script expects the developer folder layout. Copy `source\tools\` to `Documents\Claud OMD\tools\`, then
  run `python "Documents\Claud OMD\tools\exe_src\build_exe.py"`. It stages everything into `Claud OMD\exe_build\`,
  runs PyInstaller (`--onefile --windowed`, `mapbuild` and `base` as data), and copies the exe to `Claud OMD\` and the
  Desktop. Log: `Claud OMD\notes\build_exe.txt`.
- A **new builder file** must be added to the copy list in `build_exe.py` (and as a `--hidden-import` if it's a
  module), or the exe can't find it.
- **Self-update:** at start, if `srchash.source_hash()` (a hash of `exe_src` + `mapbuild` files) differs from the
  exe's built-in `version.txt` and the build script exists, the app rebuilds itself and swaps the exe. On a normal
  player's PC there is no developer folder, so this never runs.
- Test without the game: `mapv2.plan`, `Map.routes`, `tilepng.bgra` run anywhere (pure Python). The Map Maker runs
  in any browser (open the HTML file; it saves by download when it isn't served by the app).

## 6. Lua mods (UE4SS 3.0.1)

- Each mod is `Binaries\Win64\Mods\<Name>\Scripts\main.lua` + `enabled.txt`. They run on game start; restart the
  game after changing one.
- Ours:
  - **JWVersus** (VS referee: two rifts, score, sends F1-F6, curses, endless, rules).
  - **JWBarricades** (barricade walls, gates, death ravines).
  - **JWArcherAuto**, **JWArcherGrant** (Guardian Archer: a map sentinel turned into a buyable trap; selling via the
    sell button).
  - **JWTrapBarricade**, **JWTrapBarricadeGrant** (a 3 m barricade with trap spots).
  - **JWGiantFlip**, **JWGiantFlipGrant** (the Giant Flip Trap; throw settings).
  - **JWEndless** (endless waves on the game's own maps).
  - The "Grant" mods give one gold skull, once, so the new trap can be bought.
- Patterns that work:
  - `LoopInGameThreadWithDelay(ms, fn)` for polling.
  - `FindAllOf("Class")` to find things; it doesn't see blueprint classes by short name in every case, so use
    `IsA` over actors.
  - `RegisterHook("/Script/OMD4.Class:Function", fn)`.
  - `pcall` around everything.
  - Log to a file with `io.open`. The installer rewrites the default
    `C:/Program Files (x86)/Steam/steamapps/common/...` log paths to the real game folder.
- **Don't hook the game's sell RPC** (`RSTGameplayAbility_SellTrap:Server_SellTrap`) or other core ability calls:
  hooking them broke selling for every trap. Hooking `OnInputPressed` (the button) was safe.
- The host runs the logic; the second player's actions reach the host as private chat messages (`!jwsend n`,
  `!jwsell`) caught with a hook on `RSTPlayerState:Server_AddPlayerChatMessage`.

## 7. Adding a new trap (the proven recipe)

1. Copy the **Tar Trap's** inventory item (it is purchasable; most items aren't) and a trap definition. Rename the
   packages with `ue53rename.py` into `/Game/Traps/<YourTrap>/`.
   - Item: point it at the trap actor class, your definition, a new `Item.Identifier.Trap.<Name>` tag and an icon.
   - Definition: set a new `Gameplay.Property.Trap.<Name>` identifier and a price.
2. Register the new tags in a plain pak with `OMDD/Config/Tags/<Name>.ini`.
3. Pack with `retoc to-zen` (IoStore) as `zz_JW<Name>_P`.
4. Add two asset-index entries, copied from the source records:
   - The definition's `PrimaryAssetName` must be its identifier tag.
   - The item keeps `bPurchasable`.
   - Do it in `builder.write_registry` behind a `MODS` entry with `registry=True` (see `add_giantflip`).
5. Runtime behaviour, if needed, comes from a Lua mod.
   - A placed trap takes its definition from its **actor class default**, not from the item, so price/health
     changes to the placed trap are made at runtime.
   - Ability settings that are "unversioned" in the cooked file (launch force, weight classes) are also changed at
     runtime, on the class default object.
6. Icons: 512×512 DXT5 textures. Copy a game icon package and replace its pixel data at the same sizes (see
   `source\mods\guardian-archer\make_archer.py`).

## 8. Lessons learned (read before changing the builder)

1. Orcs ignore curved stairs (the navmesh treats them as slopes). Orc paths must use grid ramps/stairs.
2. The orcs' route comes from `Map.routes` (path points). Ties between equally long routes decide which way orcs go,
   so keep the tie-break stable.
3. Walls rise with neighbouring floors (3 m column steps). Changes to `WTOP` move every wall on every map, so test on
   a big map (Helm's Deep) before shipping.
4. Decks need 4 m clearance (asserted). Ogres need ~5 m in practice.
5. **Never change the user's rift type, environment or styles** when regenerating their map; merge their edits in.
6. A wall trap needs a 3 m face. Trap grids are made per surface; the builder copies extra grid actors when the base
   level has too few.
7. Unknown style names must not crash the build. Fall back to a default (the mission picture once crashed on
   `grass`).
8. The Map Maker normalizes files on load and save. Any new field must be kept in `normalize()` and `toJSON`, or the
   next save silently drops it.
9. A sold trap stays in the world with `bIsSold` for a moment. Treat it as gone, and never re-adopt it.
10. Test in game in small steps, and read the mod logs (`JW_*.txt`) after each test.

## 9. Making a change, step by step

1. Reproduce: get the map file, the app log (`%LOCALAPPDATA%\OMD Map Builder\logs\error.txt`) and the mod log.
2. Change the source (`exe_src`, `mapbuild`, or the Map Maker HTML). Keep the Map Maker's two copies identical if
   there are two.
3. Test offline: `mapv2.plan` and `routes` on several maps, before and after, and diff the routes.
4. Rebuild the exe (section 5), then Build & install, then play.
5. Write down what you learned (in a notes file next to the sources), so the next AI knows.
