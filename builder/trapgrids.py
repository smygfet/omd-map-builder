# Work out trappable surfaces (floors + wall faces next to floor) from Map Maker DATA boxes.
import json, math
TILE = 150.0

def surfaces(D, OX, OY, OZ):
    CS = D['cell']; cols, rows = D['cols'], D['rows']
    kind = [[None] * rows for _ in range(cols)]; top = [[0.0] * rows for _ in range(cols)]
    def cells_of(b):
        cx, cy = b['c'][0], b['c'][1]
        if b['f'] == 'Ramps': return [(int(cx // CS), int(cy // CS))]
        sx, sy = b['s'][0], b['s'][1]
        x0, x1 = int(round((cx - sx / 2) / CS)), int(round((cx + sx / 2) / CS))
        y0, y1 = int(round((cy - sy / 2) / CS)), int(round((cy + sy / 2) / CS))
        return [(i, j) for i in range(x0, x1) for j in range(y0, y1)]
    for order in ('Floors', 'Ramps', 'Walls'):
        for b in D['boxes']:
            if b['f'] != order: continue
            for i, j in cells_of(b):
                if 0 <= i < cols and 0 <= j < rows:
                    kind[i][j] = {'Floors': 'f', 'Ramps': 'r', 'Walls': 'w'}[order]
                    if order == 'Floors': top[i][j] = b['c'][2] + b['s'][2] / 2
    out = []
    # floors: greedy rectangles of same-height floor cells
    used = [[False] * rows for _ in range(cols)]
    for j in range(rows):
        for i in range(cols):
            if kind[i][j] != 'f' or used[i][j]: continue
            h = top[i][j]; w = 1
            while i + w < cols and kind[i + w][j] == 'f' and not used[i + w][j] and top[i + w][j] == h: w += 1
            d = 1
            while j + d < rows and all(kind[i + k][j + d] == 'f' and not used[i + k][j + d] and top[i + k][j + d] == h for k in range(w)): d += 1
            for a in range(w):
                for c in range(d): used[i + a][j + c] = True
            lx, ly = math.floor(w * CS / TILE) * TILE, math.floor(d * CS / TILE) * TILE
            if lx >= 2 * TILE and ly >= 2 * TILE:
                out.append(dict(type='floor', center=((i + w / 2) * CS + OX, (j + d / 2) * CS + OY, h + 5 + OZ), size=(lx, ly)))
    # wall faces facing floor cells
    dirs = [((1, 0), 0.0), ((-1, 0), 180.0), ((0, 1), 90.0), ((0, -1), -90.0)]
    for (dx, dy), yaw in dirs:
        faces = {}
        for i in range(cols):
            for j in range(rows):
                ni, nj = i + dx, j + dy
                if kind[i][j] == 'w' and 0 <= ni < cols and 0 <= nj < rows and kind[ni][nj] == 'f':
                    line = (i + (1 if dx > 0 else 0)) if dx else (j + (1 if dy > 0 else 0))
                    along = j if dx else i
                    faces.setdefault((line, top[ni][nj]), []).append(along)
        for (line, h), alongs in faces.items():
            alongs.sort(); run = [alongs[0]]
            for a in alongs[1:] + [None]:
                if a is not None and a == run[-1] + 1: run.append(a); continue
                L = math.floor(len(run) * CS / TILE) * TILE
                wall_top = 600.0
                H = math.floor((wall_top - h) / TILE) * TILE
                if L >= 2 * TILE and H >= 2 * TILE:
                    mid = (run[0] + len(run) / 2) * CS
                    if dx: c = (line * CS + dx * 5 + OX, mid + OY, h + H / 2 + OZ)
                    else:  c = (mid + OX, line * CS + dy * 5 + OY, h + H / 2 + OZ)
                    out.append(dict(type='wall', center=c, size=(L, H), yaw=yaw))
                run = [a] if a is not None else []
    return out

if __name__ == '__main__':
    D = json.load(open('jwmap_data_v2.json'))
    S = surfaces(D, 30000, -2400, 0)
    from collections import Counter
    print(Counter(s['type'] for s in S), "surfaces")
    for s in S: print(s)
