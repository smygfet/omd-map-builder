# Build a patched Level_Castle_CastlePlaza (legacy .umap/.uexp): move gameplay actors to a Map Maker layout,
# replace the NavPower navmesh, fix export sizes/offsets.
import json, math, struct, sys
import ue53pkg
SRC = sys.argv[1]; DST = sys.argv[2]; NAV = sys.argv[3]; LAYOUT = sys.argv[4]; NAVJSON = sys.argv[5]
OX, OY, OZ = 30000.0, -2400.0, 0.0
p = ue53pkg.Package(SRC + ".umap", SRC + ".uexp")
hdr = bytearray(p.h); x = bytearray(p.x)
act = json.load(open('castleplaza_actors.json')); D = json.load(open(LAYOUT))
navj = json.load(open(NAVJSON))['Sections'][0]['NavGraphs'][0]['Areas']

def floor_z(wx, wy):
    best = None
    for a in navj:
        v = [(e['Position']['X'], e['Position']['Y'], e['Position']['Z']) for e in a['Edges']]
        c = False
        for k in range(len(v)):
            x1, y1, _ = v[k]; x2, y2, _ = v[(k + 1) % len(v)]
            if (y1 > wy) != (y2 > wy) and wx < (x2 - x1) * (wy - y1) / (y2 - y1 + 1e-9) + x1: c = not c
        if c:
            z = sum(q[2] for q in v) / len(v)
            if best is None or z < best: best = z
    return best

def put(name, wx, wy, wz):
    off = act[name]['off']
    old = struct.unpack_from('<3d', x, off)
    assert all(abs(a - b) < 1e-6 for a, b in zip(old, act[name]['xyz'])), name
    struct.pack_into('<3d', x, off, wx, wy, wz)
    print("  %-36s (%.0f, %.0f, %.0f) -> (%.0f, %.0f, %.0f)" % (name, *old, wx, wy, wz))

mk = {m['k']: m for m in D['markers']}
rx, ry = mk['rift']['c'][0] + OX, mk['rift']['c'][1] + OY
sx, sy = mk['spawn']['c'][0] + OX, mk['spawn']['c'][1] + OY
st = mk.get('start', mk['rift'])['c']; px, py = st[0] + OX, st[1] + OY
fz_r = 0.0 + OZ  # rift cell floor top
print("rift"); put('BP_Rift_Platform_FishMarket_C_0', rx, ry, fz_r); put('BP_Rift_Crystal_C_0', rx, ry, fz_r + 95); put('BP_Onslaught_Castle_CastlePlaza_C_1', rx, ry, fz_r + 3000)
put('RSTPathPoint_1', rx, ry, fz_r + 150)

print("spawners")
spawners = sorted(n for n in act if n.startswith('BP_AISpawner_C_'))
for i, n in enumerate(spawners):
    dx = ((i % 5) - 2) * 60.0; dy = ((i // 5) - 1) * 60.0
    put(n, sx + dx, sy + dy, (floor_z(sx + dx, sy + dy) or 0) + 100)

print("player starts")
for i, n in enumerate(sorted(n for n in act if n.startswith('PlayerStart_'))):
    dx = (i - 1.5) * 120.0
    put(n, px + dx, py, (floor_z(px + dx, py) or 0) + 110)

print("path points")
route = [(q[0] + OX, q[1] + OY) for q in D['paths'][0]['pts']]
segs = [(route[i], route[i + 1], math.dist(route[i], route[i + 1])) for i in range(len(route) - 1)]
total = sum(s[2] for s in segs)
others = sorted((n for n in act if n.startswith('RSTPathPoint_') and n != 'RSTPathPoint_1'), key=lambda n: int(n.split('_')[-1]))
for i, n in enumerate(others):
    t = total * i / len(others)          # 0 = spawn ... just before the rift
    for a, b, L in segs:
        if t <= L or (a, b, L) == segs[-1]:
            f = min(1.0, t / L) if L else 0; wx, wy = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f; break
        t -= L
    put(n, wx, wy, (floor_z(wx, wy) or 0) + 50)

# trap grids: reuse Castle Plaza's compact (76-byte box) BP_OMDTrapGrid_Blank actors for our surfaces
import trapgrids
surf = trapgrids.surfaces(json.load(open(LAYOUT)), OX, OY, OZ)
pool = []
for g in [e for e in p.exports if p.class_name(e) == 'BP_OMDTrapGrid_Blank_C']:
    box = [e for e in p.exports if e['outer'] == g['index'] and p.class_name(e) == 'RSTTrapGridBoxComponent'][0]
    root = [e for e in p.exports if e['outer'] == g['index'] and e['name'] == 'RootComponent'][0]
    if box['size'] == 76 and root['size'] == 58:
        pool.append((g['name'], p.data(root)[0], p.data(box)[0]))
assert len(surf) <= len(pool), "not enough trap grid actors"
print("trap grids (%d surfaces, %d grids available)" % (len(surf), len(pool)))
TYPE = {'floor': 1, 'wall': 2, 'ceiling': 4}
for sfc, (gname, ro, bo) in zip(surf, pool):
    cx, cy, cz = sfc['center']; a, b = sfc['size']
    if sfc['type'] == 'floor':
        rot = (90.0, 0.0, 0.0); ext = (10.0, b / 2, a / 2)     # local Y -> world Y, local Z -> world X
    else:
        rot = (0.0, sfc['yaw'], 0.0); ext = (10.0, a / 2, b / 2)  # local X = outward normal, Y along wall, Z up
    struct.pack_into('<3d', x, ro + 2, cx, cy, cz)
    struct.pack_into('<3d', x, ro + 26, *rot)
    struct.pack_into('<3d', x, bo + 14, *ext)
    x[bo + 13] = TYPE[sfc['type']]
    print("  %-26s %-5s at (%.0f, %.0f, %.0f) %4.0f x %4.0f rot %s" % (gname, sfc['type'], cx, cy, cz, a, b, rot))

# navmesh splice
base = [e for e in p.exports if p.path(e).endswith("NavPowerNavigationData-NavPower Base")][0]
bs, bdata = p.data(base)
NAV_OFF = bs + 275
old_len = 24 + struct.unpack_from('<I', x, NAV_OFF + 8)[0]
nav = open(NAV, 'rb').read(); delta = len(nav) - old_len
x[NAV_OFF:NAV_OFF + old_len] = nav
# NavMeshBufferSize property (uint32) inside the export's property block - the game copies this many bytes
BUF_OFF = bs + 13
assert struct.unpack_from('<I', x, BUF_OFF)[0] == old_len, "NavMeshBufferSize not where expected"
struct.pack_into('<I', x, BUF_OFF, len(nav))
abs_nav = base['off']
for e in p.exports:
    tp = e['table_pos']
    size, off = struct.unpack_from('<qq', hdr, tp + 28)
    assert (size, off) == (e['size'], e['off'])
    if e is base: struct.pack_into('<q', hdr, tp + 28, size + delta)
    elif off > abs_nav: struct.pack_into('<q', hdr, tp + 36, off + delta)
bulk = struct.unpack_from('<q', hdr, 242)[0]; assert bulk == len(p.h) + len(p.x) - 4
struct.pack_into('<q', hdr, 242, bulk + delta)
open(DST + ".umap", 'wb').write(hdr); open(DST + ".uexp", 'wb').write(x)
print("navmesh %d -> %d bytes (delta %d); uexp %d -> %d" % (old_len, len(nav), delta, len(p.x), len(x)))
