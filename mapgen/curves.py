# Cells of a Map Maker round wall / walkway / curved stairs (same rule as the Map Maker's circle shape):
# a cell belongs when its middle lies inside the band r - t/2 < d <= r + t/2; curved stairs also only within their arc.
import math


def stair_span(cv):
    rise = max(0.0, float(cv['h1']) - float(cv['h0']))
    return float(cv['a0']), rise / min(2.0, max(1.0, float(cv.get('s', 1) or 1))) / max(0.5, float(cv['r'])) * (1 if cv.get('cw', 1) >= 0 else -1)


def ring_cells(cv, cols, rows):
    cx, cy, r, t = cv['x'], cv['y'], cv['r'], cv.get('t', 1)
    out = []
    for y in range(rows):
        for x in range(cols):
            d = math.hypot(x + .5 - cx, y + .5 - cy)
            if not (r - t / 2 < d <= r + t / 2): continue
            if cv.get('k') == 'stairs':
                a0, span = stair_span(cv)
                a = math.atan2(y + .5 - cy, x + .5 - cx)
                rel = (a - a0) * (1 if span >= 0 else -1) % (2 * math.pi)
                pad = 0.5 / max(r, 1)
                if not (rel <= abs(span) + pad or rel >= 2 * math.pi - pad): continue
            out.append((x, y))
    return out
