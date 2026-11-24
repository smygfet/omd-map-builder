# "VS Parking" (first called "Parking"): an outdoor VS map that feels like a 3-floor parking structure (the user's brief, 2026-11-21).
#  - Orcs spawn on the ground floor (south), the rift sits on the open top deck (north).
#  - Floors at 0, 5 and 10 m joined by long straight ramps (grid ramps: orcs use them; never curved stairs).
#  - Each upper floor overhangs the one below on pillars (decks), so the lower floors are covered like a garage.
#  - The side facing the middle is open on every floor, and the middle is a 5-wide ravine, so you can watch the
#    other player's whole structure. Only side A is written; the builder mirrors it into side B.
# Uses the Map Maker's own map format and features only. Output: maps/VS_Parking.omdmap.json
import json, os, sys

COLS, ROWS = 41, 30
MID = COLS // 2                       # 20: the middle column
F1, F2, F3 = 0, 5, 10                 # floor heights (m)


def cell(t='f', h=0, **kw):
    c = {'t': t, 'h': h, 'd': 1, 'c': 0, 'n': 0}
    c.update(kw)
    return c


def build():
    g = [cell('v') for _ in range(COLS * ROWS)]
    def put(x, y, c): g[y * COLS + x] = c

    # zones of side A (x 1..19 inside the outer wall at x 0)
    for y in range(1, ROWS - 1):
        for x in range(1, MID):
            if y <= 8: put(x, y, cell('f', F3))            # top deck: open sky, the rift
            elif y <= 17: put(x, y, cell('f', F2))         # middle floor
            else: put(x, y, cell('f', F1))                 # ground floor, the orc spawn
    # ramp 1: ground -> middle floor, west lane x 1..5, rising north (d 0) over rows 22..18
    for x in range(1, 6):
        for i, y in enumerate(range(22, 17, -1)):
            put(x, y, cell('r', F1 + i, d=0))
    # ramp 2: middle floor -> top deck, east lane x 14..19 (along the open middle edge), rising north over rows 13..9
    for x in range(14, MID):
        for i, y in enumerate(range(13, 8, -1)):
            put(x, y, cell('r', F2 + i, d=0))
    # overhangs (decks): the middle floor runs on over the ground floor, the top deck over the middle floor
    for y in range(18, 25):
        for x in range(6, MID - 1):
            put(x, y, dict(g[y * COLS + x], b=F2))
    for y in range(9, 15):
        for x in range(1, 13):
            put(x, y, dict(g[y * COLS + x], b=F3))
    # pillars under the overhangs (walls carrying the deck)
    for x, y in [(8, 20), (12, 20), (16, 20), (8, 23), (12, 23), (16, 23)]:
        put(x, y, cell('w', F1, b=F2))
    for x, y in [(4, 11), (8, 11), (11, 11), (4, 14), (8, 14), (11, 14)]:
        put(x, y, cell('w', F2, b=F3))
    # outer wall: west, north, south (the middle edge stays open)
    for y in range(ROWS):
        put(0, y, cell('w', 0))
    for x in range(0, MID):
        put(x, 0, cell('w', 0)); put(x, ROWS - 1, cell('w', 0))
    # the middle column: the Map Maker shows it empty for an open/cliff middle
    for y in range(ROWS):
        put(MID, y, cell('v'))
    # side B: the mirror image (as the Map Maker shows it; the builder mirrors side A itself)
    for y in range(ROWS):
        for x in range(MID + 1, COLS):
            c = dict(g[y * COLS + (COLS - 1 - x)])
            if c['t'] == 'r' and c['d'] in (1, 3): c['d'] = 4 - c['d']
            put(x, y, c)
    return g


def markers():
    a = [{'k': 'rift', 'x': 6, 'y': 4},              # top deck, far from the middle edge
         {'k': 'start', 'x': 10, 'y': 6},            # players start on the top deck
         {'k': 'spawn', 'x': 16, 'y': 27}]           # ground floor, south-east corner
    return a + [dict(m, x=COLS - 1 - m['x'], s=1) for m in a]


def main(out):
    m = {
        'format': 'omd-map-maker', 'version': 2, 'name': 'VS Parking', 'id': 'VS_Parking',
        'cols': COLS, 'rows': ROWS, 'cell': 300, 'level': 100, 'wall': 600,
        'styles': {'floor': 'drydocks', 'wall': 'stonewall', 'ceiling': 'planks'},
        'vs': 1, 'rift': 'normal', 'env': 'forest', 'wallH': 6, 'ceilH': 0, 'bt': 1,
        'fill': 'inside', 'fillPits': 1, 'vsMid': 'cliff', 'vsMidW': 5, 'vsBridge': 0, 'vsBridgeAt': 'mid',
        'rules': {'endless': 1, 'orcs': 50, 'health': 15, 'send': 1, 'prices': [1000, 1200, 1500, 2500, 5000, 6000],
                  'rise': 5, 'archers': 1, 'midkill': 1, 'coins': 0, 'rift': 0},
        'rev': 1, 'markers': markers(), 'grid': build(),
    }
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    json.dump(m, open(out, 'w'), indent=None, separators=(',', ':'))
    return m


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', '..', 'maps', 'VS_Parking.omdmap.json'))
