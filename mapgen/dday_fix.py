# D-Day Omaha (the friend's map), the user's notes of 2026-11-21:
#  1. "This 4m trench should be 3M so that a trap can be placed on the wall also there should be stairs to the bunker"
#     -> the trench (row 11, 4 m) goes down to 3 m, i.e. 3 m deep walls that take wall traps; its crossing ramps get
#        a third cell on each side; each bunker's north door gets stairs down into the trench.
#  2. "Make the bunkers have windows facing the ocean" -> openings in each bunker's south wall with a 1 m sill (a floor
#     1 m above the bunker's, too high to walk over). Walls rise with the highest floor beside them, so the wall cells
#     next to a window get a negative raise ('wh') that keeps them at the bunker's wall height.
#  3. "This orc spawn doesnt seem to want to move straight up to the left stairs" -> fixed in the builder (routes():
#     equally short walks now prefer the one that climbs first); nothing to change in the map.
# Only edits cells; keeps everything else of the user's file (sketch, markers, styles, rules).
# Usage: dday_fix.py <in.omdmap.json> <out.omdmap.json>
import json, sys

TRENCH_ROW, TRENCH_H = 11, 3
CROSS_X = [(7, 9), (23, 25), (39, 41)]          # the three lanes: trench crossings and beach ramps
DOOR_ROW = 14                                    # bunker north doors (a ceiling floor cell inside the wall line)


def fix(m):
    C, R, g = m['cols'], m['rows'], m['grid']
    at = lambda x, y: g[y * C + x]
    def put(x, y, c): g[y * C + x] = c
    log = []
    # 1a. trench 4 m -> 3 m
    n = 0
    for x in range(C):
        c = at(x, TRENCH_ROW)
        if c['t'] == 'f' and c['h'] == 4: c['h'] = TRENCH_H; n += 1
    log.append("trench: %d cells 4 m -> 3 m" % n)
    for x0, x1 in CROSS_X:
        for x in range(x0, x1 + 1):
            fs = at(x, TRENCH_ROW + 2).get('fs', 'dirt')
            # north side: rows 10, 9, 8 rise north (d 0) 3 -> 6 m
            for i, y in enumerate((10, 9, 8)):
                put(x, y, {'t': 'r', 'h': TRENCH_H + i, 'd': 0, 'c': 0, 'n': 0, 'fs': fs})
            # south side: rows 12, 13, 14 rise south (d 2) 3 -> 6 m; the bluff ramp moves one row down
            for i, y in enumerate((12, 13, 14)):
                put(x, y, {'t': 'r', 'h': TRENCH_H + i, 'd': 2, 'c': 0, 'n': 0, 'fs': fs})
            put(x, 15, {'t': 'f', 'h': 6, 'd': 1, 'c': 0, 'n': 0, 'fs': fs})          # landing on the bluff
            for i, y in enumerate(range(21, 15, -1)):                                # bluff ramp rows 21..16, 0 -> 6 m
                put(x, y, {'t': 'r', 'h': i, 'd': 0, 'c': 0, 'n': 0, 'fs': fs})
    log.append("crossings: 3 ramp cells each side of the trench; bluff ramps moved to rows 16-21")
    # 1b. stairs from the trench up to each bunker's north door
    doors = [x for x in range(1, C - 1) if at(x, DOOR_ROW)['t'] == 'f' and at(x, DOOR_ROW).get('c')
             and at(x - 1, DOOR_ROW)['t'] == 'w' and at(x + 1, DOOR_ROW)['t'] == 'w']
    for x in doors:
        for i, y in enumerate((12, 13, 14)):
            c = {'t': 'r', 'h': TRENCH_H + i, 'd': 2, 'c': 1 if y == DOOR_ROW else 0, 'n': 0, 'st': 1}
            fs = at(x, y).get('fs')
            if fs: c['fs'] = fs
            put(x, y, c)
    log.append("bunker stairs at x %s" % doors)
    # 2. windows in each bunker's south wall (bunker = connected ceiling cells below the door row)
    seen, wins = set(), []
    for y in range(DOOR_ROW + 1, R):
        for x in range(C):
            if (x, y) in seen or not (at(x, y)['t'] == 'f' and at(x, y).get('c')): continue
            comp, st_ = [], [(x, y)]; seen.add((x, y))
            while st_:
                cx, cy = st_.pop(); comp.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < C and DOOR_ROW < ny < R and (nx, ny) not in seen and at(nx, ny)['t'] == 'f' and at(nx, ny).get('c'):
                        seen.add((nx, ny)); st_.append((nx, ny))
            ymax = max(cy for _, cy in comp)
            xs = sorted(cx for cx, cy in comp if cy == ymax)
            south = ymax + 1
            if south >= R or any(at(cx, south)['t'] != 'w' for cx in xs): continue
            pick = [xs[len(xs) // 2]] if len(xs) <= 3 else xs[1::2]                  # every other cell, wall between
            for wx in pick:
                h = at(wx, ymax)['h']
                put(wx, south, {'t': 'f', 'h': h + 1, 'd': 1, 'c': 0, 'n': 1, 'fs': at(wx, ymax).get('fs', 'darkstone')})
                wins.append((wx, south))
    # keep the walls around the windows at their old height (builder: top = highest floor beside it + wall height,
    # rounded up to the 3 m column steps)
    import math
    WALLH = float(m.get('wallH') or 6)
    def ftop(c): return c['h'] + (1 if c['t'] == 'r' else 0) if c['t'] in ('f', 'r') else None
    def top(base): return math.ceil((base + WALLH) / 3.0 - 1e-6) * 3.0
    for wx, wy in wins:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x, y = wx + dx, wy + dy
                if not (0 <= x < C and 0 <= y < R) or at(x, y)['t'] != 'w': continue
                hs = [ftop(at(x + i, y + j)) for i in (-1, 0, 1) for j in (-1, 0, 1) if 0 <= x + i < C and 0 <= y + j < R]
                hs = [v for v in hs if v is not None]
                old = [ftop(at(x + i, y + j)) if (x + i, y + j) not in wins else at(x + i, y + j)['h'] - 1
                       for i in (-1, 0, 1) for j in (-1, 0, 1) if 0 <= x + i < C and 0 <= y + j < R]
                old = [v for v in old if v is not None]
                d = top(max(hs)) - top(max(old))
                if d > 0: at(x, y)['wh'] = -d
    log.append("windows %s" % wins)
    m['rev'] = int(m.get('rev') or 1) + 1
    return log


if __name__ == '__main__':
    m = json.load(open(sys.argv[1]))
    for line in fix(m): print(line)
    json.dump(m, open(sys.argv[2], 'w'), separators=(',', ':'))
