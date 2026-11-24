# Helm's Deep v32 (v32: no wall where the Deeping Wall meets the outer walkway: a 3 m step there; v30: medieval props along the walls everywhere; v28: the two bridges are straight diagonal pieces, 1 wide; v26: outer walkway 9 m like the middle one, bridges between them halfway along each arm, the
# east spawns moved to the west of the field; v24: lower walls: outer walkway 6 m = the middle ring's floor, middle 9 m = the court's floor,
# inner 13 m; a wall where the Deeping Wall meets the outer walkway; v22: straight orc stairs lower ring -> middle ring; v18: the tower's round wall arches over its gate and door, hub water, two spawns east; v16, from the v15 sketch: the tower gate one step in, castle walls along the east end of the lower
# ring, the bridge over the middle stair 3 wide x 2 deep, the normal rift) for the OMD Map Maker (v12, from the v11 sketch: the tower one cell west, grander, its walk 3 wide
# between trap walls; a 3 x 3 bridge over the middle stair; walkway stairs end on the walkway (no landing cells);
# defence towers by the gate; the great hall 12 m high under a roof, no gallery; v10, from the v9 sketch: the tower a roofed castle tower with a 3 wide gate,
# straight walls along its walk, no wall stubs in the lower ring, no tall block in the Deep, the stairs' ends covered;
# v8, from the user's sketch: the walls 6 m higher (walkways 12 / 16 / 19 m),
# the orcs' curved stairs at the far ends of the lower ring, full width, landing straight into the middle ring, the
# lower ring closed off at its north ends, straight trap walls; the round tower: a corridor with straight trap walls on
# its 6 m floor behind a breakable gate; steeper (33 degree) stairs up to the walkways; v6: flat rings 2 / 6 / 9 m, curved stairs (orcs too) from the lower ring to the
# middle ring, bridges so every walkway runs round, the outer walkway joins the Deeping Wall, a round tower with a
# ground-floor room; v5: the Hornburg's rings are round walls with walkways and crenels, curved
# stairs up to them, the great hall is a castle keep; v4: round walls and tower, an upper gallery in the hall, a tall
# mountain behind; v3: grass, a real stream, rock mountain, battlements, a breakable gate, tents), laid out like a top-down battle map (north up): the Deep (a camp) top left,
# the Deeping Wall straight across with the culvert, the Hornburg on the right as a half circle against the mountain
# whose rings rise towards it, the great hall going into the mountain, a round tower where the wall meets the Hornburg,
# the gate at the bottom of the Hornburg and the causeway going south, then west. 3 m cells, heights in m.
import json, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import curves as CV
W, H = 76, 60
N, E, S, Wd = 0, 1, 2, 3
def blank(t='w'): return {'t': t, 'h': 0, 'd': 1, 'c': 0, 'n': 0}
g = [[blank() for _ in range(W)] for _ in range(H)]
def inmap(x, y): return 0 <= x < W and 0 <= y < H
def floor(x, y, h, fs=None, **kw):
    if not inmap(x, y): return
    c = blank('f'); c['h'] = h
    if fs: c['fs'] = fs
    c.update(kw); g[y][x] = c
CASTLE = set()                                   # walls built by hand (the Hornburg, the tower): castle stone
def wall(x, y, castle=False):
    if inmap(x, y):
        g[y][x] = blank('w')
        if castle: CASTLE.add((x, y))
def void(x, y):
    if inmap(x, y): g[y][x] = blank('v')
def stair(x, y, h, d, st=1):
    if inmap(x, y):
        c = blank('r'); c['h'] = h; c['d'] = d
        if st: c['st'] = 1
        g[y][x] = c
def prop(x, y, p, r=0):
    c = g[y][x]
    if c['t'] == 'f' and not c.get('cv') and not c.get('b'): c['p'] = p; c['pr'] = r

# ---- the coomb: the open field south of the wall, h 0 ----
for y in range(32, H - 1):
    for x in range(1, W - 1): floor(x, y, 0, 'grass')
# ---- the Deep: a bowl behind the wall, h 0 (dirt with a mud middle) ----
for y in range(2, 29):
    for x in range(2, 41):
        if ((x - 21) / 19.5) ** 2 + ((y - 16) / 14) ** 2 <= 1 or y >= 22:
            floor(x, y, 0, 'dirt' if ((x - 21) / 11) ** 2 + ((y - 16) / 8) ** 2 <= 1 else 'grass')

# ---- the stream: shallow water ----
def strip(pts):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(abs(x1 - x0), abs(y1 - y0))
        px = py = None
        for i in range(n + 1):
            x = round(x0 + (x1 - x0) * i / n); y = round(y0 + (y1 - y0) * i / n)
            cells = [(x, y)] if px is None or px == x or py == y else [(x, py), (x, y)]     # no diagonal gaps
            for (cx, cy) in cells:
                if g[cy][cx]['t'] == 'f' and g[cy][cx]['h'] == 0: g[cy][cx]['fs'] = 'water'
            px, py = x, y
strip([(22, 3), (21, 9), (20, 16), (19, 22), (19, 28)])
strip([(19, 32), (21, 37), (27, 41), (35, 43), (42, 47), (44, 56), (44, 58)])

# ---- the Deeping Wall: a 6 m walkway, 3 deep, with two towers sticking out south ----
for y in range(29, 32):
    for x in range(1, 40): floor(x, y, 6, 'stoneblock')
for tx in (8, 28):
    for y in (32, 33):
        for x in (tx, tx + 1): floor(x, y, 6, 'stoneblock')
# the culvert: the stream's tunnel under the walkway (the walkway carries on as an upper deck), its mouth a barricade wall
for y in range(29, 32):
    for x in (19, 20): floor(x, y, 0, 'water', b=6)
for x in (19, 20): g[31][x]['bk'] = 1
# stairs from the Deep up onto the wall (rising south), west and east
for sx in (6, 33):
    for i in range(6):
        for x in (sx, sx + 1): stair(x, 23 + i, i, S)

# ---- the Hornburg: a half circle around (54, 26), flat side north against the mountain ----
CX, CY = 54, 26
for y in range(CY - 1, H):
    for x in range(36, W):
        r = math.hypot(x - CX, y - CY)
        if r <= 6.0: floor(x, y, 9, 'pavement')               # upper court
        elif r <= 7.0: floor(x, y, 13, 'stoneblock', cv=1)    # inner ring wall, walkway at 13 m (4 m over the court)
        elif r <= 10.0: floor(x, y, 6, 'cobblestone')         # middle ring (flat)
        elif r <= 11.0: floor(x, y, 9, 'stoneblock', cv=2)    # middle ring wall, walkway at 9 m = the upper court's floor
        elif r <= 14.5: floor(x, y, 2, 'cobblestone')         # lower ring (flat)
        elif r <= 16.6: floor(x, y, 9, 'stoneblock', cv=3)    # outer wall, walkway at 9 m, as high as the middle wall
# the great hall: from the upper court into the mountain, roofed; the rift at its far end
for y in range(7, CY - 1):
    for x in range(51, 58): floor(x, y, 9, 'woodfloor', c=1)
# (v12: no upper gallery: the hall is 12 m high under its roof, the map's ceiling height 12 m)
# middle -> upper court: stairs rising north
for x in (53, 54, 55):
    for i, y in enumerate((34, 33, 32)):
        stair(x, y, 6 + i, N)
        if y in (32, 33): g[y][x]['b'] = 13                                   # the inner walkway's bridge over it, 3 wide x 2 deep
# the gate: the outer wall at the bottom, a portcullis over three cells (two deep) that the orcs batter down; the
# outer walkway runs on over it (a bridge at 6 m)
for x in (53, 54, 55):
    for y in (41, 42): floor(x, y, 2, 'cobblestone', gt=1, b=9)
# the round tower at the Deep's north-east corner (v12: one cell further west, grander): a round wall (r 3.6) with a
# 3 m crenellated parapet over its roof (15 m); inside, at 6 m, a 9 m high corridor 3 wide between straight walls (wall
# traps) from a breakable gate in the west (stairs up from the Deep) through a 3 wide door in the east on to the walk,
# 3 wide, south to the middle ring, between straight castle walls
TX, TY = 41, 19
for y in range(TY - 5, TY + 6):
    for x in range(TX - 5, TX + 6):
        r = math.hypot(x - TX, y - TY)
        if r <= 3.1: wall(x, y, True); g[y][x]['b'] = 15                   # solid inside, carrying the roof (15 m)
        elif r <= 4.1: wall(x, y, True); g[y][x]['cv'] = 4; g[y][x]['wh'] = 6     # the round wall: 3 m over the roof
for y in (18, 19, 20):
    for x in range(38, 45): floor(x, y, 6, 'stonefloor', b=15)              # the corridor, under the roof
    for i, x in enumerate(range(31, 37)): stair(x, y, i, E)                 # up from the Deep
    floor(37, y, 6, 'stonefloor', b=15)                                     # the opening in the round wall (west), the wall arching over it
    g[y][38]['gt'] = 1                                                      # the breakable gate, 3 wide, one step in
    floor(45, y, 6, 'stonefloor', b=15)                                     # the door (east), 3 wide, under the arch
for x in (45, 46, 47):
    for y in range(18, 26): floor(x, y, 6, 'stonefloor')                    # the walk south, 3 wide
# straight castle walls (wall traps) along the walk and below the tower
TOWERWALK = [(x, 24) for x in range(61, 71)] + [(44, y) for y in range(21, 25)] + [(48, y) for y in range(17, 25)] + [(x, 24) for x in range(38, 44)] + [(x, 17) for x in (45, 46, 47)]

# ---- the causeway: from the gate south (3 m), then west, stepping down to the field ----
for x in (53, 54, 55):
    for y in range(43, 51): floor(x, y, 2, 'cobblestone')
for y in (51, 52, 53):
    for x in range(36, 56):
        if x >= 51: floor(x, y, 2, 'cobblestone')
        elif x == 50: stair(x, y, 1, E, st=0)
        elif x >= 47: floor(x, y, 1, 'cobblestone')
        elif x == 46: stair(x, y, 0, E, st=0)
        else: floor(x, y, 0, 'cobblestone')
# the drop beside the causeway's straight part
for y in range(43, 51):
    for x in (51, 52, 56, 57): void(x, y)

# ---- the camp in the Deep: tents, hay, carts, a fenced pen ----
for (x, y, p, r) in [(16, 5, 'tent', 2), (28, 6, 'tent', 2), (10, 10, 'tent', 1), (31, 12, 'tent', 3), (12, 18, 'tent', 1),
                     (28, 19, 'tent', 3), (24, 4, 'tent', 2), (35, 9, 'hay', 0), (14, 8, 'crates', 0), (26, 9, 'barrels', 0),
                     (9, 15, 'sacks', 0), (33, 16, 'cart', 1), (24, 21, 'brazier', 0), (15, 22, 'table', 0), (30, 24, 'rack', 0),
                     (11, 24, 'hay', 1), (22, 13, 'brazier', 0), (7, 13, 'cart', 0), (36, 21, 'hay', 0)]:
    prop(x, y, p, r)
for x in (4, 5, 6): prop(x, 21, 'fence', 0)
# the field: boulders, and the Uruk-hai's tents along the bottom edge
for (x, y, p, r) in [(12, 36, 'boulder', 0), (31, 46, 'boulder', 1), (62, 47, 'boulder', 2), (8, 47, 'boulder', 3), (67, 40, 'boulder', 0),
                     (10, 52, 'orctent', 0), (24, 54, 'orctent', 1), (36, 56, 'orctent', 0), (62, 56, 'orctent', 2), (70, 52, 'orctent', 3)]:
    prop(x, y, p, r)
# the great hall: throne at the far end, tables along the sides, torches
prop(54, 8, 'throne', 2)
for y in (15, 18, 21):
    prop(52, y, 'table', 1); prop(56, y, 'table', 3)
for y in (11, 20): prop(51, y, 'torches', 1); prop(57, y, 'torches', 3)
# the courts
for (x, y, p, r) in [(50, 27, 'brazier', 0), (58, 27, 'brazier', 0), (45, 34, 'barrels', 0), (63, 34, 'crates', 0)]:
    prop(x, y, p, r)

# ---- the mountain: rock only where it borders somewhere to walk, the rest open ground ('fill') ----
for x in range(W): wall(x, 0); wall(x, H - 1)
for y in range(H): wall(0, y); wall(W - 1, y)
walk = lambda c: c['t'] in ('f', 'r')
keep = {(x, y) for y in range(H) for x in range(W) if g[y][x]['t'] == 'w'
        and any(inmap(x + dx, y + dy) and walk(g[y + dy][x + dx]) for dx in (-1, 0, 1) for dy in (-1, 0, 1))}
for y in range(H):
    for x in range(W):
        if g[y][x]['t'] == 'w' and (x, y) not in keep and (x, y) not in CASTLE: void(x, y)
        elif g[y][x]['t'] == 'w' and (x, y) not in CASTLE: g[y][x]['ws'] = 'rock'      # the mountain: cliff rock
# the mountain behind (north of the Deeping Wall's line and round the hall): rock rising with the distance from the
# nearest place to walk, up to 18 m more than a plain wall; the field to the south stays open
walkc = {(x, y) for y in range(H) for x in range(W) if walk(g[y][x])}
def dist(x, y, cap=8):
    for d_ in range(1, cap):
        if any((x + dx, y + dy) in walkc for dx in range(-d_, d_ + 1) for dy in range(-d_, d_ + 1)): return d_
    return cap
for y in range(H):
    for x in range(W):
        c = g[y][x]
        if (x, y) in CASTLE or c['t'] in ('f', 'r'): continue
        if y <= 28 or (x >= 60 and y <= 34):
            g[y][x] = blank('w'); g[y][x]['ws'] = 'rock'
            wh = min(18, 3 * (dist(x, y) - 1))
            if wh: g[y][x]['wh'] = wh

# the keep: the great hall as a castle tower, walls 2 thick standing 6 m above its roof (crenels on top), a front
# with a door onto the upper court
def keepwall(x, y):
    g[y][x] = blank('w'); g[y][x]['wh'] = 6
for y in range(5, 25):
    for x in (49, 50, 58, 59): keepwall(x, y)
for y in (5, 6):
    for x in range(49, 60): keepwall(x, y)
for x in (51, 52, 56, 57): keepwall(x, 24)
# curved stairs (orcs use them too): from the lower ring (2 m) up to the middle ring (6 m) at the far (north) end of
# each arm of the lower ring, the full width of the ring; their landing runs straight on into the middle ring where
# the middle ring wall stops. Steep (2 m per 3 m) stairs up from the middle ring to the middle walkway (6 -> 16 m) and
# from the upper court to the inner walkway (9 -> 19 m)
O = (CX + .5, CY + .5)
LA = math.pi - 0.10                    # the west stairs' top (angle); the east ones mirror it
STAIRS = [dict(r=12.75, t=3.5, a0=LA - 4 / 12.75, cw=1, h0=2, h1=6), dict(r=12.75, t=3.5, a0=math.pi - LA + 4 / 12.75, cw=-1, h0=2, h1=6),
          dict(r=9.5, t=1, a0=2.0, cw=1, h0=6, h1=9, s=2), dict(r=9.5, t=1, a0=math.pi - 2.0, cw=-1, h0=6, h1=9, s=2),
          dict(r=5.4, t=1, a0=1.25, cw=-1, h0=9, h1=13, s=2), dict(r=5.4, t=1, a0=math.pi - 1.25, cw=1, h0=9, h1=13, s=2)]
def rel(x, y, a, cw):                  # how far past angle a the cell lies, going the stairs' way
    return ((math.atan2(y + .5 - O[1], x + .5 - O[0]) - a) * cw) % (2 * math.pi)
stair_curves = []
for i, st in enumerate(STAIRS):
    cv = dict(x=O[0], y=O[1], k='stairs', **st)
    a_end = st['a0'] + (st['h1'] - st['h0']) / st.get('s', 1) / st['r'] * st['cw']
    if i < 2:
        # v22: the orcs' stairs from the lower ring up to the middle ring are STRAIGHT grid stairs (orcs don't climb the
        # curved ones in game: every orc went round through the Deep). At the north end of each arm, the full width of
        # the lower ring (11 < r <= 14.5): rows 28-31 climb north 2 -> 6 m, rows 25-27 are the landing at 6 m, running
        # on into the middle ring where the middle ring wall stops
        for y in range(CY - 1, 33):
            for x in range(W):
                d_ = math.hypot(x + .5 - O[0], y + .5 - O[1])
                west = x + .5 < O[0]
                if west != (i == 0): continue
                if 11.0 < d_ <= 14.5 and 28 <= y <= 31: stair(x, y, 2 + (31 - y), N)
                elif 9.9 < d_ <= 14.5 and y <= 27: floor(x, y, 6, 'stoneblock')
        continue
    stair_curves.append(cv); k = 3 + i
    for (x, y) in CV.ring_cells(cv, W, H):
        g[y][x] = blank('w'); g[y][x]['cv'] = k
    # (walkway stairs: no landing cells; they end beside the walkway, which they step on to)
# defence towers either side of the gate: 3 wide x 2 deep, solid, their top at the outer walkway's height (12 m)
for x0 in (46, 60):
    for x in range(x0, x0 + 3):
        for y in (41, 42): floor(x, y, 9, 'stoneblock')
# the lower ring closed off at its north ends (a castle wall between it and the Deep)
# bridges at 9 m from the middle walkway to the outer walkway, over the lower ring halfway along each arm: one
# straight piece each, 1 cell wide, on the diagonal ('spans', built by the builder; v28)
SPANS = [dict(x1=O[0] + 10.5 * math.cos(a), y1=O[1] + 10.5 * math.sin(a), x2=O[0] + 15.55 * math.cos(a), y2=O[1] + 15.55 * math.sin(a), h=9, w=1)
         for a in (3 * math.pi / 4, math.pi / 4)]
# the outer walkway (9 m) and the Deeping Wall (6 m) meet with a 3 m step (no wall, no stairs: user, v32)
for (x, y) in TOWERWALK:
    if not g[y][x].get('cv'): wall(x, y, True); g[y][x].pop('ws', None); g[y][x].pop('wh', None)
# straight walls in the lower ring (wall traps) on the way from the gate to the stairs, one from each side, each arm
# ---- medieval dressing (v30): props along the walls and edges of every area, never in a passage narrower than 3 cells
# (a prop blocks its cell for orcs), away from stairs, gates, bridges and each other ----
import random
RND = random.Random(1402)
DEC = [  # (x0, x1, y0, y1, floor height, how many, props)
    (2, 40, 2, 28, 0, 26, ['kegs', 'market', 'cauldron', 'forge', 'chest', 'sacks', 'crates', 'barrels', 'bench', 'torches',
                           'castlelamp', 'pots', 'brazier', 'cart', 'hay', 'table']),                     # the Deep: the refugees' camp
    (1, 75, 33, 59, 0, 22, ['orcpillar', 'orcstatue', 'rubble', 'boulder', 'cart', 'hay', 'fence', 'orctent', 'brazier', 'ferns']),  # the field: the siege
    (38, 71, 25, 43, 2, 12, ['crates', 'barrels', 'sacks', 'kegs', 'rack', 'torches', 'brazier', 'cart', 'hay']),       # lower ring
    (40, 70, 22, 38, 6, 10, ['rack', 'barrels', 'brazier', 'castlelamp', 'chest', 'crates', 'torches']),                # middle ring
    (46, 63, 22, 34, 9, 6, ['planter', 'castlelamp', 'bench', 'pots', 'brazier']),                                     # upper court
    (51, 58, 6, 24, 9, 8, ['castlelamp', 'chest', 'kegs', 'bench', 'pillar']),                                         # the great hall
]
def dec_ok(x, y, h):
    if not (1 <= x < W - 1 and 1 <= y < H - 1): return None
    c = g[y][x]
    if c['t'] != 'f' or c['h'] != h or c.get('p') or c.get('cv') or c.get('b') or c.get('gt') or c.get('bk') or c.get('fs') == 'water': return None
    for yy in range(y - 2, y + 3):
        for xx in range(x - 2, x + 3):
            q = g[yy][xx] if 0 <= yy < H and 0 <= xx < W else None
            if q is None: continue
            if q.get('p') and (abs(xx - x) <= 2 and abs(yy - y) <= 2): return None           # 3 cells from other props
            if q['t'] == 'r' or q.get('gt') or q.get('bk') or q.get('b') or q.get('fs') == 'water':
                if abs(xx - x) <= 1 and abs(yy - y) <= 1: return None                       # not beside stairs, gates, bridges
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):                                          # against a wall or an edge,
        n = g[y + dy][x + dx]
        edge = n['t'] in ('w', 'v') or (n['t'] == 'f' and abs(n['h'] - h) >= 3)
        if not edge: continue
        ok = True                                                                              # with 3 free cells beyond it
        for k in (1, 2, 3):
            xx, yy = x - dx * k, y - dy * k
            if not (0 <= xx < W and 0 <= yy < H): ok = False; break
            q = g[yy][xx]
            if q['t'] != 'f' or q['h'] != h or q.get('p'): ok = False; break
        if ok: return (dx, dy)
    return None
KEEP = [(3, 40), (4, 55), (25, 57), (32, 57), (54, 12), (54, 28)]                          # spawns, rift, start
FACE = {(1, 0): 3, (-1, 0): 1, (0, 1): 0, (0, -1): 2}                                         # turned away from the wall
for (x0, x1, y0, y1, h, n, kinds) in DEC:
    cells = [(x, y) for y in range(y0, y1) for x in range(x0, x1)]
    RND.shuffle(cells); placed = 0
    for (x, y) in cells:
        if placed >= n: break
        if any(abs(x - kx) <= 3 and abs(y - ky) <= 3 for kx, ky in KEEP): continue
        d_ = dec_ok(x, y, h)
        if not d_: continue
        g[y][x]['p'] = kinds[placed % len(kinds)]; g[y][x]['pr'] = FACE[d_]; placed += 1

markers = [{'k': 'rift', 'x': 54, 'y': 12}, {'k': 'start', 'x': 54, 'y': 28},
           {'k': 'spawn', 'x': 3, 'y': 40}, {'k': 'spawn', 'x': 4, 'y': 55}, {'k': 'spawn', 'x': 25, 'y': 57}, {'k': 'spawn', 'x': 32, 'y': 57}]
d = {'format': 'omd-map-maker', 'version': 2, 'name': "Helm's Deep", 'id': 'Helm_s_Deep', 'cols': W, 'rows': H, 'cell': 300, 'level': 100, 'wall': 600,
     'styles': {'floor': 'cobblestone', 'wall': 'castle', 'ceiling': 'planks'}, 'vs': 0, 'rift': 'normal', 'env': 'ground', 'wallH': 6, 'ceilH': 12,
     'fill': 'outside', 'fillPits': 0, 'bt': 1, 'water': 'hub', 'rev': 32, 'revLog': [{'n': 2, 't': '2026-11-15T17:45:00Z'}, {'n': 3, 't': '2026-11-15T19:30:00Z'}, {'n': 4, 't': '2026-11-15T21:00:00Z'}, {'n': 5, 't': '2026-11-15T22:30:00Z'}, {'n': 6, 't': '2026-11-16T00:30:00Z'}, {'n': 7, 't': '2026-11-15T21:04:43Z'}, {'n': 8, 't': '2026-11-15T23:30:00Z'}, {'n': 9, 't': '2026-11-15T21:33:29Z'}, {'n': 10, 't': '2026-11-16T00:30:00Z'}, {'n': 11, 't': '2026-11-15T22:59:19Z'}, {'n': 12, 't': '2026-11-16T01:30:00Z'}, {'n': 13, 't': '2026-11-15T22:59:19Z'}, {'n': 14, 't': '2026-11-16T02:00:00Z'}, {'n': 15, 't': '2026-11-15T22:20:55Z'}, {'n': 16, 't': '2026-11-16T03:00:00Z'}, {'n': 17, 't': '2026-11-15T22:37:00Z'}, {'n': 18, 't': '2026-11-16T03:30:00Z'}, {'n': 19, 't': '2026-11-15T22:47:00Z'}, {'n': 20, 't': '2026-11-16T04:00:00Z'}, {'n': 21, 't': '2026-11-16T20:00:00Z'}, {'n': 22, 't': '2026-11-16T20:45:00Z'}, {'n': 23, 't': '2026-11-16T20:50:00Z'}, {'n': 24, 't': '2026-11-16T21:00:00Z'}, {'n': 25, 't': '2026-11-16T21:05:00Z'}, {'n': 26, 't': '2026-11-16T21:15:00Z'}, {'n': 27, 't': '2026-11-16T21:10:00Z'}, {'n': 28, 't': '2026-11-16T21:20:00Z'}, {'n': 29, 't': '2026-11-16T21:18:00Z'}, {'n': 30, 't': '2026-11-16T21:40:00Z'}, {'n': 31, 't': '2026-11-16T21:30:00Z'}, {'n': 32, 't': '2026-11-16T21:35:00Z'}],
     'curves': [{'x': CX + .5, 'y': CY + .5, 'r': 6.5, 't': 1, 'k': 'walk'}, {'x': CX + .5, 'y': CY + .5, 'r': 10.5, 't': 1, 'k': 'walk'}, {'x': CX + .5, 'y': CY + .5, 'r': 15.55, 't': 2, 'k': 'walk'},
                {'x': TX + .5, 'y': TY + .5, 'r': 3.6, 't': 1}] + stair_curves, 'spans': SPANS, 'markers': markers, 'grid': [c for row in g for c in row]}
json.dump(d, open(sys.argv[1] if len(sys.argv) > 1 else 'Helm_s_Deep.omdmap.json', 'w'))
print('ok')
