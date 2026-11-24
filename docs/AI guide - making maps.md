# AI guide: making maps for OMD Map Builder

You are helping someone make custom maps for **Orcs Must Die! Deathtrap** with **OMD Map Builder**, a Windows app. This
guide tells you how the map tool works, how a map file is put together, and how to make or change maps yourself
(usually by writing a small Python script that writes the map file), so the person only has to press one button.

Read this whole file once before you change anything. The rules under "Hard-won rules" come from in-game testing.
Breaking them gives maps that build fine but play badly.

---

## 1. The tool in one minute

- **OMD Map Builder** (desktop shortcut). Its pages:
  - **Maps:** every map it knows. **Build & install** puts all of them into the game as new missions.
  - **Mods:** extra traps and modes, each switched on/off, some with settings.
  - **Share:** send a map to a friend.
  - **Game:** the game folder; "Remove custom maps from the game".
- **Map Maker:** a grid editor that runs in the browser. The app opens it with **Open Map Maker**. With a map
  selected on the Maps page, it opens that map. Its **Save** goes straight into the app.
- **Map files** are JSON, `<id>.omdmap.json`, kept in **`%LOCALAPPDATA%\OMD Map Builder\maps\`**. Files in the
  `removed` subfolder are ignored. The app picks up any new or changed file there (press refresh or reopen the app).
- **The game must be closed** for Build & install. A build takes a minute or two per map. The missions then show in
  the game's mission choice. VS maps show as "VS: <name>" (built twice: on a crystal-rift base and on a normal-rift
  base, "(normal rift)").
- Logs: `%LOCALAPPDATA%\OMD Map Builder\logs\` (`build_log.txt`, `error.txt` with a Python traceback when a build
  fails).

## 2. How a map is built (what the grid means)

- The map is a grid of **cells, 3 m × 3 m** (`cell: 300` cm). `cols` × `rows` cells. x grows east (right), y grows
  south (down). `grid[y * cols + x]` is the cell at (x, y).
- Heights are in **metres** (`level: 100` cm per unit). Floors go from 0 to **21 m** (`MAX_H` 21); decks to 24.
- The builder turns cells into the game's own kit pieces (stone walls, floor tiles, stairs and so on), a navmesh
  for the orcs, trap surfaces (every floor, and every wall face that is high enough), the rift, player starts and orc
  spawners.
- **Walls** (`t: 'w'`) are solid columns. A wall's top is the highest floor next to it (8 neighbours) + the map's
  wall height (`wallH`, default 6 m), rounded **up** to a 3 m step, plus its own raise `wh` (metres, can be negative
  down to −12 to lower it). A wall carrying a deck (`b`) ends at the deck.
- **Raised floors** (`t: 'f'`, `h` > 0) are solid blocks down to the ground: a floor at 9 m is a 9 m-tall block with
  a walkable top. There is no "floating floor"; for that use a **deck**.
- **Decks** (`b`: deck height in m on a floor or ramp cell) are a second walkable layer above the cell's floor: an
  upper storey, a bridge, a balcony, a roof walk. A deck needs **at least 4 m** of room above the floor under it.
  `bw: 1` puts a wall on the deck. A deck on a wall cell (`t: 'w'` + `b`) makes that wall a pillar that carries the
  deck.
- **Ceilings** (`c: 1`) put a roof over a floor cell at floor + `ceilH` (map field; `0` means use `wallH`). Use them
  for halls, bunkers and tunnels.
- **Ramps / stairs** (`t: 'r'`): the cell climbs **1 m** in the direction `d` (0 north/up, 1 east, 2 south, 3 west),
  starting at its `h` (the cell's low end). So a 6 m climb takes 6 ramp cells, `h` = 0, 1, 2, 3, 4, 5, all with the same
  `d`, and the next cell is a floor at 6. `st: 1` makes it stairs instead of a smooth ramp. Orcs use both.
- **Void** (`t: 'v'`): nothing. Open sky or a drop. The map's `fill` decides what shows in empty space.

## 3. The map file

```json
{
  "format": "omd-map-maker", "version": 2,
  "name": "VS Example", "id": "VS_Example",
  "cols": 41, "rows": 30, "cell": 300, "level": 100, "wall": 600,
  "styles": {"floor": "plaza", "wall": "stonewall", "ceiling": "planks"},
  "vs": 1, "rift": "normal", "env": "forest", "wallH": 6, "ceilH": 0, "bt": 1,
  "fill": "inside", "fillPits": 1, "water": "basin",
  "vsMid": "cliff", "vsMidW": 5, "vsBridge": 0, "vsBridgeAt": "mid",
  "rules": {"endless": 1, "orcs": 50, "health": 15, "send": 1,
            "prices": [1000, 1200, 1500, 2500, 5000, 6000], "rise": 5,
            "archers": 1, "midkill": 1, "coins": 0, "rift": 0},
  "curves": [], "spans": [], "sketch": [], "rev": 1,
  "markers": [{"k": "rift", "x": 6, "y": 4}, {"k": "start", "x": 10, "y": 6}, {"k": "spawn", "x": 16, "y": 27},
              {"k": "rift", "x": 34, "y": 4, "s": 1}, {"k": "start", "x": 30, "y": 6, "s": 1}, {"k": "spawn", "x": 24, "y": 27, "s": 1}],
  "grid": [{"t": "f", "h": 0, "d": 1, "c": 0, "n": 0}, "..."]
}
```

- `id`: letters, digits and `_` only. It is the file name and the in-game level name. **A new id = a new map.** If
  you rename a map, move the old file to `maps\removed\` or the app builds both.
- `rev`: raise it by 1 every time you change a map, so the person's app sees a newer version.
- **Cell fields:**

| field | meaning |
|---|---|
| `t` | `f` floor, `w` wall, `r` ramp/stairs, `v` void |
| `h` | floor height in m (walls: usually 0) |
| `d` | ramp direction 0 N, 1 E, 2 S, 3 W (other cells: 1) |
| `c` | 1 = ceiling over this floor |
| `n` | 1 = no traps here |
| `st` | 1 = stairs (ramp cells) |
| `fs` | floor style of this cell (see styles) |
| `b` | deck height (m) |
| `bw` | 1 = a wall on the deck |
| `wh` | wall raise in m, in 3 m steps, −12..30 |
| `ws` | `"rock"` = a rock wall instead of masonry |
| `bk` | 1 = barricade wall (floor cell; orcs must break it) |
| `gt` | 1 = gate (portcullis + hidden barricades) |
| `p`, `pr` | prop and its rotation 0-3 (a prop **blocks** its cell for orcs) |
| `cv` | belongs to curve number `cv` (round walls, curved walkways, curved stairs) |

- **Markers:** `rift` (one per side), `start` (player start), `spawn` (orc spawners; several allowed, up to 7 per
  side). In a VS map, side B markers have `"s": 1`.
- **Map options:**
  - `env`: what surrounds the map: `none`, `ground`, `town`, `forest`, `fortress`.
  - `fill`: empty cells inside the map: `none`, `inside` (dark stone), `outside` (mud), `rubble`. `fillPits: 1` fills
    pits too.
  - `bt: 1`: battlements on every edge that drops 3 m or more.
  - `water`: the look of `fs: 'water'` cells: `puddle`, `basin` (+ lily pads), `hub` (+ lily pads; looks best).
  - `rift`: `normal` (orcs walk into it) or `crystal` (orcs attack a crystal).
- **Styles** (map defaults in `styles`, per-cell floor in `fs`):
  - **floor:** museum, museumB, museumD, drydocks, cobblestone, cobblefan, plaza, plazacross, plazablue, plazasquare,
    plazaB, plazaC, plazaE, wood, woodfloor, parquet, stoneblock, stonefloor, darkstone, squaretile, brick, brickborder,
    terracotta, terracottaB, pavement, resort, resortB, mud, dirt, dirtB, ceramic, scattered, scattereddk, grass, water.
  - **wall:** stonewall, stonehouse, plaster, stucco, adobe, manor, castle.
  - **ceiling:** planks, library, manor.
- **Props** (`p`): barrels, barrel, crates, kegs, sacks, chest, market, table, forge, rack, cauldron, bookcart,
  throne, brazier, torches, gardenlamp, castlelamp, fountain, hogarth, apprentice, mermaid, orcstatue, anchor, rubble,
  planter, pots, ferns, bench, pillar, orcpillar, tent, orctent, hay, cart, fence, boulder.
- **Curves** (`curves: [{x, y, r, t, k, ...}]`, centre and radius in cells, thickness `t` 1-4). `k` is one of:
  - `wall`: a round wall,
  - `walk`: a curved walkway with crenels,
  - `stairs`: curved stairs, with `a0` (start angle), `h0`→`h1` (heights), `cw` ±1 (direction) and `s` (m per 3 m, 1-2).
  - The cells they cover carry `cv` = index + 1.
- **Spans** (`spans: [{x1, y1, x2, y2, h, w}]`): a straight bridge slab at any angle, height `h` m, `w` cells wide.
- **Sketch** (`sketch`): the person's notes drawn in the Map Maker (lines, arrows, text). The builder ignores them.
  See section 6.
- **VS options:**
  - `vsMid`: what separates the sides. `wall`, `open` (a 3 m gap) or `cliff` (a death ravine `vsMidW` 3/5/7/9 cells
    wide).
  - `vsBridge`: 0-3 cells wide; heroes only, orcs never cross it. `vsBridgeAt`: `mid`, `top` or `bottom`.
  - `rules`: per map:
    - `endless`;
    - `orcs` (% more per wave) and `health` (% more enemy health per wave; 100 = doubles every wave);
    - `send` (players can send enemies to the other side with F1-F6, at `prices`, each send dearer by `rise` %);
    - `archers` (Guardian Archer trap allowed);
    - `midkill` (falling into the middle kills);
    - `coins` (starting coins; 0 = the mission's own) and `rift` (rift points per side; 0 = the mission's own).

## 4. VS maps (two players, two rifts)

- Set `"vs": 1`. Make `cols` **odd** (41 is the usual). You design **side A**, the left half (x < cols // 2). The
  builder throws away the right half and **mirrors side A** into side B (x' = cols − 1 − x; ramps facing E/W flip).
  The middle column is replaced according to `vsMid`. Write the mirror into the file too anyway, because the Map
  Maker shows the whole grid.
- Markers: put side A's rift, start and spawns on the left; add their mirror images with `"s": 1` (the builder
  recomputes them from side A).
- For "watch the other player" maps use `vsMid: "cliff"` (or `open`) and keep the edge facing the middle open, with
  no tall walls there.

## 5. Hard-won rules (from in-game testing)

1. **Orcs do not use curved stairs.** They go a long way round instead. Curved stairs are for heroes only; every orc
   path must use **straight grid ramps/stairs** (`t: 'r'`).
2. **Every spawn needs a walkable way to its rift.** The builder works out each spawn's path itself (shortest walk;
   when walks are equally long it takes the one that climbs first) and gives it to the orcs as their route. Check it
   before handing over a map (section 7).
3. **Ramps climb 1 m per cell, no more.** A drop the orcs must climb needs that many ramp cells in a straight line,
   landing on a floor exactly at the top height.
4. **A wall trap needs a 3 m tall wall face.** A trench 2 m deep gets no wall traps; make it 3 m.
5. **Decks need 4 m of room above the floor.** Pillars (walls with `b`) under big decks look right and carry them.
6. **Props block orcs and heroes.** Keep them off the orc path and out of 1-cell passages.
7. **A floor beside a wall raises the wall.** A cell 1 m higher next to a wall makes the wall 3 m taller (3 m steps).
   Lower it again with `wh: -3` if needed (e.g. a window sill in a bunker wall).
8. **Don't overwrite the person's choices.** If they set a rift type, environment, style or rules, keep them. Change
   only what they asked for.
9. **Make sure the player start can walk to the rift and to the orc path.** A start on an island makes heroes jump.
10. **Ogres are big.** Keep at least 5 m of room under decks and roofs where orcs walk.
11. Pits (void inside the map) are deadly drops on maps that have them on purpose ("death ravines"). Don't leave
    accidental holes; fill or wall them.

## 6. Working with the person: notes ("sketch")

People mark what they want **on the map** with the Map Maker's Sketch tools (pen, arrow, note), then save. You read
them from the file's `sketch` list:

- `{"k": "text", "t": "the note", "pts": [[x, y]]}`: a note at cell (x, y) (cell units, fractional).
- `{"k": "arrow", "pts": [[x1, y1], [x2, y2]]}`: the tail is at the note, the head points at the target.
- `{"k": "line", "pts": [...]}`: a loop or stroke around the area they mean.

Workflow that works well:

1. Read their latest file from the maps folder.
2. Diff it against your last version, because they may have edited cells by hand. **Keep their edits.**
3. Read every note and match it to the cells it circles or points at.
4. Change the map (best: a small Python script that reads their file, edits cells, raises `rev`, writes the file).
5. Check it (section 7). Write it back into the maps folder, after backing up their file into `maps\removed\`.
6. Clear the sketch (`"sketch": []`) once they say the notes are done.
7. Tell them to press Build & install.

## 7. Checking a map before handing it over

The builder's Python modules ship with this pack: `source\tools\mapbuild\` (`mapv2.py` etc.). With Python 3 and no
other installs:

```python
import json, sys
sys.path.insert(0, r"<pack>\For your AI\source\tools\mapbuild")
import mapv2, tilepng
d = json.load(open(r"%LOCALAPPDATA%\OMD Map Builder\maps\VS_Example.omdmap.json"))
M = mapv2.Map(d)
print([None if r is None else len(r) for r in M.routes()])   # one entry per spawn: None = can't reach its rift
P = mapv2.plan(M)                                             # raises with a clear message on impossible geometry
tilepng.bgra(d)                                               # the mission picture; fails on unknown styles
```

- `routes()` gives each spawn's path as `(x, y, layer)` cells, from the spawn to the rift. Look at whether it takes
  the way the person expects.
- `plan()` raising `AssertionError` tells you exactly what's wrong (e.g. "the deck at 4, 18 needs at least 4 m of
  room above the floor").
- Draw a quick ASCII view of the grid (heights, `#` walls, ramps) to see what you're doing. That is the fastest way
  to understand someone's map.

## 8. Writing a map from scratch

- Write a generator: a Python script with helper functions (`cell(t, h, **kw)`, `put(x, y, c)`), building the grid
  area by area. Example generators are in `source\mapgen\`:
  - `parking.py`: a 3-floor parking garage VS map (ramps, decks on pillars).
  - `twin_keeps.py`: dressing up an existing map with styles and props.
  - `helms_deep.py`: big; round walls, walkways, spans, water, a mountain.
  - `bday_fix.py` / `dday_fix.py`: editing someone's map from their notes.
- Start simple: floors, walls, ramps, markers. Check routes. Then add decks, styles, props and battlements.
- Give the person a short description of the layout (floors and heights, orc path, where the rift is) and ask them
  to open it in the Map Maker and sketch changes.
