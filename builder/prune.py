# Keep only navmesh areas connected to the given XY points (per graph); renumber indices and adjacency.
# prune.py in.json out.json x1 y1 [x2 y2 ...]  (a VS map passes both rifts)
import json, sys
from collections import deque
j = json.load(open(sys.argv[1]))
seeds = [(float(sys.argv[i]), float(sys.argv[i + 1])) for i in range(3, len(sys.argv) - 1, 2)]
def inside(v, x, y):
    c = False
    for k in range(len(v)):
        x1, y1 = v[k]; x2, y2 = v[(k + 1) % len(v)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1: c = not c
    return c
for g in j['Sections'][0]['NavGraphs']:
    A = g['Areas']; byidx = {a['Area']['Index']: a for a in A}
    keep = set(); q = deque()
    for px, py in seeds:
        start = None
        for a in A:
            if inside([(e['Position']['X'], e['Position']['Y']) for e in a['Edges']], px, py):
                if start is None or abs(a['Edges'][0]['Position']['Z']) < abs(byidx[start]['Edges'][0]['Position']['Z']): start = a['Area']['Index']
        assert start is not None, "seed point not on navmesh"
        if start not in keep: keep.add(start); q.append(start)
    while q:
        u = q.popleft()
        for e in byidx[u]['Edges']:
            v = e.get('Adjacent Area')
            if v and v not in keep: keep.add(v); q.append(v)
    remap = {old: new + 1 for new, old in enumerate(sorted(keep))}
    newA = []
    for old in sorted(keep):
        a = byidx[old]; a['Area']['Index'] = remap[old]
        for e in a['Edges']:
            if 'Adjacent Area' in e:
                if e['Adjacent Area'] in remap: e['Adjacent Area'] = remap[e['Adjacent Area']]
                else: del e['Adjacent Area']
        newA.append(a)
    print("kept %d of %d areas" % (len(newA), len(A)))
    g['Areas'] = newA
json.dump(j, open(sys.argv[2], 'w'))
