# Map Maker DATA boxes -> triangle soup in Unreal coords, outward-facing in Recast space. Optional world offset.
import json, math, sys
D = json.load(open(sys.argv[1])); ox, oy, oz = [float(v) for v in sys.argv[3:6]] if len(sys.argv) > 5 else (0, 0, 0)
def rot(v, pitch, yaw):
    x, y, z = v; p = math.radians(pitch); w = math.radians(yaw)
    x, z = x * math.cos(p) - z * math.sin(p), x * math.sin(p) + z * math.cos(p)   # UE pitch: nose up = +X toward +Z
    x, y = x * math.cos(w) - y * math.sin(w), x * math.sin(w) + y * math.cos(w)
    return (x, y, z)
def rc(v): return (v[0], v[2], -v[1])
faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
out = []
def emit(tri_pts, center):
    a, b2, c = tri_pts
    A, B, C, M = rc(a), rc(b2), rc(c), rc(center)
    e0 = [B[k] - A[k] for k in range(3)]; e1 = [C[k] - A[k] for k in range(3)]
    n = (e0[1] * e1[2] - e0[2] * e1[1], e0[2] * e1[0] - e0[0] * e1[2], e0[0] * e1[1] - e0[1] * e1[0])
    mid = [(A[k] + B[k] + C[k]) / 3 - M[k] for k in range(3)]
    if sum(n[k] * mid[k] for k in range(3)) < 0: b2, c = c, b2
    out.append(" ".join("%.3f" % v for v in (*a, *b2, *c)))
for b in D['boxes']:
    if b['f'] == 'Ramps':
        # Navmesh-only clean wedge: walkable top surface from low edge to high edge, no slab lip.
        cx, cy, cz = b['c']; p = math.radians(b.get('p', 0)); w = math.radians(b.get('y', 0))
        T = b['s'][2]; run = b['s'][0] * math.cos(p); half_w = b['s'][1] / 2
        mid = cz + (T / 2) / math.cos(p)
        zl, zh = mid - (run / 2) * math.tan(p), mid + (run / 2) * math.tan(p)
        dx, dy = math.cos(w), math.sin(w); px_, py_ = -dy, dx
        ext = 2.0
        def P(t, s, z): return (cx + dx * t + px_ * s + ox, cy + dy * t + py_ * s + oy, z + oz)
        lo, hi = -run / 2 - ext, run / 2 + ext
        zlo, zhi = zl - ext * math.tan(p), zh + ext * math.tan(p)
        top = [P(lo, -half_w, zlo), P(hi, -half_w, zhi), P(hi, half_w, zhi), P(lo, half_w, zlo)]
        bot = [P(lo, -half_w, zl - 5), P(hi, -half_w, zl - 5), P(hi, half_w, zl - 5), P(lo, half_w, zl - 5)]
        center = P(0, 0, (zl + zh) / 2 - 10)
        quads = [top, bot[::-1], [bot[1], bot[2], top[2], top[1]], [bot[0], top[0], top[3], bot[3]], [bot[0], bot[1], top[1], top[0]], [bot[3], top[3], top[2], bot[2]]]
        for q in quads:
            emit((q[0], q[1], q[2]), center); emit((q[0], q[2], q[3]), center)
        continue
    cx, cy, cz = b['c']; sx, sy, sz = [s / 2 for s in b['s']]
    corners = []
    for i in range(8):
        lx = sx if i & 1 else -sx; ly = sy if i & 2 else -sy; lz = sz if i & 4 else -sz
        r = rot((lx, ly, lz), b.get('p', 0), b.get('y', 0))
        corners.append((cx + r[0] + ox, cy + r[1] + oy, cz + r[2] + oz))
    center = (cx + ox, cy + oy, cz + oz)
    for f in faces:
        for tri in ((f[0], f[1], f[2]), (f[0], f[2], f[3])):
            a, b2, c = [corners[k] for k in tri]
            A, B, C, M = rc(a), rc(b2), rc(c), rc(center)
            e0 = [B[k] - A[k] for k in range(3)]; e1 = [C[k] - A[k] for k in range(3)]
            n = (e0[1] * e1[2] - e0[2] * e1[1], e0[2] * e1[0] - e0[0] * e1[2], e0[0] * e1[1] - e0[1] * e1[0])
            mid = [(A[k] + B[k] + C[k]) / 3 - M[k] for k in range(3)]
            if sum(n[k] * mid[k] for k in range(3)) < 0: b2, c = c, b2
            out.append(" ".join("%.3f" % v for v in (*a, *b2, *c)))
open(sys.argv[2], 'w').write("\n".join(out) + "\n")
print(len(out), "triangles")
