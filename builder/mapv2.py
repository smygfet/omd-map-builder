# Map Maker v2 (.omdmap.json, 3 m kit grid) -> build plan:
#   nav boxes (for Recast), trap surfaces, gameplay markers/routes, kit piece placements for Unreal.
# All output coordinates are world coordinates (map offset applied).
import json, math, os, sys
from collections import deque
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import props

OX, OY, OZ = 30000.0, -2400.0, 0.0
CELL, LEVEL, WALL = 300.0, 100.0, 600.0
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]          # north, east, south, west (grid y grows south = world +Y)
RIFT_R = 1
TILE = 150.0
RAMP_PITCH = math.degrees(math.atan2(LEVEL, CELL))  # 18.43 deg
RAMP_LEN = math.hypot(LEVEL, CELL)                  # 316.2 cm

A = '/Game/Environments/Arch_Order/'
# floor pieces: (cells along X, cells along Y, mesh), biggest first. Pivot at the min-X/min-Y corner, top surface at
# z=0 (checked on every mesh below from the game's own cooked bounds). Kit names read <Y>x<X>: Floor_1x2 = 2 cells X, 1 Y.
F = A + 'Floors/Mesh/'
FLOORS = {
    'museum':      [(4, 4, F + 'Floor_4X4_Museum_Pattern_C_SM'), (2, 2, F + 'Floor_2X2_Museum_Pattern_C_SM'),
                    (4, 1, F + 'Floor_1x4_Museum_Pattern_A_SM'), (2, 1, F + 'Floor_1x2_Museum_Pattern_A_SM')],
    'drydocks':    [(4, 4, F + 'Floor_4x4_Drydocks_SM'), (4, 2, F + 'Floor_2x4_Drydocks_SM')],
    'cobblestone': [(4, 4, F + 'Floor_4x4_CobbleStone_SM'), (2, 2, F + 'Floor_2x2_CobbleStone_SM'), (2, 1, F + 'Floor_1x2_CobbleStone_SM')],
    'plaza':       [(4, 4, F + 'Floor_4x4_Plaza_PatternD_SM'), (4, 2, F + 'Floor_2x4_Plaza_PatternD_SM'),
                    (2, 2, F + 'Floor_2x2_Plaza_PatternD_SM'), (4, 1, F + 'Floor_1x4_Plaza_PatternD_SM')],
    'wood':        [(2, 2, F + 'WoodPlank_2x2_Floor_A'), (2, 1, F + 'WoodPlank_2x1_Floor_A')],
    'stoneblock':  [(4, 4, F + 'Floor_4x4_StoneBlock_SM'), (4, 3, F + 'Floor_3x4_StoneBlock_SM'), (2, 2, F + 'Floor_2x2_StoneBlock_SM'),
                    (4, 1, F + 'Floor_1x4_StoneBlock_SM'), (2, 1, F + 'Floor_1x2_StoneBlock_SM')],
    'darkstone':   [(4, 4, F + 'Floor_4x4_StoneBlock_Dark_SM'), (2, 2, F + 'Floor_2x2_StoneBlock_Dark_SM')],
    'squaretile':  [(4, 4, F + 'Floor_4x4_CobbleStone_SquareTile_SM'), (2, 2, F + 'Floor_2x2_CobbleStone_SquareTIle_SM'),
                    (2, 1, F + 'Floor_1x2_SquareTile_SM')],
    'brick':       [(4, 4, F + 'Floor_4x4_Plaza_Pattern_Brick_None_SM'), (2, 2, F + 'Floor_2x2_Plaza_Pattern_Brick_None_SM'),
                    (2, 1, F + 'Floor_1x2_Plaza_Pattern_Brick_None_SM')],
    'brickborder': [(4, 4, F + 'Floor_4x4_Plaza_Brick_B_SM'), (2, 2, F + 'Floor_2x2_Plaza_Pattern_Brick_B_SM')],
    'terracotta':  [(4, 4, A + 'Courtyard/Mesh/Floor_Terracotta_4x4_A_SM'), (2, 2, A + 'Courtyard/Mesh/Floor_Terracotta_2x2_A_SM'),
                    (4, 1, A + 'Courtyard/Mesh/Floor_Terracotta_1x4_B_SM')],
    'pavement':    [(4, 4, A + 'Manor/Mesh/Floor_Manor_StonePavement_4x4_A_SM'), (2, 4, A + 'Manor/Mesh/Floor_Manor_StonePavement_2x4_A_SM'),
                    (2, 2, A + 'Manor/Mesh/Floor_Manor_StonePavement_2x2_A_SM'), (4, 1, A + 'Manor/Mesh/Floor_Manor_StonePavement_1x4_A_SM')],
    'resort':      [(4, 4, A + 'Resort/Mesh/Floor_Resort_Stone_4x4_A_SM'), (4, 2, A + 'Resort/Mesh/Floor_Resort_Stone_2x4_A_SM'),
                    (2, 2, A + 'Resort/Mesh/Floor_Resort_Stone_2x2_A_SM'), (4, 1, A + 'Resort/Mesh/Floor_Resort_Stone_1x4_A_SM'),
                    (2, 1, A + 'Resort/Mesh/Floor_Resort_Stone_1x2_A_SM')],
    'parquet':     [(4, 4, F + 'Floor_Wood_Parquet_4x4_SM'), (2, 2, F + 'Floor_Wood_Parquet_2X2_SM'), (2, 1, F + 'Floor_Wood_Parquet_1X2_SM'),
                    (1, 1, F + 'Floor_Wood_Parquet_1X1_SM')],
    'mud':         [(4, 4, F + 'Floor_4x4_Mud_SM'), (2, 2, F + 'Floor_2x2_mud_SM')],
    'dirt':        [(4, 4, A + 'Sewer/Mesh/Floor_Sewer_Dirt_4x4_SM'), (2, 2, A + 'Sewer/Mesh/Floor_Sewer_Dirt_2x2_SM')],
    'ceramic':     [(4, 4, A + 'Hub/TrainingArea/Mesh/Floor_Hub_Ceramic_4x4_A_SM'), (4, 2, A + 'Hub/TrainingArea/Mesh/Floor_Hub_Ceramic_2x4_A_SM')],
    # 4x4 only (single cells and ramps use the 4x4 tile shrunk); sizes checked: 1200 x 1200, top at z = 0
    'museumB':     [(4, 4, F + 'Floor_4X4_Museum_Pattern_B_SM')],
    'museumD':     [(4, 4, F + 'Floor_4X4_Museum_Pattern_D_SM')],
    'cobblefan':   [(4, 4, F + 'Floor_4x4_CobbleStone_Fan_A_SM')],
    'scattered':   [(4, 4, F + 'Floor_4x4_CobbleStone_Scattered_A_SM')],
    'scattereddk': [(4, 4, F + 'Floor_4x4_CobbleStone_Scattered_A_Dark_SM')],
    'plazacross':  [(4, 4, F + 'Floor_4x4_Plaza_PatternA_Cross_SM')],
    'plazablue':   [(4, 4, F + 'Floor_4x4_Plaza_PatternA_Blue_Cross_SM')],
    'plazasquare': [(4, 4, F + 'Floor_4x4_Plaza_PatternA_Square_SM')],
    'plazaB':      [(4, 4, F + 'Floor_4x4_Plaza_PatternB_SM')],
    'plazaC':      [(4, 4, F + 'Floor_4x4_Plaza_PatternC_SM')],
    'plazaE':      [(4, 4, F + 'Floor_4x4_Plaza_PatternE_SM')],
    'stonefloor':  [(4, 4, F + 'Floor_4x4_StoneFloor_A_SM')],
    'woodfloor':   [(4, 4, F + 'Floor_4x4_Wood_SM')],
    'resortB':     [(4, 4, A + 'Resort/Mesh/Floor_Resort_Stone_4x4_B_SM')],
    'dirtB':       [(4, 4, A + 'Sewer/Mesh/Floor_Sewer_Dirt_4x4_B_SM')],
    'terracottaB': [(4, 4, A + 'Courtyard/Mesh/Floor_Terracotta_4x4_B_SM')],
    # grass: the kit's only grass tile is 2 x 1 cells (600 x 300, corner pivot, top at z = 0, measured)
    'grass':       [(2, 1, F + 'Floor_1x2_Grass_SM')],
    # shallow water: mud tiles with a water surface laid 5 cm above them (WATER)
    'water':       [(4, 4, F + 'Floor_4x4_Mud_SM'), (2, 2, F + 'Floor_2x2_mud_SM')],
}
# wall panels: (cells long, mesh). Pivot at one end, run along +X, bottom at z=0.
# Per style (measured from the game's own kit blueprints): which local Y side faces out (+1/-1), where that
# side's flat face is (the game's trap grid plane), how far its footing reaches, wall top and lowest trap height.
WALLS = {
    'stonewall':  dict(pieces=[(4, A + 'Walls/Mesh/Wall_Bottom_4x2_StoneWalls_SM')], side=1, face=50, foot=75, top=625, zb=25),
    'stonehouse': dict(pieces=[(4, A + 'Walls/Mesh/Wall_Bottom_Stonewall_House_4x2_A_SM')], side=1, face=50, foot=75, top=625, zb=25),
    'plaster':    dict(pieces=[(4, A + 'Courtyard/Mesh/Wall_Bottom_Plaster_Painted_4x2_A_SM'), (1, A + 'Courtyard/Mesh/Wall_Bottom_Plaster_Painted_1x2_A_SM')], side=1, face=50, foot=75, top=625, zb=25),
    'stucco':     dict(pieces=[(4, A + 'Courtyard/Mesh/Wall_Bottom_Stucco_4x2_A_SM'), (2, A + 'Courtyard/Mesh/Wall_Bottom_Stucco_2x2_A_SM')], side=1, face=50, foot=75, top=625, zb=25),
    'adobe':      dict(pieces=[(4, A + 'Resort/Mesh/Wall_Resort_Adobe_4x2_B_SM'), (2, A + 'Resort/Mesh/Wall_Resort_Adobe_2x2_B_SM')], side=1, face=0, foot=0, top=600, zb=0),
    'manor':      dict(pieces=[(4, A + 'Manor/Mesh/Wall_Manor_WoodPanel_4x2_A_SM')], side=-1, face=10, foot=12, top=625, zb=25),
    'castle':     dict(pieces=[(2, A + 'Walls/Mesh/Wall_StoneWall_Castle_2x2_SM')], side=1, face=0, foot=0, top=600, zb=0),
}
# ceilings: (cells X, cells Y, mesh, height of the mesh's lowest point above its pivot).
# Pivot at min-X / max-Y corner, piece extends +X and -Y. The underside sits 1 cm above the wall top.
# Each layer: (mesh, roll, z of the pivot above the underside, which Y edge the pivot sits on).
# 'planks' is the plank floor tile turned upside down (planks face down), with a second tile on top as the roof.
CEILINGS = {
    'planks':  dict(cells=(2, 2), layers=[(A + 'Floors/Mesh/WoodPlank_2x2_Floor_A', 180.0, 4.0, 'max'),
                                          (A + 'Floors/Mesh/WoodPlank_2x2_Floor_A', 0.0, 20.0, 'min')]),
    'library': dict(cells=(4, 2), layers=[(A + 'RestrictedLibrary/Mesh/Library_Ceiling_Wood_2x4_A_SM', 0.0, 67.0, 'max')]),
    'manor':   dict(cells=(3, 3), layers=[(A + 'Manor/Mesh/Ceiling_Manor_Wood_3x3_A_SM', 0.0, -7.0, 'max')]),
}
COLUMN = {300.0: A + 'Columns/Mesh/Column_Square_1_1_StoneWall_SM', 600.0: A + 'Columns/Mesh/Column_Square_1_2_StoneWall_SM',
          1200.0: A + 'Columns/Mesh/Column_Square_1_4_StoneWall_SM'}     # 3 x 3 m stone columns, pivot at the bottom middle
CORE = A + 'Columns/Mesh/Column_Square_1_2_StoneWall_House_SM'   # 300 x 300 x 600, pivot bottom centre
BLOCK = A + 'Columns/Mesh/Column_Square_1_1_Stone_House_SM'      # 300 cube, pivot bottom centre
WOOD_BLOCK = A + 'Columns/Mesh/Column_Square_1_1_Wood_SM'        # 300 cube of wood, pivot bottom centre (measured): a barricade wall cell
# water surface: the game's puddle water plane (its material is the Back Alley's puddle water), 100 x 100 m, pivot in
# the middle (measured). (The hub blacksmith's trough plane, tried first, showed nothing over a 5 cm deep bed.)
WATER = ('/Game/Environments/LandScapes/Elements/Water/Mesh/WaterPlane_Puddle', 10000.0, 10000.0)
# other water surfaces (2026-11-15 test: the puddle sheet hardly shows in game): the dry docks' basin (48.6 x 66 m
# plane, centred) and the hub's rift-rocks pool (7.4 m, about centred); map field 'water': 'puddle', 'basin', 'hub', or
# 'ab' (a side-by-side test: the map's north half hub water, the south half basin water)
WATER_BASIN = ('/Game/Environments/Props_Order/DryDocks/Basin/Mesh/Basin_Water_SM', 4856.8, 6605.8, 0.0, 0.0)
WATER_HUB = ('/Game/Environments/Props_Order/Hub_RiftRocks/Mesh/Hub_RiftRocks_Water_01', 741.4, 741.3, -5.2, 2.65)
LOTUS = ['/Game/Environments/LandScapes/3rdParty/Swamp_Forest/Meshes/plants/SM_water_lotus_01',
         '/Game/Environments/LandScapes/3rdParty/Swamp_Forest/Meshes/plants/SM_water_lotus_flower_01']
WATER_BED = 28.0          # the bed under water lies this much lower (cm): heroes wade (step height 45 cm, they get out)
# rock walls: cliff rocks, (mesh, middle x, middle y, size x, size y, height) in cm, bottom at about z = 0 (measured)
ROCKS = [('/Game/Environments/LandScapes/Geology/Cliff/Mesh/Cliff_Rock_C_01', 1.0, 0.6, 491.3, 649.5, 671.5),
         ('/Game/Environments/LandScapes/Geology/Cliff/Mesh/Cliff_Rock_D_01', -58.0, 3.2, 393.1, 478.4, 669.9)]
# battlements: the crenellated wall top, 600 x 30 x 150, x 0..600, y -30..0, z 0..150 (measured); half length per cell
CRENEL = A + 'Crenellation/Mesh/Wall_2x05_Crenel_A_StoneWall_SM'
# gates: the castle's portcullis, 964 x 48 x 635, pivot bottom middle, bars along local X (measured)
PORTCULLIS = (A + 'Doors/Mesh/Portcullis_CastlePlaza_D_SM', 964.0)
CLIFFS = ['/Game/Environments/LandScapes/3rdParty/Cliff_Rock_Pack01/Meshes/Cliffs/split_cliff_01',    # pit / ravine walls
          '/Game/Environments/LandScapes/3rdParty/Cliff_Rock_Pack01/Meshes/Cliffs/split_cliff_02',
          '/Game/Environments/LandScapes/3rdParty/Cliff_Rock_Pack01/Meshes/Cliffs/cliff_02']
BRIDGE = {'deck': '/Game/Environments/Arch_Order/Floors/Mesh/WoodPlank_4x1_Floor_A',        # 1200 x 300, corner pivot
          'beam': '/Game/Environments/Arch_Order/Wood/Mesh/Wood_Square_1200W_A',          # 110 x 110 x 1200 upright
          'rail': '/Game/Environments/Arch_Order/Railing/Mesh/Wood_Railing_200C_A'}       # 200 long, pivot at its start
BANNERS = ['/Game/Environments/Props_Order/General_Decor/Banner_Coastal/Mesh/Banner_Coastal_OrderCrest_Small_SM',   # team banners
           '/Game/Environments/Props_Order/General_Decor/Banner_Order/Mesh/BannerLargeA']                         # (VS): A blue, B red


# fill materials for the empty area: (floor style tiled over the cells, z of its top in cm)
FILLS = {
    'inside':  dict(style='darkstone', z=0.0),
    'outside': dict(style='mud', z=0.0),
    'rubble':  dict(style='scattereddk', z=0.0),
}


def squares(style):
    """(big n, big mesh, small mesh, small scale x, small scale y): a style's biggest and smallest square tiles. A style
    without a square tile (grass) uses its smallest tile squeezed to one cell, also for the 'big' one."""
    fl = FLOORS[style]; sq = [(n, m) for n, k, m in fl if n == k]
    if sq: return sq[0][0], sq[0][1], sq[-1][1], 1.0 / sq[-1][0], 1.0 / sq[-1][0]
    n, k, m = min(fl, key=lambda p: p[0] * p[1])
    return 1, m, m, 1.0 / n, 1.0 / k


def tile_set(M, cells, style, z, tag):
    """Floor tiles of one style over a set of cells at height z (cm): biggest square tiles on a grid, then small ones."""
    big_n, big, small, ssx, ssy = squares(style)
    res = []; left = set(cells)
    for y in range(0, M.rows, big_n):
        for x in range(0, M.cols, big_n):
            blk = [(x + i, y + j) for i in range(big_n) for j in range(big_n)]
            if all(b in left for b in blk):
                left.difference_update(blk)
                res.append((big, (M.wx(x), M.wy(y), z + OZ), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0) if big_n > 1 else (ssx, ssy, 1.0), tag))
    for x, y in sorted(left):
        res.append((small, (M.wx(x), M.wy(y), z + OZ), (0.0, 0.0, 0.0), (ssx, ssy, 1.0), tag))
    return res


def fill_pieces(M, F, pits):
    """Tiles for the void cells joined to the map's edge (and enclosed pits too when pits=True). VS middle gap stays open."""
    cols, rows = M.cols, M.rows
    void = lambda x, y: M.at(x, y)['t'] == 'v' and not (M.vs and abs(x - getattr(M, 'mid', -99)) <= getattr(M, 'midw', 0))
    out = set(); st = [(x, y) for x in range(cols) for y in (0, rows - 1)] + [(x, y) for y in range(rows) for x in (0, cols - 1)]
    while st:
        x, y = st.pop()
        if (x, y) in out or not (0 <= x < cols and 0 <= y < rows) or not void(x, y): continue
        out.add((x, y)); st += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    cells = {(x, y) for y in range(rows) for x in range(cols) if void(x, y)} if pits else out
    M.filled = cells
    big_n, big, small, ssx, ssy = squares(F['style'])
    res = []; left = set(cells)
    for y in range(0, rows, big_n):
        for x in range(0, cols, big_n):
            blk = [(x + i, y + j) for i in range(big_n) for j in range(big_n)]
            if all(b in left for b in blk):
                left.difference_update(blk)
                res.append((big, (M.wx(x), M.wy(y), F['z'] + OZ), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0) if big_n > 1 else (ssx, ssy, 1.0), 'Fill'))
    for x, y in sorted(left):
        res.append((small, (M.wx(x), M.wy(y), F['z'] + OZ), (0.0, 0.0, 0.0), (ssx, ssy, 1.0), 'Fill'))
    return res


def curve_kind(cv):
    k = cv.get('k') if isinstance(cv, dict) else None
    return k if k in ('walk', 'stairs') else 'wall'


def stair_span(cv):
    """Curved stairs: (start angle, signed angle span, steps). They climb 's' m per 3 m cell (default 1, like grid
    stairs; 2 = steep castle steps, 33 degrees)."""
    rise = max(0.0, float(cv.get('h1', 0)) - float(cv.get('h0', 0)))
    sl = min(2.0, max(1.0, float(cv.get('s', 1) or 1)))
    span = rise / sl / max(0.5, float(cv['r'])) * (1 if int(cv.get('cw', 1)) >= 0 else -1)
    return float(cv.get('a0', 0.0)), span, max(1, int(round(rise * 5)))


def spans_of(M):
    """Straight bridges (map field 'spans': [{x1, y1, x2, y2 (cells), h (m), w (cells, default 1)}]): one straight
    piece at any angle, e.g. from one round walkway to another."""
    out = []
    for sp in M.d.get('spans') or []:
        try:
            q = dict(x1=float(sp['x1']), y1=float(sp['y1']), x2=float(sp['x2']), y2=float(sp['y2']), h=float(sp['h']), w=max(0.5, float(sp.get('w', 1))))
        except (KeyError, TypeError, ValueError): continue
        if math.hypot(q['x2'] - q['x1'], q['y2'] - q['y1']) > 0.3: out.append(q)
    return out


def span_dist(sp, px, py):
    """Distance (cm) from a point (cm, without the map offset) to a span's middle line."""
    ax, ay, bx, by = sp['x1'] * CELL, sp['y1'] * CELL, sp['x2'] * CELL, sp['y2'] * CELL
    vx, vy = bx - ax, by - ay; t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy)))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def stair_reach(M, cv, k, own):
    """How far the stairs' own cells reach before the first step (<= 0) and past the start (>= the span), as angles
    measured the way the stairs climb (from the cells' corners)."""
    a0, span, _ = stair_span(cv); cx, cy = float(cv['x']), float(cv['y'])
    sg = 1 if span >= 0 else -1; lo, hi = 0.0, abs(span)
    for y in range(M.rows):
        for x in range(M.cols):
            if not own((x, y)): continue
            for px, py in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1), (x + 0.5, y + 0.5)):
                d = ((math.atan2(py - cy, px - cx) - a0) * sg + math.pi) % (2 * math.pi) - math.pi
                lo, hi = min(lo, d), max(hi, d)
    return lo, hi


def stair_ends(M, cv):
    """Where curved stairs start and end: ((x, y, layer) at the bottom, (x, y, layer) at the top), or None for an end
    with no floor at the right height just past it. Orcs use curved stairs, so the route check joins these two."""
    a0, span, n = stair_span(cv); cx, cy, r = float(cv['x']), float(cv['y']), float(cv['r'])
    sg = 1 if span >= 0 else -1
    res = []
    for a, h in ((a0 - sg * 0.7 / r, float(cv.get('h0', 0))), (a0 + span + sg * 0.7 / r, float(cv.get('h1', 0)))):
        px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x, y = int(math.floor(px)) + dx, int(math.floor(py)) + dy
                if not (0 <= x < M.cols and 0 <= y < M.rows): continue
                c = M.at(x, y)
                if c.get('cv') and c['t'] == 'w': continue
                d = math.hypot(x + 0.5 - px, y + 0.5 - py)
                for L, top in ((0, (c['h'] + (1 if c['t'] == 'r' else 0)) if M.walk(c) else None), (1, M.deck(c) or None)):
                    if top is not None and abs(top - h) < 0.01 and (best is None or d < best[0]): best = (d, (x, y, L))
        res.append(best[1] if best and best[0] < 1.6 else None)
    return tuple(res)


def curve_plan(M, WTOP):
    """Round walls, Map Maker 'curves': [{'x', 'y' (middle, in cells), 'r' (radius of the band's middle), 't' (thickness),
    'k' (kind)}]; the cells with cv = k (1-based) belong to curve k.
      wall   (default) a smooth round wall; its cells are walls. Crenels along both edges of its top.
      walk   a round wall with a walkway on top: its cells are floors at the walkway's height; crenels on an edge
             where the ground beside drops 3 m or more.
      stairs curved stairs ('a0' start angle, 'h0' -> 'h1' heights, 'cw' +1 / -1): its cells are walls on the grid
             (orcs don't use them); built as stone steps, with sloped navmesh boxes.
    A wall / walk piece is only built where the cell under the band's middle is one of the curve's cells, and not
    where the piece would reach over a cell you walk on (a gap for stairs or a gate).
    Returns cells (built here), segs [(x, y (cm, map-local), yaw, length, thickness, top, bottom)], fill
    {(x, y): (floor height, style)}, crenels [(x, y, yaw, z)], steps [(x, y, yaw, length, width, top)], nav (boxes)."""
    out = {'cells': set(), 'segs': [], 'fill': {}, 'crenels': [], 'steps': [], 'nav': [], 'walk': set(), 'portals': [], 'wfill': {}}
    curves = M.d.get('curves') or []
    inside = lambda q: 0 <= q[0] < M.cols and 0 <= q[1] < M.rows
    def top_of(c):                               # what you stand on in a cell (None: a wall)
        if c['t'] == 'f': return max(c['h'], c.get('b') or 0)
        if c['t'] == 'r': return c['h'] + 1
        if c['t'] == 'v': return -99
        return None
    def corner_fill(k, cx, cy, r1, r2):
        """The cells' corners outside the band: the neighbouring floor on that side, at its height."""
        for q in out['cells']:
            if M.at(*q).get('cv') != k: continue
            x, y = q
            near = math.hypot(max(x - cx, 0, cx - x - 1), max(y - cy, 0, cy - y - 1))
            far = max(math.hypot(px - cx, py - cy) for px in (x, x + 1) for py in (y, y + 1))
            d0 = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            side = -1 if r1 - near > far - r2 else 1
            if (side < 0 and near > r1 - 0.03) or (side > 0 and far < r2 + 0.03): continue
            best = None
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n_ = M.at(x + dx, y + dy)
                    if n_['t'] not in ('f', 'r') or n_.get('br') or n_.get('cv'): continue
                    dd = math.hypot(x + dx + 0.5 - cx, y + dy + 0.5 - cy)
                    if (dd - d0) * side <= 0: continue
                    nh = n_['h'] + (1 if n_['t'] == 'r' else 0)     # beside straight stairs / a ramp: up to its top
                    key = (abs(dx) + abs(dy), -nh if side < 0 else nh)
                    if best is None or key < best[0]: best = (key, n_, nh)
            if best:
                nb = best[1]
                out['fill'][q] = (best[2], nb.get('fs') if nb.get('fs') in FLOORS else M.styles['floor'])
    for k, cv in enumerate(curves, 1):
        try: cx, cy, r, t = float(cv['x']), float(cv['y']), float(cv['r']), max(1.0, float(cv.get('t', 1)))
        except Exception: continue
        kind = curve_kind(cv)
        r1, r2 = max(0.3, r - t / 2), r + t / 2
        want = 'f' if kind == 'walk' else 'w'
        own = lambda q: inside(q) and M.at(*q)['t'] == want and M.at(*q).get('cv') == k
        cell_at = lambda a, rr: (int(math.floor(cx + math.cos(a) * rr)), int(math.floor(cy + math.sin(a) * rr)))
        if kind == 'stairs':
            a0, span, n = stair_span(cv); h0 = float(cv.get('h0', 0)); h1 = float(cv.get('h1', 0))
            for i in range(n):
                a = a0 + span * (i + 0.5) / n
                ln = abs(span) / n * r * CELL * 1.25
                out['steps'].append(((cx + math.cos(a) * r) * CELL, (cy + math.sin(a) * r) * CELL, math.degrees(a) + 90.0, ln, t * CELL,
                                     h0 * LEVEL + (i + 1) * (h1 - h0) * LEVEL / n))
                for f in (-0.5, 0.0, 0.5):
                    rr = r1
                    while rr <= r2 + 1e-6:
                        q = cell_at(a + f * span / n, rr)
                        if own(q): out['cells'].add(q)
                        rr += 0.2
            # the stairs' own cells reach past the first and last step: a flat piece at the bottom height before the
            # first step and a landing at the top height past the last one cover them (no holes beside the ends)
            lo, hi = stair_reach(M, cv, k, own)
            sg = 1 if span >= 0 else -1; A = abs(span)
            for (f0, f1, ht) in ((min(lo, -0.02), 0.0, max(h0 * LEVEL, 3.0)), (A, max(hi, A + 0.85 / r), h1 * LEVEL)):
                if f1 - f0 < 0.01: continue
                a = a0 + sg * (f0 + f1) / 2
                out['steps'].append(((cx + math.cos(a) * r) * CELL, (cy + math.sin(a) * r) * CELL, math.degrees(a) + 90.0, (f1 - f0) * r2 * CELL * 1.04, t * CELL, ht))
            out['portals'].append(stair_ends(M, cv))
            m = max(1, int(math.ceil(abs(span) * r - 1e-6)))       # navmesh: one sloped box per ~3 m of the arc
            for i in range(m):
                a = a0 + span * (i + 0.5) / m
                L = abs(span) / m * r * CELL; zb = h0 * LEVEL + (h1 - h0) * LEVEL * i / m; rise = (h1 - h0) * LEVEL / m
                p = math.degrees(math.atan2(rise, L)); T = 30.0
                d = 1 if span >= 0 else -1
                yaw = math.degrees(math.atan2(d * math.cos(a), -d * math.sin(a)))      # the climbing direction
                out['nav'].append({'f': 'Ramps', 'c': [(cx + math.cos(a) * r) * CELL, (cy + math.sin(a) * r) * CELL, zb + rise / 2 - (T / 2) / math.cos(math.radians(p))],
                                   's': [math.hypot(L, rise) * 1.05, t * CELL, T], 'p': p, 'y': yaw})
            corner_fill(k, cx, cy, r1, r2)
            continue
        n = max(16, int(math.ceil(2 * math.pi * r2 * CELL / 170.0)))
        da = 2 * math.pi / n
        segtop = {}                                  # built pieces: index -> top (cm)
        ownh = [M.at(x_, y_)['h'] for y_ in range(M.rows) for x_ in range(M.cols) if own((x_, y_))]
        WH = max(ownh) if (kind == 'walk' and ownh) else None
        CTOP = max([WTOP.get((x_, y_), 600.0) for y_ in range(M.rows) for x_ in range(M.cols) if own((x_, y_))] or [600.0])
        for i in range(n):
            a = (i + 0.5) * da
            hit = set(); gap = False; bridge = False; arch = []
            for f in (-0.5, 0.0, 0.5):
                rr = r1
                while rr <= r2 + 1e-6:
                    q = cell_at(a + f * da, rr)
                    if own(q): hit.add(q)
                    elif inside(q) and M.at(*q)['t'] in ('f', 'r') and M.at(*q).get('cv') != k and \
                            r1 < math.hypot(q[0] + 0.5 - cx, q[1] + 0.5 - cy) <= r2:
                        qc = M.at(*q)
                        if WH is not None and M.deckraw(qc) == WH: bridge = True              # a bridge over a passage
                        elif WH is None and M.deckraw(qc): arch.append(M.deckraw(qc))        # a round wall over a roofed opening
                        elif WH is not None and qc['t'] == 'f' and qc['h'] == WH: pass       # a floor joining at its height
                        else: gap = True             # a band cell made walkable (stairs, a gate): leave the gap clean
                    rr += 0.2
            if gap or (not hit and not arch) or (not own(cell_at(a, r)) and len(hit) < 2 and not bridge and not arch): continue
            out['cells'] |= hit
            if kind == 'walk':
                top = max(M.at(*q)['h'] for q in hit) * LEVEL; out['walk'] |= hit
            else:
                top = CTOP                               # one height for the whole round wall (a tower's top is level)
            ln = 2 * math.pi * r2 * CELL / n * 1.12
            segtop[i] = top
            bot = top - 60.0 if bridge else 0.0          # over a bridged passage only a 60 cm thick piece (the bridge's edge)
            if arch: bot = min(arch) * LEVEL - 60.0      # a round wall over a roofed opening: from the roof's slab up (an arch)
            out['segs'].append(((cx + math.cos(a) * r) * CELL, (cy + math.sin(a) * r) * CELL, math.degrees(a) + 90.0, ln, t * CELL, top, bot))
        # every cell of the curve is part of it (also corner cells no sample landed in): no square blocks poking out
        allown = {(x, y) for y in range(M.rows) for x in range(M.cols) if own((x, y))}
        if segtop:
            out['cells'] |= allown
            if kind == 'walk': out['walk'] |= allown
        # crenels along the top edges: 3 m pieces (the crenellated wall top at half length), tangent to the edge, where
        # the wall is built under the whole piece; on a walkway only where the ground beside it drops 3 m or more
        built = {q for q in out['cells'] if M.at(*q).get('cv') == k}
        for edge, R in (('in', r1), ('out', r2)):
            m = int(2 * math.pi * R * CELL // 300.0)
            if R < 1.0 or m < 4: continue
            for i in range(m):
                a = (i + 0.5) * 2 * math.pi / m
                idx = {int(math.floor(((a + f * math.pi / m) % (2 * math.pi)) / da)) for f in (-0.9, 0.0, 0.9)}
                if not all(j in segtop for j in idx): continue
                z = min(segtop[j] for j in idx)
                if kind == 'walk':
                    beyond = cell_at(a, R + (0.45 if edge == 'out' else -0.45))
                    if beyond in built: continue
                    tb = top_of(M.at(*beyond)) if inside(beyond) else -99
                    if tb is None or z - tb * LEVEL < 300: continue
                Rc = R * CELL - 30.0 if edge == 'out' else R * CELL
                px_, py_ = (cx * CELL + math.cos(a) * Rc) - (-math.sin(a)) * 150.0, (cy * CELL + math.sin(a) * Rc) - math.cos(a) * 150.0
                mx_, my_ = cx * CELL + math.cos(a) * Rc, cy * CELL + math.sin(a) * Rc
                if any(span_dist(sp, mx_, my_) < float(sp.get('w', 1)) * CELL / 2 + 120.0 for sp in spans_of(M)): continue   # a bridge lands here
                out['crenels'].append((px_, py_, math.degrees(a) + 90.0, z))
        corner_fill(k, cx, cy, r1, r2)
        if kind == 'wall' and segtop:              # where a straight wall meets the round wall: fill the round cell's
            for q in allown:                       # corners up to that wall's top (no slits down to nothing)
                tops = [WTOP[n_] for n_ in ((q[0] + 1, q[1]), (q[0] - 1, q[1]), (q[0], q[1] + 1), (q[0], q[1] - 1))
                        if n_ in WTOP and inside(n_) and M.at(*n_)['t'] == 'w' and not M.at(*n_).get('cv')]
                if tops: out['wfill'][q] = min(max(tops), CTOP)
    return out


class Map:
    def __init__(s, d):
        assert d.get('format') == 'omd-map-maker' and d.get('version') == 2 and d.get('cell') == 300, "not a v2 map file"
        s.d = d; s.name = d['name']; s.id = d.get('id') or 'Map'
        s.cols, s.rows = d['cols'], d['rows']; s.g = d['grid']; s.styles = d['styles']
        s.markers = [dict(m) for m in d['markers']]
        s.vs = bool(d.get('vs')); s.gap = bool(d.get('_gap'))
        if s.vs: s.mirror()

    def mirror(s):
        """VS map: the left half is side A. The middle column becomes a wall and the right half is side A mirrored
        (side B). Markers on the left half are side A (s=0), their mirror images side B (s=1)."""
        if s.cols % 2 == 0:                                  # odd width needed for a middle wall column
            g = []
            for y in range(s.rows): g += s.g[y * s.cols:(y + 1) * s.cols] + [dict(s.g[y * s.cols + s.cols - 1])]
            s.g = g; s.cols += 1
        m = s.cols // 2; s.mid = m
        g = [dict(c) for c in s.g]
        open_mid = s.d.get('vsMid') in ('open', 'cliff')     # "no mid wall": a 3 m gap instead, so you can watch the other side
        for y in range(s.rows):
            g[y * s.cols + m] = {'t': 'v' if open_mid else 'w', 'h': 0, 'd': 1, 'c': 0, 'n': 0}
            for x in range(m + 1, s.cols):
                c = dict(g[y * s.cols + s.cols - 1 - x])
                if c['t'] == 'r' and c['d'] in (1, 3): c['d'] = 4 - c['d']
                if c.get('p') and c.get('pr', 0) in (1, 3): c['pr'] = 4 - c['pr']
                g[y * s.cols + x] = c
        if getattr(s, 'gap', False):                         # test: one opening in the middle wall (connected navmesh)
            best = None
            for y in range(s.rows):                          # the row with the shortest wall between floor on both sides
                l = m
                while l >= 0 and g[y * s.cols + l]['t'] != 'f': l -= 1
                r = m
                while r < s.cols and g[y * s.cols + r]['t'] != 'f': r += 1
                if l >= 0 and r < s.cols and g[y * s.cols + l]['h'] == g[y * s.cols + r]['h']:
                    if best is None or r - l < best[0]: best = (r - l, y, l, r)
            if best:
                _, y, l, r = best
                for x in range(l + 1, r): g[y * s.cols + x] = dict(g[y * s.cols + l])
                s.gap_row = y
        s.midw = 0
        if s.d.get('vsMid') == 'cliff':                      # a ravine: empty columns (3, 5, 7 or 9 cells wide), a death drop
            wd = int(s.d.get('vsMidW') or 3)
            wd = max(3, min(9, wd if wd % 2 else wd + 1))
            W = wd - 1
            ng = []
            for y in range(s.rows):
                row = g[y * s.cols:(y + 1) * s.cols]
                ng += row[:m] + [dict(row[m]) for _ in range(W + 1)] + row[m + 1:]
            g = ng; s.cols += W; m += W // 2; s.mid = m; s.midw = W // 2
        # the bridge over the middle gap / ravine (Map Maker "Bridge"): floor at side A's floor height beside it, no
        # traps, no navmesh (orcs never cross: an open path made them run to the other rift), heroes walk it
        s.bridge = []
        bw = int(s.d.get('vsBridge') or 0) if open_mid else 0
        if bw:
            at = s.d.get('vsBridgeAt') or 'mid'
            cy = s.rows // 4 if at == 'top' else s.rows * 3 // 4 if at == 'bottom' else s.rows // 2
            y0 = max(0, min(s.rows - bw, cy - (bw - 1) // 2))
            for y in range(y0, y0 + bw):
                l = g[y * s.cols + m - s.midw - 1]
                h = l['h'] if l['t'] in ('f', 'r') else 0
                for x in range(m - s.midw, m + s.midw + 1):
                    g[y * s.cols + x] = {'t': 'f', 'h': h, 'd': 1, 'c': 0, 'n': 1, 'br': 1}
                s.bridge.append(y)
        s.g = g
        a = [dict(mk, s=0) for mk in s.markers if mk['x'] < m - s.midw]
        s.markers = a + [dict(mk, x=s.cols - 1 - mk['x'], s=1) for mk in a]

    def at(s, x, y):
        return s.g[y * s.cols + x] if 0 <= x < s.cols and 0 <= y < s.rows else {'t': 'v', 'h': 0, 'd': 1, 'c': 0}

    @staticmethod
    def walk(c): return ((c['t'] == 'f' and not c.get('p')) or c['t'] == 'r') and not c.get('br')     # a prop blocks its cell; orcs never use the VS bridge

    @staticmethod
    def edge_h(c, side):
        if c['t'] == 'f': return c['h']
        if c['t'] == 'r':
            if side == c['d']: return c['h'] + 1
            if side == (c['d'] + 2) % 4: return c['h']
        return None

    def connected(s, a, side, b):
        if not (s.walk(a) and s.walk(b)): return False
        ea, eb = s.edge_h(a, side), s.edge_h(b, (side + 2) % 4)
        if ea is None or eb is None:
            return a['t'] == 'r' and b['t'] == 'r' and a['h'] == b['h'] and a['d'] == b['d']
        return ea == eb

    # two walking layers per cell: 0 = its floor/ramp, 1 = its upper deck ('b' = deck height in m). A deck joins a
    # neighbour's deck at the same height, or a neighbour's floor / ramp edge at that height.
    @staticmethod
    def deck(c): return c.get('b') if c.get('b') and not c.get('bw') else 0      # walkable deck (also on a wall: an upper floor)
    @staticmethod
    def deckraw(c): return c.get('b') if c.get('b') else 0                         # any deck (also under an upper wall)
    def has(s, c, L): return s.deck(c) > 0 if L else s.walk(c)
    def connected_l(s, a, La, side, b, Lb):
        if not (s.has(a, La) and s.has(b, Lb)): return False
        if not La and not Lb: return s.connected(a, side, b)
        ea = s.deck(a) if La else s.edge_h(a, side)
        eb = s.deck(b) if Lb else s.edge_h(b, (side + 2) % 4)
        return ea is not None and eb is not None and ea == eb
    def node(s, x, y):
        c = s.at(x, y)
        return 0 if s.walk(c) else (1 if s.deck(c) else None)
    def portals(s):
        """Curved stairs joining their bottom and top cells (both ways)."""
        if not hasattr(s, '_portals'):
            s._portals = {}
            for cv in s.d.get('curves') or []:
                if curve_kind(cv) != 'stairs': continue
                a, b = stair_ends(s, cv)
                if a and b: s._portals.setdefault(a, []).append(b); s._portals.setdefault(b, []).append(a)
        return s._portals

    def routes(s):
        """Shortest walk from every spawn to a rift (its own side's rift in a VS map). None = cannot reach.
        Among equally short walks it takes the one that climbs earliest (least time spent low), so a spawn goes up
        its own nearest stairs instead of walking along the bottom to other stairs of the same length."""
        out = []
        for m in s.markers:
            if m['k'] != 'spawn': continue
            rifts = [r for r in s.markers if r['k'] == 'rift' and r.get('s', 0) == m.get('s', 0)]
            best = None
            for rift in rifts:
                L0 = s.node(rift['x'], rift['y'])
                if L0 is None: continue
                st = (rift['x'], rift['y'], L0); dist = {st: 0}; pars = {}; order = [st]; q = deque([st])
                pt = s.portals()
                def link(cur, n):
                    if n not in dist:
                        dist[n] = dist[cur] + 1; pars[n] = [cur]; q.append(n); order.append(n)
                    elif dist[n] == dist[cur] + 1 and cur not in pars[n]:
                        pars[n].append(cur)                    # another equally short way
                while q:
                    x, y, L = q.popleft()
                    for side, (dx, dy) in enumerate(DIRS):
                        for Lb in (0, 1):
                            n = (x + dx, y + dy, Lb)
                            if n == st or not s.connected_l(s.at(x, y), L, side, s.at(x + dx, y + dy), Lb): continue
                            link((x, y, L), n)
                    for n in pt.get((x, y, L), ()):            # up / down curved stairs
                        if n != st: link((x, y, L), n)
                Lm = s.node(m['x'], m['y'])
                k = (m['x'], m['y'], Lm)
                if Lm is None or k not in dist: continue
                # tie-break: least "lowness" summed along the walk (cells below the rift's height count by how far)
                top = s.surface_z(*st)
                low = {st: 0.0}; pick = {}
                for n in order[1:]:
                    c = max(0.0, top - s.surface_z(*n))
                    b = min(pars[n], key=lambda p_: low[p_])   # first of the equal ones wins a tie (as before)
                    low[n] = low[b] + c; pick[n] = b
                cells = [k]
                while cells[-1] in pick: cells.append(pick[cells[-1]])
                if best is None or len(cells) < len(best): best = cells    # spawn ... rift, (x, y, layer)
            out.append(best)
        return out

    # world helpers
    @staticmethod
    def wx(x): return x * CELL + OX
    @staticmethod
    def wy(y): return y * CELL + OY

    def surface_z(s, x, y, layer=None):
        c = s.at(x, y)
        if layer == 1 or (layer is None and not s.walk(c) and s.deck(c)): return s.deck(c) * LEVEL + OZ
        return c['h'] * LEVEL + (LEVEL / 2 if c['t'] == 'r' else 0) + OZ

    def centre(s, x, y, dz=0.0):
        return [s.wx(x + 0.5), s.wy(y + 0.5), s.surface_z(x, y) + dz]


def rects(cells, key):
    """Greedy rectangles over a set of (x, y) cells with equal key(x, y). Returns (x, y, w, h)."""
    left = set(cells); out = []
    for y, x in sorted((y, x) for x, y in cells):
        if (x, y) not in left: continue
        k = key(x, y); w = 1
        while (x + w, y) in left and key(x + w, y) == k: w += 1
        h = 1
        while all((x + i, y + h) in left and key(x + i, y + h) == k for i in range(w)): h += 1
        for i in range(w):
            for j in range(h): left.discard((x + i, y + j))
        out.append((x, y, w, h))
    return out


def plan(M):
    P = {'name': M.name, 'id': M.id, 'styles': M.styles, 'offset': [OX, OY, OZ], 'vs': M.vs}
    sides = (0, 1) if M.vs else (0,)
    rifts = [[m for m in M.markers if m['k'] == 'rift' and m.get('s', 0) == sd] for sd in sides]
    if M.vs:
        assert all(len(r) == 1 for r in rifts), "a VS map needs exactly one rift on the left half"
    else:
        assert len(rifts[0]) == 1, "the map needs exactly one rift"
    rifts = [r[0] for r in rifts]; rift = rifts[0]
    spawns = [m for m in M.markers if m['k'] == 'spawn']
    assert spawns, "the map needs at least one orc spawn"
    if M.vs: assert len(spawns) <= 28, "a VS map can have at most 14 orc spawns per side"
    starts = [next((m for m in M.markers if m['k'] == 'start' and m.get('s', 0) == sd), None) for sd in sides]
    start = starts[0]
    W = WALLS[M.styles['wall']]
    # walls are built the way the game builds its own: from the stone columns of the wall kit (BP_Column_Square_1_x
    # in the base game, 3 x 3 m footprint, 3 / 6 / 12 m tall, flat faces exactly on the cell edge, a trap grid on every
    # face from the floor to the top). One column stack per wall cell, never stretched; the trap areas lie on the cell
    # edges, so corners, ends and thin walls need no special cases. (The old panel walls with their footings, recesses,
    # cores and set-backs are kept below for reference but are off.)
    COLS = True
    RECESS = 0 if COLS else W['foot'] - W['face'] + 1   # boundary -> flat wall face
    INSET = RECESS + 4                          # (panel walls) wall core sits 4 cm behind the face
    XTRA = 0 if COLS else W['top'] - WALL       # (panel walls) the panel's cap above the 6 m mark
    WALLH = float(M.d.get('wallH') or 6) * 100.0               # wall height above the highest floor beside it
    CEILH = float(M.d.get('ceilH') or M.d.get('wallH') or 6) * 100.0   # ceiling height above its own floor
    CEIL_UNDER = W['top'] + 1                   # ceiling underside over a 0 m floor with the default heights
    # every wall cell's top: wall height above the highest floor in the 8 cells around it; thick walls take their
    # neighbours' height so the top stays flat
    def floor_top(c):
        g = c['h'] + (1 if c['t'] == 'r' else 0) if c['t'] in ('f', 'r') else None
        return max(g or 0, M.deckraw(c)) if M.deckraw(c) else g
    # decks need room under them
    for y in range(M.rows):
        for x in range(M.cols):
            c = M.at(x, y); b = M.deckraw(c)
            if b and c['t'] in ('f', 'r'):
                assert b - (c['h'] + (1 if c['t'] == 'r' else 0)) >= 4, "the deck at %d, %d needs at least 4 m of room above the floor" % (x, y)
    wbase = {}
    for y in range(M.rows):
        for x in range(M.cols):
            if M.at(x, y)['t'] != 'w': continue
            hs = [floor_top(M.at(x + dx, y + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
            hs = [h for h in hs if h is not None]
            wbase[(x, y)] = max(hs) if hs else None
    changed = True
    while changed:
        changed = False
        for (x, y), b in list(wbase.items()):
            if b is not None: continue
            nb = [wbase.get((x + dx, y + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
            nb = [h for h in nb if h is not None]
            if nb: wbase[(x, y)] = max(nb); changed = True
    WTOP = {k: (b or 0) * LEVEL + WALLH + XTRA for k, b in wbase.items()}
    if COLS:                                    # column walls: tops on the columns' 3 m steps
        WTOP = {k: math.ceil(v / 300.0 - 1e-6) * 300.0 for k, v in WTOP.items()}
    def ceil_z(c): return (M.deckraw(c) or c['h']) * LEVEL + CEILH + XTRA + 1      # ceiling underside over a flat cell (or its deck)
    # covered ceilings sit 75 cm higher than the plain wall top, and the walls around them rise with them: a wall
    # trap's top row right under the ceiling failed (the trap needs room above it)
    CEIL_LIFT = 0.0 if COLS else 75.0
    _cz = ceil_z
    def ceil_z(c): return _cz(c) + CEIL_LIFT
    for (x, y) in list(WTOP):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = M.at(x + dx, y + dy)
                if q.get('c') and q['t'] == 'f':
                    want = ceil_z(q) - 1
                    if 0 < want - WTOP[(x, y)] <= CEIL_LIFT + 1: WTOP[(x, y)] = want
    for k in list(WTOP):                         # extra height painted on a wall (Map Maker: raise a wall), e.g. a mountain
        wh = M.at(*k).get('wh')
        if wh: WTOP[k] += float(wh) * LEVEL
        if M.at(*k).get('b'): WTOP[k] = M.at(*k)['b'] * LEVEL - 58.0      # a wall carrying a deck: up to the deck's slab
    # upper walls: from their deck up by the wall height (or to the ceiling over that deck), on the columns' 3 m steps
    UWTOP = {}
    for y in range(M.rows):
        for x in range(M.cols):
            c = M.at(x, y)
            if c.get('bw') and M.deckraw(c):
                UWTOP[(x, y)] = math.ceil((M.deckraw(c) * LEVEL + (CEILH if c.get('c') else WALLH)) / 300.0 - 1e-6) * 300.0
    CURVE = curve_plan(M, WTOP)                  # smooth round walls (Map Maker: wall drawn with the circle shape)
    _cvs = M.d.get('curves') or []
    STAIRC = {q for q in CURVE['cells'] if M.at(*q)['t'] == 'w' and 0 < (M.at(*q).get('cv') or 0) <= len(_cvs)
              and curve_kind(_cvs[M.at(*q)['cv'] - 1]) == 'stairs'}
    foot = {(r['x'] + dx, r['y'] + dy) for r in rifts for dx in range(-RIFT_R, RIFT_R + 1) for dy in range(-RIFT_R, RIFT_R + 1)}

    # ---- navmesh boxes (map-local, boxes2tris applies the offset) ----
    boxes = []
    for y in range(M.rows):
        for x in range(M.cols):
            c = M.at(x, y); cx, cy = (x + 0.5) * CELL, (y + 0.5) * CELL
            if c['t'] == 'f' and c.get('br'): continue           # the VS bridge: heroes only, no navmesh
            if c['t'] == 'f':
                top = c['h'] * LEVEL
                boxes.append({'f': 'Floors', 'c': [cx, cy, (top - 30) / 2], 's': [CELL, CELL, top + 30]})
                if c.get('p'):                         # prop: a solid block on the cell (its top is cut off the navmesh)
                    ph = max(300.0, props.height(c['p']))
                    boxes.append({'f': 'Walls', 'c': [cx, cy, top + ph / 2], 's': [CELL, CELL, ph]})
            elif c['t'] == 'w':
                if (x, y) in STAIRC: continue          # under curved stairs: their sloped boxes (below) instead
                T = WTOP[(x, y)] - XTRA
                boxes.append({'f': 'Walls', 'c': [cx, cy, (T - 30) / 2], 's': [CELL, CELL, T + 30]})
            elif c['t'] == 'r':
                base = c['h'] * LEVEL
                if base > 0:
                    boxes.append({'f': 'Floors', 'c': [cx, cy, (base - 30) / 2], 's': [CELL, CELL, base + 30]})
                p = math.radians(RAMP_PITCH); T = 30.0
                dx, dy = DIRS[c['d']]
                boxes.append({'f': 'Ramps', 'c': [cx, cy, base + LEVEL / 2 - (T / 2) / math.cos(p)],
                              's': [RAMP_LEN, CELL, T], 'p': RAMP_PITCH, 'y': math.degrees(math.atan2(dy, dx))})
    for y in range(M.rows):                          # upper decks: a 60 cm slab, its top walkable
        for x in range(M.cols):
            c = M.at(x, y); b = M.deckraw(c)
            if b: boxes.append({'f': 'Floors', 'c': [(x + 0.5) * CELL, (y + 0.5) * CELL, b * LEVEL - 30], 's': [CELL, CELL, 60]})
            if b and c.get('bw'):                    # an upper wall: blocks the deck
                T = UWTOP[(x, y)] - b * LEVEL
                boxes.append({'f': 'Walls', 'c': [(x + 0.5) * CELL, (y + 0.5) * CELL, b * LEVEL + T / 2], 's': [CELL, CELL, T]})
    boxes += CURVE['nav']
    P['nav_boxes'] = boxes

    # ---- gameplay markers ----
    P['rift'] = M.centre(rift['x'], rift['y'])
    P['rifts'] = [M.centre(r['x'], r['y']) for r in rifts]
    P['spawns'] = [M.centre(m['x'], m['y']) for m in spawns]
    P['spawn_sides'] = [m.get('s', 0) for m in spawns]
    P['starts'] = [M.centre(st['x'], st['y']) if st else M.centre(r['x'], r['y']) for st, r in zip(starts, rifts)]
    P['start'] = P['starts'][0]
    routes = M.routes()
    bad = [i + 1 for i, r in enumerate(routes) if r is None]
    assert not bad, "spawn(s) %s cannot reach %s" % (bad, "their side's rift" if M.vs else "the rift")
    P['routes'] = [[[M.wx(x + 0.5), M.wy(y + 0.5), M.surface_z(x, y, L)] for x, y, L in r] for r in routes]
    # team banners (VS): along every spawn's route, at 10 %, 20 % ... 90 % of the way to its rift, on a wall beside the
    # route. Each: side, the wall face point (world), the floor height there, and the face's outward normal. The
    # referee hangs a banner in the side's colour there (spawned in game, no collision)
    if M.vs:
        bn = []; taken = []
        for m, r in zip([mk for mk in M.markers if mk['k'] == 'spawn'], routes):
            if not r: continue
            sd = m.get('s', 0)
            for k in range(1, 10):
                i0 = round(k * (len(r) - 1) / 10)
                for j in (i0, i0 + 1, i0 - 1, i0 + 2, i0 - 2):           # this cell, else the next ones along the route
                    if not 0 <= j < len(r): continue
                    x, y, L = r[j]
                    if L != 0 or M.at(x, y)['t'] != 'f': continue
                    hit = None
                    for dx, dy in DIRS:
                        if M.at(x + dx, y + dy)['t'] == 'w': hit = (dx, dy); break
                    if not hit: continue
                    if any(t[0] == sd and abs(t[1] - x) + abs(t[2] - y) < 3 for t in taken): break
                    dx, dy = hit                                       # towards the wall; the face looks back (-dx, -dy)
                    fx = (x + 0.5 + dx * 0.5) * CELL + dx * RECESS         # the cell edge, then RECESS into the wall (its face)
                    fy = (y + 0.5 + dy * 0.5) * CELL + dy * RECESS
                    bn.append({'side': sd, 'x': round(fx + OX, 1), 'y': round(fy + OY, 1), 'z': round(M.surface_z(x, y, 0), 1),
                               'nx': -dx, 'ny': -dy})
                    taken.append((sd, x, y)); break
        P['banners'] = bn
    if M.vs: P['mid_x'] = M.wx(M.mid + 0.5)
    if M.vs: P['mid_half'] = (getattr(M, 'midw', 0) + 0.5) * CELL if M.d.get('vsMid') in ('open', 'cliff') else 0.0   # the middle strip, each side of mid_x
    br = getattr(M, 'bridge', [])                    # the VS bridge's world Y range (the referee spares heroes on it)
    if br: P['bridge'] = [M.wy(min(br)), M.wy(max(br) + 1)]

    # ---- barricade walls (Map Maker 'bk' on a floor cell) ----
    # Looks: a 3 m wooden block (the wall kit's wood column, the same size as the stone columns of the walls), built
    # into the level below. Works: the game's own barricade (BP_Barricade, 3.1 x 3.1 m, i.e. one cell) inside it,
    # placed by the JWBarricades game mod when the level loads: blocked orcs attack it, and when it breaks the mod
    # removes the wooden block. The cell stays walkable floor in the navmesh (orcs plan their route through it).
    # barricades.txt gets one line per cell: the cell centre and its floor top.
    bars = []
    for y in range(M.rows):
        for x in range(M.cols):
            c = M.at(x, y)
            if not c.get('bk') or c.get('gt') or c['t'] != 'f' or c.get('p') or c.get('br'): continue
            bars.append({'x': round(M.wx(x + 0.5), 1), 'y': round(M.wy(y + 0.5), 1), 'z': round(c['h'] * LEVEL + OZ, 1), 'yaw': 0, 'g': 0})
    # ---- gates (Map Maker 'gt' on floor cells) ----
    # Each run of joined gate cells is one gate: the castle's portcullis across it (stretched to the run's width),
    # with one hidden barricade per cell. The cells share a gate number (g): when orcs break any of them, the
    # JWBarricades mod lifts the portcullis away and removes the gate's other barricades, so the whole gate opens.
    gates = []; seen = set()
    isgate = lambda q: (0 <= q[0] < M.cols and 0 <= q[1] < M.rows and M.at(*q).get('gt') and M.at(*q)['t'] == 'f'
                        and not M.at(*q).get('p') and not M.at(*q).get('br'))
    for y in range(M.rows):
        for x in range(M.cols):
            if (x, y) in seen or not isgate((x, y)): continue
            grp, st = [], [(x, y)]
            while st:
                q = st.pop()
                if q in seen or not isgate(q): continue
                seen.add(q); grp.append(q); st += [(q[0] + 1, q[1]), (q[0] - 1, q[1]), (q[0], q[1] + 1), (q[0], q[1] - 1)]
            gid = len(gates) + 1
            xs, ys = [q[0] for q in grp], [q[1] for q in grp]
            w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            z = max(M.at(*q)['h'] for q in grp) * LEVEL + OZ
            dk = [M.deckraw(M.at(*q)) for q in grp if M.deckraw(M.at(*q))]           # a bridge over the gate: the portcullis fits under it
            hz = min(1.8, (min(dk) * LEVEL - 60.0 - (z - OZ)) / 635.0) if dk else 1.0     # fills the arch up to the bridge
            gates.append({'g': gid, 'x': round(M.wx((min(xs) + max(xs) + 1) / 2), 1), 'y': round(M.wy((min(ys) + max(ys) + 1) / 2), 1),
                          'z': round(z, 1), 'yaw': 0 if w >= h else 90, 'w': round(max(w, h) * CELL, 1), 'hz': round(hz, 3)})
            for q in sorted(grp):
                bars.append({'x': round(M.wx(q[0] + 0.5), 1), 'y': round(M.wy(q[1] + 0.5), 1), 'z': round(M.at(*q)['h'] * LEVEL + OZ, 1), 'yaw': 0, 'g': gid})
    P['barricades'] = bars
    P['gates'] = gates

    # ---- trap surfaces ----
    surf = []
    nt = lambda x, y: bool(M.at(x, y).get('n'))          # 'No traps' cells
    bk = lambda x, y: bool(M.at(x, y).get('bk') or M.at(x, y).get('gt'))   # barricade / gate cells: the game's barricades stand there, no floor traps
    floor_cells = [(x, y) for y in range(M.rows) for x in range(M.cols) if M.at(x, y)['t'] == 'f' and (x, y) not in foot and not nt(x, y) and not M.at(x, y).get('p') and not bk(x, y)
                   and (x, y) not in CURVE['walk']]
    for x, y, w, h in rects(floor_cells, lambda x, y: M.at(x, y)['h']):
        z = M.at(x, y)['h'] * LEVEL + 5 + OZ
        surf.append({'type': 'floor', 'center': [M.wx(x + w / 2), M.wy(y + h / 2), z], 'size': [w * CELL, h * CELL]})
    deck_cells = [(x, y) for y in range(M.rows) for x in range(M.cols) if M.deck(M.at(x, y)) and not nt(x, y)]
    for x, y, w, h in rects(deck_cells, lambda x, y: M.deck(M.at(x, y))):
        surf.append({'type': 'floor', 'center': [M.wx(x + w / 2), M.wy(y + h / 2), M.deck(M.at(x, y)) * LEVEL + 5 + OZ], 'size': [w * CELL, h * CELL]})
    # wall faces next to floor or ramp; bottom of the grid = highest walkable point beside it
    # the wall panels up a face: (bottom, top, set back). 6 m panels; taller walls stretch one panel up to 1.6x, then
    # stack two or more. Beside an upper deck: one stack up to the deck and one from the deck up (its footing on the
    # deck). A stacked panel above another is set back by its footing's reach, so its footing doesn't stick out of
    # the wall halfway up (that ledge blocked every trap across it, e.g. on the tall walls along stairs)
    SETBACK = 0 if COLS else (W['foot'] - W['face'] + 1 if W['foot'] > W['face'] else 0)
    def wall_pieces(z0base, wt, dk):
        if COLS:                                # one flat face from the floor to the top (an upper deck splits it)
            return [(z0base, dk * LEVEL, False, 1.0), (dk * LEVEL, wt, False, 1.0)] if dk and z0base < dk * LEVEL < wt - 100 else [(z0base, wt, False, 1.0)]
        """The wall panels of one face, bottom to top: (z0, z1, set back?, height scale). A face's panels start at the
        floor beside it (below that the floor hides the wall core): most walls are then one panel at its own size.
        A face up to 2 panels tall is one stretched panel (no seam: a seam cost a trap row); taller ones get equal pieces; the upper ones are set back (SETBACK) so the
        upper panel's foot doesn't stick out halfway up the wall. An upper deck beside the face splits it there."""
        segs = [(z0base, dk * LEVEL), (dk * LEVEL, wt)] if dk and z0base < dk * LEVEL < wt - 100 else [(z0base, wt)]
        out = []
        for z0, z1 in segs:
            hgt = z1 - z0
            if hgt <= 1: continue
            stack = 1 if hgt <= 2.0 * W['top'] + 1 else math.ceil(hgt / (1.3 * W['top']) - 1e-9)
            z = z0
            for i in range(stack):
                h_ = hgt / stack
                out.append((z, z + h_, i > 0 and SETBACK > 0, h_ / W['top'])); z += h_
        return out
    # a stair flight (ramp cells joined to each other) starts its wall panels at its lowest step, so the wall along the
    # stairs is one panel instead of one stepped panel per step
    flight = {}
    for y in range(M.rows):
        for x in range(M.cols):
            if M.at(x, y)['t'] != 'r' or (x, y) in flight: continue
            comp, st = [], [(x, y)]
            while st:
                q = st.pop()
                if q in comp or not (0 <= q[0] < M.cols and 0 <= q[1] < M.rows) or M.at(*q)['t'] != 'r': continue
                comp.append(q); st += [(q[0] + 1, q[1]), (q[0] - 1, q[1]), (q[0], q[1] + 1), (q[0], q[1] - 1)]
            lo = min(M.at(*q)['h'] for q in comp)
            for q in comp: flight[q] = lo
    def panel_start(c, at=None):                # where a face's panels start: the floor beside it (0 next to a pit)
        if c['t'] == 'r' and at in flight: return flight[at] * LEVEL
        return c['h'] * LEVEL if c['t'] in ('f', 'r') else 0.0
    runs = {}
    for y in range(M.rows):
        for x in range(M.cols):
            if M.at(x, y)['t'] != 'w' or M.at(x, y).get('ws') == 'rock' or (x, y) in CURVE['cells']: continue     # rock and round walls take no traps
            for s, (dx, dy) in enumerate(DIRS):
                nb = M.at(x + dx, y + dy)
                if nt(x, y) or nt(x + dx, y + dy): continue
                line = x + (1 if dx > 0 else 0) if dx else y + (1 if dy > 0 else 0)
                along = y if dx else x
                dk = M.deckraw(nb)
                # (floor height beside, top of this grid): under an upper deck the grid stops below its slab, and the
                # deck gets a grid of its own from the deck up (one grid through the slab put the upper panel's
                # footing and the slab in the way of the deck's lowest traps)
                if M.walk(nb):
                    hb = (nb['h'] + (1 if nb['t'] == 'r' else 0)) * LEVEL
                    # under a ceiling the grid stops 58 cm below it too (a trap's top row against the ceiling fails)
                    gt = dk * LEVEL - 58 if dk else (min(WTOP[(x, y)], ceil_z(nb) - (1 if COLS else 58)) if nb.get('c') and nb['t'] == 'f' else WTOP[(x, y)])
                    runs.setdefault((s, line, hb, gt, WTOP[(x, y)], dk, panel_start(nb, (x + dx, y + dy))), []).append(along)
                if dk and M.deck(nb):
                    runs.setdefault((s, line, dk * LEVEL, WTOP[(x, y)], WTOP[(x, y)], dk, panel_start(nb, (x + dx, y + dy))), []).append(along)
    for (s, line, hb, wt, wtop, dk, pst), al in sorted(runs.items()):
        al.sort(); groups = [[al[0]]]
        for a in al[1:]:
            if a == groups[-1][-1] + 1: groups[-1].append(a)
            else: groups.append([a])
        dx, dy = DIRS[s]; yaw = math.degrees(math.atan2(dy, dx))
        wf = line - 1 if (dx > 0 or dy > 0) else line            # the wall cells' column (dx) or row (dy)
        def wcell(a, front=0):
            cx, cy = (wf + dx * front, a) if dx else (a, wf + dy * front)
            return M.at(cx, cy)['t'] == 'w' if (0 <= cx < M.cols and 0 <= cy < M.rows) else True
        def end_kind(a):
            # what the face meets past this end: 'out' = the wall ends (outside corner: its face turns away),
            # 'in' = another wall stands in front (inside corner: that wall's face), else the face just goes on
            if not wcell(a): return 'out'
            return 'in' if wcell(a, 1) else 'straight'
        # the grid splits where a set-back panel starts: below it on the face, above it on the set-back face
        bands = []
        for z0, z1, back, _ in wall_pieces(pst, wtop, dk):
            if bands and bands[-1][2] == back: bands[-1][1] = z1
            else: bands.append([z0, z1, back])
        for g in groups:
          for z0, z1, back in bands:
            bottom = max(hb, z0) + (0 if COLS else W['zb'])           # the wall kit's lowest trap height, above the floor (or footing)
            top = min(wt, z1)
            H = math.floor((top - bottom) / TILE) * TILE
            if H < 2 * TILE: continue
            # the grid covers the face as it is seen: the flat face sits RECESS inside the wall cell, so at an outside
            # corner it stops RECESS short of the cell edge and at an inside corner it runs RECESS past it (to the
            # other wall's face). A whole number of tiles, flush with a corner (outside corners first): the corner
            # tiles used to hang 26 cm off an outside corner or stop short of an inside one, and traps failed there.
            k0, k1 = end_kind(g[0] - 1), end_kind(g[-1] + 1)
            sh = {'out': RECESS, 'in': -RECESS, 'straight': 0}
            a0, a1 = g[0] * CELL + sh[k0], (g[-1] + 1) * CELL - sh[k1]
            L = math.floor((a1 - a0) / TILE + 1e-6) * TILE
            if L < TILE: continue
            if k0 == 'out' or (k0 == 'in' and k1 != 'out'): s0 = a0
            elif k1 in ('out', 'in'): s0 = a1 - L
            else: s0 = a0
            # the grid starts at its bottom (the floor beside it): any leftover that doesn't make a whole tile is at the
            # top. Anchored at the top, odd heights (ramps beside, wall tops above floors) lost the row next to the floor.
            zc = bottom + H / 2 + OZ
            rc = RECESS + (SETBACK if back else 0)
            # both ends at a corner and a leftover that isn't a whole tile: two grids, one flush with each end, the
            # leftover between them. One grid flush with one end only left the other end of the wall without traps.
            n = round(L / TILE)
            if k0 != 'straight' and k1 != 'straight' and (a1 - a0) - L > 1 and n >= 2:
                n0 = n // 2
                parts = [(a0, n0 * TILE), (a1 - (n - n0) * TILE, (n - n0) * TILE)]
            else:
                parts = [(s0, L)]
            for p0, pl in parts:
                mid = p0 + pl / 2
                c = [line * CELL - dx * rc + OX, mid + OY, zc] if dx else [mid + OX, line * CELL - dy * rc + OY, zc]
                surf.append({'type': 'wall', 'center': c, 'size': [pl, H], 'yaw': yaw})
    # steps between floors (a landing 3 m or more above the floor next to it) take wall traps on their side face
    steps = {}
    for y in range(M.rows):
        for x in range(M.cols):
            a = M.at(x, y)
            if a['t'] != 'f' or nt(x, y) or a.get('p'): continue
            for s_, (dx, dy) in enumerate(DIRS):
                bx, by = x + dx, y + dy
                if not (0 <= bx < M.cols and 0 <= by < M.rows): continue
                b = M.at(bx, by)
                if b['t'] != 'f' or nt(bx, by) or b['h'] > a['h'] - 3: continue
                line = x + (1 if dx > 0 else 0) if dx else y + (1 if dy > 0 else 0)
                steps.setdefault((s_, line, b['h'], a['h']), []).append(y if dx else x)
    for (s_, line, lo, hi), al in sorted(steps.items()):
        al.sort(); groups = [[al[0]]]
        for a_ in al[1:]:
            if a_ == groups[-1][-1] + 1: groups[-1].append(a_)
            else: groups.append([a_])
        dx, dy = DIRS[s_]; yaw = math.degrees(math.atan2(dy, dx))
        for g in groups:
            L = len(g) * CELL; H = math.floor((hi - lo) * LEVEL / TILE) * TILE
            if H < 2 * TILE: continue
            mid = (g[0] * CELL + L / 2); zc = lo * LEVEL + H / 2 + OZ
            c = [line * CELL - dx * 1 + OX, mid + OY, zc] if dx else [mid + OX, line * CELL - dy * 1 + OY, zc]
            surf.append({'type': 'wall', 'center': c, 'size': [L, H], 'yaw': yaw})
    # upper walls: their faces beside a walkable deck at the same height, from the deck to the wall top
    uruns = {}
    for (x, y), top in UWTOP.items():
        if nt(x, y): continue
        b = M.deckraw(M.at(x, y))
        for s_, (dx, dy) in enumerate(DIRS):
            nb = M.at(x + dx, y + dy)
            if M.deck(nb) != b or nt(x + dx, y + dy): continue
            line = x + (1 if dx > 0 else 0) if dx else y + (1 if dy > 0 else 0)
            uruns.setdefault((s_, line, b, top), []).append(y if dx else x)
    for (s_, line, b, top), al in sorted(uruns.items()):
        al.sort(); groups = [[al[0]]]
        for a_ in al[1:]:
            if a_ == groups[-1][-1] + 1: groups[-1].append(a_)
            else: groups.append([a_])
        dx, dy = DIRS[s_]; yaw = math.degrees(math.atan2(dy, dx))
        for g in groups:
            L = len(g) * CELL; H = math.floor((top - b * LEVEL) / TILE) * TILE
            if H < 2 * TILE: continue
            mid = g[0] * CELL + L / 2; zc = b * LEVEL + H / 2 + OZ
            c = [line * CELL - dx * 1 + OX, mid + OY, zc] if dx else [mid + OX, line * CELL - dy * 1 + OY, zc]
            surf.append({'type': 'wall', 'center': c, 'size': [L, H], 'yaw': yaw})
    # the underside of a deck over a walkable floor (a tunnel roof, seen from inside the tunnel) takes ceiling traps
    under = [(x, y) for y in range(M.rows) for x in range(M.cols)
             if M.deckraw(M.at(x, y)) and M.at(x, y)['t'] in ('f', 'r') and not nt(x, y)]
    for x, y, w, h in rects(under, lambda x, y: M.deckraw(M.at(x, y))):
        surf.append({'type': 'ceiling', 'center': [M.wx(x + w / 2), M.wy(y + h / 2), M.deckraw(M.at(x, y)) * LEVEL - 58 - 6 + OZ],
                     'size': [w * CELL, h * CELL]})
    ceil_cells = [(x, y) for y in range(M.rows) for x in range(M.cols) if M.at(x, y)['c'] and (M.walk(M.at(x, y)) or M.at(x, y).get('p'))]
    flat_ceil = [q for q in ceil_cells if M.at(*q)['t'] == 'f']
    for x, y, w, h in rects([q for q in flat_ceil if not nt(*q)], lambda x, y: M.at(x, y)['h']):
        surf.append({'type': 'ceiling', 'center': [M.wx(x + w / 2), M.wy(y + h / 2), ceil_z(M.at(x, y)) - 6 + OZ], 'size': [w * CELL, h * CELL]})
    P['surfaces'] = surf

    # ---- kit pieces for Unreal ----
    pieces = []
    def put(mesh, loc, rot=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0), tag=''):
        pieces.append({'m': mesh, 'l': [round(v, 3) for v in loc], 'r': [round(v, 4) for v in rot], 's': [round(v, 5) for v in scale], 't': tag})

    # Floor style per cell: a cell's own 'fs' (painted in the Map Maker) or the map's floor style. Each style is tiled
    # on its own; a cell of another style at the same height counts as an obstacle, so tiles never overlap styles.
    def fstyle(c): return c.get('fs') if c.get('fs') in FLOORS else M.styles['floor']
    def small(st):                                                   # smallest piece (ramps): (cells x, cells y, mesh)
        sq_ = [(n, k, m) for n, k, m in FLOORS[st] if n == k]
        return sq_[-1] if sq_ else min(FLOORS[st], key=lambda p: p[0] * p[1])
    # 1. big square tiles on a fixed world grid (blocks start at multiples of n), so the kit pattern lines up across the
    #    map. A tile may also lie under walls and higher floors (hidden there).
    # 2. what is left: the real smaller kit pieces (both orientations), placed only where they fit exactly.
    # 3. single cells nothing fits: the smallest piece shrunk to one cell.
    floors = {(x, y) for y in range(M.rows) for x in range(M.cols) if M.at(x, y)['t'] == 'f' and not M.at(x, y).get('br') and (x, y) not in CURVE['walk']}
    cur = [None]                                                     # style being tiled
    def hides(x, y, h):
        if not (0 <= x < M.cols and 0 <= y < M.rows): return False
        c = M.at(x, y)
        return c['t'] == 'w' or (c['t'] == 'f' and (c['h'] > h or (c['h'] == h and fstyle(c) == cur[0])))
    def tile(cx, cy, mesh, x0, y0, h, turned, k=1.0):
        sc = (k, k, 1.0); z = h * LEVEL + OZ - (WATER_BED if cur[0] == 'water' else 0.0)
        if not turned: put(mesh, (M.wx(x0), M.wy(y0), z), scale=sc, tag='Floor')
        else: put(mesh, (M.wx(x0 + cy), M.wy(y0), z), rot=(0.0, 90.0, 0.0), scale=sc, tag='Floor')
    for st in sorted({fstyle(M.at(x, y)) for x, y in floors}):
        cur[0] = st; fl = FLOORS[st]
        sq = [(n, m) for n, k, m in fl if n == k]
        left = {q for q in floors if fstyle(M.at(*q)) == st}
        for n, m in sq:
            if n < 2: continue
            for by in range(0, M.rows, n):
                for bx in range(0, M.cols, n):
                    blk = [(bx + i, by + j) for j in range(n) for i in range(n)]
                    for h in sorted({M.at(*b)['h'] for b in blk if b in left}):
                        if all(hides(x, y, h) for x, y in blk):
                            tile(n, n, m, bx, by, h, False)
                            for b in blk:
                                if b in left and M.at(*b)['h'] == h: left.discard(b)
        # real pieces, then the same pieces at half size (pattern stays square, just finer), biggest first
        cand = [(cx, cy, m, 1.0) for cx, cy, m in fl] + [(cx // 2, cy // 2, m, 0.5) for cx, cy, m in fl if cx % 2 == 0 and cy % 2 == 0]
        cand.sort(key=lambda p: (-p[0] * p[1], p[3] != 1.0))
        for cx, cy, m, k in cand:
            for turned in ((False, True) if cx != cy else (False,)):
                w, d = (cy, cx) if turned else (cx, cy)
                for x0, y0 in sorted(left, key=lambda p: (p[1], p[0])):
                    if (x0, y0) not in left: continue
                    h = M.at(x0, y0)['h']
                    cells = [(x0 + i, y0 + j) for j in range(d) for i in range(w)]
                    if all(((c in left and M.at(*c)['h'] == h) or (c not in left and c not in floors and hides(c[0], c[1], h))
                            or (c not in left and c in floors and M.at(*c)['h'] > h)) for c in cells) and \
                            sum(1 for c in cells if c in left) * 2 >= len(cells):
                        tile(cx, cy, m, x0, y0, h, turned, k)
                        for c in cells:
                            if c in left and M.at(*c)['h'] == h: left.discard(c)
        # single cells: the piece that needs the least stretching (planks and cobbles may stretch, patterns may not)
        stretch_ok = st in ('wood', 'cobblestone', 'mud', 'dirt', 'grass', 'water', 'parquet', 'scattered', 'scattereddk', 'stonefloor', 'woodfloor', 'dirtB')
        one = min(fl, key=lambda p: (max(p[0], p[1]) if stretch_ok else max(p[0], p[1]) / min(p[0], p[1]), p[0] * p[1]))
        for x, y in sorted(left):
            put(one[2], (M.wx(x), M.wy(y), M.at(x, y)['h'] * LEVEL + OZ - (WATER_BED if st == 'water' else 0.0)), scale=(1 / one[0], 1 / one[1], 1), tag='Floor')
    # the VS bridge, built like the game's own garden bridge (BP_Bridge_4x2_Gardens_Patio): a deck of wooden planks
    # (WoodPlank_4x1_Floor_A), two square beams under its long edges (Wood_Square_1200W_A, laid down), wooden
    # railings along both sides (Wood_Railing_200C_A) and four posts at the ends reaching down into the ravine
    br = getattr(M, 'bridge', [])
    if br:
        x0, x1 = M.mid - M.midw, M.mid + M.midw + 1                 # the gap's cells; the deck reaches 1 m onto each side
        y0, y1 = min(br), max(br) + 1
        h = M.at(M.mid, y0)['h'] * LEVEL + OZ
        X0, X1 = M.wx(x0) - 100, M.wx(x1) + 100; L = X1 - X0
        for y in range(y0, y1):                                      # deck: one plank piece per 3 m row, stretched to L
            put(BRIDGE['deck'], (X0, M.wy(y), h - 4), scale=(L / 1200.0, 1.0, 1.0), tag='Bridge')
        for yy, side in ((M.wy(y0) + 45, -1), (M.wy(y1) - 45, 1)):   # beams under the long edges
            put(BRIDGE['beam'], (X0, yy, h - 70), rot=(-90.0, 0.0, 0.0), scale=(0.55, 0.55, L / 1200.0), tag='Bridge')
            n = max(1, round(L / 200.0))                             # railings, 2 m sections, stretched to fit
            for i in range(n):
                put(BRIDGE['rail'], (X0 + i * L / n, yy - side * 25, h), scale=(L / n / 202.0, 1.0, 1.0), tag='Bridge')
            for xx in (X0 + 40, X1 - 40):                            # posts down into the ravine
                put(BRIDGE['beam'], (xx, yy, OZ - 1500), scale=(0.6, 0.6, (h - OZ + 1500 - 70) / 1200.0), tag='Bridge')
    # round walls: one stack of stone columns per short piece of the circle, turned along it, a little longer than
    # the piece so neighbours overlap; then floor in the cells' corners that lie outside the round band (the floor
    # beside it, at that floor's height), so the round wall meets the floors without holes
    FOOT = 60.0     # walls and stairs reach 60 cm into the ground: the stone pieces' bevelled lower edges left a thin
                    # see-through line where they stood on the grass (nothing under the ground there)
    for (cx_, cy_, yaw, ln, th, top, bot) in CURVE['segs']:
        z = bot if bot > 0 else -FOOT
        while z < top - 1:
            hgt = 1200.0 if top - z >= 1200 else 600.0 if top - z >= 600 else 300.0
            put(COLUMN[hgt], (cx_ + OX, cy_ + OY, z + OZ), rot=(0.0, yaw, 0.0), scale=(ln / 300.0, th / 300.0, min(1.0, (top - z) / hgt)), tag='RoundWall')
            z += hgt
    # straight bridges: a 60 cm stone slab with the floor style on top and crenels along both sides
    for sp in spans_of(M):
        ax, ay = sp['x1'] * CELL, sp['y1'] * CELL; L = math.hypot(sp['x2'] - sp['x1'], sp['y2'] - sp['y1']) * CELL
        ux, uy = (sp['x2'] - sp['x1']) * CELL / L, (sp['y2'] - sp['y1']) * CELL / L; nx, ny = -uy, ux
        yaw = math.degrees(math.atan2(uy, ux)); W_ = sp['w'] * CELL; z = sp['h'] * LEVEL
        put(BLOCK, (ax + ux * L / 2 + OX, ay + uy * L / 2 + OY, z - 60.0 + OZ), rot=(0.0, yaw, 0.0), scale=(L / 300.0, W_ / 300.0, 60.0 / 300.0), tag='Bridge')
        st = M.styles['floor'] if M.styles['floor'] in FLOORS else 'stoneblock'
        one = min(FLOORS[st], key=lambda p_: p_[0] * p_[1])
        put(one[2], (ax - nx * W_ / 2 + OX, ay - ny * W_ / 2 + OY, z + 1.0 + OZ), rot=(0.0, yaw, 0.0),
            scale=(L / (one[0] * CELL), W_ / (one[1] * CELL), 1.0), tag='Bridge')
        for s_ in (1, -1):
            n_ = int(L // 300.0)
            for i in range(n_):
                t0 = (L - n_ * 300.0) / 2 + i * 300.0
                ex, ey = ax + ux * t0 + nx * s_ * W_ / 2, ay + uy * t0 + ny * s_ * W_ / 2
                if s_ > 0: ex, ey = ex - nx * 30.0, ey - ny * 30.0
                put(CRENEL, (ex + OX, ey + OY, z + OZ), rot=(0.0, yaw, 0.0), scale=(0.5, 1.0, 1.0), tag='Battlement')
    for (px_, py_, yaw, z) in CURVE['crenels']:              # crenels along round wall tops (half-length pieces, 3 m)
        put(CRENEL, (px_ + OX, py_ + OY, z + OZ), rot=(0.0, yaw, 0.0), scale=(0.5, 1.0, 1.0), tag='Battlement')
    for (sx_, sy_, yaw, ln, wd, top) in CURVE['steps']:     # curved stairs: solid stone steps, 20 cm each
        put(BLOCK, (sx_ + OX, sy_ + OY, OZ), rot=(0.0, yaw, 0.0), scale=(ln / 300.0, wd / 300.0, top / 300.0), tag='Stairs')
    for (x, y), top in sorted(CURVE['wfill'].items()):        # round wall cells beside a straight wall: a square block
        put(BLOCK, (M.wx(x + 0.5), M.wy(y + 0.5), OZ), scale=(298 / 300.0, 298 / 300.0, top / 300.0), tag='RoundWall')
    for (x, y), (h, st) in sorted(CURVE['fill'].items()):
        n_, k_, mesh_ = small(st)
        put(mesh_, (M.wx(x), M.wy(y), h * LEVEL + OZ), scale=(1.0 / n_, 1.0 / k_, 1.0), tag='RoundFill')
        if h > 0: put(BLOCK, (M.wx(x + 0.5), M.wy(y + 0.5), OZ), scale=(298 / 300.0, 298 / 300.0, (h * LEVEL - 5) / 300.0), tag='Support')
    # shallow water: the bed (mud) lies WATER_BED lower, one water surface per rectangle of water cells, 6 cm under the
    # floor's own height (orcs walk at the floor's height: they wade with their feet in it)
    wcells = [(x, y) for y in range(M.rows) for x in range(M.cols) if M.at(x, y)['t'] == 'f' and fstyle(M.at(x, y)) == 'water' and not M.at(x, y).get('br')]
    for x, y, w, h in rects(wcells, lambda x, y: M.at(x, y)['h']):
        wm = M.d.get('water') or 'puddle'
        if wm == 'ab': wm = 'hub' if y + h / 2 < M.rows / 2 else 'basin'
        z0 = M.at(x, y)['h'] * LEVEL + OZ
        if wm == 'basin':
            put(WATER_BASIN[0], (M.wx(x + w / 2), M.wy(y + h / 2), z0 - 8.0), scale=(w * CELL / WATER_BASIN[1], h * CELL / WATER_BASIN[2], 1.0), tag='Water')
        elif wm == 'hub':                        # one pool piece per cell, 1.5x so its (maybe round) edge covers the corners
            k_ = 1.5 * CELL / WATER_HUB[1]
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    put(WATER_HUB[0], (M.wx(xx + 0.5) - WATER_HUB[3] * k_, M.wy(yy + 0.5) - WATER_HUB[4] * k_, z0 - 8.0), scale=(k_, k_, 1.0), tag='Water')
        else:
            for dz in (-6.0, -14.0, -22.0):      # three layers: one puddle-water sheet alone is too clear, the stones showed through
                put(WATER[0], (M.wx(x + w / 2), M.wy(y + h / 2), z0 + dz), scale=(w * CELL / WATER[1], h * CELL / WATER[2], 1.0), tag='Water')
    # lily pads (and a few flowers) on some water cells, so a stream reads as water from far away
    if M.d.get('water') and M.d.get('water') != 'puddle':
        for (x, y) in wcells:
            hsh = (x * 73856093 ^ y * 19349663) & 0xffff
            if hsh % 5: continue
            put(LOTUS[1 if hsh % 3 == 0 else 0], (M.wx(x + 0.3 + (hsh % 7) / 16.0), M.wy(y + 0.3 + (hsh % 11) / 25.0), M.at(x, y)['h'] * LEVEL + OZ - 9.0),
                rot=(0.0, float(hsh % 360), 0.0), scale=(1.2, 1.2, 1.2), tag='Prop')
    # sloped banks: where a stream steps diagonally (a water cell with grass on two sides and in the corner between
    # them, water on the other two sides), a grass tile turned 45 degrees covers the water cell's half in that corner,
    # so the stream runs at 45 degrees instead of in steps (the tile is a 4.24 m square centred on the cell corner;
    # it overlaps the grass cells' halves 1.5 cm higher)
    def grassy(x_, y_, h_):
        if not (0 <= x_ < M.cols and 0 <= y_ < M.rows): return False
        c_ = M.at(x_, y_)
        return c_['t'] == 'f' and c_['h'] == h_ and fstyle(c_) == 'grass' and not c_.get('br') and not c_.get('b')
    wet = lambda x_, y_: 0 <= x_ < M.cols and 0 <= y_ < M.rows and M.at(x_, y_)['t'] == 'f' and fstyle(M.at(x_, y_)) == 'water'
    GR = FLOORS['grass'][0]
    for (x, y) in wcells:
        h = M.at(x, y)['h']
        if M.at(x, y).get('b'): continue
        for dx, dy in ((1, -1), (1, 1), (-1, 1), (-1, -1)):
            if grassy(x + dx, y, h) and grassy(x, y + dy, h) and grassy(x + dx, y + dy, h) and wet(x - dx, y) and wet(x, y - dy):
                cxw, cyw = M.wx(x + (1 if dx > 0 else 0)), M.wy(y + (1 if dy > 0 else 0))
                side = CELL * math.sqrt(2)
                put(GR[2], (cxw, cyw - side / 2 * math.sqrt(2), h * LEVEL + OZ + 1.5), rot=(0.0, 45.0, 0.0),
                    scale=(side / (GR[0] * CELL), side / (GR[1] * CELL), 1.0), tag='Bank')
    # battlements (map option 'bt'): the crenellated wall top along every floor edge 3 m or more above the ground beside it
    if M.d.get('bt'):
        for y in range(M.rows):
            for x in range(M.cols):
                c = M.at(x, y)
                if c['t'] != 'f' or c.get('br') or c['h'] < 3 or (x, y) in CURVE['walk']: continue
                for s_, (dx, dy) in enumerate(DIRS):
                    n = M.at(x + dx, y + dy)
                    if (x + dx, y + dy) in CURVE['cells']: continue
                    top = n['h'] if n['t'] == 'f' else n['h'] + 1 if n['t'] == 'r' else -99 if n['t'] == 'v' else None
                    if top is not None and M.deckraw(n): top = max(top, M.deckraw(n))     # a deck beside it (a bridge) at its height
                    if top is None or c['h'] - top < 3: continue
                    X0, Y0, X1, Y1, z = M.wx(x), M.wy(y), M.wx(x + 1), M.wy(y + 1), c['h'] * LEVEL + OZ
                    loc, yaw = {0: ((X0, Y0 + 30, z), 0.0), 2: ((X0, Y1, z), 0.0), 3: ((X0, Y0, z), 90.0), 1: ((X1 - 30, Y0, z), 90.0)}[s_]
                    put(CRENEL, loc, rot=(0.0, yaw, 0.0), scale=(0.5, 1.0, 1.0), tag='Battlement')
    # towers: castle walls made taller (Map Maker: raise a wall, 'wh') get crenels round their top where they stand
    # above what is beside them
    for y in range(M.rows):
        for x in range(M.cols):
            c = M.at(x, y)
            if c['t'] != 'w' or not c.get('wh') or c.get('ws') == 'rock' or (x, y) in CURVE['cells']: continue
            top = WTOP[(x, y)]
            for s_, (dx, dy) in enumerate(DIRS):
                nb = (x + dx, y + dy)
                if M.at(*nb)['t'] == 'w' and (not (0 <= nb[0] < M.cols and 0 <= nb[1] < M.rows) or WTOP.get(nb, 0) > top - 300): continue
                X0, Y0, X1, Y1, z = M.wx(x), M.wy(y), M.wx(x + 1), M.wy(y + 1), top + OZ
                loc, yaw = {0: ((X0, Y0 + 30, z), 0.0), 2: ((X0, Y1, z), 0.0), 3: ((X0, Y0, z), 90.0), 1: ((X1 - 30, Y0, z), 90.0)}[s_]
                put(CRENEL, loc, rot=(0.0, yaw, 0.0), scale=(0.5, 1.0, 1.0), tag='Battlement')
    # gates: the portcullis (the mod finds it by its mesh and position, hides it when the gate breaks)
    for gq in P.get('gates') or []:
        put(PORTCULLIS[0], (gq['x'], gq['y'], gq['z']), rot=(0.0, float(gq['yaw']), 0.0), scale=(gq['w'] / PORTCULLIS[1], 1.6, gq.get('hz', 1.0)), tag='Gate')
    # props on floor cells
    for y in range(M.rows):
        for x in range(M.cols):
            c = M.at(x, y)
            if c['t'] == 'f' and c.get('p') in props.PROPS:
                props.place(c['p'], c.get('pr', 0), M.wx(x + 0.5), M.wy(y + 0.5), c['h'] * LEVEL + OZ, put)
    # raised supports
    for y in range(M.rows):
        for x in range(M.cols):
            c = M.at(x, y)
            if c['t'] in ('f', 'r') and c['h'] > 0 and not c.get('br') and (x, y) not in CURVE['walk']:
                put(BLOCK, (M.wx(x + 0.5), M.wy(y + 0.5), OZ - FOOT), scale=(298 / 300.0, 298 / 300.0, (c['h'] * LEVEL - 5 + FOOT) / 300.0), tag='Support')
            elif c['t'] == 'r' and not c.get('br'):                  # stairs / a ramp on the ground: a footing under it
                put(BLOCK, (M.wx(x + 0.5), M.wy(y + 0.5), OZ - FOOT), scale=(298 / 300.0, 298 / 300.0, FOOT / 300.0), tag='Support')
            if c['t'] == 'r' and c.get('st'):                       # stairs: 5 stone steps of 20 cm over the cell
                dx, dy = DIRS[c['d']]
                for k in range(5):
                    t = (k + 0.5) / 5.0 - 0.5                        # step middle, -0.5 .. 0.5 along the uphill direction
                    cx_, cy_ = M.wx(x + 0.5) + dx * t * CELL, M.wy(y + 0.5) + dy * t * CELL
                    sx, sy = (CELL / 5 / 300.0, 298 / 300.0) if dx else (298 / 300.0, CELL / 5 / 300.0)
                    put(BLOCK, (cx_, cy_, c['h'] * LEVEL + OZ), scale=(sx, sy, (k + 1) * LEVEL / 5 / 300.0), tag='Stairs')
            elif c['t'] == 'r':
                dx, dy = DIRS[c['d']]; yaw = math.degrees(math.atan2(dy, dx))
                ly = (-dy, dx)                                        # local +Y for this yaw
                mx, my = M.wx(x + 0.5) - dx * CELL / 2, M.wy(y + 0.5) - dy * CELL / 2   # low edge midpoint
                small_nx, small_ny, small_mesh = small(fstyle(c))
                put(small_mesh, (mx - ly[0] * CELL / 2, my - ly[1] * CELL / 2, c['h'] * LEVEL + OZ),
                    rot=(RAMP_PITCH, yaw, 0.0), scale=(RAMP_LEN / (small_nx * CELL), 1 / small_ny, 1), tag='Ramp')
                # solid under the slope (else the wedge under a ramp is open and you see through to nothing):
                # 10 stone blocks stepping up under the ramp's surface
                for k in range(1, 10):
                    t = (k + 0.5) / 10.0 - 0.5
                    cx_, cy_ = M.wx(x + 0.5) + dx * t * CELL, M.wy(y + 0.5) + dy * t * CELL
                    sx, sy = (CELL / 10 / 300.0, 298 / 300.0) if dx else (298 / 300.0, CELL / 10 / 300.0)
                    put(BLOCK, (cx_, cy_, c['h'] * LEVEL + OZ - 25.0), scale=(sx, sy, (k * LEVEL / 10 + 25.0 - 12.0) / 300.0), tag='Support')
            if c['t'] == 'f' and c.get('bk') and not c.get('p') and not c.get('br'):      # barricade wall: a wooden block
                put(WOOD_BLOCK, (M.wx(x + 0.5), M.wy(y + 0.5), c['h'] * LEVEL + OZ), tag='Barricade')
            if c['t'] == 'w' and c.get('ws') == 'rock':
                # rock wall: cliff rocks instead of columns, a little bigger than the cell (neighbours overlap, no gaps),
                # turned a random quarter, stacked when the wall is tall (each rock up to about 7 m)
                # inside a mountain (walls on all 4 sides) the rocks start a little under the lowest neighbour's top:
                # the neighbours' rocks hide the rest, and the pieces may be taller (10 m)
                top = WTOP[(x, y)]; r = (x * 73856093 ^ y * 19349663) & 0xffff
                nbw = [WTOP.get((x + dx, y + dy)) for dx, dy in DIRS]
                z0 = max(0.0, min(nbw) - 450.0) if all(v is not None for v in nbw) else 0.0
                z0 = min(z0, max(0.0, top - 600.0)); span = top - z0
                n = max(1, math.ceil(span / (720.0 if z0 == 0 else 1000.0) - 1e-6))
                for k in range(n):
                    mesh, mx_, my_, sx_, sy_, hh = ROCKS[(r + k) % 2]
                    q = (r >> 3) + k * 3; yaw = 90.0 * (q % 4); turned = q % 2
                    fx_, fy_ = (sy_, sx_) if turned else (sx_, sy_)
                    kx, ky = CELL * 1.22 / fx_, CELL * 1.22 / fy_            # world footprint ~ 3.66 m square
                    scl = (ky, kx, span / n / hh * 1.04) if turned else (kx, ky, span / n / hh * 1.04)
                    a = math.radians(yaw); ox_ = mx_ * scl[0]; oy_ = my_ * scl[1]   # keep the rock's middle on the cell's middle
                    cxw = M.wx(x + 0.5) - (ox_ * math.cos(a) - oy_ * math.sin(a)); cyw = M.wy(y + 0.5) - (ox_ * math.sin(a) + oy_ * math.cos(a))
                    put(mesh, (cxw, cyw, OZ + z0 + k * span / n - 15), rot=(0.0, yaw, 0.0), scale=scl, tag='Rock')
            elif c['t'] == 'w' and (x, y) in CURVE['cells']:
                pass                                         # a round wall: built below along its circle
            elif c['t'] == 'w' and COLS:
                z = -FOOT; top = WTOP[(x, y)]                # a stack of stone columns, 12 / 6 / 3 m, from the ground up
                while z < top - 1:
                    hgt = 1200.0 if top - z >= 1200 else 600.0 if top - z >= 600 else 300.0
                    put(COLUMN[hgt], (M.wx(x + 0.5), M.wy(y + 0.5), z + OZ), scale=(1.0, 1.0, min(1.0, (top - z) / hgt)), tag='Wall')
                    z += hgt
            elif c['t'] == 'w':
                def solid(nx, ny): return not (0 <= nx < M.cols and 0 <= ny < M.rows) or M.at(nx, ny)['t'] == 'w'
                def exposed(dx, dy): return not solid(x + dx, y + dy)
                # a tall wall's upper panels are set back (SETBACK) into the wall: the core then sits behind those too,
                # else it stood in front of them (the darker stones near the top) and the traps there failed
                nbs = [M.at(x + ddx, y + ddy) for ddx, ddy in DIRS if 0 <= x + ddx < M.cols and 0 <= y + ddy < M.rows]
                nbs = [q for q in nbs if q['t'] != 'w']
                ins = INSET + (SETBACK if any(bk for q in nbs for _, _, bk, _ in wall_pieces(panel_start(q), WTOP[(x, y)], M.deck(q))) else 0)
                x0 = x * CELL + (ins if exposed(-1, 0) else 0); x1 = (x + 1) * CELL - (ins if exposed(1, 0) else 0)
                y0 = y * CELL + (ins if exposed(0, -1) else 0); y1 = (y + 1) * CELL - (ins if exposed(0, 1) else 0)
                # inside corners: walls on two sides with open floor diagonally between them. The faces sit inside
                # the cells, so a full core would stick out into that corner (and block the corner trap tiles): the
                # core is then two boxes that leave the corner notch free (the wall panels run on to fill it)
                notch = [(dx, dy) for dx in (-1, 1) for dy in (-1, 1)
                         if solid(x + dx, y) and solid(x, y + dy) and not solid(x + dx, y + dy)]
                boxes = [(x0, x1, y0, y1)]
                if notch:
                    bx0 = x0 + (ins if any(d == (-1, e) for d in notch for e in (-1, 1)) else 0)
                    bx1 = x1 - (ins if any(d == (1, e) for d in notch for e in (-1, 1)) else 0)
                    by0 = y0 + (ins if any(d == (e, -1) for d in notch for e in (-1, 1)) else 0)
                    by1 = y1 - (ins if any(d == (e, 1) for d in notch for e in (-1, 1)) else 0)
                    boxes = [(bx0, bx1, y0, y1), (x0, x1, by0, by1)]
                for x0, x1, y0, y1 in boxes:
                    put(CORE, ((x0 + x1) / 2 + OX, (y0 + y1) / 2 + OY, OZ),
                        scale=((x1 - x0) / 300.0, (y1 - y0) / 300.0, WTOP[(x, y)] / 600.0), tag='WallCore')
    # death pits and the VS ravine: rock cliffs (Split Stairs' cliff pack) down every edge of an empty cell inside the
    # map, 15 m deep, so a pit looks like a ravine and not a hole in the air. Anyone who falls in dies (the referee
    # kills everything that drops below P['killz']).
    filled = getattr(M, 'filled', set()) if M.d.get('fill') in FILLS else set()
    outside = set(); st = [(x, y) for x in range(M.cols) for y in (0, M.rows - 1)] + [(x, y) for y in range(M.rows) for x in (0, M.cols - 1)]
    midcols = set(range(M.mid - M.midw, M.mid + M.midw + 1)) if M.vs and M.d.get('vsMid') in ('open', 'cliff') else set()
    while st:                                                # empty cells joined to the map's edge (not counting the ravine)
        x, y = st.pop()
        if (x, y) in outside or not (0 <= x < M.cols and 0 <= y < M.rows) or x in midcols or M.at(x, y)['t'] != 'v': continue
        outside.add((x, y)); st += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    pits = {(x, y) for y in range(M.rows) for x in range(M.cols)
            if M.at(x, y)['t'] == 'v' and (x, y) not in filled and ((x, y) not in outside or x in midcols)}
    # the VS ravine runs on through the scenery ring around the map, to its end: the bridge is then the only way over
    if midcols and M.d.get('vsMid') == 'cliff':
        import envdeco
        R = (envdeco.ENVS.get(M.d.get('env')) or {}).get('ring', 0)
        for x in midcols:
            for y in list(range(-R, 0)) + list(range(M.rows, M.rows + R)): pits.add((x, y))
    P['pits'] = len(pits)
    if pits:
        # a gorge, 15 m deep: along every pit edge a solid stone backing wall (nothing to see through) with rough rocks
        # in front; the ravine's ends at the map's edge are closed the same way; the bottom is dirt with rocks,
        # bushes and a few trees
        import envdeco
        EM = envdeco.MESH
        DEPTH = 1500.0
        k = 0
        # the bridge's cells count as ravine below the deck: the ravine's side walls and its bottom run on under it
        brc = {(x, y) for y in range(M.rows) for x in range(M.cols) if M.at(x, y).get('br')}
        runs = {}                                            # straight runs of edges: (dx, dy, fixed line, top) -> positions
        for x, y in sorted(pits | brc):
            for dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if (nx, ny) in pits or (nx, ny) in brc: continue
                inmap = 0 <= nx < M.cols and 0 <= ny < M.rows
                c = M.at(nx, ny) if inmap else None
                if inmap and c['t'] == 'v': continue
                if inmap and c.get('br'): continue                   # the bridge: open below, no wall under it
                if not inmap and nx in midcols: continue             # the ravine's far ends: left open (no end wall)
                top = ((c['h'] * LEVEL if c['t'] in ('f', 'r') else 0.0) - 80 + OZ) if inmap else OZ - 5   # 80 cm under the floor's edge (floor traps sink in); outside the map up to the thin ground (else a slot to see through)
                runs.setdefault((dx, dy, x if dx else y, top), []).append(y if dx else x)
        # each straight run: a solid backing wall just behind the edge (nothing to see through), and in front of it big
        # rock cliffs stretched to cover the whole face from the bottom to the floor's edge, one per stretch of up to
        # 3 cells (the cliff mesh is 5 x 3 x 13 m: stretched along the edge and to the depth)
        CL = [(CLIFFS[0], 504.0, 1325.0), (CLIFFS[1], 396.0, 1198.0)]
        for (dx, dy, line, top), al in sorted(runs.items()):
            al.sort(); groups = [[al[0]]]
            for a in al[1:]:
                if a == groups[-1][-1] + 1: groups[-1].append(a)
                else: groups.append([a])
            BELOW = 150.0                                            # walls and cliffs reach under the dirt (no crack at the foot)
            hgt = top - (OZ - DEPTH) + BELOW
            for g in groups:
                a0, a1 = g[0], g[-1] + 1                             # cells a0 .. a1 along the edge
                if dx:
                    ex = (line + 0.5 + dx * 0.5) * CELL + OX
                    put(CORE, (ex + dx * 70, M.wy((a0 + a1) / 2), OZ - DEPTH - BELOW), scale=(0.4, (a1 - a0) * CELL / 300.0 + 0.1, hgt / 600.0), tag='Cliff')
                else:
                    ey = (line + 0.5 + dy * 0.5) * CELL + OY
                    put(CORE, (M.wx((a0 + a1) / 2), ey + dy * 70, OZ - DEPTH - BELOW), scale=((a1 - a0) * CELL / 300.0 + 0.1, 0.4, hgt / 600.0), tag='Cliff')
                # two layers so the rocks' ragged edges never show the stone behind: the back layer in pieces of up
                # to 2 cells, the front layer shifted by half a piece (its gaps sit over the back layer's rock) and
                # turned around, both reaching a little past the run's ends
                n = max(1, -(-(a1 - a0) // 2))
                seg = (a1 - a0) / n
                for layer in (0, 1):
                    starts = [a0 + i * seg for i in range(n)] if layer == 0 else [a0 - seg / 2 + i * seg for i in range(n + 1)]
                    for b0 in starts:
                        b1 = b0 + seg
                        b0c, b1c = max(b0, a0 - 0.15), min(b1, a1 + 0.15)
                        if b1c - b0c < 0.3: continue
                        k += 1
                        mesh, mw, mh = CL[k % 2]
                        mid_ = (b0c + b1c) / 2
                        sx = (b1c - b0c) * CELL * 1.35 / mw              # wide overlap with the neighbours
                        sz = hgt * 1.04 / mh
                        yaw0 = (180.0 if layer else 0.0) + (k * 37 % 15 - 7)
                        if dx:
                            px_, py_, yaw = ex + dx * 20 - dx * layer * 45, M.wy(mid_), 90.0 + yaw0   # (front layer 45 cm further out)
                        else:
                            px_, py_, yaw = M.wx(mid_), ey + dy * 20 - dy * layer * 45, 0.0 + yaw0
                        put(mesh, (px_, py_, top - hgt / 2 - layer * 30), rot=(0.0, yaw, 0.0), scale=(sx, 0.55, sz), tag='Cliff')
        # the bottom: dirt, and on some cells a rock, a rock group, a bush or a small tree
        dirt = envdeco.GROUND['dirt'][1]
        for x, y in sorted(pits | brc):
            # the dirt a little bigger than the cell (no seams), and a stone slab under it: no crack to the void below
            put(dirt, (M.wx(x - 0.05), M.wy(y - 0.05), OZ - DEPTH), scale=(0.55, 0.55, 1.0), tag='PitFloor')
            put(CORE, (M.wx(x + 0.5), M.wy(y + 0.5), OZ - DEPTH - 605), scale=(1.15, 1.15, 1.0), tag='PitFloor')
            r = (x * 73856093 ^ y * 19349663) % 100
            jx, jy = M.wx(x + 0.3 + (r % 5) * 0.1), M.wy(y + 0.3 + (r // 5 % 5) * 0.1)
            yaw = float(r * 37 % 360)
            if r < 22: put(EM['rockG'][0], (jx, jy, OZ - DEPTH + 60), rot=(0.0, yaw, 0.0), scale=(0.8 + r % 5 * 0.12,) * 3, tag='PitDeco')
            elif r < 38: put(EM['rocks'][0], (jx, jy, OZ - DEPTH), rot=(0.0, yaw, 0.0), scale=(1.5, 1.5, 1.5), tag='PitDeco')
            elif r < 55: put(EM['bush'][0], (jx, jy, OZ - DEPTH), rot=(0.0, yaw, 0.0), scale=(0.7, 0.7, 0.7), tag='PitDeco')
            elif r < 61: put(EM['conifer5'][0], (jx, jy, OZ - DEPTH), rot=(0.0, yaw, 0.0), scale=(0.65, 0.65, 0.65), tag='PitDeco')
            elif r < 70: put(EM['rockF'][0], (jx, jy, OZ - DEPTH + 50), rot=(0.0, yaw, 0.0), scale=(1.0, 1.0, 1.0), tag='PitDeco')
    P['killz'] = OZ - 400.0
    # team banners (VS): the game's large banner on the wall at each spot of P['banners']. The referee turns off their
    # collision, tints them in the side's colour and puts them exactly in place (it reads the mesh's real size)
    for q in P.get('banners') or []:
        put(BANNERS[q['side']], (q['x'] + q['nx'] * 20, q['y'] + q['ny'] * 20, q['z'] + 450), rot=(0.0, math.degrees(math.atan2(q['ny'], q['nx'])) - 90, 0.0), tag='JWBanner')
    # wall panels on every face that is not against another wall
    wl = W['pieces']
    faces = {}
    for y in range(M.rows if not COLS else 0):
        for x in range(M.cols):
            if M.at(x, y)['t'] != 'w': continue
            for s, (dx, dy) in enumerate(DIRS):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < M.cols and 0 <= ny < M.rows): continue
                if M.at(nx, ny)['t'] == 'w': continue
                line = x + (1 if dx > 0 else 0) if dx else y + (1 if dy > 0 else 0)
                faces.setdefault((s, line, WTOP[(x, y)], M.deck(M.at(nx, ny)), panel_start(M.at(nx, ny), (nx, ny))), []).append(y if dx else x)
    for (s, line, wt, dk, pst), al in sorted(faces.items()):
        al.sort(); groups = [[al[0]]]
        for a in al[1:]:
            if a == groups[-1][-1] + 1: groups[-1].append(a)
            else: groups.append([a])
        nx_, ny_ = DIRS[s]                                           # outward normal
        # yaw so that the style's outward side (local +Y or -Y) points along the normal
        yaw = {(0, 1): 0.0, (0, -1): 180.0, (1, 0): -90.0, (-1, 0): 90.0}[(nx_ * W['side'], ny_ * W['side'])]
        tx, ty = round(math.cos(math.radians(yaw))), round(math.sin(math.radians(yaw)))   # local +X in world
        wall_fixed = (line - 1 if (nx_ > 0 or ny_ > 0) else line)  # wall cell column (east/west faces) or row (north/south)
        def is_wall(a, front=0):
            wx_, wy_ = (wall_fixed + nx_ * front, a) if nx_ else (a, wall_fixed + ny_ * front)
            return M.at(wx_, wy_)['t'] == 'w' if (0 <= wx_ < M.cols and 0 <= wy_ < M.rows) else True
        def end_shift(a):
            if not is_wall(a): return RECESS                 # outside corner: stop at the other face
            if is_wall(a, 1): return -RECESS                 # inside corner: run on to the other wall's face
            return 0
        for g in groups:
            lo = g[0] * CELL + end_shift(g[0] - 1)
            hi = (g[-1] + 1) * CELL - end_shift(g[-1] + 1)
            pos, length = 0.0, hi - lo
            while pos < length - 1:
                rem = (length - pos) / CELL
                n, mesh = next(((n, m) for n, m in wl if n <= rem + 1e-6), wl[-1])
                k = min(n, rem)                                      # cells this piece covers
                along = (lo + pos) if (tx + ty) > 0 else (hi - pos)  # where this piece starts, walking along local +X
                off = -(W['foot'] + 1)                               # pivot line: footing ends 1 cm inside the wall cell
                if nx_ == 0:
                    px, py = along, line * CELL + ny_ * off
                else:
                    px, py = line * CELL + nx_ * off, along
                for z0, z1, back, zs in wall_pieces(pst, wt, dk):
                    sb = SETBACK if back else 0.0                        # set back into the wall (see wall_pieces)
                    put(mesh, (px - nx_ * sb + OX, py - ny_ * sb + OY, OZ + z0), rot=(0.0, yaw, 0.0), scale=(k / n, 1, zs), tag='Wall')
                pos += k * CELL
    # ceilings: every ceiling cell sits at its own floor height + the ceiling height. Walls around get covered too when
    # the ceiling meets their top (ceiling height = wall height), so the roof rests on them. Ramps get a slanted board.
    style = M.styles.get('ceiling')
    if style in CEILINGS and ceil_cells:
        C = CEILINGS[style]; cw, ch = C['cells']
        zc = {}
        for x, y in ceil_cells:
            c = M.at(x, y)
            z = ceil_z(c) if c['t'] == 'f' else (c['h'] + 1) * LEVEL + CEILH + XTRA + 1 + CEIL_LIFT
            if c['t'] == 'f': zc[(x, y)] = z
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n = (x + dx, y + dy)
                    if n in WTOP and abs(WTOP[n] + 1 - z) < 1: zc[n] = z
        def lay(x, y, w, h, sx, sy, z):
            for mesh, roll, dz, anchor in C['layers']:
                py = M.wy(y + h) if anchor == 'max' else M.wy(y)
                put(mesh, (M.wx(x), py, z + dz + OZ), rot=(0.0, 0.0, roll), scale=(sx, sy, 1), tag='Ceiling')
        for zv in sorted(set(zc.values())):
            left = {q for q, z in zc.items() if z == zv}
            for y in range(M.rows):
                for x in range(M.cols):
                    blk = [(x + i, y + j) for i in range(cw) for j in range(ch)]
                    if all(b in left for b in blk):
                        for b in blk: left.discard(b)
                        lay(x, y, cw, ch, 1, 1, zv)
            for x, y in sorted(left):
                lay(x, y, 1, 1, 1 / cw, 1 / ch, zv)
        plank = A + 'Floors/Mesh/WoodPlank_2x2_Floor_A'
        for x, y in ceil_cells:
            c = M.at(x, y)
            if c['t'] != 'r': continue
            dx, dy = DIRS[c['d']]; yaw = math.degrees(math.atan2(dy, dx)); ly = (-dy, dx)
            mx, my = M.wx(x + 0.5) - dx * CELL / 2, M.wy(y + 0.5) - dy * CELL / 2
            z = c['h'] * LEVEL + CEILH + XTRA + 1 + CEIL_LIFT + OZ; sc = (RAMP_LEN / (2 * CELL), 0.5, 1)
            # underside: the plank tile turned over (roll 180 flips its +Y side, so the pivot moves to the other edge)
            put(plank, (mx + ly[0] * CELL / 2, my + ly[1] * CELL / 2, z + 4), rot=(RAMP_PITCH, yaw, 180.0), scale=sc, tag='Ceiling')
            put(plank, (mx - ly[0] * CELL / 2, my - ly[1] * CELL / 2, z + 20), rot=(RAMP_PITCH, yaw, 0.0), scale=sc, tag='Ceiling')
    # upper decks: floor tiles at the deck height with a stone slab under them (the tunnel's roof)
    decks = {}
    for y in range(M.rows):
        for x in range(M.cols):
            b = M.deckraw(M.at(x, y))
            if b: decks.setdefault((b, fstyle(M.at(x, y))), set()).add((x, y))
    for (b, st), cells in sorted(decks.items()):
        for item in tile_set(M, cells, st, b * LEVEL, 'Deck'): put(*item)
        for x, y, w, h in rects(cells, lambda x, y: 0):
            put(BLOCK, (M.wx(x + w / 2), M.wy(y + h / 2), b * LEVEL - 58 + OZ), scale=(w * CELL / 300.0, h * CELL / 300.0, 28 / 300.0), tag='DeckSlab')
    # upper walls (Map Maker 'bw' on a deck cell): stone columns from the deck up, like the ground walls
    for (x, y), top in sorted(UWTOP.items()):
        z = M.deckraw(M.at(x, y)) * LEVEL
        while z < top - 1:
            hgt = 1200.0 if top - z >= 1200 else 600.0 if top - z >= 600 else 300.0
            put(COLUMN[hgt], (M.wx(x + 0.5), M.wy(y + 0.5), z + OZ), tag='UpperWall')
            z += hgt
    # fill: the empty area around (and optionally in) the map, decoration only: no navmesh, so orcs never walk on it
    fill = M.d.get('fill')
    if fill in FILLS:
        for item in fill_pieces(M, FILLS[fill], bool(M.d.get('fillPits'))): put(*item)
    # surroundings (decoration outside the map)
    if M.d.get('env'):
        import envdeco
        P['env_pieces'] = envdeco.decorate(M, M.d['env'], put, CELL=CELL, OZ=OZ)
    P['pieces'] = pieces
    return P


if __name__ == '__main__':
    M = Map(json.load(open(sys.argv[1], encoding='utf-8')))
    P = plan(M)
    json.dump(P, open(sys.argv[2], 'w'), indent=1)
    from collections import Counter
    print(M.name, M.cols, 'x', M.rows, M.styles)
    print('nav boxes', len(P['nav_boxes']), '| routes', [len(r) for r in P['routes']])
    print('surfaces', Counter(s['type'] for s in P['surfaces']))
    print('pieces', Counter(p['t'] for p in P['pieces']), '| meshes', len({p['m'] for p in P['pieces']}))
