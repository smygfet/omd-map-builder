# "VS Twin Keeps" (was "dagens VS"), 2026-11-21: the user's map with flair, same layout and balance.
#  - Floor styles per area: cobbled orc yard, stone stair corridor, plaza keep top with a patterned ring round the
#    rift, wooden hall floor under the roof, stone tower, paved lower walks.
#  - Battlements on every edge that drops 3 m or more (map option bt).
#  - Props off the orc route (an orc camp at the spawn, braziers at the rift, a fountain and lamps on the keep top,
#    a weapon rack and table in the hall, storage in the corners).
#  - Flow fix: the player start sat on a 9 m tower with no walk off it; two floor cells at 9 m join it to the hall.
# Only side A is designed; side B is its mirror (the builder mirrors anyway; the Map Maker shows both).
# Usage: twin_keeps.py <dagens_VS.omdmap.json> <out.omdmap.json>
import json, sys

FS = []          # (x0, x1, y0, y1, style) on floor cells of side A, in order (later wins)
FS += [(3, 9, 1, 7, 'cobblestone'), (3, 9, 1, 2, 'cobblestone')]              # orc yard
FS += [(0, 6, 9, 16, 'plaza')]                                                 # keep top
FS += [(1, 3, 10, 12, 'museum')]                                               # ring round the rift (2, 11)
FS += [(7, 14, 14, 17, 'parquet')]                                             # roofed hall
FS += [(7, 10, 18, 24, 'stoneblock')]                                          # the start tower (+ bridge)
FS += [(11, 14, 18, 19, 'stoneblock')]
FS += [(10, 11, 3, 6, 'woodfloor')]                                            # roofed room by the yard
FS += [(11, 19, 23, 24, 'pavement'), (18, 19, 7, 24, 'pavement'), (11, 12, 9, 10, 'pavement')]

PROPS = [  # (x, y, prop, rotation 0-3)
    (4, 4, 'orctent', 0), (3, 7, 'hay', 1), (8, 3, 'barrels', 0), (8, 7, 'crates', 0),     # orc camp at the spawn
    (1, 12, 'brazier', 0), (3, 12, 'brazier', 0),                                           # the rift
    (5, 14, 'fountain', 0), (6, 9, 'castlelamp', 1), (6, 16, 'castlelamp', 1), (0, 16, 'planter', 0), (3, 16, 'bench', 0),
    (8, 14, 'rack', 0), (11, 15, 'table', 0), (14, 14, 'cauldron', 0),                     # the hall
    (7, 24, 'brazier', 0), (9, 24, 'brazier', 0),                                           # the tower
    (10, 3, 'kegs', 0), (19, 24, 'crates', 0), (11, 24, 'barrels', 0),
]


def build(d):
    C, R, g = d['cols'], d['rows'], d['grid']
    at = lambda x, y: g[y * C + x]
    mid = C // 2
    # flow fix: bridge the start tower (x 7-9) to the hall's 9 m floor (x 11-14) at rows 18-19
    for y in (18, 19):
        if at(10, y)['t'] == 'v':
            g[y * C + 10] = {'t': 'f', 'h': 9, 'd': 1, 'c': 0, 'n': 0}
    for x0, x1, y0, y1, st in FS:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if x < mid and at(x, y)['t'] == 'f': at(x, y)['fs'] = st
    for x, y, p, r in PROPS:
        c = at(x, y)
        assert c['t'] == 'f' and not c.get('b') and not c.get('gt') and not c.get('bk'), (x, y, c)
        c['p'] = p; c['pr'] = r
    # side B = mirror of side A
    for y in range(R):
        for x in range(mid + 1, C):
            c = dict(at(C - 1 - x, y))
            if c['t'] == 'r' and c['d'] in (1, 3): c['d'] = 4 - c['d']
            if c.get('p') and c.get('pr', 0) in (1, 3): c['pr'] = 4 - c['pr']
            g[y * C + x] = c
    d['bt'] = 1
    d['name'] = 'VS Twin Keeps'; d['id'] = 'VS_Twin_Keeps'
    d['sketch'] = []
    d['rev'] = int(d.get('rev') or 1) + 1
    return d


if __name__ == '__main__':
    d = build(json.load(open(sys.argv[1])))
    json.dump(d, open(sys.argv[2], 'w'), separators=(',', ':'))
    print('ok', d['name'], 'rev', d['rev'])
