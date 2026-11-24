# Surroundings for a Map Maker map ("env" in the map file): ground around the map plus scenery placed outside it.
# Decoration only: no navmesh, no trap surfaces. Pieces are added to the plan like the kit pieces (tag 'Env').
# Sizes below were read from the game's own cooked meshes (render bounds, cm): min/max relative to the pivot.
import random, zlib

E = '/Game/Environments/'
A = E + 'Arch_Order/'
L = E + 'LandScapes/'
MESH = {
    # name: (path, (minx, miny, minz), (maxx, maxy, maxz))
    'core':     (A + 'Columns/Mesh/Column_Square_1_2_StoneWall_House_SM', (-150, -150, 0), (150, 150, 600)),
    'block':    (A + 'Courtyard/Mesh/Tower_Square_Stone_Castle_Courtyard_3x3_A', (-450, -450, 0), (450, 450, 450)),
    'attic':    (A + 'Roof/Mesh/Attic_B_2x3_Wood_ShingleC_SM_Union', (-304, -656, -78), (303, 191, 981)),
    'tower':    (A + 'Courtyard/Mesh/Courtyard_Stone_Tower_A_SM', (-320, -320, -75), (320, 320, 2325)),
    'towerroof': (A + 'Courtyard/Mesh/Tower_Terracotta_Roof_A_SM_Union', (-335, -335, -108), (342, 343, 849)),
    'ftower':   (A + 'Fortress/Coastal/Mesh/Fortress_Coastal_TowerSquareMed_3x_SM', (-450, -450, 0), (450, 450, 2700)),
    'crenel':   (A + 'Crenellation/Mesh/Crenellation_Coastal_4x_SM', (-605, -9, -65), (605, 109, 105)),
    'lamp':     (L + '3rdParty/Medieval_Village/Meshes/props/SM_lamppost_02', (-150, -21, 0), (73, 21, 504)),
    'rockpile': (A + 'Courtyard/Mesh/Courtyard_Rock_Pile_A_SM', (-305, -283, -2), (305, 283, 202)),
    'conifer1': (L + '3rdParty/DreamscapeSeries/DreamscapeMountains/Meshes/Foliage/Trees/SM_Conifer_01', (-513, -530, -1), (515, 502, 1624)),
    'conifer5': (L + '3rdParty/DreamscapeSeries/DreamscapeMountains/Meshes/Foliage/Trees/SM_Conifer_05', (-396, -482, -16), (406, 462, 1100)),
    'treeE':    (L + '3rdParty/DreamscapeSeries/DreamscapeTower/Meshes/Trees/SM_Tree_E_01_WIP', (-708, -846, 0), (816, 720, 2491)),
    'treeF':    (L + '3rdParty/DreamscapeSeries/DreamscapeTower/Meshes/Trees/SM_Tree_F_01_WIP', (-371, -548, -20), (378, 507, 1364)),
    'rockG':    (L + 'Geology/rock/Mesh/Rock_G_SM', (-189, -160, -176), (185, 160, 176)),
    'rockF':    (L + 'Geology/rock/Mesh/Rock_F_SM', (-164, -124, -139), (164, 124, 139)),
    'rocks':    (L + 'Geology/RocksStones/Meshes/SM_rocks_group', (-177, -120, -11), (128, 112, 40)),
    'bush':     (L + 'Foliage/Bush/Mesh/Bush_Circle_01', (-162, -169, -12), (166, 179, 292)),
}
F = A + 'Floors/Mesh/'
GROUND = {          # (4x4 tile, smallest square tile, its size in cells)
    'cobble': (F + 'Floor_4x4_CobbleStone_SM', F + 'Floor_2x2_CobbleStone_SM', 2),
    'mud':    (F + 'Floor_4x4_Mud_SM', F + 'Floor_2x2_mud_SM', 2),
    'stone':  (F + 'Floor_4x4_StoneBlock_SM', F + 'Floor_2x2_StoneBlock_SM', 2),
    'dirt':   (A + 'Sewer/Mesh/Floor_Sewer_Dirt_4x4_SM', A + 'Sewer/Mesh/Floor_Sewer_Dirt_2x2_SM', 2),
}
ENVS = {
    'town':     dict(ground='cobble', ring=10, label='Town'),
    'forest':   dict(ground='mud', ring=10, label='Forest'),
    'fortress': dict(ground='stone', ring=9, label='Fortress'),
    'ground':   dict(ground='dirt', ring=8, label='Open ground'),
}


def decorate(M, env, put, CELL=300.0, OZ=0.0):
    """Ground ring + scenery around the map. put(mesh, loc, rot, scale, tag) as in mapv2.plan. Returns pieces added."""
    cfg = ENVS.get(env)
    if not cfg: return 0
    n0 = [0]
    def P(key, x, y, z=0.0, yaw=0.0, s=(1.0, 1.0, 1.0)):
        put(MESH[key][0] if key in MESH else key, (x, y, z + OZ), (0.0, yaw, 0.0), s, 'Env'); n0[0] += 1
    R = cfg['ring']; cols, rows = M.cols, M.rows
    wx = lambda cx: M.wx(cx); wy = lambda cy: M.wy(cy)
    rnd = random.Random(zlib.crc32((M.id + env).encode()))
    # void cells joined to the map's edge count as outside (ground goes there too); pits enclosed by the map stay holes
    out_void = set(); st = [(x, y) for x in range(cols) for y in (0, rows - 1)] + [(x, y) for y in range(rows) for x in (0, cols - 1)]
    while st:
        x, y = st.pop()
        if (x, y) in out_void or not (0 <= x < cols and 0 <= y < rows) or M.at(x, y)['t'] != 'v': continue
        out_void.add((x, y)); st += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    out_void -= getattr(M, 'filled', set())                # filled cells (the map's fill option) are not ground
    if getattr(M, 'vs', False) and M.d.get('vsMid') in ('open', 'cliff'):   # the VS middle gap / ravine stays open
        mid, mw = getattr(M, 'mid', -99), getattr(M, 'midw', 0)
        out_void = {(x, y) for x, y in out_void if abs(x - mid) > mw}
    band = (getattr(M, 'mid', -99), getattr(M, 'midw', 0)) if getattr(M, 'vs', False) and M.d.get('vsMid') == 'cliff' else None
    # inside the map, or the VS ravine running on through the ring (no ground or trees there)
    inside = lambda x, y: (0 <= x < cols and 0 <= y < rows and (x, y) not in out_void) or \
                          (band is not None and abs(x - band[0]) <= band[1])
    # distance (in cells, 8 directions) from every cell to the nearest map cell that is not outside
    from collections import deque
    dist = {}; q = deque()
    for y in range(rows):
        for x in range(cols):
            if inside(x, y): dist[(x, y)] = 0; q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n in dist or not (-R <= n[0] < cols + R and -R <= n[1] < rows + R): continue
                dist[n] = dist[(x, y)] + 1; q.append(n)
    # ---- ground: 4x4 tiles on a grid anchored at (-R, -R), single cells (the 2x2 tile shrunk) next to the map ----
    big, small, sn = GROUND[cfg['ground']]
    x0, y0, x1, y1 = -R, -R, cols + R, rows + R
    left = {(x, y) for y in range(y0, y1) for x in range(x0, x1) if not inside(x, y)}
    for by in range(y0, y1, 4):
        for bx in range(x0, x1, 4):
            blk = [(bx + i, by + j) for j in range(4) for i in range(4)]
            if all(b in left for b in blk):
                P(big, wx(bx), wy(by), -2.0); left.difference_update(blk)
    for by in range(y0, y1, 2):                       # 2x2 where they fit, then single cells
        for bx in range(x0, x1, 2):
            blk = [(bx + i, by + j) for j in range(2) for i in range(2)]
            if all(b in left for b in blk):
                P(small, wx(bx), wy(by), -2.0, s=(2.0 / sn, 2.0 / sn, 1.0)); left.difference_update(blk)
    for x, y in sorted(left):
        P(small, wx(x), wy(y), -2.0, s=(1.0 / sn, 1.0 / sn, 1.0))
    # ---- scenery: an occupancy grid of cells; nothing within 1 cell of the map ----
    used = set()
    def free(x, y, w, h, gap=1):
        for j in range(y - gap, y + h + gap):
            for i in range(x - gap, x + w + gap):
                if inside(i, j) or (i, j) in used: return False
        return x >= x0 and y >= y0 and x + w <= x1 and y + h <= y1
    def take(x, y, w, h):
        for j in range(y, y + h):
            for i in range(x, x + w): used.add((i, j))
    def ring_cells(d0, d1):                           # cells whose distance to the map is d0..d1 (Chebyshev)
        out = []
        for y in range(y0, y1):
            for x in range(x0, x1):
                # (the ravine through the ring is "inside" but has no distance of 0 outside the map: skip it, else
                # rocks and bushes were placed over it in the air)
                if d0 <= dist.get((x, y), 99) <= d1 and not inside(x, y): out.append((x, y))
        rnd.shuffle(out); return out
    def centre(x, y, w, h): return wx(x + w / 2.0), wy(y + h / 2.0)

    if env == 'town':
        for x, y in ring_cells(2, R - 3):             # houses: 2 x 3 cells (6 x 9 m) or turned
            turned = rnd.random() < 0.5; w, h = (3, 2) if turned else (2, 3)
            if not free(x, y, w, h, gap=0) or rnd.random() < 0.35: continue
            take(x, y, w, h); cx, cy = centre(x, y, w, h)
            floors = 1 if rnd.random() < 0.6 else 2; hz = 600.0 * floors
            # body: the house stone block stretched to 6 x 8.5 m (roof size), 6 or 12 m tall
            sx, sy = (850 / 300.0, 600 / 300.0) if turned else (600 / 300.0, 850 / 300.0)
            P('core', cx, cy, 0.0, s=(sx, sy, float(floors)))
            # roof (pivot is 2.32 m off the roof's middle along its length)
            if turned: P('attic', cx - 232.0, cy, hz, yaw=90.0)
            else: P('attic', cx, cy + 232.0, hz)
        for x, y in ring_cells(R - 2, R):             # a few towers at the back
            if not free(x, y, 2, 2, gap=1) or rnd.random() < 0.93: continue
            take(x, y, 2, 2); cx, cy = centre(x, y, 2, 2)
            P('tower', cx, cy, 75.0); P('towerroof', cx, cy, 75.0 + 2325.0 + 108.0)
        for x, y in ring_cells(1, 1):                 # lampposts and rubble along the map
            if rnd.random() < 0.1 and free(x, y, 1, 1, gap=0):
                take(x, y, 1, 1); cx, cy = centre(x, y, 1, 1); P('lamp', cx, cy, 0.0, yaw=rnd.choice((0, 90, 180, 270)))
            elif rnd.random() < 0.04 and free(x, y, 1, 1, gap=0):
                take(x, y, 1, 1); cx, cy = centre(x, y, 1, 1); P('rockpile', cx, cy, 0.0, yaw=rnd.uniform(0, 360), s=(0.45, 0.45, 0.45))
    elif env == 'forest':
        trees = 0
        for x, y in ring_cells(2, R):                 # trees: 2 x 2 cells of room each (at most 90: they are heavy)
            if trees >= 90 or not free(x, y, 2, 2, gap=0) or rnd.random() < 0.3: continue
            trees += 1
            take(x, y, 2, 2); cx, cy = centre(x, y, 2, 2)
            k = rnd.choice(('conifer1', 'conifer1', 'conifer5', 'conifer5', 'treeF', 'treeE'))
            sc = rnd.uniform(0.55, 0.85) if k in ('conifer1', 'treeE') else rnd.uniform(0.7, 1.0)
            P(k, cx + rnd.uniform(-60, 60), cy + rnd.uniform(-60, 60), 0.0, yaw=rnd.uniform(0, 360), s=(sc, sc, sc))
        for x, y in ring_cells(1, R):                 # rocks and bushes between them
            if (x, y) in used or rnd.random() > 0.12: continue
            used.add((x, y)); cx, cy = centre(x, y, 1, 1)
            k = rnd.choice(('rockG', 'rockF', 'rocks', 'bush', 'bush'))
            sc = rnd.uniform(0.5, 0.9)
            z = -MESH[k][1][2] * sc * 0.6                 # centred pivots: sink the rock a bit into the ground
            P(k, cx, cy, z if k in ('rockG', 'rockF') else 0.0, yaw=rnd.uniform(0, 360), s=(sc, sc, sc))
    elif env == 'fortress':
        d = 3                                         # rampart: a ring of stone blocks 3 cells (9 m) out, 9 m tall
        xa, ya = -d - 3, -d - 3                                   # outer ring of 3x3-cell blocks
        def block(bx, by):
            cx, cy = centre(bx, by, 3, 3)
            P('block', cx, cy, 0.0); P('block', cx, cy, 450.0)
            take(bx, by, 3, 3)
        xs = list(range(xa, cols + d + 3, 3)); ys = list(range(ya, rows + d + 3, 3))
        for bx in xs: block(bx, ya); block(bx, ys[-1])
        for by in ys[1:-1]: block(xa, by); block(xs[-1], by)
        # crenellations along the top (12 m pieces, 1.2 m deep), on the outer edge
        top = 900.0
        for bx in xs:
            for by, yaw in ((ya, 180.0), (ys[-1], 0.0)):
                cx, cy = centre(bx, by, 3, 3); P('crenel', cx, cy + (450 - 60) * (1 if yaw == 0 else -1), top + 65.0, yaw=yaw, s=(900 / 1210.0, 1, 1))
        for by in ys[1:-1]:
            for bx, yaw in ((xa, 90.0), (xs[-1], -90.0)):
                cx, cy = centre(bx, by, 3, 3); P('crenel', cx + (450 - 60) * (-1 if yaw == 90 else 1), cy, top + 65.0, yaw=yaw, s=(900 / 1210.0, 1, 1))
        for bx, by in ((xa, ya), (xs[-1], ya), (xa, ys[-1]), (xs[-1], ys[-1])):   # corner towers, 27 m
            cx, cy = centre(bx, by, 3, 3); P('ftower', cx, cy, 0.0)
        for x, y in ring_cells(1, 2):                 # rubble between map and rampart
            if (x, y) in used or rnd.random() > 0.05: continue
            used.add((x, y)); cx, cy = centre(x, y, 1, 1); P('rockpile', cx, cy, 0.0, yaw=rnd.uniform(0, 360), s=(0.4, 0.4, 0.4))
        for x, y in ring_cells(d + 4, R):             # a few trees outside the walls
            if not free(x, y, 2, 2, gap=0) or rnd.random() < 0.85: continue
            take(x, y, 2, 2); cx, cy = centre(x, y, 2, 2); sc = rnd.uniform(0.6, 0.9)
            P('conifer5', cx, cy, 0.0, yaw=rnd.uniform(0, 360), s=(sc, sc, sc))
    return n0[0]
