# "B- Day Orcmaha beach" (renamed D-Day Omaha), the user's notes of 2026-11-21 18:29:
#  1. "This top should be 2 spaces wide on all 3" -> the landing at the top of each bluff ramp (between the bluff ramp
#     and the trench crossing) is 2 cells deep instead of 1; the bluff ramps move one more row towards the sea.
#  2. "they can enter from the side of the ramps. maybe put a rock on each side" -> rock walls on both sides of each
#     bluff ramp where it runs on the beach (its two lowest cells), so orcs only get on from the front.
#  3. Re-applies the lowered walls beside the bunker windows (the Map Maker used to drop negative 'wh' on save).
#  4. "once done you can remove all sketches" -> sketch cleared.
# Usage: bday_fix.py <in.omdmap.json> <out.omdmap.json>
import json, math, sys

LANES = [(7, 9), (23, 25), (39, 41)]
LANDING = (15, 16)                  # rows of the 2-deep landing at 6 m
RAMP_ROWS = range(22, 16, -1)       # bluff ramp, bottom (0 m) at row 22 up to row 17 (5 m), rising north


def fix(m):
    C, R, g = m['cols'], m['rows'], m['grid']
    at = lambda x, y: g[y * C + x]
    def put(x, y, c): g[y * C + x] = c
    log = []
    beach = at(12, 22).get('fs', 'dirtB')
    for x0, x1 in LANES:
        fs = at(x0, 14).get('fs', 'dirt')
        for x in range(x0, x1 + 1):
            for y in LANDING: put(x, y, {'t': 'f', 'h': 6, 'd': 1, 'c': 0, 'n': 0, 'fs': fs})
            for i, y in enumerate(RAMP_ROWS): put(x, y, {'t': 'r', 'h': i, 'd': 0, 'c': 0, 'n': 0, 'fs': fs})
        # rocks beside the ramp's two lowest cells (the ones on the beach)
        for y in (21, 22):
            for x in (x0 - 1, x1 + 1):
                put(x, y, {'t': 'w', 'h': 0, 'd': 1, 'c': 0, 'n': 0, 'ws': 'rock'})
    log.append("landings 2 deep (rows 15-16), bluff ramps rows 22..17, rocks beside rows 21-22")
    # row 23 in front of each ramp foot: plain beach (it was beach already; make sure)
    for x0, x1 in LANES:
        for x in range(x0, x1 + 1):
            c = at(x, 23)
            if c['t'] != 'f' or c['h'] != 0: put(x, 23, {'t': 'f', 'h': 0, 'd': 1, 'c': 0, 'n': 0, 'fs': beach})
    # bunker windows: floor 1 m above the bunker, in the south wall line (walls left and right); keep the walls beside
    # them at the bunker's wall height (top = highest floor beside + wall height, on 3 m steps)
    wins = [(x, y) for y in range(1, R - 1) for x in range(1, C - 1)
            if at(x, y)['t'] == 'f' and at(x - 1, y)['t'] == 'w' and at(x + 1, y)['t'] == 'w'
            and at(x, y - 1)['t'] == 'f' and at(x, y - 1).get('c') and at(x, y)['h'] == at(x, y - 1)['h'] + 1]
    WALLH = float(m.get('wallH') or 6)
    def ftop(c): return c['h'] + (1 if c['t'] == 'r' else 0) if c['t'] in ('f', 'r') else None
    def top(base): return math.ceil((base + WALLH) / 3.0 - 1e-6) * 3.0
    n = 0
    for wx, wy in wins:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x, y = wx + dx, wy + dy
                if not (0 <= x < C and 0 <= y < R) or at(x, y)['t'] != 'w': continue
                nb = [(x + i, y + j) for i in (-1, 0, 1) for j in (-1, 0, 1) if 0 <= x + i < C and 0 <= y + j < R]
                hs = [v for v in (ftop(at(*q)) for q in nb) if v is not None]
                old = [v for v in ((at(*q)['h'] - 1) if q in wins else ftop(at(*q)) for q in nb) if v is not None]
                d = top(max(hs)) - top(max(old))
                if d > 0: at(x, y)['wh'] = -int(d); n += 1
                elif 'wh' in at(x, y) and at(x, y)['wh'] < 0: del at(x, y)['wh']
    log.append("windows %s, %d walls beside them kept low" % (wins, n))
    m['sketch'] = []
    m['rev'] = int(m.get('rev') or 1) + 1
    log.append("sketch cleared, rev %d" % m['rev'])
    return log


if __name__ == '__main__':
    m = json.load(open(sys.argv[1]))
    for line in fix(m): print(line)
    json.dump(m, open(sys.argv[2], 'w'), separators=(',', ':'))
