# v2 (plan.json from mapv2.py). Build a patched Level_Castle_CastlePlaza (legacy .umap/.uexp): move gameplay actors to a Map Maker layout,
# replace the NavPower navmesh, fix export sizes/offsets.
import json, math, os, struct, sys
import ue53pkg
SRC = sys.argv[1]; DST = sys.argv[2]; NAV = sys.argv[3]; LAYOUT = sys.argv[4]; NAVJSON = sys.argv[5]
ACTORS = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] else 'castleplaza_actors.json'   # VS base level: its own (moved) offsets
# base level config (bases.patch_config): rift/platform/rift path point per side, onslaught, spawner pairs
if len(sys.argv) > 7:
    CFG = json.load(open(sys.argv[7]))
else:                                               # old call: Castle Plaza with fixed names
    CFG = {'rifts': [{'rift': 'BP_Rift_Crystal_C_0', 'platform': 'BP_Rift_Platform_FishMarket_C_0', 'pp': 'RSTPathPoint_1', 'dz': 95},
                     {'rift': 'BP_Rift_Crystal_C_1', 'platform': 'BP_Rift_Platform_FishMarket_C_1', 'pp': 'RSTPathPoint_16', 'dz': 95}],
           'onslaught': 'BP_Onslaught_Castle_CastlePlaza_C_1',
           'spawners': [['BP_AISpawner_C_%d' % i, 'BP_AISpawner_C_%d' % (i + 14)] for i in range(14)]}
OX, OY, OZ = 30000.0, -2400.0, 0.0
p = ue53pkg.Package(SRC + ".umap", SRC + ".uexp")
hdr = bytearray(p.h); x = bytearray(p.x)
act = json.load(open(ACTORS)); D = json.load(open(LAYOUT))

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

P = json.load(open(LAYOUT))
VS = bool(P.get('vs'))
rifts = P.get('rifts') or [P['rift']]
print("rift" + ("s (VS: side A, side B)" if VS else ""))
for k, (rx, ry, rz) in enumerate(rifts):
    R = CFG['rifts'][k]
    if R.get('platform'): put(R['platform'], rx, ry, rz)
    put(R['rift'], rx, ry, rz + R['dz'])
    put(R['pp'], rx, ry, rz + 150)
rx, ry, rz = rifts[0]
put(CFG['onslaught'], rx, ry, rz + 3000)
RIFT_PPS = {R['pp'] for R in CFG['rifts'][:len(rifts)]}

print("spawners")
pairs = CFG['spawners']
S = P['spawns']
sides = P.get('spawn_sides') or [0] * len(S)
A = [sp for sp, sd in zip(S, sides) if sd == 0]
for i, (n, cp) in enumerate(pairs):
    sx, sy, sz = A[i % len(A)]; k = i // len(A)
    dx = ((k % 3) - 1) * 60.0; dy = ((k // 3) - 1) * 60.0
    put(n, sx + dx, sy + dy, sz + 100)
    if VS:                                          # its copy: the mirror image on side B
        put(cp, 2 * P['mid_x'] - (sx + dx), sy + dy, sz + 100)

print("player starts")
starts = P.get('starts') or [P['start']]
pls = sorted(n for n in act if n.startswith('PlayerStart_'))
per = len(pls) // len(starts)                                   # VS: PlayerStart_1/2 side A, 3/4 side B
for i, n in enumerate(pls):
    px, py, pz = starts[min(i // per, len(starts) - 1)]; k = i % per
    put(n, px + (k - (per - 1) / 2) * 60.0, py, pz + 110)

print("path points")
others = sorted((n for n in act if n.startswith('RSTPathPoint_') and n not in RIFT_PPS
                 and n not in {R['pp'] for R in CFG['rifts']}), key=lambda n: int(n.split('_')[-1]))
lens = [sum(math.dist(r[i], r[i + 1]) for i in range(len(r) - 1)) for r in P['routes']]
share = [max(1, round(len(others) * L / sum(lens))) for L in lens]
while sum(share) > len(others): share[share.index(max(share))] -= 1
while sum(share) < len(others): share[share.index(max(share))] += 1
it = iter(others)
for r, cnt, total in zip(P['routes'], share, lens):
    segs = [(r[i], r[i + 1], math.dist(r[i], r[i + 1])) for i in range(len(r) - 1)]
    for i in range(cnt):
        n = next(it); t = total * i / cnt          # 0 = spawn ... just before the rift
        for a, b, L in segs:
            if t <= L or (a, b, L) == segs[-1]:
                f = min(1.0, t / L) if L else 0; w = [a[q] + (b[q] - a[q]) * f for q in range(3)]; break
            t -= L
        put(n, w[0], w[1], w[2] + 50)

# path points marked as start points (bIsStartPoint, e.g. Arboretum's 3 and 5) end up on one side only: switch the flag
# off so both sides are alike (blocked orcs on the side with the start points never broke barricades)
import findloc
T = p.total_header
for e in p.exports:
    if p.class_name(e) != 'RSTPathPoint': continue
    s0 = e['off'] - T; d = bytes(x[s0:s0 + e['size']])
    he, fr = findloc.header(d)
    idx, vals = 0, []
    for skip, vn, hz in fr:                       # value indices present (zero-masked ones count, but have no bytes)
        idx += skip; vals += list(range(idx, idx + vn)); idx += vn
    # property order: 0 PathPointType (byte), 1 ReachRadius, 2 AdvanceRadius (floats), 3 bIsStartPoint, 4 bIsExitPoint
    if 3 in vals and not any(hz for _, _, hz in fr if False):
        zm = any(hz for _, _, hz in fr)
        o = he
        for v in vals:
            if v == 3: break
            if zm and v == 0: continue            # a zero-masked enum value has no bytes
            o += 1 if v in (0, 4) else 4
        if x[s0 + o] == 1:
            x[s0 + o] = 0; print("  %s: start point flag off" % e['name'])

# trap grids: reuse Castle Plaza's compact (76-byte box) BP_OMDTrapGrid_Blank actors for our surfaces
surf = P['surfaces']
pool = []
for g in [e for e in p.exports if p.class_name(e) == 'BP_OMDTrapGrid_Blank_C']:
    box = [e for e in p.exports if e['outer'] == g['index'] and p.class_name(e) == 'RSTTrapGridBoxComponent'][0]
    root = [e for e in p.exports if e['outer'] == g['index'] and e['name'] == 'RootComponent'][0]
    if box['size'] == 76 and root['size'] == 58:
        pool.append((g['name'], p.data(root)[0], p.data(box)[0]))
if len(surf) > len(pool):                         # more trap areas than the base level has trap grids: keep the biggest
    keep = sorted(range(len(surf)), key=lambda i: -surf[i]['size'][0] * surf[i]['size'][1])[:len(pool)]
    print("WARNING: %d trap areas but only %d trap grids in this base level: the %d smallest areas get no traps"
          % (len(surf), len(pool), len(surf) - len(pool)))
    surf = [surf[i] for i in sorted(keep)]
print("trap grids (%d surfaces, %d grids available)" % (len(surf), len(pool)))
TYPE = {'floor': 1, 'wall': 2, 'ceiling': 4}
for sfc, (gname, ro, bo) in zip(surf, pool):
    cx, cy, cz = sfc['center']; a, b = sfc['size']
    if sfc['type'] == 'floor':
        rot = (90.0, 0.0, 0.0); ext = (10.0, b / 2, a / 2)     # local Y -> world Y, local Z -> world X
    elif sfc['type'] == 'ceiling':
        rot = (-90.0, 0.0, 0.0); ext = (10.0, b / 2, a / 2)    # normal points down
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
import dupactors
BULK = dupactors._summary(bytes(hdr))['bulk_off']      # 242 in Castle Plaza, 238 in Colosseum
bulk = struct.unpack_from('<q', hdr, BULK)[0]; assert bulk == len(p.h) + len(p.x) - 4
struct.pack_into('<q', hdr, BULK, bulk + delta)
open(DST + ".umap", 'wb').write(hdr); open(DST + ".uexp", 'wb').write(x)
print("navmesh %d -> %d bytes (delta %d); uexp %d -> %d" % (old_len, len(nav), delta, len(p.x), len(x)))
