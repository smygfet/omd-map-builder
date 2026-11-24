# OMD Map Builder

Custom maps, a versus mode and new traps for **Orcs Must Die! Deathtrap**.

Draw a map in the Map Maker, check it in 3D, and press **Build & install**. The app turns it into a real mission in
the game. This repo is the full source of the app, the map builder, the mods and the four starter maps.

Orcs Must Die! Deathtrap is made by Robot Entertainment, and all credit for the game goes to them. This is a
fan-made mod made out of love for their game. It is not affiliated with or endorsed by Robot Entertainment.

## What's in it

| Folder | What it is |
|---|---|
| `app/` | The Windows app (`app.py`), the build-and-install logic (`builder.py`), the Map Maker (`mapmaker.html`, a single offline page) and `build_exe.py`, which packs it all into `OMD Map Builder.exe` |
| `builder/` | The map builder: turns a Map Maker map into a patched game level, geometry, navmesh and asset registry. Also the UE4SS Lua scripts for versus mode (`JWVersus_main.lua`) and barricades (`JWBarricades_main.lua`) |
| `navmesh/` | `navbuild.cpp` (map geometry to a Recast navmesh) and `navtool.cpp` (writes the game's NavPower format) |
| `mods/` | The new traps and modes: Guardian Archer, Trap Barricade, Giant Flip, Endless. UE4SS Lua scripts plus the Python scripts that made their game files |
| `mapgen/` | Python scripts that generated or edited the starter maps |
| `maps/` | The four starter maps (`*.omdmap.json`): Helm's Deep, B- Day Orcmaha beach, VS Parking, VS Twin Keeps |
| `docs/` | Player guide (`START HERE.html`) and two guides written for AI assistants: making maps, and how it all works |

New to the code? Start with `docs/AI guide - how it all works.md`. It works just as well for people.

## Playing

Download the release from Nexus Mods and follow `START HERE.html`. In short: close the game, run `Install.bat`,
open OMD Map Builder and press **Build & install**.

## Building it yourself

See [BUILDING.md](BUILDING.md).

## Credits

- **Robot Entertainment** for Orcs Must Die! Deathtrap.
- [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) runs the Lua mods.
- [retoc](https://github.com/trumank/retoc) and [repak](https://github.com/trumank/repak) by trumank read and write the game's pak files.
- [Recast](https://github.com/recastnavigation/recastnavigation) builds the navmesh.
- [NavKit / NavWeakness](https://github.com/glacier-modding/NavKit) by the Glacier modding team reads and writes NavPower navmeshes.
